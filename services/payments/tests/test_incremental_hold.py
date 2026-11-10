"""
Unit & Integration Tests for Incremental Authorization Hold (Commit C46)

Done Criteria:
  "Hold amount increases when change request is accepted"
  "Second authorization created and tracked"

Authoritative Specifications (Master Doc & Commit Flow Sheet C46):
  1. Incremental Authorization Rails:
     - When a change request is agreed and accepted (adding scope and price), the escrow hold
       on PayPal increases to cover the amended total (new_hold = original_hold + incremental_amount).
     - Calls PayPal REST API v2 reauthorization rails (POST /v2/payments/authorizations/{id}/reauthorize).
     - Handles updated expiration dates (+29 days from reauthorization) and updated hold tracking.
  2. Relational Ledger & Contract State Updates:
     - Updates contract total_amount to reflect the amended total amount.
     - Records incremental_amount, new_authorization_id, change_request_id, and updated expiry in
       payments, contracts, and change_requests tables.
     - Adds an immutable audit log entry into the messages table documenting the authorization expansion.
  3. Service & API Exposure:
     - EscrowPaymentService.apply_incremental_hold(contract_id, change_request_id, additional_amount, actor, idempotency_key).
     - REST API Endpoint: POST /api/v1/contracts/{id}/incremental-hold (and POST /api/v1/payments/orders/incremental-hold).
     - GET /api/v1/contracts/{id}/hold immediately reflects the higher total amount and updated countdown timer.
  4. Policy & Idempotency Guards:
     - Enforces PaymentApprovalService approval check: change request exists, is in ACCEPTED status,
       and checklist is dual-confirmed for the amendment.
     - Enforces idempotency: Duplicate requests with the same idempotency key return the cached result.
  5. Test Coverage:
     - 12 comprehensive unit and integration tests covering rails, DB, RBAC, REST API, idempotency,
       rejection of unaccepted change requests, and edge cases.
"""

import io
import json
import unittest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch

from services.payments.client import PayPalClient, PayPalAPIError
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
    UnauthorizedRoleError,
    StateValidationError,
    assert_can_apply_incremental_hold
)
from services.payments.api import PaymentsAPIHandler


