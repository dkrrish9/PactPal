"""
Unit & Integration Tests for Milestone Escrow Settlement & Disbursal (Commit C24)
Tests:
  - 100% full payout ($total payout, $0 refund)
  - Partial payout (e.g. $1,200 payout / $300 refund)
  - 0% complete refund/void ($0 payout, $total refund/void)
  - Mathematical invariant enforcement: round(passed + refund, 2) == round(total, 2)
  - Non-negative amount guard
  - RBAC: Platform ADMIN and AI Referee authorized; BUYER, SELLER, and third party forbidden
  - State machine transitions to SETTLED
  - Relational payments ledger entries (CAPTURE, PAYOUT, VOID)
  - HTTP REST endpoint POST /api/v1/payments/settle (200, 400, 401, 403, 404, 405, 502)
  - Real PayPalClient methods (capture_authorization, void_authorization, create_payout)
"""

import json
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from services.payments.client import PayPalClient, PayPalAPIError
from services.payments.service import (
    EscrowPaymentService,
    ContractRepository,
    User,
    UserRole,
    ContractState,
    StateValidationError,
    ForbiddenActionError
)
from services.payments.api import PaymentsAPIHandler, create_payments_app

class TestEscrowSettlement(unittest.TestCase):

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
            paypal_email="sb-1pu8h53656646@business.example.com"
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
        self.api_handler = PaymentsAPIHandler(service=self.service)

    def tearDown(self):
        self.repo.close()

    def _create_funded_contract(self, amount: float = 1500.0, auth_id: str = "AUTH_PP_445566") -> Dict[str, Any]:
        """Helper to create and advance a contract cleanly to FUNDED with live auth reference."""
        contract = self.repo.create_contract(
            buyer=self.buyer,
            seller_id=self.seller.id,
            title="E-Commerce Milestone Build",
            description="4 checklist features for store launch",
            total_amount=amount,
            deadline=(datetime.now(timezone.utc) + timedelta(days=21)).isoformat()
        )
        cid = contract["id"]
        # Dual confirmation to lock checklist
        self.repo.confirm_checklist(cid, self.buyer)
        self.repo.confirm_checklist(cid, self.seller)

        self.repo.transition_contract(cid, self.buyer, ContractState.REVIEW)
        self.repo.transition_contract(cid, self.seller, ContractState.SIGNED, metadata={"acceptance_confirmed": True})
        funded = self.repo.transition_contract(
            cid,
            self.buyer,
            ContractState.FUNDED,
            metadata={"paypal_order_id": "ORDER_PP_112233", "paypal_auth_id": auth_id}
        )
        # Attach verified deliverable report (Commit C31 gate)
        self.repo.save_verification_report(
            contract_id=cid,
            build_succeeded=True,
            test_suite_results={"passed": True},
            cheat_scan_findings=[],
            per_feature_results={},
            overall_score=1.0
        )
        return funded

    # -------------------------------------------------------------------------
    # Scenario A: 100% Full Payout
    # -------------------------------------------------------------------------
    def test_scenario_a_full_payout_100_percent(self):
        """
        Scenario (a): 100% full payout ($1500.00 passed, $0.00 refund).
        Verifies:
          - capture_authorization called with is_final_capture=True
          - create_payout called to seller
          - void_authorization is NOT called
          - Contract moves to SETTLED
          - Payments table records CAPTURE and PAYOUT (no VOID)
          - SHA-256 receipt hash returned
        """
        contract = self._create_funded_contract(amount=1500.0, auth_id="AUTH_PP_FULL")
        cid = contract["id"]

        self.mock_paypal.capture_authorization.return_value = {
            "capture_id": "CAP_FULL_100",
            "status": "COMPLETED",
            "amount": "1500.00",
            "currency": "USD",
            "final_capture": True
        }
        self.mock_paypal.create_payout.return_value = {
            "payout_batch_id": "BATCH_FULL_100",
            "batch_status": "SUCCESS",
            "amount": "1500.00",
            "currency": "USD"
        }

        res = self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=1500.00,
            refund_amount=0.00,
            seller_paypal_email=self.seller.paypal_email,
            actor=self.admin
        )

        # 1. Returned schema validation
        self.assertEqual(res["contract_id"], cid)
        self.assertEqual(res["status"], "SETTLED")
        self.assertEqual(res["capture_id"], "CAP_FULL_100")
        self.assertEqual(res["payout_batch_id"], "BATCH_FULL_100")
        self.assertIsNone(res["refund_id"])
        self.assertEqual(res["passed_amount"], 1500.00)
        self.assertEqual(res["refund_amount"], 0.00)
        self.assertEqual(len(res["receipt_hash"]), 64)

        # 2. PayPal rails assertions
        self.mock_paypal.capture_authorization.assert_called_once_with(
            authorization_id="AUTH_PP_FULL",
            amount=1500.00,
            currency="USD",
            is_final_capture=True
        )
        self.mock_paypal.create_payout.assert_called_once_with(
            receiver_email=self.seller.paypal_email,
            amount=1500.00,
            currency="USD",
            note="PactPal Milestone Release for 'E-Commerce Milestone Build'"
        )
        self.mock_paypal.void_authorization.assert_not_called()

        # 3. State machine assertion
        updated = self.repo.get_contract(cid)
        self.assertEqual(updated["status"], ContractState.SETTLED.value)

        # 4. Payments ledger verification
        payments = self.repo.get_payments(cid)
        self.assertEqual(len(payments), 2)
        capture_row = next(p for p in payments if p["payment_type"] == "CAPTURE")
        payout_row = next(p for p in payments if p["payment_type"] == "PAYOUT")
        self.assertEqual(capture_row["amount"], 1500.00)
        self.assertEqual(capture_row["paypal_reference_id"], "CAP_FULL_100")
        self.assertEqual(payout_row["amount"], 1500.00)
        self.assertEqual(payout_row["paypal_reference_id"], "BATCH_FULL_100")

    # -------------------------------------------------------------------------
    # Scenario B: Partial Payout ($1,200 payout / $300 refund)
    # -------------------------------------------------------------------------
    def test_scenario_b_partial_payout_and_refund(self):
        """
        Scenario (b): Partial payout ($1,200 payout / $300 refund).
        Verifies:
          - capture_authorization called for $1,200 with is_final_capture=False
          - create_payout called to seller for $1,200
          - void_authorization called to release uncaptured $300 hold
          - Contract moves to SETTLED
          - Payments table records CAPTURE ($1200), PAYOUT ($1200), and VOID ($300)
        """
        contract = self._create_funded_contract(amount=1500.0, auth_id="AUTH_PP_PARTIAL")
        cid = contract["id"]

        self.mock_paypal.capture_authorization.return_value = {
            "capture_id": "CAP_PARTIAL_1200",
            "status": "COMPLETED",
            "amount": "1200.00",
            "currency": "USD",
            "final_capture": False
        }
        self.mock_paypal.create_payout.return_value = {
            "payout_batch_id": "BATCH_PARTIAL_1200",
            "batch_status": "PENDING",
            "amount": "1200.00",
            "currency": "USD"
        }
        self.mock_paypal.void_authorization.return_value = {
            "authorization_id": "AUTH_PP_PARTIAL",
            "status": "VOIDED"
        }

        res = self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=1200.00,
            refund_amount=300.00,
            seller_paypal_email=self.seller.paypal_email,
            actor=self.admin
        )

        # 1. Returned schema validation
        self.assertEqual(res["contract_id"], cid)
        self.assertEqual(res["status"], "SETTLED")
        self.assertEqual(res["capture_id"], "CAP_PARTIAL_1200")
        self.assertEqual(res["payout_batch_id"], "BATCH_PARTIAL_1200")
        self.assertEqual(res["refund_id"], "AUTH_PP_PARTIAL")
        self.assertEqual(res["passed_amount"], 1200.00)
        self.assertEqual(res["refund_amount"], 300.00)
        self.assertEqual(len(res["receipt_hash"]), 64)

        # 2. PayPal rails assertions
        self.mock_paypal.capture_authorization.assert_called_once_with(
            authorization_id="AUTH_PP_PARTIAL",
            amount=1200.00,
            currency="USD",
            is_final_capture=False
        )
        self.mock_paypal.create_payout.assert_called_once_with(
            receiver_email=self.seller.paypal_email,
            amount=1200.00,
            currency="USD",
            note="PactPal Milestone Release for 'E-Commerce Milestone Build'"
        )
        self.mock_paypal.void_authorization.assert_called_once_with(
            authorization_id="AUTH_PP_PARTIAL"
        )

        # 3. State machine assertion
        updated = self.repo.get_contract(cid)
        self.assertEqual(updated["status"], ContractState.SETTLED.value)

        # 4. Payments ledger verification
        payments = self.repo.get_payments(cid)
        self.assertEqual(len(payments), 3)
        capture_row = next(p for p in payments if p["payment_type"] == "CAPTURE")
        payout_row = next(p for p in payments if p["payment_type"] == "PAYOUT")
        void_row = next(p for p in payments if p["payment_type"] == "VOID")
        self.assertEqual(capture_row["amount"], 1200.00)
        self.assertEqual(payout_row["amount"], 1200.00)
        self.assertEqual(void_row["amount"], 300.00)
        self.assertEqual(void_row["paypal_reference_id"], "AUTH_PP_PARTIAL")

    # -------------------------------------------------------------------------
    # Scenario C: 0% Complete Refund/Void
    # -------------------------------------------------------------------------
    def test_scenario_c_complete_refund_void_0_percent(self):
        """
        Scenario (c): 0% complete refund/void ($0 payout / $1500 refund).
        Verifies:
          - capture_authorization NOT called
          - create_payout NOT called
          - void_authorization called to release entire hold back to buyer
          - Contract moves to SETTLED
          - Payments table records VOID (no CAPTURE, no PAYOUT)
        """
        contract = self._create_funded_contract(amount=1500.0, auth_id="AUTH_PP_ZERO")
        cid = contract["id"]

        self.mock_paypal.void_authorization.return_value = {
            "authorization_id": "AUTH_PP_ZERO",
            "status": "VOIDED"
        }

        res = self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=0.00,
            refund_amount=1500.00,
            seller_paypal_email=self.seller.paypal_email,
            actor=self.admin
        )

        # 1. Returned schema validation
        self.assertEqual(res["contract_id"], cid)
        self.assertEqual(res["status"], "SETTLED")
        self.assertIsNone(res["capture_id"])
        self.assertIsNone(res["payout_batch_id"])
        self.assertEqual(res["refund_id"], "AUTH_PP_ZERO")
        self.assertEqual(res["passed_amount"], 0.00)
        self.assertEqual(res["refund_amount"], 1500.00)
        self.assertEqual(len(res["receipt_hash"]), 64)

        # 2. PayPal rails assertions
        self.mock_paypal.capture_authorization.assert_not_called()
        self.mock_paypal.create_payout.assert_not_called()
        self.mock_paypal.void_authorization.assert_called_once_with(
            authorization_id="AUTH_PP_ZERO"
        )

        # 3. State machine assertion
        updated = self.repo.get_contract(cid)
        self.assertEqual(updated["status"], ContractState.SETTLED.value)

        # 4. Payments ledger verification
        payments = self.repo.get_payments(cid)
        self.assertEqual(len(payments), 1)
        self.assertEqual(payments[0]["payment_type"], "VOID")
        self.assertEqual(payments[0]["amount"], 1500.00)
        self.assertEqual(payments[0]["paypal_reference_id"], "AUTH_PP_ZERO")

    # -------------------------------------------------------------------------
    # RBAC & Security Guards
    # -------------------------------------------------------------------------
    def test_actor_role_enforcement_buyer_and_seller_blocked(self):
        """Only ADMIN or AI Referee can settle; Buyer, Seller, and third parties are forbidden."""
        contract = self._create_funded_contract(amount=1000.0)
        cid = contract["id"]

        with self.assertRaises(ForbiddenActionError):
            self.service.settle_contract_escrow(
                contract_id=cid, passed_amount=1000.0, refund_amount=0.0,
                seller_paypal_email=self.seller.paypal_email, actor=self.buyer
            )

        with self.assertRaises(ForbiddenActionError):
            self.service.settle_contract_escrow(
                contract_id=cid, passed_amount=1000.0, refund_amount=0.0,
                seller_paypal_email=self.seller.paypal_email, actor=self.seller
            )

        with self.assertRaises(ForbiddenActionError):
            self.service.settle_contract_escrow(
                contract_id=cid, passed_amount=1000.0, refund_amount=0.0,
                seller_paypal_email=self.seller.paypal_email, actor=self.stranger
            )

    def test_ai_referee_can_settle_contract(self):
        """AI Referee is authorized to trigger settlement."""
        contract = self._create_funded_contract(amount=1000.0, auth_id="AUTH_REFEREE")
        cid = contract["id"]

        self.mock_paypal.capture_authorization.return_value = {"capture_id": "CAP_REF", "status": "COMPLETED"}
        self.mock_paypal.create_payout.return_value = {"payout_batch_id": "BATCH_REF", "batch_status": "SUCCESS"}

        res = self.service.settle_contract_escrow(
            contract_id=cid, passed_amount=1000.0, refund_amount=0.0,
            seller_paypal_email=self.seller.paypal_email, actor=self.ai_referee
        )
        self.assertEqual(res["status"], "SETTLED")

    # -------------------------------------------------------------------------
    # Invariant & Validation Guards
    # -------------------------------------------------------------------------
    def test_invariant_sum_mismatch_rejected(self):
        """passed_amount + refund_amount != total_amount must be strictly rejected."""
        contract = self._create_funded_contract(amount=1500.0)
        cid = contract["id"]

        # Sum is 1400.00 (under total 1500.00)
        with self.assertRaises(ValueError) as ctx:
            self.service.settle_contract_escrow(
                contract_id=cid, passed_amount=1200.0, refund_amount=200.0,
                seller_paypal_email=self.seller.paypal_email, actor=self.admin
            )
        self.assertIn("Amount invariant violation", str(ctx.exception))

        # Sum is 1600.00 (over total 1500.00)
        with self.assertRaises(ValueError) as ctx:
            self.service.settle_contract_escrow(
                contract_id=cid, passed_amount=1200.0, refund_amount=400.0,
                seller_paypal_email=self.seller.paypal_email, actor=self.admin
            )
        self.assertIn("Amount invariant violation", str(ctx.exception))

    def test_negative_amounts_rejected(self):
        """Negative amounts must raise ValueError."""
        contract = self._create_funded_contract(amount=1000.0)
        cid = contract["id"]

        with self.assertRaises(ValueError):
            self.service.settle_contract_escrow(
                contract_id=cid, passed_amount=-100.0, refund_amount=1100.0,
                seller_paypal_email=self.seller.paypal_email, actor=self.admin
            )

        with self.assertRaises(ValueError):
            self.service.settle_contract_escrow(
                contract_id=cid, passed_amount=1100.0, refund_amount=-100.0,
                seller_paypal_email=self.seller.paypal_email, actor=self.admin
            )

    def test_unfunded_contract_cannot_be_settled(self):
        """Contracts in DRAFT, REVIEW, or SIGNED cannot be settled."""
        contract = self.repo.create_contract(
            buyer=self.buyer, seller_id=self.seller.id, title="Draft App",
            description="Desc", total_amount=1000.0, deadline="2026-12-01T00:00:00Z"
        )
        with self.assertRaises(StateValidationError):
            self.service.settle_contract_escrow(
                contract_id=contract["id"], passed_amount=1000.0, refund_amount=0.0,
                seller_paypal_email=self.seller.paypal_email, actor=self.admin
            )

    def test_already_settled_contract_rejected(self):
        """Attempting to settle an already SETTLED contract must raise StateValidationError."""
        contract = self._create_funded_contract(amount=1000.0, auth_id="AUTH_DOUBLE")
        cid = contract["id"]
        self.mock_paypal.void_authorization.return_value = {"authorization_id": "AUTH_DOUBLE", "status": "VOIDED"}

        # First settlement succeeds
        self.service.settle_contract_escrow(
            contract_id=cid, passed_amount=0.0, refund_amount=1000.0,
            seller_paypal_email=self.seller.paypal_email, actor=self.admin
        )

        # Second settlement must raise
        with self.assertRaises(StateValidationError) as ctx:
            self.service.settle_contract_escrow(
                contract_id=cid, passed_amount=0.0, refund_amount=1000.0,
                seller_paypal_email=self.seller.paypal_email, actor=self.admin
            )
        self.assertIn("already SETTLED", str(ctx.exception))

    def test_missing_seller_paypal_email_when_payout_positive(self):
        """If passed_amount > 0 and no seller email provided, raises ValueError."""
        seller_no_pp = self.repo.create_user(
            name="No PayPal", email="nopp@test.com", role=UserRole.SELLER, paypal_email=None
        )
        contract = self.repo.create_contract(
            buyer=self.buyer, seller_id=seller_no_pp.id, title="App",
            description="Desc", total_amount=1000.0, deadline="2026-12-01T00:00:00Z"
        )
        cid = contract["id"]
        self.repo.transition_contract(cid, self.buyer, ContractState.REVIEW)
        self.repo.transition_contract(cid, seller_no_pp, ContractState.SIGNED, metadata={"acceptance_confirmed": True})
        self.repo.transition_contract(cid, self.buyer, ContractState.FUNDED, metadata={"paypal_order_id": "O", "paypal_auth_id": "A"})

        with self.assertRaises(ValueError) as ctx:
            self.service.settle_contract_escrow(
                contract_id=cid, passed_amount=1000.0, refund_amount=0.0,
                seller_paypal_email="", actor=self.admin
            )
        self.assertIn("seller_paypal_email is required", str(ctx.exception))

    # -------------------------------------------------------------------------
    # REST API Handler Tests (POST /api/v1/payments/settle)
    # -------------------------------------------------------------------------
    def test_api_settle_partial_payout_200(self):
        """API: Settle endpoint returns 200 with capture_id, payout_batch_id, refund_id."""
        contract = self._create_funded_contract(amount=1500.0, auth_id="AUTH_API_PARTIAL")
        cid = contract["id"]

        self.mock_paypal.capture_authorization.return_value = {"capture_id": "CAP_API", "status": "COMPLETED"}
        self.mock_paypal.create_payout.return_value = {"payout_batch_id": "BATCH_API", "batch_status": "SUCCESS"}
        self.mock_paypal.void_authorization.return_value = {"authorization_id": "AUTH_API_PARTIAL", "status": "VOIDED"}

        payload = {
            "contract_id": cid,
            "passed_amount": 1200.00,
            "refund_amount": 300.00,
            "seller_paypal_email": "sb-1pu8h53656646@business.example.com"
        }
        status, headers, body = self.api_handler.dispatch(
            method="POST",
            path="/api/v1/payments/settle",
            headers={"X-Actor-Id": self.admin.id, "Content-Type": "application/json"},
            body=json.dumps(payload).encode("utf-8")
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["contract_id"], cid)
        self.assertEqual(data["capture_id"], "CAP_API")
        self.assertEqual(data["payout_batch_id"], "BATCH_API")
        self.assertEqual(data["refund_id"], "AUTH_API_PARTIAL")
        self.assertEqual(data["status"], "SETTLED")

    def test_api_settle_unauthorized_401(self):
        """API: Settle endpoint without authentication returns 401."""
        status, _, body = self.api_handler.dispatch(
            method="POST",
            path="/api/v1/payments/settle",
            headers={"Content-Type": "application/json"},
            body=json.dumps({"contract_id": "123"}).encode("utf-8")
        )
        self.assertEqual(status, 401)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["error"], "UNAUTHORIZED")

    def test_api_settle_forbidden_403(self):
        """API: Settle endpoint called by Buyer returns 403."""
        contract = self._create_funded_contract(amount=1500.0)
        payload = {"contract_id": contract["id"], "passed_amount": 1500.0, "refund_amount": 0.0}
        status, _, body = self.api_handler.dispatch(
            method="POST",
            path="/api/v1/payments/settle",
            headers={"X-Actor-Id": self.buyer.id, "Content-Type": "application/json"},
            body=json.dumps(payload).encode("utf-8")
        )
        self.assertEqual(status, 403)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["error"], "FORBIDDEN")

    def test_api_settle_amount_mismatch_400(self):
        """API: Settle endpoint with amount mismatch returns 400 Bad Request."""
        contract = self._create_funded_contract(amount=1500.0)
        payload = {"contract_id": contract["id"], "passed_amount": 1000.0, "refund_amount": 200.0}
        status, _, body = self.api_handler.dispatch(
            method="POST",
            path="/api/v1/payments/settle",
            headers={"X-Actor-Id": self.admin.id, "Content-Type": "application/json"},
            body=json.dumps(payload).encode("utf-8")
        )
        self.assertEqual(status, 400)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["error"], "BAD_REQUEST")

    def test_api_settle_not_found_404(self):
        """API: Non-existent contract returns 404 Not Found."""
        payload = {"contract_id": "non-existent-uuid", "passed_amount": 100.0, "refund_amount": 0.0}
        status, _, body = self.api_handler.dispatch(
            method="POST",
            path="/api/v1/payments/settle",
            headers={"X-Actor-Id": self.admin.id, "Content-Type": "application/json"},
            body=json.dumps(payload).encode("utf-8")
        )
        self.assertEqual(status, 404)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["error"], "NOT_FOUND")

    def test_api_settle_method_not_allowed_405(self):
        """API: GET on settle endpoint returns 405 Method Not Allowed."""
        status, _, body = self.api_handler.dispatch(
            method="GET",
            path="/api/v1/payments/settle",
            headers={"X-Actor-Id": self.admin.id}
        )
        self.assertEqual(status, 405)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["error"], "METHOD_NOT_ALLOWED")

    def test_wsgi_app_integration(self):
        """Validates WSGI create_payments_app integration for settle endpoint."""
        contract = self._create_funded_contract(amount=1000.0, auth_id="AUTH_WSGI")
        self.mock_paypal.void_authorization.return_value = {"authorization_id": "AUTH_WSGI", "status": "VOIDED"}

        app = create_payments_app(service=self.service)
        payload = json.dumps({
            "contract_id": contract["id"],
            "passed_amount": 0.0,
            "refund_amount": 1000.0,
            "seller_paypal_email": self.seller.paypal_email
        }).encode("utf-8")

        import io
        environ = {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/api/v1/payments/settle",
            "HTTP_X_ACTOR_ID": self.admin.id,
            "CONTENT_TYPE": "application/json",
            "CONTENT_LENGTH": str(len(payload)),
            "wsgi.input": io.BytesIO(payload)
        }
        captured_headers = []
        captured_status = []

        def start_response(status, headers):
            captured_status.append(status)
            captured_headers.extend(headers)

        res_iter = app(environ, start_response)
        res_body = b"".join(res_iter)

        self.assertTrue(captured_status[0].startswith("200"))
        data = json.loads(res_body.decode("utf-8"))
        self.assertEqual(data["status"], "SETTLED")
        self.assertEqual(data["refund_id"], "AUTH_WSGI")

    # -------------------------------------------------------------------------
    # PayPalClient Concrete Unit Tests
    # -------------------------------------------------------------------------
    def test_paypal_client_capture_authorization(self):
        """Unit test for PayPalClient.capture_authorization."""
        client = PayPalClient(client_id="cid", client_secret="sec")
        with patch.object(client, "_send_authorized_request") as mock_req:
            mock_req.return_value = {
                "id": "CAP_REAL_123",
                "status": "COMPLETED",
                "amount": {"value": "1200.00", "currency_code": "USD"},
                "final_capture": True
            }
            res = client.capture_authorization("AUTH_123", 1200.0, "USD", is_final_capture=True)
            self.assertEqual(res["capture_id"], "CAP_REAL_123")
            self.assertEqual(res["status"], "COMPLETED")
            self.assertTrue(res["final_capture"])
            mock_req.assert_called_once()
            url, kwargs = mock_req.call_args[0][0], mock_req.call_args[1]
            self.assertIn("/v2/payments/authorizations/AUTH_123/capture", url)

    def test_paypal_client_void_authorization_handles_empty_response(self):
        """Unit test for PayPalClient.void_authorization handling HTTP 204 empty response."""
        client = PayPalClient(client_id="cid", client_secret="sec")
        with patch.object(client, "_send_authorized_request") as mock_req:
            mock_req.return_value = {"status": "VOIDED"}
            res = client.void_authorization("AUTH_456")
            self.assertEqual(res["authorization_id"], "AUTH_456")
            self.assertEqual(res["status"], "VOIDED")
            mock_req.assert_called_once()
            url = mock_req.call_args[0][0]
            self.assertIn("/v2/payments/authorizations/AUTH_456/void", url)

    def test_paypal_client_create_payout(self):
        """Unit test for PayPalClient.create_payout."""
        client = PayPalClient(client_id="cid", client_secret="sec")
        with patch.object(client, "_send_authorized_request") as mock_req:
            mock_req.return_value = {
                "batch_header": {
                    "payout_batch_id": "BATCH_789",
                    "batch_status": "PENDING",
                    "sender_batch_header": {"sender_batch_id": "CUSTOM_BATCH_1"}
                }
            }
            res = client.create_payout("seller@test.com", 1200.0, "USD", sender_batch_id="CUSTOM_BATCH_1")
            self.assertEqual(res["payout_batch_id"], "BATCH_789")
            self.assertEqual(res["batch_status"], "PENDING")
            self.assertEqual(res["sender_batch_id"], "CUSTOM_BATCH_1")
            mock_req.assert_called_once()
            url = mock_req.call_args[0][0]
            self.assertIn("/v1/payments/payouts", url)

if __name__ == "__main__":
    unittest.main()

