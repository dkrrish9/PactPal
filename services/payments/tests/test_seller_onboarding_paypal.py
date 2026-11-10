"""
Unit and Integration Tests for Seller Onboarding & PayPal Email Capture (Commit C09d).

Milestone: M1 (Sign & Fund)
Task: C09d
Branch: feature/payments
Commit Message: feat(pay): capture seller PayPal email at onboarding
Done When / Acceptance Criteria:
  "Seller can't be paid out without a saved PayPal email"

Verifies:
  1. Onboarding saves verified PayPal email into user repository and sets role to SELLER.
  2. Input validation: invalid or empty email addresses are strictly rejected with ValueError.
  3. RBAC: users can onboard/update their own email, Platform Admin / AI Referee can onboard any seller,
     unauthorized third parties are rejected with ForbiddenActionError (HTTP 403).
  4. Core Done When Guard: settle_contract_escrow strictly blocks payouts when seller has no saved PayPal email.
  5. Pre-flight approval policy check fails with SELLER_PAYPAL_EMAIL_SAVED when seller email is missing.
  6. Automatic resolution: once seller onboards, settlement automatically uses saved email from DB.
  7. 100% Buyer abandonment refunds ($0 passed) are not blocked by a missing seller PayPal email.
  8. Payout retry automatically persists newly provided receiver email to seller profile in repository.
  9. REST API routes for onboarding, updating email, and querying payout eligibility.
  10. REST API settle returns HTTP 422 with structured MissingSellerPayPalEmailError payload.
  11. Email notifications sent to seller upon successful onboarding.
"""

import json
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

from services.payments.client import PayPalClient, PayPalAPIError
from services.payments.service import (
    EscrowPaymentService,
    ContractRepository,
    User,
    UserRole,
    ContractState,
    ForbiddenActionError,
    PaymentApprovalError,
    MissingSellerPayPalEmailError,
)
from services.payments.notifications import EmailNotificationService, InMemoryEmailProvider
from services.payments.api import PaymentsAPIHandler, create_payments_app