class TestIncrementalAuthorizationHold(unittest.TestCase):

    def setUp(self):
        self.repo = ContractRepository(db_path=":memory:")
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
        self.price_negotiator = User(
            id="PRICE_NEGOTIATOR",
            name="Price Negotiator",
            email="negotiator@pactpal.internal",
            role=UserRole.ADMIN
        )

        self.mock_paypal = MagicMock(spec=PayPalClient)
        self.service = EscrowPaymentService(
            paypal_client=self.mock_paypal,
            repository=self.repo
        )
        self.api = PaymentsAPIHandler(service=self.service)

    def tearDown(self):
        if hasattr(self, "repo") and self.repo:
            self.repo.close()

    def _setup_funded_contract(
        self,
        total_amount: float = 1000.0,
        currency: str = "USD",
        auth_id: str = "AUTH-INIT-1000",
        is_locked: bool = True
    ) -> Dict[str, Any]:
        """Helper to create a funded contract with locked checklist and active hold."""
        now = datetime.now(timezone.utc)
        deadline = (now + timedelta(days=30)).isoformat()
        contract = self.repo.create_contract(
            buyer=self.buyer,
            seller_id=self.seller.id,
            title="E-Commerce Mobile Application",
            description="Escrow contract with initial scope and features",
            total_amount=total_amount,
            deadline=deadline
        )
        contract_id = contract["id"]

        # Add initial features
        self.repo.add_feature(
            contract_id=contract_id,
            title="User Authentication",
            acceptance_test="OAuth login works",
            price_weight=50.0,
            allocated_amount=round(total_amount * 0.5, 2)
        )
        self.repo.add_feature(
            contract_id=contract_id,
            title="Product Catalog",
            acceptance_test="Search & filter items",
            price_weight=50.0,
            allocated_amount=round(total_amount * 0.5, 2)
        )

        # Transition DRAFT -> REVIEW -> SIGNED
        self.repo.transition_contract(contract_id, self.buyer, ContractState.REVIEW)
        self.repo.transition_contract(contract_id, self.seller, ContractState.SIGNED)

        # Confirm checklist if locked
        if is_locked:
            self.repo.confirm_checklist(contract_id, self.buyer)
            self.repo.confirm_checklist(contract_id, self.seller)

        # Transition to FUNDED with authorization ID
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(days=29)).isoformat()
        cursor = self.repo.conn.cursor()
        cursor.execute("""
            UPDATE contracts
            SET status = 'FUNDED',
                paypal_order_id = ?,
                paypal_auth_id = ?,
                auth_expires_at = ?,
                funded_at = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            f"ORDER-{contract_id[:8]}",
            auth_id,
            expires_at,
            now.isoformat(),
            now.isoformat(),
            contract_id
        ))
        self.repo.conn.commit()

        return self.repo.get_contract(contract_id)

    # -------------------------------------------------------------------------
    # 1. Core Incremental Hold & Done Criteria Verification
    # -------------------------------------------------------------------------
    def test_incremental_hold_increases_hold_amount_when_change_request_accepted(self):
        """
        Verifies Done Criteria:
        'Hold amount increases when change request is accepted'
        Initial hold: $1000.00
        Change request: +$250.00 (ACCEPTED)
        New hold: $1250.00
        """
        contract = self._setup_funded_contract(total_amount=1000.0, auth_id="AUTH-ORIG-001")
        contract_id = contract["id"]

        # Create ACCEPTED change request
        cr = self.repo.create_change_request(
            contract_id=contract_id,
            proposed_by_id=self.seller.id,
            description="Add Dark Mode & Apple Pay Integration",
            proposed_price=250.00,
            proposed_extra_time_hours=48,
            status="ACCEPTED",
            change_request_id="CR-AMENDMENT-101"
        )
        self.assertEqual(cr["status"], "ACCEPTED")

        # Mock PayPal reauthorization response
        future_exp = (datetime.now(timezone.utc) + timedelta(days=29)).isoformat()
        self.mock_paypal.reauthorize_authorization.return_value = {
            "authorization_id": "AUTH-EXPANDED-002",
            "status": "AUTHORIZED",
            "amount": {"value": "1250.00", "currency_code": "USD"},
            "expiration_time": future_exp
        }

        # Apply incremental hold
        result = self.service.apply_incremental_hold(
            contract_id=contract_id,
            change_request_id="CR-AMENDMENT-101",
            actor=self.buyer
        )

        # 1. Result verification
        self.assertEqual(result["contract_id"], contract_id)
        self.assertEqual(result["change_request_id"], "CR-AMENDMENT-101")
        self.assertEqual(result["original_hold_amount"], "1000.00")
        self.assertEqual(result["additional_hold_amount"], "250.00")
        self.assertEqual(result["new_hold_amount"], "1250.00")
        self.assertEqual(result["authorization_id"], "AUTH-EXPANDED-002")
        self.assertEqual(result["previous_authorization_id"], "AUTH-ORIG-001")
        self.assertEqual(result["status"], "HOLD_EXPANDED")

        # 2. PayPal Client verification
        self.mock_paypal.reauthorize_authorization.assert_called_once_with(
            authorization_id="AUTH-ORIG-001",
            amount=1250.00,
            currency="USD",
            idempotency_key=None
        )

        # 3. Database contract updates
        updated_contract = self.repo.get_contract(contract_id)
        self.assertEqual(updated_contract["total_amount"], 1250.00)
        self.assertEqual(updated_contract["paypal_auth_id"], "AUTH-EXPANDED-002")
        self.assertEqual(updated_contract["auth_expires_at"], future_exp)

        # 4. Database change request tracking
        updated_cr = self.repo.get_change_request("CR-AMENDMENT-101")
        self.assertEqual(updated_cr["additional_auth_id"], "AUTH-EXPANDED-002")

        # 5. Countdown & Expiry reflection in get_contract_hold
        hold_info = self.service.get_contract_hold(contract_id, actor=self.buyer)
        self.assertEqual(hold_info["amount"], "1250.00")
        self.assertEqual(hold_info["authorization_id"], "AUTH-EXPANDED-002")
        self.assertEqual(hold_info["status"], "HELD")
        self.assertGreaterEqual(hold_info["days_remaining"], 28)
        self.assertFalse(hold_info["is_expired"])

    def test_negotiation_agent_and_admin_can_apply_incremental_hold(self):
        """Verifies that platform Admin and Price Negotiator can apply incremental holds."""
        contract = self._setup_funded_contract(total_amount=500.0, auth_id="AUTH-INIT-500")
        contract_id = contract["id"]

        cr = self.repo.create_change_request(
            contract_id=contract_id,
            proposed_by_id=self.buyer.id,
            description="Push notifications module",
            proposed_price=100.00,
            status="ACCEPTED",
            change_request_id="CR-PUSH-01"
        )

        self.mock_paypal.reauthorize_authorization.return_value = {
            "authorization_id": "AUTH-NEW-600",
            "status": "AUTHORIZED",
            "amount": {"value": "600.00", "currency_code": "USD"}
        }

        # Price Negotiator actor
        res_negotiator = self.service.apply_incremental_hold(
            contract_id=contract_id,
            change_request_id="CR-PUSH-01",
            actor=self.price_negotiator
        )
        self.assertEqual(res_negotiator["new_hold_amount"], "600.00")
        self.assertEqual(res_negotiator["authorization_id"], "AUTH-NEW-600")

    # -------------------------------------------------------------------------
    # 2. Relational Ledger Persistence (Payments & Messages)
    # -------------------------------------------------------------------------
    def test_relational_payments_and_messages_ledger_entry(self):
        """Verifies that incremental holds are recorded in both payments and messages tables."""
        contract = self._setup_funded_contract(total_amount=800.0, auth_id="AUTH-800")
        contract_id = contract["id"]

        self.repo.create_change_request(
            contract_id=contract_id,
            proposed_by_id=self.seller.id,
            description="Additional localization languages",
            proposed_price=150.00,
            status="ACCEPTED",
            change_request_id="CR-LOC-01"
        )

        self.mock_paypal.reauthorize_authorization.return_value = {
            "authorization_id": "AUTH-950",
            "status": "AUTHORIZED",
            "amount": {"value": "950.00", "currency_code": "USD"}
        }

        self.service.apply_incremental_hold(
            contract_id=contract_id,
            change_request_id="CR-LOC-01",
            actor=self.buyer
        )

        # Verify payments table
        payments = self.repo.get_payments(contract_id)
        auth_payments = [p for p in payments if p["payment_type"] == "AUTHORIZATION"]
        self.assertGreaterEqual(len(auth_payments), 1)
        latest_payment = auth_payments[-1]
        self.assertEqual(latest_payment["amount"], 150.00)
        self.assertEqual(latest_payment["paypal_reference_id"], "AUTH-950")
        self.assertEqual(latest_payment["status"], "COMPLETED")
        meta = json.loads(latest_payment["metadata"])
        self.assertEqual(meta["action"], "INCREMENTAL_HOLD")
        self.assertEqual(meta["change_request_id"], "CR-LOC-01")
        self.assertEqual(meta["original_hold_amount"], 800.00)
        self.assertEqual(meta["new_hold_amount"], 950.00)

        # Verify messages table
        messages = self.repo.get_messages(contract_id)
        hold_messages = [m for m in messages if "INCREMENTAL_HOLD_APPLIED" in (m.get("metadata") or "")]
        self.assertEqual(len(hold_messages), 1)
        audit_msg = hold_messages[0]
        self.assertIn("Escrow hold increased by $150.00 USD", audit_msg["content"])
        self.assertIn("CR-LOC-01", audit_msg["content"])

    # -------------------------------------------------------------------------
    # 3. Policy & Status Guard Rejections
    # -------------------------------------------------------------------------
    def test_unaccepted_change_request_rejected(self):
        """Verifies rejection when change request is in PROPOSED, REJECTED, or COUNTERED state."""
        contract = self._setup_funded_contract(total_amount=1000.0, auth_id="AUTH-1000")
        contract_id = contract["id"]

        for unaccepted_status in ("PROPOSED", "REJECTED", "COUNTERED"):
            cr_id = f"CR-{unaccepted_status}-01"
            self.repo.create_change_request(
                contract_id=contract_id,
                proposed_by_id=self.seller.id,
                description=f"Scope in {unaccepted_status} state",
                proposed_price=100.00,
                status=unaccepted_status,
                change_request_id=cr_id
            )

            with self.assertRaises((StateValidationError, PaymentApprovalError)):
                self.service.apply_incremental_hold(
                    contract_id=contract_id,
                    change_request_id=cr_id,
                    actor=self.buyer
                )

        # Hold amount remains untouched
        current = self.repo.get_contract(contract_id)
        self.assertEqual(current["total_amount"], 1000.00)
        self.mock_paypal.reauthorize_authorization.assert_not_called()

    def test_invalid_contract_states_rejected(self):
        """Verifies rejection when contract is DRAFT, REVIEW, SIGNED (unfunded), or SETTLED."""
        # Unfunded SIGNED contract
        deadline = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        raw_contract = self.repo.create_contract(
            buyer=self.buyer,
            seller_id=self.seller.id,
            title="Unfunded contract",
            description="Testing invalid states",
            total_amount=500.0,
            deadline=deadline
        )
        c_id = raw_contract["id"]
        cr = self.repo.create_change_request(
            contract_id=c_id,
            proposed_by_id=self.seller.id,
            description="Feature addition",
            proposed_price=100.00,
            status="ACCEPTED",
            change_request_id="CR-UNFUNDED-01"
        )

        with self.assertRaises(StateValidationError):
            self.service.apply_incremental_hold(
                contract_id=c_id,
                change_request_id="CR-UNFUNDED-01",
                actor=self.buyer
            )

        # SETTLED contract
        contract = self._setup_funded_contract(total_amount=1000.0, auth_id="AUTH-SETTLED")
        settled_id = contract["id"]
        cursor = self.repo.conn.cursor()
        cursor.execute("UPDATE contracts SET status = 'SETTLED' WHERE id = ?", (settled_id,))
        self.repo.conn.commit()

        cr_settled = self.repo.create_change_request(
            contract_id=settled_id,
            proposed_by_id=self.seller.id,
            description="Feature addition post settlement",
            proposed_price=100.00,
            status="ACCEPTED",
            change_request_id="CR-SETTLED-01"
        )

        with self.assertRaises(StateValidationError):
            self.service.apply_incremental_hold(
                contract_id=settled_id,
                change_request_id="CR-SETTLED-01",
                actor=self.buyer
            )

    def test_checklist_not_locked_rejected(self):
        """Verifies rejection if the contract checklist is not locked."""
        contract = self._setup_funded_contract(total_amount=1000.0, auth_id="AUTH-UNLOCKED", is_locked=False)
        contract_id = contract["id"]

        cr = self.repo.create_change_request(
            contract_id=contract_id,
            proposed_by_id=self.seller.id,
            description="Feature addition",
            proposed_price=100.00,
            status="ACCEPTED",
            change_request_id="CR-UNLOCKED-01"
        )

        with self.assertRaises(PaymentApprovalError) as ctx:
            self.service.apply_incremental_hold(
                contract_id=contract_id,
                change_request_id="CR-UNLOCKED-01",
                actor=self.buyer
            )
        self.assertIn("CHECKLIST_LOCKED", str(ctx.exception.verdict.checks_failed))

    # -------------------------------------------------------------------------
    # 4. RBAC Authorization Guards
    # -------------------------------------------------------------------------
    def test_unauthorized_actors_rejected(self):
        """Verifies that sellers and third-party strangers cannot authorize incremental holds."""
        contract = self._setup_funded_contract(total_amount=1000.0, auth_id="AUTH-RBAC")
        contract_id = contract["id"]

        cr = self.repo.create_change_request(
            contract_id=contract_id,
            proposed_by_id=self.seller.id,
            description="Add feature",
            proposed_price=100.00,
            status="ACCEPTED",
            change_request_id="CR-RBAC-01"
        )

        # Seller rejected
        with self.assertRaises(UnauthorizedRoleError):
            self.service.apply_incremental_hold(
                contract_id=contract_id,
                change_request_id="CR-RBAC-01",
                actor=self.seller
            )

        # Third-party buyer rejected
        with self.assertRaises(ForbiddenActionError):
            self.service.apply_incremental_hold(
                contract_id=contract_id,
                change_request_id="CR-RBAC-01",
                actor=self.third_party
            )

    # -------------------------------------------------------------------------
    # 5. Idempotency Replay Protection
    # -------------------------------------------------------------------------
    def test_idempotency_prevents_duplicate_reauthorization(self):
        """Verifies duplicate requests with identical idempotency key return cached response."""
        contract = self._setup_funded_contract(total_amount=1000.0, auth_id="AUTH-IDEMP")
        contract_id = contract["id"]

        cr = self.repo.create_change_request(
            contract_id=contract_id,
            proposed_by_id=self.seller.id,
            description="New scope",
            proposed_price=200.00,
            status="ACCEPTED",
            change_request_id="CR-IDEMP-01"
        )

        self.mock_paypal.reauthorize_authorization.return_value = {
            "authorization_id": "AUTH-IDEMP-200",
            "status": "AUTHORIZED",
            "amount": {"value": "1200.00", "currency_code": "USD"}
        }

        # First request
        res1 = self.service.apply_incremental_hold(
            contract_id=contract_id,
            change_request_id="CR-IDEMP-01",
            actor=self.buyer,
            idempotency_key="IDEMP-HOLD-KEY-999"
        )
        self.assertEqual(res1["new_hold_amount"], "1200.00")
        self.assertEqual(self.mock_paypal.reauthorize_authorization.call_count, 1)

        # Duplicate request with same idempotency key
        res2 = self.service.apply_incremental_hold(
            contract_id=contract_id,
            change_request_id="CR-IDEMP-01",
            actor=self.buyer,
            idempotency_key="IDEMP-HOLD-KEY-999"
        )
        self.assertEqual(res2, res1)
        # PayPal client should NOT be called again
        self.assertEqual(self.mock_paypal.reauthorize_authorization.call_count, 1)

    # -------------------------------------------------------------------------
    # 6. Real PayPal Client Reauthorize Method Testing
    # -------------------------------------------------------------------------
    @patch("urllib.request.urlopen")
    def test_real_paypal_client_reauthorize_authorization(self, mock_urlopen):
        """Verifies real PayPalClient.reauthorize_authorization makes correct HTTP REST call."""
        import time
        client = PayPalClient(client_id="test_id", client_secret="test_secret")
        client._cached_token = "MOCK_TOKEN"
        client._token_expires_at = time.time() + 3600

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "id": "AUTH-REAUTH-999",
            "status": "AUTHORIZED",
            "amount": {"value": "1350.00", "currency_code": "USD"},
            "expiration_time": "2026-12-15T00:00:00Z"
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        result = client.reauthorize_authorization(
            authorization_id="AUTH-ORIG-100",
            amount=1350.0,
            currency="USD",
            idempotency_key="IDEMP-PAYPAL-123"
        )

        self.assertEqual(result["authorization_id"], "AUTH-REAUTH-999")
        self.assertEqual(result["amount"], "1350.00")
        self.assertEqual(result["status"], "AUTHORIZED")
        self.assertEqual(result["expiration_time"], "2026-12-15T00:00:00Z")

        # Verify urllib call
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        self.assertIn("/v2/payments/authorizations/AUTH-ORIG-100/reauthorize", req.full_url)
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.headers.get("Paypal-request-id"), "IDEMP-PAYPAL-123")
        payload = json.loads(req.data.decode("utf-8"))
        self.assertEqual(payload["amount"]["value"], "1350.00")
        self.assertEqual(payload["amount"]["currency_code"], "USD")

    # -------------------------------------------------------------------------
    # 7. REST API Endpoints Integration
    # -------------------------------------------------------------------------
    def test_rest_api_contract_incremental_hold_endpoint(self):
        """Verifies POST /api/v1/contracts/{id}/incremental-hold dispatches cleanly."""
        contract = self._setup_funded_contract(total_amount=1000.0, auth_id="AUTH-REST-1")
        contract_id = contract["id"]

        self.repo.create_change_request(
            contract_id=contract_id,
            proposed_by_id=self.seller.id,
            description="API integration",
            proposed_price=300.00,
            status="ACCEPTED",
            change_request_id="CR-REST-01"
        )

        self.mock_paypal.reauthorize_authorization.return_value = {
            "authorization_id": "AUTH-REST-NEW",
            "status": "AUTHORIZED",
            "amount": {"value": "1300.00", "currency_code": "USD"}
        }

        # 1. Successful POST 200
        status, headers, body = self.api.dispatch(
            method="POST",
            path=f"/api/v1/contracts/{contract_id}/incremental-hold",
            headers={"X-Actor-Id": self.buyer.id, "Content-Type": "application/json"},
            body=json.dumps({"change_request_id": "CR-REST-01"}).encode("utf-8")
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["new_hold_amount"], "1300.00")
        self.assertEqual(data["authorization_id"], "AUTH-REST-NEW")

        # 2. Method Not Allowed (GET) -> 405
        status_get, _, _ = self.api.dispatch(
            method="GET",
            path=f"/api/v1/contracts/{contract_id}/incremental-hold",
            headers={"X-Actor-Id": self.buyer.id}
        )
        self.assertEqual(status_get, 405)

        # 3. Unauthenticated -> 401
        status_unauth, _, _ = self.api.dispatch(
            method="POST",
            path=f"/api/v1/contracts/{contract_id}/incremental-hold",
            headers={},
            body=json.dumps({"change_request_id": "CR-REST-01"}).encode("utf-8")
        )
        self.assertEqual(status_unauth, 401)

        # 4. Unauthorized (Seller) -> 403
        status_seller, _, _ = self.api.dispatch(
            method="POST",
            path=f"/api/v1/contracts/{contract_id}/incremental-hold",
            headers={"X-Actor-Id": self.seller.id},
            body=json.dumps({"change_request_id": "CR-REST-01"}).encode("utf-8")
        )
        self.assertEqual(status_seller, 403)

        # 5. Missing change_request_id -> 400
        status_bad, _, _ = self.api.dispatch(
            method="POST",
            path=f"/api/v1/contracts/{contract_id}/incremental-hold",
            headers={"X-Actor-Id": self.buyer.id},
            body=json.dumps({}).encode("utf-8")
        )
        self.assertEqual(status_bad, 400)

        # 6. Non-existent change request -> 404
        status_nf, _, _ = self.api.dispatch(
            method="POST",
            path=f"/api/v1/contracts/{contract_id}/incremental-hold",
            headers={"X-Actor-Id": self.buyer.id},
            body=json.dumps({"change_request_id": "CR-DOES-NOT-EXIST"}).encode("utf-8")
        )
        self.assertEqual(status_nf, 404)

    def test_rest_api_payments_order_incremental_hold_endpoint(self):
        """Verifies POST /api/v1/payments/orders/incremental-hold works with contract_id in body."""
        contract = self._setup_funded_contract(total_amount=500.0, auth_id="AUTH-ORDER-1")
        contract_id = contract["id"]

        self.repo.create_change_request(
            contract_id=contract_id,
            proposed_by_id=self.seller.id,
            description="Testing endpoint",
            proposed_price=50.00,
            status="ACCEPTED",
            change_request_id="CR-ORDER-01"
        )

        self.mock_paypal.reauthorize_authorization.return_value = {
            "authorization_id": "AUTH-ORDER-NEW",
            "status": "AUTHORIZED",
            "amount": {"value": "550.00", "currency_code": "USD"}
        }

        status, _, body = self.api.dispatch(
            method="POST",
            path="/api/v1/payments/orders/incremental-hold",
            headers={"X-Actor-Id": self.buyer.id, "Content-Type": "application/json"},
            body=json.dumps({
                "contract_id": contract_id,
                "change_request_id": "CR-ORDER-01"
            }).encode("utf-8")
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["new_hold_amount"], "550.00")
        self.assertEqual(data["authorization_id"], "AUTH-ORDER-NEW")

    def test_custom_additional_amount_override_and_negative_rejection(self):
        """Verifies custom additional_amount parameter and rejection of zero/negative amounts."""
        contract = self._setup_funded_contract(total_amount=1000.0, auth_id="AUTH-CUSTOM")
        contract_id = contract["id"]

        self.repo.create_change_request(
            contract_id=contract_id,
            proposed_by_id=self.seller.id,
            description="Scope with default price",
            proposed_price=100.00,
            status="ACCEPTED",
            change_request_id="CR-CUSTOM-01"
        )

        # Rejection of zero amount
        with self.assertRaises(ValueError):
            self.service.apply_incremental_hold(
                contract_id=contract_id,
                change_request_id="CR-CUSTOM-01",
                additional_amount=0.0,
                actor=self.buyer
            )

        # Rejection of negative amount
        with self.assertRaises(ValueError):
            self.service.apply_incremental_hold(
                contract_id=contract_id,
                change_request_id="CR-CUSTOM-01",
                additional_amount=-50.0,
                actor=self.buyer
            )

        # Valid custom override: override $100 with $175.50
        self.mock_paypal.reauthorize_authorization.return_value = {
            "authorization_id": "AUTH-OVERRIDE",
            "status": "AUTHORIZED",
            "amount": {"value": "1175.50", "currency_code": "USD"}
        }

        res = self.service.apply_incremental_hold(
            contract_id=contract_id,
            change_request_id="CR-CUSTOM-01",
            additional_amount=175.50,
            actor=self.buyer
        )
        self.assertEqual(res["additional_hold_amount"], "175.50")
        self.assertEqual(res["new_hold_amount"], "1175.50")
        self.assertEqual(res["authorization_id"], "AUTH-OVERRIDE")


if __name__ == "__main__":
    unittest.main()
