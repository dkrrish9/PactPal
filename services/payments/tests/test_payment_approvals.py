"""
Unit & Integration Tests for Automated Payment Approval Checks (Commit C31)
Milestone 2: Verify & Decide

Validates:
1. Approval granted when all criteria are met (hold creation, settlement with verified report).
2. Settlement blocked when checklist is unlocked (is_locked=False).
3. Settlement blocked when verification report is missing (without admin override).
4. Settlement blocked when cheat scan has unresolved high-severity flags.
5. Settlement allowed without verification report when explicit platform ADMIN dispute resolution override is attached.
6. Settlement blocked when amounts mismatch verified feature weights/scores.
7. Settlement blocked when deliverable build failed and positive seller payout is requested.
8. Approval check REST API endpoint POST /api/v1/payments/approval-check (200 approved, 200 blocked with reasons, 400, 401, 403, 404).
9. Contract approval GET /api/v1/contracts/{id}/payment-approval.
10. Interception: No payment action fires without passing the approval check (PayPal calls prevented).
11. Audit logging into immutable messages compliance table for every check.
"""

import json
import unittest
from unittest.mock import MagicMock
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from services.payments.client import PayPalClient
from services.payments.service import (
    EscrowPaymentService,
    PaymentApprovalService,
    PaymentApprovalError,
    ApprovalVerdict,
    ContractRepository,
    User,
    UserRole,
    ContractState,
    ForbiddenActionError,
    StateValidationError
)
from services.payments.api import PaymentsAPIHandler