class TestSellerOnboardingPayPal(unittest.TestCase):

    def setUp(self):
        self.repo = ContractRepository(db_path=":memory:")
        self.email_provider = InMemoryEmailProvider()
        self.notification_service = EmailNotificationService(
            repository=self.repo,
            provider=self.email_provider
        )
        self.mock_paypal = MagicMock(spec=PayPalClient)
        self.service = EscrowPaymentService(
            repository=self.repo,
            paypal_client=self.mock_paypal,
            notification_service=self.notification_service
        )
        self.api_handler = PaymentsAPIHandler(
            service=self.service,
            notification_service=self.notification_service
        )

        # Users
        self.buyer = self.repo.create_user(
            name="Alice Buyer",
            email="alice@buyer.test",
            role=UserRole.BUYER,
            paypal_email="sb-alice@business.example.com"
        )
        # Seller initially without saved PayPal email (simulates newly signed up user prior to C09d onboarding)
        self.seller = self.repo.create_user(
            name="Bob Freelancer",
            email="bob@seller.test",
            role=UserRole.SELLER,
            paypal_email=None
        )
        self.admin = self.repo.create_user(
            name="Platform Admin",
            email="admin@pactpal.test",
            role=UserRole.ADMIN
        )
        self.stranger = self.repo.create_user(
            name="Charlie Stranger",
            email="charlie@stranger.test",
            role=UserRole.BUYER
        )

    def tearDown(self):
        if hasattr(self.repo, "close"):
            self.repo.close()
        elif hasattr(self.repo, "conn") and self.repo.conn:
            self.repo.conn.close()

    def _create_funded_contract(self, amount: float = 1000.0, seller: Optional[User] = None) -> str:
        """Helper to create a contract transition to FUNDED state with dual confirmation."""
        target_seller = seller or self.seller
        contract = self.repo.create_contract(
            buyer=self.buyer,
            seller_id=target_seller.id,
            title="E-Commerce Website",
            description="Build modern e-commerce site",
            total_amount=amount,
            deadline=(datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        )
        cid = contract["id"]

        # Add feature checklist items
        self.repo.add_feature(
            contract_id=cid,
            title="Catalog Page",
            acceptance_test="Catalog renders products",
            price_weight=60.0,
            allocated_amount=amount * 0.60
        )
        self.repo.add_feature(
            contract_id=cid,
            title="Checkout Cart",
            acceptance_test="Checkout accepts card",
            price_weight=40.0,
            allocated_amount=amount * 0.40
        )

        # Dual confirmation & checklist lock
        self.repo.transition_contract(cid, self.buyer, ContractState.REVIEW)
        self.repo.transition_contract(cid, target_seller, ContractState.SIGNED, metadata={"acceptance_confirmed": True})
        self.repo.confirm_checklist(cid, self.buyer)
        self.repo.confirm_checklist(cid, target_seller)

        # Fund escrow
        self.repo.transition_contract(
            cid,
            self.buyer,
            ContractState.FUNDED,
            metadata={"paypal_order_id": f"ORD_{cid[:8]}", "paypal_auth_id": f"AUTH_{cid[:8]}"}
        )
        return cid

    # =========================================================================
    # 1. Onboarding & Repository Tests
    # =========================================================================

    def test_onboard_seller_saves_paypal_email_and_sets_role(self):
        """Onboarding captures verified PayPal email and transitions user role to SELLER."""
        user = self.repo.create_user(
            name="Dev David",
            email="david@example.com",
            role=UserRole.BUYER,  # Initial default role upon first Google sign-in
            paypal_email=None
        )
        self.assertIsNone(user.paypal_email)
        self.assertEqual(user.role, UserRole.BUYER)

        res = self.service.onboard_seller(
            user_id=user.id,
            paypal_email="David.Dev@Sandbox.PayPal.com",
            actor=user
        )

        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(res["role"], "SELLER")
        self.assertEqual(res["paypal_email"], "david.dev@sandbox.paypal.com")
        self.assertTrue(res["payout_eligible"])

        # Verify DB persistence
        fresh_user = self.repo.get_user(user.id)
        self.assertEqual(fresh_user.role, UserRole.SELLER)
        self.assertEqual(fresh_user.paypal_email, "david.dev@sandbox.paypal.com")

    def test_onboard_seller_invalid_email_format_rejected(self):
        """Invalid or empty PayPal email addresses are rejected with ValueError."""
        invalid_emails = [
            "",
            "   ",
            "not-an-email",
            "missing-domain@",
            "@missing-user.com",
            "spaces in@email.com",
            12345
        ]
        for inv in invalid_emails:
            with self.subTest(invalid_email=inv):
                with self.assertRaises(ValueError):
                    self.service.onboard_seller(
                        user_id=self.seller.id,
                        paypal_email=inv,  # type: ignore
                        actor=self.seller
                    )

    def test_onboard_seller_rbac(self):
        """User can onboard themselves; admin can onboard anyone; stranger is rejected."""
        # Self-onboard
        res = self.service.onboard_seller(
            user_id=self.seller.id,
            paypal_email="bob.freelancer@paypal.test",
            actor=self.seller
        )
        self.assertEqual(res["status"], "SUCCESS")

        # Admin update
        res_admin = self.service.onboard_seller(
            user_id=self.seller.id,
            paypal_email="bob.updated.by.admin@paypal.test",
            actor=self.admin
        )
        self.assertEqual(res_admin["paypal_email"], "bob.updated.by.admin@paypal.test")

        # Stranger forbidden
        with self.assertRaises(ForbiddenActionError):
            self.service.onboard_seller(
                user_id=self.seller.id,
                paypal_email="hacker@paypal.test",
                actor=self.stranger
            )

    def test_update_seller_paypal_email(self):
        """Seller can update their saved PayPal email address."""
        # First onboard
        self.service.onboard_seller(
            user_id=self.seller.id,
            paypal_email="initial@paypal.test",
            actor=self.seller
        )
        # Update
        res = self.service.update_seller_paypal_email(
            user_id=self.seller.id,
            paypal_email="new.payout.email@paypal.test",
            actor=self.seller
        )
        self.assertEqual(res["paypal_email"], "new.payout.email@paypal.test")
        self.assertEqual(self.repo.get_user(self.seller.id).paypal_email, "new.payout.email@paypal.test")

    def test_get_seller_payout_eligibility_and_privacy_masking(self):
        """Queries seller payout eligibility and enforces email privacy masking for third parties."""
        # Before saving PayPal email: ONBOARDING_REQUIRED
        elig_before = self.service.get_seller_payout_eligibility(self.seller.id, actor=self.seller)
        self.assertFalse(elig_before["has_saved_paypal_email"])
        self.assertFalse(elig_before["payout_eligible"])
        self.assertEqual(elig_before["status"], "ONBOARDING_REQUIRED")

        # Onboard seller
        self.service.onboard_seller(self.seller.id, "robert.freelancer@gmail.com", actor=self.seller)

        # Self inspection: full email visible
        elig_self = self.service.get_seller_payout_eligibility(self.seller.id, actor=self.seller)
        self.assertTrue(elig_self["payout_eligible"])
        self.assertEqual(elig_self["paypal_email"], "robert.freelancer@gmail.com")

        # Admin inspection: full email visible
        elig_admin = self.service.get_seller_payout_eligibility(self.seller.id, actor=self.admin)
        self.assertEqual(elig_admin["paypal_email"], "robert.freelancer@gmail.com")

        # Stranger inspection: masked email for privacy (e.g. ro***@gmail.com)
        elig_stranger = self.service.get_seller_payout_eligibility(self.seller.id, actor=self.stranger)
        self.assertTrue(elig_stranger["payout_eligible"])
        self.assertIn("***@", elig_stranger["paypal_email"])
        self.assertNotEqual(elig_stranger["paypal_email"], "robert.freelancer@gmail.com")

    # =========================================================================
    # 2. Core Done When Acceptance Criteria Tests
    # =========================================================================

    def test_seller_cannot_be_paid_out_without_saved_paypal_email(self):
        """
        CRITICAL ACCEPTANCE CRITERIA:
        'Seller can't be paid out without a saved PayPal email'
        Attempts to settle with passed_amount > 0 when seller has no saved PayPal email must fail.
        """
        cid = self._create_funded_contract(amount=1000.0)

        # Set up mock verification report so verification check passes
        self.repo.save_verification_report(
            contract_id=cid,
            build_succeeded=True,
            test_suite_results={"passed": True, "tests_run": 10},
            cheat_scan_findings=[],
            per_feature_results={
                "f1": {"status": "PASSED", "allocated_amount": 600.0, "price_weight": 60.0},
                "f2": {"status": "PASSED", "allocated_amount": 400.0, "price_weight": 40.0}
            },
            overall_score=1.0
        )

        # Seller has no saved paypal_email in DB
        self.assertIsNone(self.repo.get_user(self.seller.id).paypal_email)

        # 1. Attempt settlement without passing seller_paypal_email
        with self.assertRaises(MissingSellerPayPalEmailError) as ctx:
            self.service.settle_contract_escrow(
                contract_id=cid,
                passed_amount=1000.0,
                refund_amount=0.0,
                actor=self.admin
            )
        self.assertIn("cannot be paid out", str(ctx.exception).lower())
        self.assertIn("saved paypal email", str(ctx.exception).lower())

        # Verify NO PayPal capture or payout was fired
        self.mock_paypal.capture_authorization.assert_not_called()
        self.mock_paypal.create_payout.assert_not_called()

        # Verify contract is NOT in SETTLED state
        contract_record = self.repo.get_contract(cid)
        self.assertNotEqual(contract_record["status"], ContractState.SETTLED.value)

    def test_seller_can_be_paid_out_after_onboarding_with_saved_paypal_email(self):
        """
        After completing onboarding to save a PayPal email, settlement succeeds automatically
        without requiring caller to supply seller_paypal_email in method arguments.
        """
        cid = self._create_funded_contract(amount=1000.0)

        # Verification report passing
        self.repo.save_verification_report(
            contract_id=cid,
            build_succeeded=True,
            test_suite_results={"passed": True, "tests_run": 10},
            cheat_scan_findings=[],
            per_feature_results={
                "f1": {"status": "PASSED", "allocated_amount": 600.0, "price_weight": 60.0},
                "f2": {"status": "PASSED", "allocated_amount": 400.0, "price_weight": 40.0}
            },
            overall_score=1.0
        )

        # Seller completes onboarding
        self.service.onboard_seller(
            user_id=self.seller.id,
            paypal_email="bob.verified.freelancer@example.com",
            actor=self.seller
        )

        # Mock PayPal APIs
        self.mock_paypal.capture_authorization.return_value = {
            "capture_id": "CAP_AUTO_SAVED_123",
            "status": "COMPLETED",
            "amount": {"value": "1000.00", "currency_code": "USD"}
        }
        self.mock_paypal.create_payout.return_value = {
            "payout_batch_id": "BATCH_AUTO_SAVED_999",
            "batch_status": "SUCCESS"
        }

        # Settle without supplying seller_paypal_email explicitly
        settle_res = self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=1000.0,
            refund_amount=0.0,
            actor=self.admin
        )

        self.assertEqual(settle_res["status"], "SETTLED")
        self.assertEqual(settle_res["passed_amount"], 1000.0)
        self.assertEqual(settle_res.get("seller_summary", {}).get("seller_paypal_email"), "bob.verified.freelancer@example.com")

        # Verify payout was disbursed to the saved PayPal email
        self.mock_paypal.create_payout.assert_called_once()
        call_kwargs = self.mock_paypal.create_payout.call_args.kwargs
        self.assertEqual(call_kwargs["receiver_email"], "bob.verified.freelancer@example.com")
        self.assertEqual(call_kwargs["amount"], 1000.0)

    def test_approval_check_blocks_settlement_when_seller_paypal_email_missing(self):
        """PaymentApprovalService.validate_payment_approval reports SELLER_PAYPAL_EMAIL_SAVED failure if unsaved."""
        cid = self._create_funded_contract(amount=1000.0)

        # Check approval before onboarding
        verdict = self.service.approval_service.validate_payment_approval(
            contract_id=cid,
            action="SETTLE_ESCROW",
            actor=self.admin,
            metadata={"passed_amount": 1000.0, "refund_amount": 0.0}
        )
        self.assertFalse(verdict.approved)
        self.assertIn("SELLER_PAYPAL_EMAIL_SAVED", verdict.checks_failed)

        # Onboard seller
        self.service.onboard_seller(self.seller.id, "freelancer@sandbox.test", actor=self.seller)

        # Check approval after onboarding
        verdict_after = self.service.approval_service.validate_payment_approval(
            contract_id=cid,
            action="SETTLE_ESCROW",
            actor=self.admin,
            metadata={"passed_amount": 1000.0, "refund_amount": 0.0}
        )
        self.assertIn("SELLER_PAYPAL_EMAIL_SAVED", verdict_after.checks_passed)

    def test_zero_passed_abandonment_refund_allowed_even_if_seller_paypal_email_missing(self):
        """100% Buyer abandonment refund ($0 seller payout) is allowed even if seller has not saved PayPal email."""
        cid = self._create_funded_contract(amount=1000.0)

        # Mock void
        self.mock_paypal.void_authorization.return_value = {
            "authorization_id": f"AUTH_{cid[:8]}",
            "status": "VOIDED"
        }

        # 0.0 passed, 1000.0 refund
        settle_res = self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=0.0,
            refund_amount=1000.0,
            actor=self.admin,
            metadata={"deadline_expired": True}
        )
        self.assertEqual(settle_res["status"], "SETTLED")
        self.assertEqual(settle_res["refund_amount"], 1000.0)
        self.assertEqual(settle_res["passed_amount"], 0.0)

        # Payout should not be attempted
        self.mock_paypal.create_payout.assert_not_called()

    def test_admin_retry_payout_with_new_email_saves_to_seller_profile(self):
        """When Admin retries a failed payout with a new email, it updates and saves to the seller's user record."""
        cid = self._create_funded_contract(amount=1000.0)

        # First onboard seller with wrong email
        self.service.onboard_seller(self.seller.id, "bad.email@example.com", actor=self.seller)

        # Simulate failed payout entry in payments table
        self.repo.record_payment(
            contract_id=cid,
            payment_type="PAYOUT",
            paypal_reference_id="FAILED_BATCH_1",
            amount=1000.0,
            status="FAILED",
            metadata={"recipient_email": "bad.email@example.com", "escalated": True}
        )

        self.mock_paypal.create_payout.return_value = {
            "payout_batch_id": "RETRY_BATCH_SUCCESS",
            "batch_status": "SUCCESS"
        }

        retry_res = self.service.retry_failed_payout(
            contract_id=cid,
            actor=self.admin,
            new_receiver_email="corrected.freelancer@example.com"
        )
        self.assertEqual(retry_res["payout_status"], "COMPLETED")

        # Verify seller record in DB was updated with the new email
        updated_seller = self.repo.get_user(self.seller.id)
        self.assertEqual(updated_seller.paypal_email, "corrected.freelancer@example.com")

    # =========================================================================
    # 3. REST API & HTTP Handler Tests
    # =========================================================================

    def test_rest_api_seller_onboard_success(self):
        """POST /api/v1/payments/seller/onboard saves PayPal email and returns 200 OK."""
        status_code, headers, body_bytes = self.api_handler.dispatch(
            method="POST",
            path="/api/v1/payments/seller/onboard",
            headers={"X-Actor-Id": self.seller.id, "Content-Type": "application/json"},
            body=json.dumps({"paypal_email": "rest.seller@sandbox.test"}).encode("utf-8")
        )
        self.assertEqual(status_code, 200)
        payload = json.loads(body_bytes.decode("utf-8"))
        self.assertEqual(payload["status"], "SUCCESS")
        self.assertEqual(payload["role"], "SELLER")
        self.assertEqual(payload["paypal_email"], "rest.seller@sandbox.test")
        self.assertTrue(payload["payout_eligible"])

    def test_rest_api_seller_onboard_unauthenticated_and_rbac(self):
        """POST /api/v1/payments/seller/onboard rejects unauthenticated (401) and unauthorized stranger (403)."""
        # Unauthenticated without user_id
        status_code, _, _ = self.api_handler.dispatch(
            method="POST",
            path="/api/v1/payments/seller/onboard",
            body=json.dumps({"paypal_email": "rest.seller@sandbox.test"}).encode("utf-8")
        )
        self.assertEqual(status_code, 401)

        # Stranger attempting to onboard another user
        status_code_forbid, _, _ = self.api_handler.dispatch(
            method="POST",
            path="/api/v1/payments/seller/onboard",
            headers={"X-Actor-Id": self.stranger.id, "Content-Type": "application/json"},
            body=json.dumps({"user_id": self.seller.id, "paypal_email": "hacker@test.com"}).encode("utf-8")
        )
        self.assertEqual(status_code_forbid, 403)

    def test_rest_api_update_seller_paypal_email(self):
        """PUT /api/v1/payments/seller/{id}/paypal-email updates email and returns 200 OK."""
        # Onboard first
        self.service.onboard_seller(self.seller.id, "old.email@test.com", actor=self.seller)

        status_code, _, body_bytes = self.api_handler.dispatch(
            method="PUT",
            path=f"/api/v1/payments/seller/{self.seller.id}/paypal-email",
            headers={"X-Actor-Id": self.seller.id, "Content-Type": "application/json"},
            body=json.dumps({"paypal_email": "new.updated.email@test.com"}).encode("utf-8")
        )
        self.assertEqual(status_code, 200)
        payload = json.loads(body_bytes.decode("utf-8"))
        self.assertEqual(payload["paypal_email"], "new.updated.email@test.com")

    def test_rest_api_get_seller_payout_eligibility(self):
        """GET /api/v1/payments/seller/{id}/payout-eligibility returns eligibility status."""
        # Before onboarding
        status_code, _, body_bytes = self.api_handler.dispatch(
            method="GET",
            path=f"/api/v1/payments/seller/{self.seller.id}/payout-eligibility",
            headers={"X-Actor-Id": self.seller.id}
        )
        self.assertEqual(status_code, 200)
        payload = json.loads(body_bytes.decode("utf-8"))
        self.assertFalse(payload["payout_eligible"])
        self.assertEqual(payload["status"], "ONBOARDING_REQUIRED")

        # After onboarding
        self.service.onboard_seller(self.seller.id, "eligible.bob@test.com", actor=self.seller)
        status_code2, _, body_bytes2 = self.api_handler.dispatch(
            method="GET",
            path=f"/api/v1/payments/seller/{self.seller.id}/payout-eligibility",
            headers={"X-Actor-Id": self.seller.id}
        )
        self.assertEqual(status_code2, 200)
        payload2 = json.loads(body_bytes2.decode("utf-8"))
        self.assertTrue(payload2["payout_eligible"])
        self.assertEqual(payload2["status"], "ELIGIBLE")

    def test_rest_api_settle_blocked_when_seller_paypal_email_missing(self):
        """POST /api/v1/payments/settle returns HTTP 422 with MissingSellerPayPalEmailError when seller email is unsaved."""
        cid = self._create_funded_contract(amount=1000.0)

        # Verification report passing
        self.repo.save_verification_report(
            contract_id=cid,
            build_succeeded=True,
            test_suite_results={"passed": True, "tests_run": 10},
            cheat_scan_findings=[],
            per_feature_results={
                "f1": {"status": "PASSED", "allocated_amount": 600.0, "price_weight": 60.0},
                "f2": {"status": "PASSED", "allocated_amount": 400.0, "price_weight": 40.0}
            },
            overall_score=1.0
        )

        status_code, _, body_bytes = self.api_handler.dispatch(
            method="POST",
            path="/api/v1/payments/settle",
            headers={"X-Actor-Id": self.admin.id, "Content-Type": "application/json"},
            body=json.dumps({
                "contract_id": cid,
                "passed_amount": 1000.0,
                "refund_amount": 0.0
            }).encode("utf-8")
        )
        self.assertEqual(status_code, 422)
        payload = json.loads(body_bytes.decode("utf-8"))
        self.assertEqual(payload["error"], "MissingSellerPayPalEmailError")
        self.assertTrue(payload["payout_blocked"])
        self.assertEqual(payload["action_required"], "SELLER_ONBOARDING_REQUIRED")

    # =========================================================================
    # 4. Email Notification Tests
    # =========================================================================

    def test_notification_dispatched_on_seller_onboarding(self):
        """Onboarding triggers a confirmation email to the seller confirming saved payout rails."""
        self.email_provider.clear()

        self.service.onboard_seller(
            user_id=self.seller.id,
            paypal_email="freelancer.verified@paypal.test",
            actor=self.seller
        )

        sent_emails = self.email_provider.get_sent_emails()
        self.assertEqual(len(sent_emails), 1)
        onboard_email = sent_emails[0]
        self.assertEqual(onboard_email["to_email"], self.seller.email)
        self.assertIn("Payout Rails Connected", onboard_email["subject"])
        self.assertIn("freelancer.verified@paypal.test", onboard_email["body_html"])


if __name__ == "__main__":
    unittest.main()
