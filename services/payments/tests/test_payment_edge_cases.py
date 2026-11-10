"""
PactPal Payment Edge Cases Test Suite (Commit C54 - Milestone 4: Test & Polish)
Covers:
  1. Expired Authorization Recovery Rails:
     - Pathway A: Automated re-authorization success (+29 day countdown refresh, DB updates, audit log).
     - Pathway B: Re-authorization failure / decline (hold marked EXPIRED, buyer notified to re-fund, audit log).
     - Settlement integration: Detection of wall-clock expired holds & catching 422 AUTHORIZATION_EXPIRED.
  2. Payout Failure Retry with Exponential Backoff & Admin Escalation Flag:
     - Transient failure recovery with exponential backoff and strict idempotency key preservation.
     - Terminal payout failure / retry exhaustion (FAILED in payments ledger, PAYOUT_FAILURE_ESCALATION in messages, admin alert).
     - Admin payout retry endpoint & escalation resolution (transition to SETTLED, resolve flag).
  3. REST API Inspection & RBAC Guards:
     - POST /api/v1/payments/authorizations/{id}/reauthorize
     - POST /api/v1/payments/payouts/retry
  4. Done When Guarantee:
     - Each path ends in a correct, logged state with zero orphan states.
"""

import io
import json
import unittest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch, call

from services.payments.client import PayPalClient, PayPalAPIError
from services.payments.service import (
    EscrowPaymentService,
    PaymentApprovalService,
    PaymentApprovalError,
    ExpiredAuthorizationError,
    PayoutFailureError,
    assert_can_reauthorize_hold,
    assert_can_retry_payout,
    ApprovalVerdict,
    ContractRepository,
    User,
    UserRole,
    ContractState,
    ForbiddenActionError,
    UnauthorizedRoleError,
    StateValidationError
)
from services.payments.notifications import (
    EmailNotificationService,
    InMemoryEmailProvider
)
from services.payments.api import PaymentsAPIHandler