class TestPaymentApprovals(unittest.TestCase):

    def setUp(self):
        self.repo = ContractRepository(db_path=":memory:")
        self.buyer = self.repo.create_user(
            name="Alice Buyer",
            email="buyer@pactpal.test",
            role=UserRole.BUYER,
            paypal_email="sb-buyer@example.com"
        )
        self.seller = self.repo.create_user(
            name="Bob Freelancer",
            email="seller@pactpal.test",
            role=UserRole.SELLER,
            paypal_email="sb-seller@example.com"
        )
        self.admin = self.repo.create_user(
            name="Platform Admin",
            email="admin@pactpal.test",
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
            email="stranger@pactpal.test",
            role=UserRole.BUYER
        )

        self.mock_paypal = MagicMock(spec=PayPalClient)
        self.service = EscrowPaymentService(repository=self.repo, paypal_client=self.mock_paypal)
        self.approval_service = self.service.approval_service
        self.api_handler = PaymentsAPIHandler(service=self.service)

    def tearDown(self):
        self.repo.close()

    def _create_contract(self, amount: float = 1000.0, lock: bool = True) -> str:
        """Helper to create a contract, add features, and transition to SIGNED."""
        contract = self.repo.create_contract(
            buyer=self.buyer,
            seller_id=self.seller.id,
            title="Fullstack Escrow Milestone",
            description="Verified milestone deliverable",
            total_amount=amount,
            deadline=(datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        )
        cid = contract["id"]

        # Add features
        self.repo.add_feature(cid, "Feature 1", "Unit tests pass", 60.0, amount * 0.6, sort_order=0)
        self.repo.add_feature(cid, "Feature 2", "UI matches Figma", 40.0, amount * 0.4, sort_order=1)

        # Dual confirmation to lock checklist
        if lock:
            self.repo.confirm_checklist(cid, self.buyer)
            self.repo.confirm_checklist(cid, self.seller)

        self.repo.transition_contract(cid, self.buyer, ContractState.REVIEW)
        self.repo.transition_contract(cid, self.seller, ContractState.SIGNED, metadata={"acceptance_confirmed": True})
        return cid

    def _create_funded_contract(self, amount: float = 1000.0, lock: bool = True, auth_id: str = "AUTH_PP_TEST_999") -> str:
        """Helper to create a contract and advance it to FUNDED with PayPal auth ID."""
        cid = self._create_contract(amount=amount, lock=lock)
        self.repo.transition_contract(
            cid,
            self.buyer,
            ContractState.FUNDED,
            metadata={"paypal_order_id": f"ORD_{cid[:8]}", "paypal_auth_id": auth_id}
        )
        return cid

    # -------------------------------------------------------------------------
    # 1. Hold Creation Approval Tests
    # -------------------------------------------------------------------------
    def test_hold_creation_approved_when_all_criteria_met(self):
        """Approval is granted for CREATE_HOLD when checklist is locked and actor is buyer."""
        cid = self._create_contract(amount=1000.0, lock=True)

        verdict = self.approval_service.validate_payment_approval(
            contract_id=cid,
            action="CREATE_HOLD",
            actor=self.buyer
        )

        self.assertTrue(verdict.approved)
        self.assertIn("CHECKLIST_LOCKED", verdict.checks_passed)
        self.assertIn("ROLE_AUTHORIZED", verdict.checks_passed)
        self.assertIn("STATE_MACHINE_CONSISTENT", verdict.checks_passed)
        self.assertEqual(len(verdict.checks_failed), 0)
        self.assertIn("All policy criteria met.", verdict.reasons)

    def test_hold_creation_blocked_when_checklist_unlocked(self):
        """CREATE_HOLD is BLOCKED if contract checklist is not dual-confirmed and locked."""
        cid = self._create_contract(amount=1000.0, lock=False)

        # 1. Policy check directly
        verdict = self.approval_service.validate_payment_approval(
            contract_id=cid,
            action="CREATE_HOLD",
            actor=self.buyer
        )
        self.assertFalse(verdict.approved)
        self.assertIn("CHECKLIST_LOCKED", verdict.checks_failed)
        self.assertTrue(any("not locked" in r for r in verdict.reasons))

        # 2. Intercepted execution check: initiate_contract_hold raises PaymentApprovalError
        with self.assertRaises(PaymentApprovalError) as ctx:
            self.service.initiate_contract_hold(cid, self.buyer)
        self.assertIn("CHECKLIST_LOCKED", ctx.exception.verdict.checks_failed)

        # Verify PayPal API was NEVER called
        self.mock_paypal.create_authorize_order.assert_not_called()

    def test_hold_creation_blocked_for_unauthorized_role(self):
        """Only assigned buyer can initiate hold; seller or stranger are rejected."""
        cid = self._create_contract(amount=1000.0, lock=True)

        # Stranger
        with self.assertRaises(ForbiddenActionError):
            self.service.initiate_contract_hold(cid, self.stranger)

        # Direct policy check with stranger
        verdict = self.approval_service.validate_payment_approval(
            contract_id=cid,
            action="CREATE_HOLD",
            actor=self.stranger
        )
        self.assertFalse(verdict.approved)
        self.assertIn("ROLE_AUTHORIZED", verdict.checks_failed)

    # -------------------------------------------------------------------------
    # 2. Pre-Settlement Approval Tests (Checklist, Reports, Cheats, Overrides)
    # -------------------------------------------------------------------------
    def test_settlement_approved_with_verified_report_and_matching_amounts(self):
        """Settlement is approved when checklist is locked, verified report exists, and amounts match."""
        cid = self._create_funded_contract(amount=1000.0, lock=True)
        features = self.repo.get_features(cid)
        f1_id = features[0]["id"]
        f2_id = features[1]["id"]

        # Save verification report where Feature 1 passed ($600) and Feature 2 failed ($400)
        self.repo.save_verification_report(
            contract_id=cid,
            build_succeeded=True,
            test_suite_results={"passed": True, "tests_run": 10},
            cheat_scan_findings=[],
            per_feature_results={
                f1_id: {"feature_id": f1_id, "status": "PASSED", "allocated_amount": 600.0, "price_weight": 60.0},
                f2_id: {"feature_id": f2_id, "status": "FAILED", "allocated_amount": 400.0, "price_weight": 40.0}
            },
            overall_score=0.6
        )

        verdict = self.approval_service.validate_payment_approval(
            contract_id=cid,
            action="SETTLE_ESCROW",
            actor=self.ai_referee,
            metadata={"passed_amount": 600.0, "refund_amount": 400.0}
        )

        self.assertTrue(verdict.approved)
        self.assertIn("CHECKLIST_LOCKED", verdict.checks_passed)
        self.assertIn("VERIFICATION_REPORT_EXISTS", verdict.checks_passed)
        self.assertIn("CHEAT_SCAN_CLEARED", verdict.checks_passed)
        self.assertIn("AMOUNT_ALIGNMENT", verdict.checks_passed)
        self.assertIn("AMOUNT_INVARIANT", verdict.checks_passed)

    def test_settlement_blocked_when_checklist_unlocked(self):
        """Settlement is BLOCKED if checklist was never dual-confirmed/locked."""
        cid = self._create_funded_contract(amount=1000.0, lock=False)

        # Save valid report
        self.repo.save_verification_report(
            contract_id=cid,
            build_succeeded=True,
            cheat_scan_findings=[]
        )

        # Check verdict
        verdict = self.approval_service.validate_payment_approval(
            contract_id=cid,
            action="SETTLE_ESCROW",
            actor=self.ai_referee,
            metadata={"passed_amount": 1000.0, "refund_amount": 0.0}
        )
        self.assertFalse(verdict.approved)
        self.assertIn("CHECKLIST_LOCKED", verdict.checks_failed)

        # Intercepted service call fails
        with self.assertRaises(PaymentApprovalError) as ctx:
            self.service.settle_contract_escrow(
                contract_id=cid,
                passed_amount=1000.0,
                refund_amount=0.0,
                seller_paypal_email=self.seller.paypal_email,
                actor=self.ai_referee
            )
        self.assertIn("CHECKLIST_LOCKED", ctx.exception.verdict.checks_failed)
        self.mock_paypal.capture_authorization.assert_not_called()

    def test_settlement_blocked_when_verification_report_missing_without_admin_override(self):
        """Settlement is BLOCKED if no verification report exists and no ADMIN override is attached."""
        cid = self._create_funded_contract(amount=1000.0, lock=True)
        # Note: No verification report saved in repo

        # 1. AI Referee attempt without override -> Blocked
        verdict = self.approval_service.validate_payment_approval(
            contract_id=cid,
            action="SETTLE_ESCROW",
            actor=self.ai_referee,
            metadata={"passed_amount": 1000.0, "refund_amount": 0.0}
        )
        self.assertFalse(verdict.approved)
        self.assertIn("VERIFICATION_REPORT_EXISTS", verdict.checks_failed)

        # Service interception raises error
        with self.assertRaises(PaymentApprovalError):
            self.service.settle_contract_escrow(
                contract_id=cid,
                passed_amount=1000.0,
                refund_amount=0.0,
                seller_paypal_email=self.seller.paypal_email,
                actor=self.ai_referee
            )

        # 2. Admin attempt without explicit override -> Blocked
        verdict_admin = self.approval_service.validate_payment_approval(
            contract_id=cid,
            action="SETTLE_ESCROW",
            actor=self.admin,
            metadata={"passed_amount": 1000.0, "refund_amount": 0.0}
        )
        self.assertFalse(verdict_admin.approved)
        self.assertIn("VERIFICATION_REPORT_EXISTS", verdict_admin.checks_failed)

    def test_settlement_allowed_without_report_when_admin_override_attached(self):
        """Platform ADMIN can attach an explicit dispute override to settle without verification report."""
        cid = self._create_funded_contract(amount=1000.0, lock=True)
        # No verification report

        self.mock_paypal.capture_authorization.return_value = {"capture_id": "CAP_ADMIN_99", "status": "COMPLETED"}
        self.mock_paypal.create_payout.return_value = {"payout_batch_id": "BATCH_ADMIN_99", "status": "PENDING"}

        verdict = self.approval_service.validate_payment_approval(
            contract_id=cid,
            action="SETTLE_ESCROW",
            actor=self.admin,
            metadata={"passed_amount": 1000.0, "refund_amount": 0.0, "admin_override": True}
        )
        self.assertTrue(verdict.approved)
        self.assertIn("ADMIN_OVERRIDE", verdict.checks_passed)

        # Execute via service with override
        res = self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=1000.0,
            refund_amount=0.0,
            seller_paypal_email=self.seller.paypal_email,
            actor=self.admin,
            metadata={"admin_override": True}
        )
        self.assertEqual(res["status"], "SETTLED")
        self.assertEqual(res["capture_id"], "CAP_ADMIN_99")

    def test_settlement_blocked_when_cheat_scan_has_high_severity_flags(self):
        """Settlement is BLOCKED if verification report contains unresolved high-severity cheat findings."""
        cid = self._create_funded_contract(amount=1000.0, lock=True)

        self.repo.save_verification_report(
            contract_id=cid,
            build_succeeded=True,
            cheat_scan_findings=[
                {"title": "Hardcoded Mock Data Detected", "severity": "HIGH", "file": "src/api.js", "line": 42},
                {"title": "Placeholder comments", "severity": "LOW", "file": "src/style.css"}
            ],
            per_feature_results={},
            overall_score=0.9
        )

        verdict = self.approval_service.validate_payment_approval(
            contract_id=cid,
            action="SETTLE_ESCROW",
            actor=self.ai_referee,
            metadata={"passed_amount": 1000.0, "refund_amount": 0.0}
        )

        self.assertFalse(verdict.approved)
        self.assertIn("CHEAT_SCAN_CLEARED", verdict.checks_failed)
        self.assertTrue(any("Hardcoded Mock Data Detected" in r for r in verdict.reasons))

        with self.assertRaises(PaymentApprovalError):
            self.service.settle_contract_escrow(
                contract_id=cid,
                passed_amount=1000.0,
                refund_amount=0.0,
                seller_paypal_email=self.seller.paypal_email,
                actor=self.ai_referee
            )
        self.mock_paypal.capture_authorization.assert_not_called()

    def test_cheat_scan_high_severity_overridden_by_admin(self):
        """High-severity cheat findings can be resolved/overridden by Platform ADMIN during dispute."""
        cid = self._create_funded_contract(amount=1000.0, lock=True)

        self.repo.save_verification_report(
            contract_id=cid,
            build_succeeded=True,
            cheat_scan_findings=[
                {"title": "Exposed testing API key", "severity": "HIGH"}
            ]
        )

        verdict = self.approval_service.validate_payment_approval(
            contract_id=cid,
            action="SETTLE_ESCROW",
            actor=self.admin,
            metadata={"passed_amount": 500.0, "refund_amount": 500.0, "admin_override": True}
        )
        self.assertTrue(verdict.approved)
        self.assertIn("ADMIN_OVERRIDE", verdict.checks_passed)

    def test_settlement_blocked_when_amounts_mismatch_verified_features(self):
        """Settlement is BLOCKED if requested passed_amount does not match verified feature results."""
        cid = self._create_funded_contract(amount=1000.0, lock=True)
        features = self.repo.get_features(cid)
        f1_id = features[0]["id"]
        f2_id = features[1]["id"]

        # Feature 1 passed ($600), Feature 2 failed ($400)
        self.repo.save_verification_report(
            contract_id=cid,
            build_succeeded=True,
            per_feature_results={
                f1_id: {"feature_id": f1_id, "status": "PASSED", "allocated_amount": 600.0},
                f2_id: {"feature_id": f2_id, "status": "FAILED", "allocated_amount": 400.0}
            }
        )

        # AI Referee attempts to pass $900 instead of $600
        verdict = self.approval_service.validate_payment_approval(
            contract_id=cid,
            action="SETTLE_ESCROW",
            actor=self.ai_referee,
            metadata={"passed_amount": 900.0, "refund_amount": 100.0}
        )
        self.assertFalse(verdict.approved)
        self.assertIn("AMOUNT_ALIGNMENT", verdict.checks_failed)
        self.assertTrue(any("does not match verified feature results" in r for r in verdict.reasons))

    def test_settlement_blocked_when_build_failed_and_payout_requested(self):
        """Cannot release payout to seller if deliverable failed Stage B build."""
        cid = self._create_funded_contract(amount=1000.0, lock=True)

        self.repo.save_verification_report(
            contract_id=cid,
            build_succeeded=False,
            build_logs="SyntaxError: Unexpected token",
            test_suite_results={"status": "SKIPPED"},
            cheat_scan_findings=[]
        )

        verdict = self.approval_service.validate_payment_approval(
            contract_id=cid,
            action="SETTLE_ESCROW",
            actor=self.ai_referee,
            metadata={"passed_amount": 800.0, "refund_amount": 200.0}
        )
        self.assertFalse(verdict.approved)
        self.assertIn("BUILD_SUCCEEDED", verdict.checks_failed)

    # -------------------------------------------------------------------------
    # 3. REST API Endpoint Tests (POST /api/v1/payments/approval-check)
    # -------------------------------------------------------------------------
    def test_api_approval_check_endpoint_approved_200(self):
        """POST /api/v1/payments/approval-check returns 200 with approved=True when valid."""
        cid = self._create_contract(amount=1000.0, lock=True)

        payload = json.dumps({
            "contract_id": cid,
            "action": "CREATE_HOLD"
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "X-Actor-Id": self.buyer.id
        }

        status, resp_headers, body = self.api_handler.dispatch("POST", "/api/v1/payments/approval-check", headers, payload)
        self.assertEqual(status, 200)

        data = json.loads(body.decode("utf-8"))
        self.assertTrue(data["approved"])
        self.assertEqual(data["contract_id"], cid)
        self.assertEqual(data["action"], "CREATE_HOLD")
        self.assertIn("CHECKLIST_LOCKED", data["checks_passed"])
        self.assertEqual(len(data["checks_failed"]), 0)

    def test_api_approval_check_endpoint_blocked_with_reasons_200(self):
        """POST /api/v1/payments/approval-check returns 200 with approved=False and detailed reasons when blocked."""
        cid = self._create_contract(amount=1000.0, lock=False)  # Unlocked

        payload = json.dumps({
            "contract_id": cid,
            "action": "CREATE_HOLD"
        }).encode("utf-8")

        headers = {"X-Actor-Id": self.buyer.id}

        status, _, body = self.api_handler.dispatch("POST", "/api/v1/payments/approval-check", headers, payload)
        self.assertEqual(status, 200)

        data = json.loads(body.decode("utf-8"))
        self.assertFalse(data["approved"])
        self.assertIn("CHECKLIST_LOCKED", data["checks_failed"])
        self.assertTrue(len(data["reasons"]) > 0)

    def test_api_approval_check_400_bad_request(self):
        """Returns 400 when contract_id or action is missing or invalid."""
        headers = {"X-Actor-Id": self.buyer.id}

        # Missing contract_id
        payload1 = json.dumps({"action": "CREATE_HOLD"}).encode("utf-8")
        status1, _, body1 = self.api_handler.dispatch("POST", "/api/v1/payments/approval-check", headers, payload1)
        self.assertEqual(status1, 400)
        self.assertEqual(json.loads(body1)["error"], "BAD_REQUEST")

        # Invalid action
        payload2 = json.dumps({"contract_id": "test", "action": "INVALID_ACTION"}).encode("utf-8")
        status2, _, body2 = self.api_handler.dispatch("POST", "/api/v1/payments/approval-check", headers, payload2)
        self.assertEqual(status2, 400)
        self.assertEqual(json.loads(body2)["error"], "BAD_REQUEST")

    def test_api_approval_check_401_unauthorized(self):
        """Returns 401 when authentication header is missing."""
        payload = json.dumps({"contract_id": "any", "action": "CREATE_HOLD"}).encode("utf-8")
        status, _, body = self.api_handler.dispatch("POST", "/api/v1/payments/approval-check", {}, payload)
        self.assertEqual(status, 401)
        self.assertEqual(json.loads(body)["error"], "UNAUTHORIZED")

    def test_api_approval_check_403_forbidden(self):
        """Returns 403 when user role is not authorized for the requested action."""
        cid = self._create_contract(amount=1000.0, lock=True)

        # Buyer trying to check settlement action
        payload = json.dumps({"contract_id": cid, "action": "SETTLE_ESCROW"}).encode("utf-8")
        headers = {"X-Actor-Id": self.buyer.id}
        status, _, body = self.api_handler.dispatch("POST", "/api/v1/payments/approval-check", headers, payload)
        self.assertEqual(status, 403)
        self.assertEqual(json.loads(body)["error"], "FORBIDDEN")

    def test_api_approval_check_404_not_found(self):
        """Returns 404 when contract_id does not exist."""
        payload = json.dumps({"contract_id": "non_existent_contract", "action": "CREATE_HOLD"}).encode("utf-8")
        headers = {"X-Actor-Id": self.buyer.id}
        status, _, body = self.api_handler.dispatch("POST", "/api/v1/payments/approval-check", headers, payload)
        self.assertEqual(status, 404)
        self.assertEqual(json.loads(body)["error"], "NOT_FOUND")

    def test_api_get_contract_payment_approval(self):
        """GET /api/v1/contracts/{id}/payment-approval returns approval status."""
        cid = self._create_contract(amount=1000.0, lock=True)
        headers = {"X-Actor-Id": self.buyer.id}

        status, _, body = self.api_handler.dispatch("GET", f"/api/v1/contracts/{cid}/payment-approval", headers)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertTrue(data["approved"])
        self.assertEqual(data["action"], "CREATE_HOLD")

    def test_api_intercepts_payment_action_and_returns_403(self):
        """API endpoints return 403 PAYMENT_APPROVAL_BLOCKED when approval check fails."""
        cid = self._create_contract(amount=1000.0, lock=False)  # Unlocked

        # POST /api/v1/payments/orders/create-hold
        create_payload = json.dumps({"contract_id": cid}).encode("utf-8")
        headers = {"X-Actor-Id": self.buyer.id}
        status, _, body = self.api_handler.dispatch("POST", "/api/v1/payments/orders/create-hold", headers, create_payload)

        self.assertEqual(status, 403)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["error"], "PAYMENT_APPROVAL_BLOCKED")
        self.assertIn("verdict", data)
        self.assertFalse(data["verdict"]["approved"])

    # -------------------------------------------------------------------------
    # 4. Audit Logging Tests
    # -------------------------------------------------------------------------
    def test_audit_logging_to_messages_table(self):
        """Every approval check is written immutably into the messages table."""
        cid = self._create_contract(amount=1000.0, lock=True)

        verdict = self.approval_service.validate_payment_approval(
            contract_id=cid,
            action="CREATE_HOLD",
            actor=self.buyer
        )

        cursor = self.repo.conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE contract_id = ? ORDER BY sent_at DESC LIMIT 1", (cid,))
        row = cursor.fetchone()

        self.assertIsNotNone(row)
        msg = dict(row)
        self.assertIn("Payment approval check for 'CREATE_HOLD'", msg["content"])
        self.assertIn("APPROVED", msg["content"])

        meta = json.loads(msg["metadata"])
        self.assertEqual(meta["approval_id"], verdict.approval_id)
        self.assertTrue(meta["approved"])
        self.assertIn("CHECKLIST_LOCKED", meta["checks_passed"])


if __name__ == "__main__":
    unittest.main()

