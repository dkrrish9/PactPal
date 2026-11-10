"""
PactPal Automated Email Notification Test Suite
Commit C51: feat(notify): email notifications for every state change
Checklist / Done When:
  'Signed, funded, submitted, verifying, decision, payout complete all send'

Covers:
1. Pluggable email providers (InMemoryEmailProvider, SMTPEmailProvider, SendGridEmailProvider, get_email_provider factory)
2. All 6 mandatory contract state transitions:
   - SIGNED (notifies buyer & seller of signed agreement, prompts funding)
   - FUNDED (notifies seller funds are held in escrow, buyer gets 29-day countdown)
   - SUBMITTED (notifies buyer deliverable is submitted, seller gets receipt)
   - VERIFYING (notifies both parties that test execution, cheat scan, and visual diff analysis are underway)
   - DECISION (notifies both parties of AI Referee verdict and score breakdown)
   - SETTLED / PAYOUT COMPLETE (notifies seller of disbursed earnings with payout batch reference, buyer of release/refund amounts with cryptographic receipt hash link)
3. Zero hardcoding & dynamic interpolation (arbitrary currencies, non-standard prices, custom participant names)
4. Relational messages audit ledger persistence (event="EMAIL_NOTIFICATION_SENT")
5. Automatic state machine transition integration (transition_contract, confirm_and_store_authorization, settle_contract_escrow)
6. Autonomous deadline watcher sweep notifications
7. REST API endpoints (POST /api/v1/payments/notifications/dispatch, GET /api/v1/contracts/{id}/notifications)
8. RBAC security guards (assert_can_view_notifications, assert_can_dispatch_notification)
"""

import os
import json
import uuid
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from services.payments.notifications import (
    BaseEmailProvider,
    InMemoryEmailProvider,
    SMTPEmailProvider,
    SendGridEmailProvider,
    get_email_provider,
    EmailTemplateEngine,
    EmailNotificationService,
    NotificationRecipient,
    NotificationMessage
)
from services.payments.service import (
    EscrowPaymentService,
    PaymentApprovalService,
    ContractRepository,
    User,
    UserRole,
    ContractState,
    ForbiddenActionError,
    assert_can_view_notifications,
    assert_can_dispatch_notification
)
from services.payments.api import PaymentsAPIHandler
from services.payments.deadline_watcher import DeadlineWatcherService