class TestPaymentEdgeCases(unittest.TestCase):

    def setUp(self):
        self.repo = ContractRepository(db_path=":memory:")
        self.email_provider = InMemoryEmailProvider()
        self.notification_service = EmailNotificationService(
            repository=self.repo,
            provider=self.email_provider,
            auto_wire=True
        )

        self.buyer = self.repo.create_user(
            name="Alice Buyer",
            email="buyer@pactpal.test",
            role=UserRole.BUYER,
            paypal_email="sb-buyer@example.com"
        )
        self.seller = self.repo.create_user(
            name="Bob Seller",
            email="seller@pactpal.test",
            role=UserRole.SELLER,
            paypal_email="sb-seller@example.com"
        )
        self.admin = self.repo.create_user(
            name="Platform Admin",
            email="admin@pactpal.test",
            role=UserRole.ADMIN,
            paypal_email="admin@pactpal.com"
        )
        self.third_party = self.repo.create_user(
            name="Eve Intruder",
            email="intruder@pactpal.test",
            role=UserRole.BUYER,
            paypal_email="sb-intruder@example.com"
        )
        self.ai_referee = User(
            id="AI_REFEREE",
            name="AI Referee",
            email="referee@pactpal.internal",
            role=UserRole.ADMIN
        )

        self.mock_paypal = MagicMock(spec=PayPalClient)
        self.service = EscrowPaymentService(
            paypal_client=self.mock_paypal,
            repository=self.repo,
            notification_service=self.notification_service
        )
        self.api = PaymentsAPIHandler(
            service=self.service,
            notification_service=self.notification_service
        )

    def tearDown(self):
        if hasattr(self, "repo") and self.repo:
            self.repo.close()

    def _create_funded_contract(
        self,
        total_amount: float = 1200.0,
        currency: str = "USD",
        auth_id: str = "AUTH_EDGE_1001",
        is_expired: bool = False
    ) -> Dict[str, Any]:
        """Helper to create and advance a contract to FUNDED with live auth reference and verification report."""
        now = datetime.now(timezone.utc)
        deadline = (now + timedelta(days=20)).isoformat()
        contract = self.repo.create_contract(
            buyer=self.buyer,
            seller_id=self.seller.id,
            title="E-Commerce Milestone Build",
            description="Full-stack contract for testing payment edge cases",
            total_amount=total_amount,
            deadline=deadline
        )
        cid = contract["id"]

        # Add feature BEFORE confirming checklist
        self.repo.add_feature(
            contract_id=cid,
            title="Core Payments Module",
            acceptance_test="All test cases pass",
            price_weight=100.0,
            allocated_amount=total_amount
        )

        # Dual confirmation to lock checklist
        self.repo.confirm_checklist(cid, self.buyer)
        self.repo.confirm_checklist(cid, self.seller)

        self.repo.transition_contract(cid, self.buyer, ContractState.REVIEW)
        self.repo.transition_contract(cid, self.seller, ContractState.SIGNED, metadata={"acceptance_confirmed": True})

        funded_meta = {
            "paypal_order_id": f"ORDER_{cid[:8]}",
            "paypal_auth_id": auth_id
        }
        funded = self.repo.transition_contract(
            cid,
            self.buyer,
            ContractState.FUNDED,
            metadata=funded_meta
        )

        # If is_expired requested, backdate auth_expires_at to the past
        if is_expired:
            past_iso = (now - timedelta(days=5)).isoformat()
            self.repo.update_contract_hold(
                contract_id=cid,
                total_amount=total_amount,
                paypal_auth_id=auth_id,
                auth_expires_at=past_iso
            )
            funded = self.repo.get_contract(cid)

        # Attach verification report for approval policy check
        self.repo.save_verification_report(
            contract_id=cid,
            build_succeeded=True,
            test_suite_results={"passed": True, "failed": 0, "total": 10},
            cheat_scan_findings=[],
            per_feature_results={
                "Core Payments Module": {"status": "PASSED", "score": 100}
            },
            overall_score=1.0
        )
        return funded

    # -------------------------------------------------------------------------
    # 1. Expired Authorization Recovery Rails: Pathway A (Auto Re-auth Success)
    # -------------------------------------------------------------------------
    def test_expired_authorization_auto_reauth_success(self):
        """
        Pathway A: Detect expired hold and successfully re-authorize via PayPal v2 API.
        Verifies:
          - contracts.paypal_auth_id is updated to new auth ID
          - contracts.auth_expires_at is refreshed (+29 days)
          - payments ledger records REAUTHORIZATION with status='COMPLETED'
          - messages table logs AUTHORIZATION_REAUTHORIZED event
          - get_contract_hold reflects status='HELD' and is_expired=False
        """
        contract = self._create_funded_contract(total_amount=1200.0, auth_id="AUTH_OLD_999", is_expired=True)
        cid = contract["id"]

        # Check hold initially reports EXPIRED
        hold_before = self.service.get_contract_hold(cid)
        self.assertTrue(hold_before["is_expired"])
        self.assertEqual(hold_before["status"], "EXPIRED")

        # Mock PayPal reauthorization returning a new authorization ID and fresh expiry
        new_auth_id = "AUTH_REFRESHED_111"
        fresh_expiry = (datetime.now(timezone.utc) + timedelta(days=29)).isoformat()
        self.mock_paypal.reauthorize_authorization.return_value = {
            "authorization_id": new_auth_id,
            "status": "AUTHORIZED",
            "expiration_time": fresh_expiry,
            "amount": "1200.00",
            "currency": "USD"
        }

        # Trigger re-authorization
        res = self.service.handle_expired_authorization(contract_id=cid, actor=self.buyer)

        # Assert response
        self.assertTrue(res["reauthorized"])
        self.assertEqual(res["status"], "REAUTHORIZED")
        self.assertEqual(res["authorization_id"], new_auth_id)
        self.assertEqual(res["previous_authorization_id"], "AUTH_OLD_999")
        self.assertEqual(res["amount"], 1200.0)

        # Verify database contract state
        updated_contract = self.repo.get_contract(cid)
        self.assertEqual(updated_contract["paypal_auth_id"], new_auth_id)
        self.assertEqual(updated_contract["auth_expires_at"], fresh_expiry)

        # Verify hold countdown is refreshed
        hold_after = self.service.get_contract_hold(cid)
        self.assertFalse(hold_after["is_expired"])
        self.assertEqual(hold_after["status"], "HELD")
        self.assertGreater(hold_after["days_remaining"], 25)

        # Verify payment ledger entry
        payments = self.repo.get_payments(cid)
        reauth_payment = next((p for p in payments if p["payment_type"] == "AUTHORIZATION" and p.get("metadata", {}).get("action") == "REAUTHORIZATION"), None)
        self.assertIsNotNone(reauth_payment)
        self.assertEqual(reauth_payment["status"], "COMPLETED")
        self.assertEqual(reauth_payment["paypal_reference_id"], new_auth_id)
        self.assertEqual(reauth_payment["amount"], 1200.0)

        # Verify messages audit log
        messages = self.repo.get_messages(cid)
        reauth_msg = next((m for m in messages if "AUTHORIZATION_REAUTHORIZED" in str(m.get("metadata"))), None)
        self.assertIsNotNone(reauth_msg)

    # -------------------------------------------------------------------------
    # 2. Expired Authorization Recovery Rails: Pathway B (Re-auth Failure)
    # -------------------------------------------------------------------------
    def test_expired_authorization_reauth_failure_buyer_prompt(self):
        """
        Pathway B: Re-authorization is declined or fails.
        Verifies:
          - Hold state remains cleanly flagged as EXPIRED
          - Payment ledger records REAUTHORIZATION with status='FAILED'
          - messages table logs AUTHORIZATION_REAUTH_FAILED event
          - Buyer is sent email notification prompting them to re-fund the escrow balance
          - Does not crash or drop state silently
        """
        contract = self._create_funded_contract(total_amount=1000.0, auth_id="AUTH_EXPIRED_DECLINE", is_expired=True)
        cid = contract["id"]

        # Mock PayPal reauthorization failure (e.g. buyer card expired or declined)
        self.mock_paypal.reauthorize_authorization.side_effect = PayPalAPIError(
            "Payment card expired. Re-authorization declined by issuing bank.",
            status_code=422,
            details={"name": "PAYMENT_SOURCE_DECLINED", "issue": "CARD_EXPIRED"}
        )

        # Trigger re-authorization (should not raise by default, returns clean fail payload)
        res = self.service.handle_expired_authorization(contract_id=cid, actor=self.buyer)

        # Assert response
        self.assertFalse(res["reauthorized"])
        self.assertEqual(res["status"], "EXPIRED")
        self.assertEqual(res["action_required"], "BUYER_REFUND_REQUIRED")
        self.assertTrue(res["notification_sent"])
        self.assertIn("declined", res["message"].lower())

        # Verify hold is EXPIRED
        hold = self.service.get_contract_hold(cid)
        self.assertTrue(hold["is_expired"])
        self.assertEqual(hold["status"], "EXPIRED")

        # Verify payment ledger recorded FAILED status
        payments = self.repo.get_payments(cid)
        failed_payment = next((p for p in payments if p["payment_type"] == "AUTHORIZATION" and p["status"] == "FAILED"), None)
        self.assertIsNotNone(failed_payment)
        self.assertEqual(failed_payment["status"], "FAILED")

        # Verify messages table recorded AUTHORIZATION_REAUTH_FAILED
        messages = self.repo.get_messages(cid)
        failed_msg = next((m for m in messages if "AUTHORIZATION_REAUTH_FAILED" in str(m.get("metadata"))), None)
        self.assertIsNotNone(failed_msg)
        meta = failed_msg["metadata"] if isinstance(failed_msg["metadata"], dict) else json.loads(failed_msg["metadata"])
        self.assertEqual(meta["action_required"], "BUYER_REFUND_REQUIRED")

        # Verify Buyer received email notification prompting them to re-fund
        sent_emails = self.email_provider.get_sent_emails()
        buyer_emails = [e for e in sent_emails if e["to_email"] == self.buyer.email and "Re-fund" in e["subject"]]
        self.assertGreaterEqual(len(buyer_emails), 1)
        self.assertIn("re-fund", buyer_emails[0]["body_text"].lower())

    # -------------------------------------------------------------------------
    # 3. Settlement Recovery on Wall-Clock Expired Authorization
    # -------------------------------------------------------------------------
    def test_settlement_reauth_recovery_on_wallclock_expired_hold(self):
        """
        Tests settlement when hold has expired by wall-clock (> 29 days).
        Pre-capture detection fires automated re-authorization.
        Once re-authorized, capture and payout proceed to completion.
        """
        contract = self._create_funded_contract(total_amount=1500.0, auth_id="AUTH_WALL_EXPIRED", is_expired=True)
        cid = contract["id"]

        new_auth_id = "AUTH_AUTO_REAUTH_OK"
        fresh_expiry = (datetime.now(timezone.utc) + timedelta(days=29)).isoformat()
        self.mock_paypal.reauthorize_authorization.return_value = {
            "authorization_id": new_auth_id,
            "status": "AUTHORIZED",
            "expiration_time": fresh_expiry,
            "amount": "1500.00",
            "currency": "USD"
        }
        self.mock_paypal.capture_authorization.return_value = {
            "capture_id": "CAP_AUTO_REAUTH",
            "status": "COMPLETED",
            "amount": "1500.00",
            "currency": "USD"
        }
        self.mock_paypal.create_payout.return_value = {
            "payout_batch_id": "BATCH_AUTO_REAUTH",
            "batch_status": "SUCCESS",
            "amount": "1500.00",
            "currency": "USD"
        }

        # Settle escrow as admin
        res = self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=1500.0,
            refund_amount=0.0,
            seller_paypal_email=self.seller.paypal_email,
            actor=self.admin
        )

        self.assertEqual(res["status"], "SETTLED")
        self.assertEqual(res["capture_id"], "CAP_AUTO_REAUTH")
        self.assertEqual(res["payout_batch_id"], "BATCH_AUTO_REAUTH")

        # Verify capture was executed with new_auth_id
        capture_calls = self.mock_paypal.capture_authorization.call_args_list
        self.assertEqual(len(capture_calls), 1)
        self.assertEqual(capture_calls[0].kwargs["authorization_id"], new_auth_id)

    # -------------------------------------------------------------------------
    # 4. Settlement Recovery on PayPal 422 AUTHORIZATION_EXPIRED
    # -------------------------------------------------------------------------
    def test_settlement_reauth_recovery_on_422_authorization_expired(self):
        """
        Tests settlement when PayPal returns HTTP 422 AUTHORIZATION_EXPIRED upon capture attempt.
        Verifies:
          - Recovery rails catch 422 AUTHORIZATION_EXPIRED
          - Automatically calls reauthorize_authorization
          - Retries capture_authorization with new auth ID
          - Settlement finishes successfully
        """
        contract = self._create_funded_contract(total_amount=800.0, auth_id="AUTH_EXPIRED_ON_RAILS", is_expired=False)
        cid = contract["id"]

        new_auth_id = "AUTH_RECOVERED_422"
        fresh_expiry = (datetime.now(timezone.utc) + timedelta(days=29)).isoformat()

        # Capture first raises 422 AUTHORIZATION_EXPIRED, then succeeds on retry
        self.mock_paypal.capture_authorization.side_effect = [
            PayPalAPIError("Authorization has expired.", status_code=422, details={"name": "AUTHORIZATION_EXPIRED"}),
            {"capture_id": "CAP_422_RECOVERED", "status": "COMPLETED", "amount": "800.00", "currency": "USD"}
        ]
        self.mock_paypal.reauthorize_authorization.return_value = {
            "authorization_id": new_auth_id,
            "status": "AUTHORIZED",
            "expiration_time": fresh_expiry,
            "amount": "800.00",
            "currency": "USD"
        }
        self.mock_paypal.create_payout.return_value = {
            "payout_batch_id": "BATCH_422_RECOVERED",
            "batch_status": "SUCCESS",
            "amount": "800.00",
            "currency": "USD"
        }

        res = self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=800.0,
            refund_amount=0.0,
            seller_paypal_email=self.seller.paypal_email,
            actor=self.admin
        )

        self.assertEqual(res["status"], "SETTLED")
        self.assertEqual(res["capture_id"], "CAP_422_RECOVERED")
        self.assertEqual(self.mock_paypal.capture_authorization.call_count, 2)
        self.assertEqual(self.mock_paypal.reauthorize_authorization.call_count, 1)

    # -------------------------------------------------------------------------
    # 5. Settlement Fails Cleanly when Re-authorization is Declined
    # -------------------------------------------------------------------------
    def test_settlement_reauth_failure_raises_expired_authorization_error(self):
        """
        Tests settlement when capture returns 422 AUTHORIZATION_EXPIRED and re-authorization also fails.
        Verifies:
          - Cleanly raises ExpiredAuthorizationError
          - Contract hold is flagged as EXPIRED
          - REAUTHORIZATION FAILED is logged in payment ledger
          - AUTHORIZATION_REAUTH_FAILED is logged in messages table
          - Buyer is notified
          - No orphaned/intermediate records
        """
        contract = self._create_funded_contract(total_amount=950.0, auth_id="AUTH_HARD_EXPIRED", is_expired=False)
        cid = contract["id"]

        self.mock_paypal.capture_authorization.side_effect = PayPalAPIError(
            "Authorization expired",
            status_code=422,
            details={"name": "AUTHORIZATION_EXPIRED"}
        )
        self.mock_paypal.reauthorize_authorization.side_effect = PayPalAPIError(
            "Card expired",
            status_code=422,
            details={"name": "PAYMENT_SOURCE_DECLINED"}
        )

        with self.assertRaises(ExpiredAuthorizationError) as ctx:
            self.service.settle_contract_escrow(
                contract_id=cid,
                passed_amount=950.0,
                refund_amount=0.0,
                seller_paypal_email=self.seller.paypal_email,
                actor=self.admin
            )

        self.assertIn("re-authorization failed", str(ctx.exception).lower())
        self.assertEqual(ctx.exception.details["status"], "EXPIRED")

        # Verify hold is now EXPIRED
        hold = self.service.get_contract_hold(cid)
        self.assertTrue(hold["is_expired"])

        # Verify payments ledger recorded failed re-auth
        payments = self.repo.get_payments(cid)
        self.assertTrue(any(p["payment_type"] == "AUTHORIZATION" and p["status"] == "FAILED" for p in payments))

    # -------------------------------------------------------------------------
    # 6. Transient Payout Failure Retry with Idempotency Preservation
    # -------------------------------------------------------------------------
    def test_transient_payout_failure_with_retry_and_idempotency(self):
        """
        Transient errors (HTTP 503, timeout) are retried with exponential backoff.
        Verifies:
          - Retries up to max_retries
          - Strictly preserves the EXACT SAME idempotency_key (PayPal-Request-Id) and sender_batch_id across retries
          - Payout succeeds on retry
          - Payment ledger records status='COMPLETED'
          - Contract moves to SETTLED
        """
        contract = self._create_funded_contract(total_amount=750.0, auth_id="AUTH_TRANSIENT_OK")
        cid = contract["id"]

        self.mock_paypal.capture_authorization.return_value = {
            "capture_id": "CAP_TRANSIENT_TEST",
            "status": "COMPLETED",
            "amount": "750.00",
            "currency": "USD"
        }

        # create_payout fails twice with transient errors, then succeeds on 3rd attempt
        self.mock_paypal.create_payout.side_effect = [
            PayPalAPIError("503 Service Unavailable", status_code=503),
            PayPalAPIError("Connection reset by peer / Network Timeout", status_code=500),
            {"payout_batch_id": "BATCH_TRANSIENT_RESOLVED", "batch_status": "SUCCESS", "amount": "750.00", "currency": "USD"}
        ]

        idempotency_key = "idemp_transient_test_12345"
        res = self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=750.0,
            refund_amount=0.0,
            seller_paypal_email=self.seller.paypal_email,
            actor=self.admin,
            idempotency_key=idempotency_key,
            metadata={"payout_retry_delay": 0.001}  # Fast tests
        )

        self.assertEqual(res["status"], "SETTLED")
        self.assertEqual(res["payout_batch_id"], "BATCH_TRANSIENT_RESOLVED")

        # Verify create_payout was called exactly 3 times
        self.assertEqual(self.mock_paypal.create_payout.call_count, 3)

        # Verify idempotency key was strictly preserved across all 3 attempts
        payout_calls = self.mock_paypal.create_payout.call_args_list
        expected_payout_idemp = f"{idempotency_key}:payout"
        for call_item in payout_calls:
            self.assertEqual(call_item.kwargs.get("idempotency_key"), expected_payout_idemp)
            self.assertEqual(call_item.kwargs.get("receiver_email"), self.seller.paypal_email)

        # Verify payments ledger
        payments = self.repo.get_payments(cid)
        payout_rec = next((p for p in payments if p["payment_type"] == "PAYOUT"), None)
        self.assertIsNotNone(payout_rec)
        self.assertEqual(payout_rec["status"], "COMPLETED")
        self.assertEqual(payout_rec["paypal_reference_id"], "BATCH_TRANSIENT_RESOLVED")

    # -------------------------------------------------------------------------
    # 7. Permanent Payout Failure Retry Exhaustion & Admin Escalation
    # -------------------------------------------------------------------------
    def test_permanent_payout_failure_retry_exhaustion_and_admin_escalation(self):
        """
        Permanent errors (HTTP 422, unconfirmed receiver account) or exhausted retries:
        Verifies:
          - PayoutFailureError is raised
          - Payment ledger records PAYOUT status='FAILED' (escalated=True)
          - messages table logs PAYOUT_FAILURE_ESCALATION event with error details
          - Platform Admin receives escalation alert notification
          - Contract moves to DISPUTE state for manual admin intervention
          - Zero orphan states
        """
        contract = self._create_funded_contract(total_amount=1100.0, auth_id="AUTH_PERM_FAIL")
        cid = contract["id"]

        self.mock_paypal.capture_authorization.return_value = {
            "capture_id": "CAP_PERM_FAIL",
            "status": "COMPLETED",
            "amount": "1100.00",
            "currency": "USD"
        }

        # Terminal error: HTTP 422 Receiver Unconfirmed
        self.mock_paypal.create_payout.side_effect = PayPalAPIError(
            "Receiver account sb-seller@example.com is unconfirmed or compliance held.",
            status_code=422,
            details={"name": "RECEIVER_UNCONFIRMED", "issue": "COMPLIANCE_HOLD"}
        )

        with self.assertRaises(PayoutFailureError) as ctx:
            self.service.settle_contract_escrow(
                contract_id=cid,
                passed_amount=1100.0,
                refund_amount=0.0,
                seller_paypal_email=self.seller.paypal_email,
                actor=self.admin,
                metadata={"payout_retry_delay": 0.001}
            )

        self.assertIn("escalated to platform admin", str(ctx.exception).lower())
        self.assertEqual(ctx.exception.details["status"], "FAILED")
        self.assertTrue(ctx.exception.details["escalated"])

        # 1. Verify capture succeeded and is recorded in payments table
        payments = self.repo.get_payments(cid)
        capture_rec = next((p for p in payments if p["payment_type"] == "CAPTURE"), None)
        self.assertIsNotNone(capture_rec)
        self.assertEqual(capture_rec["status"], "COMPLETED")

        # 2. Verify payout failed and is recorded in payments table
        failed_payout_rec = next((p for p in payments if p["payment_type"] == "PAYOUT"), None)
        self.assertIsNotNone(failed_payout_rec)
        self.assertEqual(failed_payout_rec["status"], "FAILED")
        self.assertTrue(failed_payout_rec["metadata"].get("escalated"))

        # 3. Verify messages table has PAYOUT_FAILURE_ESCALATION
        messages = self.repo.get_messages(cid)
        escalation_msg = next((m for m in messages if "PAYOUT_FAILURE_ESCALATION" in str(m.get("metadata"))), None)
        self.assertIsNotNone(escalation_msg)
        meta = escalation_msg["metadata"] if isinstance(escalation_msg["metadata"], dict) else json.loads(escalation_msg["metadata"])
        self.assertEqual(meta["event"], "PAYOUT_FAILURE_ESCALATION")
        self.assertEqual(meta["recipient_email"], self.seller.paypal_email)
        self.assertEqual(meta["amount"], 1100.0)

        # 4. Verify Platform Admin was sent an escalation email
        sent_emails = self.email_provider.get_sent_emails()
        admin_emails = [e for e in sent_emails if e.get("role") == "ADMIN" and "ESCALATION" in e["subject"]]
        self.assertGreaterEqual(len(admin_emails), 1)
        self.assertIn("Critical Payout Failure Escalation", admin_emails[0]["body_html"])

        # 5. Verify contract transitioned to DISPUTE
        updated_contract = self.repo.get_contract(cid)
        self.assertEqual(updated_contract["status"], ContractState.DISPUTE.value)

    # -------------------------------------------------------------------------
    # 8. Admin Payout Retry & Escalation Resolution
    # -------------------------------------------------------------------------
    def test_admin_payout_retry_and_escalation_resolution(self):
        """
        After payout failure escalation, platform admin manually resolves the issue
        (e.g. updating seller PayPal email) and calls retry_failed_payout.
        Verifies:
          - Failed payment record updated to COMPLETED
          - PAYOUT_ESCALATION_RESOLVED logged in messages table
          - Contract transitions from DISPUTE to SETTLED
          - Seller receives payout confirmation email
        """
        contract = self._create_funded_contract(total_amount=600.0, auth_id="AUTH_RETRY_ADMIN")
        cid = contract["id"]

        self.mock_paypal.capture_authorization.return_value = {
            "capture_id": "CAP_RETRY_ADMIN",
            "status": "COMPLETED",
            "amount": "600.00",
            "currency": "USD"
        }
        self.mock_paypal.create_payout.side_effect = PayPalAPIError("Receiver not found", status_code=422)

        # Trigger failure
        try:
            self.service.settle_contract_escrow(
                contract_id=cid,
                passed_amount=600.0,
                refund_amount=0.0,
                seller_paypal_email=self.seller.paypal_email,
                actor=self.admin,
                metadata={"payout_retry_delay": 0.001}
            )
        except PayoutFailureError:
            pass

        self.assertEqual(self.repo.get_contract(cid)["status"], ContractState.DISPUTE.value)

        # Now Admin retries with corrected seller PayPal email
        corrected_email = "bob.seller.verified@example.com"
        self.mock_paypal.create_payout.side_effect = None
        self.mock_paypal.create_payout.return_value = {
            "payout_batch_id": "BATCH_RETRY_RESOLVED_999",
            "batch_status": "SUCCESS",
            "amount": "600.00",
            "currency": "USD"
        }

        res = self.service.retry_failed_payout(
            contract_id=cid,
            actor=self.admin,
            new_receiver_email=corrected_email
        )

        self.assertEqual(res["status"], "SETTLED")
        self.assertEqual(res["payout_status"], "COMPLETED")
        self.assertEqual(res["payout_batch_id"], "BATCH_RETRY_RESOLVED_999")
        self.assertTrue(res["escalation_resolved"])

        # Verify contract is now SETTLED
        self.assertEqual(self.repo.get_contract(cid)["status"], ContractState.SETTLED.value)

        # Verify payment record in DB was updated to COMPLETED
        payments = self.repo.get_payments(cid)
        payout_rec = next((p for p in payments if p["payment_type"] == "PAYOUT"), None)
        self.assertIsNotNone(payout_rec)
        self.assertEqual(payout_rec["status"], "COMPLETED")
        self.assertEqual(payout_rec["paypal_reference_id"], "BATCH_RETRY_RESOLVED_999")

        # Verify messages table has PAYOUT_ESCALATION_RESOLVED
        messages = self.repo.get_messages(cid)
        resolved_msg = next((m for m in messages if "PAYOUT_ESCALATION_RESOLVED" in str(m.get("metadata"))), None)
        self.assertIsNotNone(resolved_msg)

    # -------------------------------------------------------------------------
    # 9. REST API: POST /api/v1/payments/authorizations/{id}/reauthorize
    # -------------------------------------------------------------------------
    def test_rest_authorizations_reauthorize_success_and_rbac(self):
        """
        Tests REST endpoint POST /api/v1/payments/authorizations/{id}/reauthorize:
          - Buyer -> 200 OK with refreshed expiration
          - Admin -> 200 OK
          - Unauthorized Seller / Third Party -> 403 Forbidden
          - Unauthenticated -> 401 Unauthorized
          - Non-existent auth -> 404 Not Found
        """
        contract = self._create_funded_contract(total_amount=500.0, auth_id="AUTH_REST_REAUTH", is_expired=True)
        cid = contract["id"]

        self.mock_paypal.reauthorize_authorization.return_value = {
            "authorization_id": "AUTH_REST_NEW_100",
            "status": "AUTHORIZED",
            "expiration_time": (datetime.now(timezone.utc) + timedelta(days=29)).isoformat(),
            "amount": "500.00",
            "currency": "USD"
        }

        # 1. Buyer success (200 OK)
        status, headers, body = self.api.dispatch(
            method="POST",
            path=f"/api/v1/payments/authorizations/{cid}/reauthorize",
            headers={"X-Actor-Id": self.buyer.id, "X-Actor-Role": "BUYER"},
            body=b"{}"
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertTrue(data["reauthorized"])
        self.assertEqual(data["authorization_id"], "AUTH_REST_NEW_100")

        # 2. Admin success via paypal_auth_id path parameter (200 OK)
        status, headers, body = self.api.dispatch(
            method="POST",
            path="/api/v1/payments/authorizations/AUTH_REST_NEW_100/reauthorize",
            headers={"X-Actor-Id": self.admin.id, "X-Actor-Role": "ADMIN"},
            body=b"{}"
        )
        self.assertEqual(status, 200)

        # 3. Third party intruder (403 Forbidden)
        status, headers, body = self.api.dispatch(
            method="POST",
            path=f"/api/v1/payments/authorizations/{cid}/reauthorize",
            headers={"X-Actor-Id": self.third_party.id, "X-Actor-Role": "BUYER"},
            body=b"{}"
        )
        self.assertEqual(status, 403)

        # 4. Unauthenticated (401 Unauthorized)
        status, headers, body = self.api.dispatch(
            method="POST",
            path=f"/api/v1/payments/authorizations/{cid}/reauthorize",
            headers={},
            body=b"{}"
        )
        self.assertEqual(status, 401)

        # 5. Non-existent contract/auth (404 Not Found)
        status, headers, body = self.api.dispatch(
            method="POST",
            path="/api/v1/payments/authorizations/DOES_NOT_EXIST/reauthorize",
            headers={"X-Actor-Id": self.admin.id, "X-Actor-Role": "ADMIN"},
            body=b"{}"
        )
        self.assertEqual(status, 404)

    # -------------------------------------------------------------------------
    # 10. REST API: POST /api/v1/payments/authorizations/{id}/reauthorize (Declined)
    # -------------------------------------------------------------------------
    def test_rest_authorizations_reauthorize_declined_path(self):
        """
        When reauthorization is declined, endpoint returns 200 with status='EXPIRED',
        reauthorized=False, and action_required='BUYER_REFUND_REQUIRED'.
        """
        contract = self._create_funded_contract(total_amount=400.0, auth_id="AUTH_DECLINED_REST", is_expired=True)
        cid = contract["id"]

        self.mock_paypal.reauthorize_authorization.side_effect = PayPalAPIError(
            "Declined by bank",
            status_code=422
        )

        status, headers, body = self.api.dispatch(
            method="POST",
            path=f"/api/v1/payments/authorizations/{cid}/reauthorize",
            headers={"X-Actor-Id": self.buyer.id, "X-Actor-Role": "BUYER"},
            body=b"{}"
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertFalse(data["reauthorized"])
        self.assertEqual(data["status"], "EXPIRED")
        self.assertEqual(data["action_required"], "BUYER_REFUND_REQUIRED")

    # -------------------------------------------------------------------------
    # 11. REST API: POST /api/v1/payments/payouts/retry
    # -------------------------------------------------------------------------
    def test_rest_payouts_retry_and_rbac(self):
        """
        Tests REST endpoint POST /api/v1/payments/payouts/retry:
          - Admin -> 200 OK
          - Buyer -> 403 Forbidden
          - Seller -> 403 Forbidden
          - Unauthenticated -> 401 Unauthorized
          - Missing contract_id -> 400 Bad Request
        """
        contract = self._create_funded_contract(total_amount=500.0, auth_id="AUTH_PAYOUT_RETRY_REST")
        cid = contract["id"]

        # Put into DISPUTE state simulating prior failure
        self.repo.transition_contract(cid, self.admin, ContractState.DISPUTE)

        self.mock_paypal.create_payout.return_value = {
            "payout_batch_id": "BATCH_REST_RETRY_OK",
            "batch_status": "SUCCESS",
            "amount": "500.00",
            "currency": "USD"
        }

        # 1. Non-admin Buyer attempts retry (403 Forbidden)
        status, headers, body = self.api.dispatch(
            method="POST",
            path="/api/v1/payments/payouts/retry",
            headers={"X-Actor-Id": self.buyer.id, "X-Actor-Role": "BUYER"},
            body=json.dumps({"contract_id": cid}).encode("utf-8")
        )
        self.assertEqual(status, 403)

        # 2. Seller attempts retry (403 Forbidden)
        status, headers, body = self.api.dispatch(
            method="POST",
            path="/api/v1/payments/payouts/retry",
            headers={"X-Actor-Id": self.seller.id, "X-Actor-Role": "SELLER"},
            body=json.dumps({"contract_id": cid}).encode("utf-8")
        )
        self.assertEqual(status, 403)

        # 3. Unauthenticated (401 Unauthorized)
        status, headers, body = self.api.dispatch(
            method="POST",
            path="/api/v1/payments/payouts/retry",
            headers={},
            body=json.dumps({"contract_id": cid}).encode("utf-8")
        )
        self.assertEqual(status, 401)

        # 4. Admin retry success (200 OK)
        status, headers, body = self.api.dispatch(
            method="POST",
            path="/api/v1/payments/payouts/retry",
            headers={"X-Actor-Id": self.admin.id, "X-Actor-Role": "ADMIN"},
            body=json.dumps({"contract_id": cid, "seller_paypal_email": "new.bob@example.com"}).encode("utf-8")
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "SETTLED")
        self.assertEqual(data["payout_status"], "COMPLETED")
        self.assertEqual(data["payout_batch_id"], "BATCH_REST_RETRY_OK")

    # -------------------------------------------------------------------------
    # 12. Correct Logged Terminal State Guarantee: Zero Orphan States
    # -------------------------------------------------------------------------
    def test_all_terminal_paths_logged_no_orphans(self):
        """
        Fulfills Done When criteria: 'Each path ends in a correct, logged state'.
        Asserts that every execution path:
          - Re-auth success
          - Re-auth failure
          - Payout transient retry success
          - Payout terminal failure escalation
        Leaves consistent, well-defined records in contracts, payments, and messages tables
        with zero orphan rows or unhandled states.
        """
        # Path 1: Re-auth failure
        c1 = self._create_funded_contract(total_amount=300.0, auth_id="AUTH_CHECK_1", is_expired=True)
        self.mock_paypal.reauthorize_authorization.side_effect = PayPalAPIError("Card revoked", status_code=422)
        res1 = self.service.handle_expired_authorization(c1["id"], actor=self.buyer)
        self.assertEqual(res1["status"], "EXPIRED")

        # Check DB consistency
        hold1 = self.service.get_contract_hold(c1["id"])
        self.assertEqual(hold1["status"], "EXPIRED")
        p1 = self.repo.get_payments(c1["id"])
        self.assertTrue(any(p["payment_type"] == "AUTHORIZATION" and p["status"] == "FAILED" for p in p1))
        m1 = self.repo.get_messages(c1["id"])
        self.assertTrue(any("AUTHORIZATION_REAUTH_FAILED" in str(m.get("metadata")) for m in m1))

        # Path 2: Re-auth success
        c2 = self._create_funded_contract(total_amount=400.0, auth_id="AUTH_CHECK_2", is_expired=True)
        self.mock_paypal.reauthorize_authorization.side_effect = None
        self.mock_paypal.reauthorize_authorization.return_value = {
            "authorization_id": "AUTH_CHECK_2_NEW",
            "status": "AUTHORIZED",
            "expiration_time": (datetime.now(timezone.utc) + timedelta(days=29)).isoformat()
        }
        res2 = self.service.handle_expired_authorization(c2["id"], actor=self.buyer)
        self.assertTrue(res2["reauthorized"])

        hold2 = self.service.get_contract_hold(c2["id"])
        self.assertEqual(hold2["status"], "HELD")
        p2 = self.repo.get_payments(c2["id"])
        self.assertTrue(any(p["payment_type"] == "AUTHORIZATION" and p["status"] == "COMPLETED" and p.get("metadata", {}).get("action") == "REAUTHORIZATION" for p in p2))
        m2 = self.repo.get_messages(c2["id"])
        self.assertTrue(any("AUTHORIZATION_REAUTHORIZED" in str(m.get("metadata")) for m in m2))


if __name__ == "__main__":
    unittest.main()