class TestEmailNotificationProviders(unittest.TestCase):
    """Tests for pluggable email transport providers."""

    def test_in_memory_provider_send_and_filter(self):
        """InMemoryEmailProvider stores and filters sent emails without network calls."""
        provider = InMemoryEmailProvider()
        self.assertEqual(len(provider.sent_emails), 0)

        res1 = provider.send_email(
            to_email="buyer@example.com",
            subject="Test Subject 1",
            body_text="Hello Buyer",
            body_html="<p>Hello Buyer</p>",
            metadata={"contract_id": "CNT-001", "state_transition": "SIGNED"}
        )
        self.assertEqual(res1["status"], "SENT")
        self.assertEqual(res1["to_email"], "buyer@example.com")
        self.assertEqual(res1["provider"], "in_memory")
        self.assertTrue(res1["message_id"].startswith("mem_"))

        res2 = provider.send_email(
            to_email="seller@example.com",
            subject="Test Subject 2",
            body_text="Hello Seller",
            metadata={"contract_id": "CNT-001", "state_transition": "FUNDED"}
        )

        # Query all
        all_emails = provider.get_sent_emails()
        self.assertEqual(len(all_emails), 2)

        # Filter by recipient
        buyer_emails = provider.get_sent_emails(to_email="buyer@example.com")
        self.assertEqual(len(buyer_emails), 1)
        self.assertEqual(buyer_emails[0]["subject"], "Test Subject 1")

        # Filter by contract_id
        cnt_emails = provider.get_sent_emails(contract_id="CNT-001")
        self.assertEqual(len(cnt_emails), 2)

        # Filter by state
        funded_emails = provider.get_sent_emails(state="FUNDED")
        self.assertEqual(len(funded_emails), 1)
        self.assertEqual(funded_emails[0]["to_email"], "seller@example.com")

        # Clear
        provider.clear()
        self.assertEqual(len(provider.get_sent_emails()), 0)

    @patch("smtplib.SMTP")
    def test_smtp_provider_mocked(self, mock_smtp_cls):
        """SMTPEmailProvider builds valid MIME messages and executes SMTP commands over TLS."""
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        provider = SMTPEmailProvider(
            host="smtp.example.com",
            port=587,
            user="user@example.com",
            password="secretpassword",
            use_tls=True,
            from_email="escrow@pactpal.com"
        )

        res = provider.send_email(
            to_email="recipient@example.com",
            subject="Escrow Notice",
            body_text="Your payment has settled.",
            body_html="<b>Your payment has settled.</b>"
        )

        mock_smtp_cls.assert_called_with("smtp.example.com", 587, timeout=10)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user@example.com", "secretpassword")
        mock_server.sendmail.assert_called_once()
        self.assertEqual(res["status"], "SENT")
        self.assertTrue(res["message_id"].startswith("smtp_"))

    @patch("urllib.request.urlopen")
    def test_sendgrid_provider_mocked(self, mock_urlopen):
        """SendGridEmailProvider formats correct JSON payload for SendGrid v3 mail send endpoint."""
        mock_resp = MagicMock()
        mock_resp.status = 202
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        provider = SendGridEmailProvider(
            api_key="SG.fake_api_key_12345",
            from_email="no-reply@pactpal.com"
        )

        res = provider.send_email(
            to_email="dev@example.com",
            subject="Verification Complete",
            body_text="All 3 features passed.",
            body_html="<p>All 3 features passed.</p>"
        )

        self.assertEqual(res["status"], "SENT")
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.get_full_url(), "https://api.sendgrid.com/v3/mail/send")
        self.assertEqual(req.get_header("Authorization"), "Bearer SG.fake_api_key_12345")

    def test_get_email_provider_factory(self):
        """get_email_provider resolves instances according to string or environment variable."""
        mem_prov = get_email_provider("memory")
        self.assertIsInstance(mem_prov, InMemoryEmailProvider)

        mock_prov = get_email_provider("mock")
        self.assertIsInstance(mock_prov, InMemoryEmailProvider)

        smtp_prov = get_email_provider("smtp", host="mail.test.com")
        self.assertIsInstance(smtp_prov, SMTPEmailProvider)

        sg_prov = get_email_provider("sendgrid", api_key="SG.test")
        self.assertIsInstance(sg_prov, SendGridEmailProvider)

        # Default fallback
        with patch.dict(os.environ, {"EMAIL_PROVIDER": "memory"}):
            env_prov = get_email_provider()
            self.assertIsInstance(env_prov, InMemoryEmailProvider)


class TestEmailNotificationService(unittest.TestCase):
    """
    Core test suite validating that every state change milestone triggers role-tailored notifications.
    Done When: 'Signed, funded, submitted, verifying, decision, payout complete all send'
    """

    def setUp(self):
        self.repo = ContractRepository(db_path=":memory:")
        self.buyer = self.repo.create_user(
            name="Alice Buyer",
            email="alice.buyer@testescrow.com",
            role=UserRole.BUYER,
            paypal_email="alice.buyer.pp@example.com"
        )
        self.seller = self.repo.create_user(
            name="Bob Freelancer",
            email="bob.freelancer@testescrow.com",
            role=UserRole.SELLER,
            paypal_email="bob.seller.pp@example.com"
        )
        self.admin = self.repo.create_user(
            name="Platform Admin",
            email="admin@pactpal.com",
            role=UserRole.ADMIN
        )
        self.ai_referee = User(
            id="AI_REFEREE",
            name="AI Referee",
            email="referee@pactpal.internal",
            role=UserRole.ADMIN
        )
        self.stranger = self.repo.create_user(
            name="Charlie Stranger",
            email="charlie@thirdparty.com",
            role=UserRole.BUYER
        )

        self.mock_provider = InMemoryEmailProvider()
        self.notif_service = EmailNotificationService(
            repository=self.repo,
            provider=self.mock_provider,
            auto_wire=True
        )

        self.mock_paypal = MagicMock()
        self.payment_service = EscrowPaymentService(
            repository=self.repo,
            paypal_client=self.mock_paypal,
            notification_service=self.notif_service
        )
        self.api_handler = PaymentsAPIHandler(
            service=self.payment_service,
            notification_service=self.notif_service
        )

    def tearDown(self):
        if hasattr(self, "repo") and hasattr(self.repo, "conn"):
            try:
                self.repo.conn.close()
            except Exception:
                pass

    def _create_contract(self, amount: float = 1250.0, currency: str = "USD") -> str:
        """Helper creating contract with locked features."""
        contract = self.repo.create_contract(
            buyer=self.buyer,
            seller_id=self.seller.id,
            title="E-Commerce Payment Gateway",
            description="Build PayPal Express Checkout and refund engine.",
            total_amount=amount,
            deadline=(datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        )
        cid = contract["id"]
        self.repo.add_feature(cid, "Auth Hold", "Authorizes payment", 50.0, amount * 0.5, 1)
        self.repo.add_feature(cid, "Capture Disbursal", "Captures and payouts", 50.0, amount * 0.5, 2)
        self.repo.confirm_checklist(cid, self.buyer)
        self.repo.confirm_checklist(cid, self.seller)
        return cid

    # -------------------------------------------------------------------------
    # Milestone 1: SIGNED
    # -------------------------------------------------------------------------
    def test_milestone_signed_notification(self):
        """1. SIGNED: Contract signed by both parties -> notifies buyer & seller that agreement is formalized and ready for funding."""
        cid = self._create_contract(amount=1500.0, currency="USD")
        self.repo.transition_contract(cid, self.buyer, ContractState.REVIEW)

        # Clear any setup logs
        self.mock_provider.clear()

        # Seller signs contract
        self.repo.transition_contract(cid, self.seller, ContractState.SIGNED)

        sent = self.mock_provider.get_sent_emails(contract_id=cid, state="SIGNED")
        self.assertEqual(len(sent), 2, "Expected 2 emails sent on SIGNED state transition (1 to Buyer, 1 to Seller).")

        # Buyer Email
        buyer_email = next((e for e in sent if e["to_email"] == self.buyer.email), None)
        self.assertIsNotNone(buyer_email)
        self.assertIn("Contract Signed", buyer_email["subject"])
        self.assertIn("Action Required", buyer_email["subject"])
        self.assertIn(self.buyer.name, buyer_email["body_text"])
        self.assertIn(self.seller.name, buyer_email["body_text"])
        self.assertIn("1,500.00 USD", buyer_email["body_text"])
        self.assertIn("fund the escrow authorization hold", buyer_email["body_text"].lower())

        # Seller Email
        seller_email = next((e for e in sent if e["to_email"] == self.seller.email), None)
        self.assertIsNotNone(seller_email)
        self.assertIn("Contract Signed", seller_email["subject"])
        self.assertIn("Awaiting Buyer Escrow Funding", seller_email["subject"])
        self.assertIn(self.seller.name, seller_email["body_text"])
        self.assertIn(self.buyer.name, seller_email["body_text"])
        self.assertIn("1,500.00 USD", seller_email["body_text"])
        self.assertIn("wait for the escrow confirmation", seller_email["body_text"].lower())

        # Audit messages recorded
        notifs = self.repo.get_contract_notifications(cid)
        signed_notifs = [n for n in notifs if n["state_transition"] == "SIGNED"]
        self.assertEqual(len(signed_notifs), 2)

    # -------------------------------------------------------------------------
    # Milestone 2: FUNDED
    # -------------------------------------------------------------------------
    def test_milestone_funded_notification(self):
        """2. FUNDED: Escrow authorization hold created -> notifies seller that funds are secured in escrow, and notifies buyer with hold confirmation & 29-day countdown."""
        cid = self._create_contract(amount=2000.0, currency="USD")
        self.repo.transition_contract(cid, self.buyer, ContractState.REVIEW)
        self.repo.transition_contract(cid, self.seller, ContractState.SIGNED)
        self.mock_provider.clear()

        # Buyer funds escrow with PayPal authorization
        auth_expires = (datetime.now(timezone.utc) + timedelta(days=29)).isoformat()
        funding_meta = {
            "paypal_order_id": "ORDER-PP-1001",
            "paypal_auth_id": "AUTH-PP-9999",
            "auth_expires_at": auth_expires
        }
        self.repo.transition_contract(cid, self.buyer, ContractState.FUNDED, metadata=funding_meta)

        sent = self.mock_provider.get_sent_emails(contract_id=cid, state="FUNDED")
        self.assertEqual(len(sent), 2, "Expected 2 emails sent on FUNDED transition.")

        # Buyer Email: 29-day countdown and auth confirmation
        buyer_email = next((e for e in sent if e["to_email"] == self.buyer.email), None)
        self.assertIsNotNone(buyer_email)
        self.assertIn("Escrow Funded", buyer_email["subject"])
        self.assertIn("2,000.00 USD", buyer_email["subject"])
        self.assertIn("AUTH-PP-9999", buyer_email["body_text"])
        self.assertIn("29-day", buyer_email["body_text"].lower())
        self.assertIn(self.seller.name, buyer_email["body_text"])

        # Seller Email: Funds secured, start work
        seller_email = next((e for e in sent if e["to_email"] == self.seller.email), None)
        self.assertIsNotNone(seller_email)
        self.assertIn("Escrow Secured", seller_email["subject"])
        self.assertIn("Work Begins", seller_email["subject"])
        self.assertIn("AUTH-PP-9999", seller_email["body_text"])
        self.assertIn("2,000.00 USD", seller_email["body_text"])
        self.assertIn("commence development", seller_email["body_text"].lower())

    # -------------------------------------------------------------------------
    # Milestone 3: SUBMITTED
    # -------------------------------------------------------------------------
    def test_milestone_submitted_notification(self):
        """3. SUBMITTED: Deliverable submitted by seller -> notifies buyer that deliverable code is ready for automated referee inspection."""
        cid = self._create_contract(amount=1800.0, currency="USD")
        self.repo.transition_contract(cid, self.buyer, ContractState.REVIEW)
        self.repo.transition_contract(cid, self.seller, ContractState.SIGNED)
        self.repo.transition_contract(cid, self.buyer, ContractState.FUNDED, metadata={"paypal_order_id": "O1", "paypal_auth_id": "A1"})
        self.repo.transition_contract(cid, self.seller, ContractState.IN_PROGRESS)
        self.mock_provider.clear()

        # Seller submits deliverable
        sub_meta = {
            "repo_url": "https://github.com/freelancer/pactpal-client",
            "commit_sha": "a1b2c3d4e5f6",
            "submission_number": 1
        }
        self.repo.create_submission(
            contract_id=cid,
            seller_id=self.seller.id,
            repo_url=sub_meta["repo_url"],
            commit_sha=sub_meta["commit_sha"],
            submission_number=1
        )
        self.repo.transition_contract(cid, self.seller, ContractState.SUBMITTED, metadata=sub_meta)

        sent = self.mock_provider.get_sent_emails(contract_id=cid, state="SUBMITTED")
        self.assertEqual(len(sent), 2)

        # Buyer Email: Verification queued, repo details
        buyer_email = next((e for e in sent if e["to_email"] == self.buyer.email), None)
        self.assertIsNotNone(buyer_email)
        self.assertIn("Deliverable Submitted", buyer_email["subject"])
        self.assertIn("Verification Queued", buyer_email["subject"])
        self.assertIn("a1b2c3d4e5f6", buyer_email["body_text"])
        self.assertIn("https://github.com/freelancer/pactpal-client", buyer_email["body_text"])
        self.assertIn("#1", buyer_email["body_text"])

        # Seller Email: Submission confirmation
        seller_email = next((e for e in sent if e["to_email"] == self.seller.email), None)
        self.assertIsNotNone(seller_email)
        self.assertIn("Submission Confirmed", seller_email["subject"])
        self.assertIn("#1", seller_email["subject"])
        self.assertIn("a1b2c3d4e5f6", seller_email["body_text"])

    # -------------------------------------------------------------------------
    # Milestone 4: VERIFYING
    # -------------------------------------------------------------------------
    def test_milestone_verifying_notification(self):
        """4. VERIFYING: Multi-modal verification pipeline triggered -> notifies both parties that test execution, cheat scan, and visual diff analysis are underway."""
        cid = self._create_contract(amount=2500.0, currency="USD")
        self.repo.transition_contract(cid, self.buyer, ContractState.REVIEW)
        self.repo.transition_contract(cid, self.seller, ContractState.SIGNED)
        self.repo.transition_contract(cid, self.buyer, ContractState.FUNDED, metadata={"paypal_order_id": "O1", "paypal_auth_id": "A1"})
        self.repo.transition_contract(cid, self.seller, ContractState.IN_PROGRESS)
        self.repo.transition_contract(cid, self.seller, ContractState.SUBMITTED)
        self.mock_provider.clear()

        # Automated pipeline enters VERIFYING
        self.repo.transition_contract(cid, self.admin, ContractState.VERIFYING)

        sent = self.mock_provider.get_sent_emails(contract_id=cid, state="VERIFYING")
        self.assertEqual(len(sent), 2)

        for email in sent:
            self.assertIn("Verification", email["subject"])
            self.assertIn("Stage A", email["body_text"])
            self.assertIn("Stage B", email["body_text"])
            self.assertIn("Stage C", email["body_text"])
            self.assertIn("Stage D", email["body_text"])
            self.assertIn("ast cheat scan", email["body_text"].lower())

    # -------------------------------------------------------------------------
    # Milestone 5: DECISION
    # -------------------------------------------------------------------------
    def test_milestone_decision_notification(self):
        """5. DECISION: AI Referee decision generated -> notifies both parties with the verdict overview and next steps."""
        cid = self._create_contract(amount=3000.0, currency="USD")
        self.repo.transition_contract(cid, self.buyer, ContractState.REVIEW)
        self.repo.transition_contract(cid, self.seller, ContractState.SIGNED)
        self.repo.transition_contract(cid, self.buyer, ContractState.FUNDED, metadata={"paypal_order_id": "O1", "paypal_auth_id": "A1"})
        self.repo.transition_contract(cid, self.seller, ContractState.IN_PROGRESS)
        self.repo.transition_contract(cid, self.seller, ContractState.SUBMITTED)
        self.repo.transition_contract(cid, self.admin, ContractState.VERIFYING)
        self.mock_provider.clear()

        decision_meta = {
            "decision": "PASSED",
            "score": "95%",
            "overall_score": 95.0,
            "build_succeeded": True,
            "features_passed": 2,
            "features_total": 2,
            "passed_amount": 3000.0,
            "refund_amount": 0.0,
            "summary": "All acceptance tests executed and passed successfully with zero cheat findings."
        }
        self.repo.transition_contract(cid, self.admin, ContractState.DECISION, metadata=decision_meta)

        sent = self.mock_provider.get_sent_emails(contract_id=cid, state="DECISION")
        self.assertEqual(len(sent), 2)

        # Buyer Email: Verdict overview
        buyer_email = next((e for e in sent if e["to_email"] == self.buyer.email), None)
        self.assertIsNotNone(buyer_email)
        self.assertIn("AI Referee Verdict", buyer_email["subject"])
        self.assertIn("PASSED", buyer_email["subject"])
        self.assertIn("95%", buyer_email["body_text"])
        self.assertIn("3,000.00 USD", buyer_email["body_text"])
        self.assertIn("Release to Seller", buyer_email["body_text"])

        # Seller Email: Payout anticipation
        seller_email = next((e for e in sent if e["to_email"] == self.seller.email), None)
        self.assertIsNotNone(seller_email)
        self.assertIn("AI Referee Verdict", seller_email["subject"])
        self.assertIn("PASSED", seller_email["subject"])
        self.assertIn("Disbursed Earnings", seller_email["body_text"])
        self.assertIn("3,000.00 USD", seller_email["body_text"])

    # -------------------------------------------------------------------------
    # Milestone 6: SETTLED / PAYOUT COMPLETE
    # -------------------------------------------------------------------------
    def test_milestone_settled_payout_complete_notification(self):
        """6. SETTLED / PAYOUT COMPLETE: Escrow capture & payout executed -> notifies seller of disbursed earnings with payout batch reference, and notifies buyer of release/refund amounts with cryptographic receipt hash link."""
        cid = self._create_contract(amount=1000.0, currency="USD")
        self.repo.transition_contract(cid, self.buyer, ContractState.REVIEW)
        self.repo.transition_contract(cid, self.seller, ContractState.SIGNED)
        self.repo.transition_contract(cid, self.buyer, ContractState.FUNDED, metadata={"paypal_order_id": "O1", "paypal_auth_id": "A1"})

        self.mock_paypal.capture_authorization.return_value = {"capture_id": "CAP-PP-1111"}
        self.mock_paypal.create_payout.return_value = {"payout_batch_id": "BATCH-PP-2222"}
        self.mock_paypal.void_authorization.return_value = {"status": "VOIDED"}

        self.mock_provider.clear()

        # Save report
        self.repo.save_verification_report(
            contract_id=cid,
            build_succeeded=True,
            test_suite_results={"passed": 2, "failed": 0, "total": 2, "status": "PASSED"}
        )

        # Execute settlement via payment service
        settle_res = self.payment_service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=750.0,
            refund_amount=250.0,
            seller_paypal_email=self.seller.paypal_email,
            actor=self.admin,
            metadata={"admin_override": True}
        )

        self.assertEqual(settle_res["status"], "SETTLED")

        sent = self.mock_provider.get_sent_emails(contract_id=cid, state="SETTLED")
        self.assertEqual(len(sent), 2, "Expected 2 emails sent on SETTLED state transition.")

        # Buyer Email: Released amount, refund amount, and receipt hash link
        buyer_email = next((e for e in sent if e["to_email"] == self.buyer.email), None)
        self.assertIsNotNone(buyer_email)
        self.assertIn("Escrow Settlement Completed", buyer_email["subject"])
        self.assertIn("750.00 USD", buyer_email["body_text"])
        self.assertIn("250.00 USD", buyer_email["body_text"])
        self.assertIn(settle_res["receipt_hash"], buyer_email["body_text"])
        self.assertIn(f"/api/v1/contracts/{cid}/receipt", buyer_email["body_text"])

        # Seller Email: Disbursed earnings and payout batch reference
        seller_email = next((e for e in sent if e["to_email"] == self.seller.email), None)
        self.assertIsNotNone(seller_email)
        self.assertIn("Payout Disbursed", seller_email["subject"])
        self.assertIn("750.00 USD", seller_email["subject"])
        self.assertIn(settle_res["receipt_hash"], seller_email["body_text"])
        self.assertIn("750.00 USD", seller_email["body_text"])
        self.assertIn("pactpal_payout_", seller_email["body_text"])

    def test_payout_complete_alias_handling(self):
        """PAYOUT_COMPLETE is recognized as canonical SETTLED milestone."""
        cid = self._create_contract(amount=800.0, currency="EUR")
        self.mock_provider.clear()

        dispatched = self.notif_service.notify_state_change(
            contract_id=cid,
            new_state="PAYOUT_COMPLETE",
            metadata={
                "passed_amount": 800.0,
                "refund_amount": 0.0,
                "payout_batch_reference": "BATCH-EUR-88",
                "receipt_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            },
            force=True
        )
        self.assertEqual(len(dispatched), 2)
        self.assertEqual(dispatched[0]["state_transition"], "SETTLED")

    # -------------------------------------------------------------------------
    # Zero Hardcoding & Dynamic Interpolation
    # -------------------------------------------------------------------------
    def test_dynamic_interpolation_zero_hardcoding(self):
        """Verifies completely custom participant names, currencies, and amounts are interpolated dynamically."""
        custom_buyer = self.repo.create_user(
            name="Dr. Evelyn Wright",
            email="evelyn.wright@fintechlabs.io",
            role=UserRole.BUYER
        )
        custom_seller = self.repo.create_user(
            name="Liam O'Connor",
            email="liam.dev@dublincode.ie",
            role=UserRole.SELLER,
            paypal_email="liam.paypal@dublincode.ie"
        )
        contract = self.repo.create_contract(
            buyer=custom_buyer,
            seller_id=custom_seller.id,
            title="Custom Smart Contract Oracle",
            description="Build decentralized price feed bridge.",
            total_amount=4875.25,
            deadline="2027-01-15T12:00:00Z"
        )
        cid = contract["id"]
        # Update currency to GBP
        self.repo.conn.execute("UPDATE contracts SET currency = 'GBP' WHERE id = ?", (cid,))
        self.repo.conn.commit()

        self.mock_provider.clear()

        # Trigger FUNDED
        self.notif_service.notify_state_change(
            contract_id=cid,
            new_state="FUNDED",
            metadata={
                "paypal_auth_id": "AUTH-GBP-UK-4875",
                "auth_expires_at": "2027-02-13T12:00:00Z"
            },
            force=True
        )

        sent = self.mock_provider.get_sent_emails(contract_id=cid)
        self.assertEqual(len(sent), 2)

        buyer_mail = next(e for e in sent if e["to_email"] == "evelyn.wright@fintechlabs.io")
        self.assertIn("Dr. Evelyn Wright", buyer_mail["body_text"])
        self.assertIn("Liam O'Connor", buyer_mail["body_text"])
        self.assertIn("4,875.25 GBP", buyer_mail["body_text"])
        self.assertIn("AUTH-GBP-UK-4875", buyer_mail["body_text"])

        seller_mail = next(e for e in sent if e["to_email"] == "liam.dev@dublincode.ie")
        self.assertIn("Liam O'Connor", seller_mail["body_text"])
        self.assertIn("Dr. Evelyn Wright", seller_mail["body_text"])
        self.assertIn("4,875.25 GBP", seller_mail["body_text"])

    # -------------------------------------------------------------------------
    # Audit Logging in Messages Table
    # -------------------------------------------------------------------------
    def test_relational_messages_audit_ledger(self):
        """Every sent notification creates an immutable event in the relational messages table."""
        cid = self._create_contract(amount=1000.0)
        self.mock_provider.clear()

        self.notif_service.notify_state_change(
            contract_id=cid,
            new_state="SIGNED",
            force=True
        )

        cursor = self.repo.conn.cursor()
        cursor.execute("""
            SELECT * FROM messages
            WHERE contract_id = ? AND metadata LIKE '%EMAIL_NOTIFICATION_SENT%'
            ORDER BY sent_at ASC
        """, (cid,))
        rows = [dict(r) for r in cursor.fetchall()]
        self.assertEqual(len(rows), 2)

        meta0 = json.loads(rows[0]["metadata"])
        self.assertEqual(meta0["event"], "EMAIL_NOTIFICATION_SENT")
        self.assertEqual(meta0["state_transition"], "SIGNED")
        self.assertIn(meta0["role"], ("BUYER", "SELLER"))
        self.assertEqual(meta0["delivery_status"], "SENT")
        self.assertEqual(meta0["provider"], "in_memory")

    # -------------------------------------------------------------------------
    # Autonomous Deadline Watcher Sweep Notifications
    # -------------------------------------------------------------------------
    def test_deadline_watcher_sweep_triggers_email_notifications(self):
        """Autonomous scheduled sweep of expired contract triggers SETTLED notifications without manual help."""
        cid = self._create_contract(amount=1000.0)
        self.repo.transition_contract(cid, self.buyer, ContractState.REVIEW)
        self.repo.transition_contract(cid, self.seller, ContractState.SIGNED)
        self.repo.transition_contract(cid, self.buyer, ContractState.FUNDED, metadata={"paypal_order_id": "O_EXP", "paypal_auth_id": "A_EXP"})

        # Set contract deadline to yesterday
        past_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        self.repo.conn.execute("UPDATE contracts SET deadline = ?, status = 'IN_PROGRESS' WHERE id = ?", (past_time, cid))
        self.repo.conn.commit()

        # Zero submission abandonment -> 100% refund
        self.mock_paypal.void_authorization.return_value = {"status": "VOIDED"}
        self.mock_provider.clear()

        watcher = DeadlineWatcherService(
            repository=self.repo,
            payment_service=self.payment_service
        )
        sweep_res = watcher.sweep_expired_deadlines()
        self.assertEqual(len(sweep_res), 1)
        self.assertEqual(sweep_res[0]["rule_applied"], "FULL_REFUND_ABANDONMENT_NO_SUBMISSION")

        # Check notifications were fired
        sent = self.mock_provider.get_sent_emails(contract_id=cid, state="SETTLED")
        self.assertEqual(len(sent), 2)
        buyer_mail = next(e for e in sent if e["to_email"] == self.buyer.email)
        self.assertIn("1,000.00 USD", buyer_mail["body_text"])
        self.assertIn("Escrow Settlement Completed", buyer_mail["subject"])

    # -------------------------------------------------------------------------
    # REST API Endpoints Tests
    # -------------------------------------------------------------------------
    def test_api_dispatch_notification_200_ok(self):
        """POST /api/v1/payments/notifications/dispatch returns 200 with delivery summary."""
        cid = self._create_contract(amount=1000.0)
        self.mock_provider.clear()

        payload = json.dumps({
            "contract_id": cid,
            "state": "SIGNED"
        }).encode("utf-8")
        headers = {"X-Actor-Id": self.buyer.id}

        status, _, body = self.api_handler.dispatch("POST", "/api/v1/payments/notifications/dispatch", headers, payload)
        self.assertEqual(status, 200)

        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["contract_id"], cid)
        self.assertEqual(data["state"], "SIGNED")
        self.assertEqual(data["notifications_sent"], 2)
        self.assertEqual(len(data["dispatched"]), 2)

    def test_api_get_contract_notifications_200_ok(self):
        """GET /api/v1/contracts/{id}/notifications returns full audit history."""
        cid = self._create_contract(amount=1000.0)
        self.notif_service.notify_state_change(cid, "SIGNED", force=True)
        self.notif_service.notify_state_change(cid, "FUNDED", force=True)

        headers = {"X-Actor-Id": self.seller.id}
        status, _, body = self.api_handler.dispatch("GET", f"/api/v1/contracts/{cid}/notifications", headers)
        self.assertEqual(status, 200)

        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["contract_id"], cid)
        self.assertEqual(data["total_notifications"], 4)
        self.assertEqual(len(data["notifications"]), 4)

    def test_api_nested_contract_notifications_post_dispatch_200(self):
        """POST /api/v1/contracts/{id}/notifications/dispatch nested route returns 200."""
        cid = self._create_contract(amount=1000.0)
        payload = json.dumps({"state": "SUBMITTED"}).encode("utf-8")
        headers = {"X-Actor-Id": self.seller.id}

        status, _, body = self.api_handler.dispatch("POST", f"/api/v1/contracts/{cid}/notifications/dispatch", headers, payload)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["state"], "SUBMITTED")
        self.assertEqual(data["notifications_sent"], 2)

    def test_api_dispatch_notification_400_missing_fields(self):
        """POST /api/v1/payments/notifications/dispatch returns 400 when contract_id or state is missing."""
        headers = {"X-Actor-Id": self.buyer.id}

        # Missing state
        payload1 = json.dumps({"contract_id": "test"}).encode("utf-8")
        s1, _, b1 = self.api_handler.dispatch("POST", "/api/v1/payments/notifications/dispatch", headers, payload1)
        self.assertEqual(s1, 400)
        self.assertEqual(json.loads(b1)["error"], "BAD_REQUEST")

        # Missing contract_id
        payload2 = json.dumps({"state": "SIGNED"}).encode("utf-8")
        s2, _, b2 = self.api_handler.dispatch("POST", "/api/v1/payments/notifications/dispatch", headers, payload2)
        self.assertEqual(s2, 400)

    def test_api_dispatch_notification_401_unauthorized(self):
        """POST /api/v1/payments/notifications/dispatch returns 401 when auth header is missing."""
        cid = self._create_contract(amount=1000.0)
        payload = json.dumps({"contract_id": cid, "state": "SIGNED"}).encode("utf-8")
        status, _, b = self.api_handler.dispatch("POST", "/api/v1/payments/notifications/dispatch", {}, payload)
        self.assertEqual(status, 401)
        self.assertEqual(json.loads(b)["error"], "UNAUTHORIZED")

    def test_api_dispatch_notification_403_forbidden_for_stranger(self):
        """POST /api/v1/payments/notifications/dispatch returns 403 when an unrelated actor attempts dispatch."""
        cid = self._create_contract(amount=1000.0)
        payload = json.dumps({"contract_id": cid, "state": "SIGNED"}).encode("utf-8")
        headers = {"X-Actor-Id": self.stranger.id}

        status, _, b = self.api_handler.dispatch("POST", "/api/v1/payments/notifications/dispatch", headers, payload)
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(b)["error"], "FORBIDDEN")

    def test_api_dispatch_notification_404_contract_not_found(self):
        """POST /api/v1/payments/notifications/dispatch returns 404 when contract does not exist."""
        payload = json.dumps({"contract_id": "non-existent-contract-9999", "state": "SIGNED"}).encode("utf-8")
        headers = {"X-Actor-Id": self.buyer.id}

        status, _, b = self.api_handler.dispatch("POST", "/api/v1/payments/notifications/dispatch", headers, payload)
        self.assertEqual(status, 404)
        self.assertEqual(json.loads(b)["error"], "NOT_FOUND")

    def test_api_get_notifications_403_for_stranger(self):
        """GET /api/v1/contracts/{id}/notifications returns 403 when unrelated actor attempts inspection."""
        cid = self._create_contract(amount=1000.0)
        headers = {"X-Actor-Id": self.stranger.id}

        status, _, b = self.api_handler.dispatch("GET", f"/api/v1/contracts/{cid}/notifications", headers)
        self.assertEqual(status, 403)

    def test_api_notifications_405_method_not_allowed(self):
        """Returns 405 when invalid HTTP methods are used."""
        cid = self._create_contract(amount=1000.0)
        headers = {"X-Actor-Id": self.buyer.id}

        # GET on /dispatch
        status1, _, _ = self.api_handler.dispatch("GET", "/api/v1/payments/notifications/dispatch", headers)
        self.assertEqual(status1, 405)

        # DELETE on /notifications
        status2, _, _ = self.api_handler.dispatch("DELETE", f"/api/v1/contracts/{cid}/notifications", headers)
        self.assertEqual(status2, 405)

    # -------------------------------------------------------------------------
    # RBAC Guard Unit Tests
    # -------------------------------------------------------------------------
    def test_rbac_assert_can_view_and_dispatch_guards(self):
        """RBAC guards permit Buyer, Seller, Platform Admin, and AI Referee, while rejecting strangers."""
        cid = self._create_contract(amount=1000.0)
        contract = self.repo.get_contract(cid)

        # Allowed actors
        assert_can_view_notifications(self.buyer, contract)
        assert_can_view_notifications(self.seller, contract)
        assert_can_view_notifications(self.admin, contract)
        assert_can_view_notifications(self.ai_referee, contract)

        assert_can_dispatch_notification(self.buyer, contract)
        assert_can_dispatch_notification(self.seller, contract)
        assert_can_dispatch_notification(self.admin, contract)
        assert_can_dispatch_notification(self.ai_referee, contract)

        # Forbidden actor
        with self.assertRaises(ForbiddenActionError):
            assert_can_view_notifications(self.stranger, contract)

        with self.assertRaises(ForbiddenActionError):
            assert_can_dispatch_notification(self.stranger, contract)


if __name__ == "__main__":
    unittest.main()
