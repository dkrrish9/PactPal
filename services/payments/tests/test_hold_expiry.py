"""
Unit and Integration Tests for Authorization Expiry & Hold Countdown (Commit C14)
Validates:
  - 29-day authorization hold limit calculation
  - Real-time countdown: seconds_remaining and ceil(days_remaining)
  - Status progression: HELD -> EXPIRING_SOON (<= 3 days) -> EXPIRED
  - Boundary and expired clamping (seconds_remaining >= 0)
  - Unfunded contract and non-existent contract guards
  - RBAC: Buyer, Seller, and Admin authorized; third party forbidden
  - HTTP REST endpoint GET /api/v1/contracts/{id}/hold conforming to shared/docs/SHARED_API_CONTRACT.md
"""

import json
import unittest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

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

class TestHoldExpiryAndCountdown(unittest.TestCase):

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
        self.stranger = self.repo.create_user(
            name="Charlie Stranger",
            email="stranger@pactpal.test",
            role=UserRole.BUYER
        )

        self.service = EscrowPaymentService(repository=self.repo)
        self.api_handler = PaymentsAPIHandler(service=self.service)

    def tearDown(self):
        self.repo.close()

    def _create_funded_contract(
        self,
        amount: float = 1500.0,
        funded_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Creates a contract and transitions it to FUNDED with live PayPal authorization metadata."""
        contract = self.repo.create_contract(
            buyer=self.buyer,
            seller_id=self.seller.id,
            title="E-commerce Platform v2",
            description="Escrow funded milestone",
            total_amount=amount,
            deadline=(datetime.now(timezone.utc) + timedelta(days=20)).isoformat()
        )
        cid = contract["id"]

        # Advance DRAFT -> REVIEW -> SIGNED -> FUNDED
        self.repo.transition_contract(cid, self.buyer, ContractState.REVIEW)
        self.repo.transition_contract(cid, self.seller, ContractState.SIGNED, metadata={"acceptance_confirmed": True})

        auth_meta = {
            "paypal_order_id": "ORDER_PP_123456",
            "paypal_auth_id": "8BA1234567890123"
        }
        funded_contract = self.repo.transition_contract(cid, self.buyer, ContractState.FUNDED, metadata=auth_meta)

        # If a custom funded_at timestamp is requested, manually adjust the DB record
        if funded_at:
            funded_iso = funded_at.isoformat()
            expires_iso = (funded_at + timedelta(days=29)).isoformat()
            cursor = self.repo.conn.cursor()
            cursor.execute(
                "UPDATE contracts SET funded_at = ?, auth_expires_at = ? WHERE id = ?",
                (funded_iso, expires_iso, cid)
            )
            self.repo.conn.commit()
            funded_contract = self.repo.get_contract(cid)

        return funded_contract

    # --- 1. Expiry Calculation & Countdown Tests ---

    def test_initial_hold_expiry_calculation(self):
        """At authorization inception, countdown equals 29 days with HELD status."""
        t0 = datetime(2026, 11, 10, 1, 30, 0, tzinfo=timezone.utc)
        contract = self._create_funded_contract(amount=1500.00, funded_at=t0)

        # Query at T0
        hold = self.service.get_contract_hold(contract["id"], actor=self.buyer, current_time=t0)

        self.assertEqual(hold["contract_id"], contract["id"])
        self.assertEqual(hold["authorization_id"], "8BA1234567890123")
        self.assertEqual(hold["amount"], "1500.00")
        self.assertEqual(hold["currency"], "USD")
        self.assertEqual(hold["status"], "HELD")
        self.assertFalse(hold["is_expired"])
        self.assertEqual(hold["days_remaining"], 29)
        self.assertEqual(hold["seconds_remaining"], 29 * 86400)
        self.assertEqual(hold["expires_at"], (t0 + timedelta(days=29)).isoformat())

    def test_mid_cycle_countdown_day_15(self):
        """At Day 15 (14 days left), countdown calculates correctly."""
        t0 = datetime(2026, 11, 10, 1, 30, 0, tzinfo=timezone.utc)
        contract = self._create_funded_contract(amount=1500.00, funded_at=t0)

        # Current time is 15 days later
        now = t0 + timedelta(days=15)
        hold = self.service.get_contract_hold(contract["id"], actor=self.buyer, current_time=now)

        self.assertEqual(hold["status"], "HELD")
        self.assertFalse(hold["is_expired"])
        self.assertEqual(hold["days_remaining"], 14)
        self.assertEqual(hold["seconds_remaining"], 14 * 86400)

    def test_expiring_soon_status_within_three_days(self):
        """When 3 days or fewer remain (<= 259,200s), status becomes EXPIRING_SOON."""
        t0 = datetime(2026, 11, 10, 1, 30, 0, tzinfo=timezone.utc)
        contract = self._create_funded_contract(amount=1500.00, funded_at=t0)

        # 27 days in -> 2 days remaining (<= 3 days honor period threshold)
        now = t0 + timedelta(days=27)
        hold = self.service.get_contract_hold(contract["id"], actor=self.seller, current_time=now)

        self.assertEqual(hold["status"], "EXPIRING_SOON")
        self.assertFalse(hold["is_expired"])
        self.assertEqual(hold["days_remaining"], 2)
        self.assertEqual(hold["seconds_remaining"], 2 * 86400)

    def test_partial_day_ceiling_rounding(self):
        """Ensure days_remaining uses ceiling: 1 second or partial day rounds UP to next full day."""
        t0 = datetime(2026, 11, 10, 1, 30, 0, tzinfo=timezone.utc)
        contract = self._create_funded_contract(amount=1500.00, funded_at=t0)

        # 28 days + 14 hours in -> 10 hours left (36,000 seconds)
        now = t0 + timedelta(days=28, hours=14)
        hold = self.service.get_contract_hold(contract["id"], actor=self.buyer, current_time=now)

        self.assertEqual(hold["seconds_remaining"], 36000)
        # ceil(36000 / 86400) = 1
        self.assertEqual(hold["days_remaining"], 1)
        self.assertEqual(hold["status"], "EXPIRING_SOON")
        self.assertFalse(hold["is_expired"])

        # 27 days + 23 hours in -> 25 hours left (90,000 seconds)
        now_25h = t0 + timedelta(days=27, hours=23)
        hold_25h = self.service.get_contract_hold(contract["id"], actor=self.buyer, current_time=now_25h)
        # ceil(90000 / 86400) = 2
        self.assertEqual(hold_25h["days_remaining"], 2)

    def test_exact_expiration_boundary(self):
        """At exactly 29 days, seconds_remaining=0, days_remaining=0, status=EXPIRED, is_expired=True."""
        t0 = datetime(2026, 11, 10, 1, 30, 0, tzinfo=timezone.utc)
        contract = self._create_funded_contract(amount=1500.00, funded_at=t0)

        now = t0 + timedelta(days=29)
        hold = self.service.get_contract_hold(contract["id"], actor=self.admin, current_time=now)

        self.assertEqual(hold["status"], "EXPIRED")
        self.assertTrue(hold["is_expired"])
        self.assertEqual(hold["seconds_remaining"], 0)
        self.assertEqual(hold["days_remaining"], 0)

    def test_past_expiration_is_clamped(self):
        """Past 29 days, seconds_remaining does not go negative; clamped to 0."""
        t0 = datetime(2026, 11, 10, 1, 30, 0, tzinfo=timezone.utc)
        contract = self._create_funded_contract(amount=1500.00, funded_at=t0)

        # 35 days in (6 days past expiry)
        now = t0 + timedelta(days=35)
        hold = self.service.get_contract_hold(contract["id"], actor=self.buyer, current_time=now)

        self.assertEqual(hold["status"], "EXPIRED")
        self.assertTrue(hold["is_expired"])
        self.assertEqual(hold["seconds_remaining"], 0)
        self.assertEqual(hold["days_remaining"], 0)

    # --- 2. Guards & Permissions Tests ---

    def test_unfunded_contract_raises_error(self):
        """Calling hold expiry on DRAFT, REVIEW, or SIGNED contract raises StateValidationError."""
        draft = self.repo.create_contract(
            buyer=self.buyer,
            seller_id=self.seller.id,
            title="Draft Contract",
            description="Not yet funded",
            total_amount=500.0,
            deadline=(datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        )

        with self.assertRaises(StateValidationError):
            self.service.get_contract_hold(draft["id"], actor=self.buyer)

    def test_nonexistent_contract_raises_error(self):
        """Calling hold on non-existent ID raises ValueError."""
        with self.assertRaises(ValueError):
            self.service.get_contract_hold("00000000-0000-0000-0000-000000000000", actor=self.buyer)

    def test_rbac_buyer_seller_admin_allowed(self):
        """Buyer, Seller, and Admin can all access hold details."""
        contract = self._create_funded_contract()
        cid = contract["id"]

        hold_buyer = self.service.get_contract_hold(cid, actor=self.buyer)
        self.assertEqual(hold_buyer["contract_id"], cid)

        hold_seller = self.service.get_contract_hold(cid, actor=self.seller)
        self.assertEqual(hold_seller["contract_id"], cid)

        hold_admin = self.service.get_contract_hold(cid, actor=self.admin)
        self.assertEqual(hold_admin["contract_id"], cid)

    def test_rbac_unrelated_party_forbidden(self):
        """Third party user attempting to read hold details raises ForbiddenActionError."""
        contract = self._create_funded_contract()
        cid = contract["id"]

        with self.assertRaises(ForbiddenActionError):
            self.service.get_contract_hold(cid, actor=self.stranger)

    # --- 3. REST API HTTP Endpoint Tests (GET /api/v1/contracts/{id}/hold) ---

    def test_api_get_hold_success(self):
        """GET /api/v1/contracts/{id}/hold returns 200 OK with correct JSON schema."""
        contract = self._create_funded_contract(amount=2500.0)
        cid = contract["id"]

        status, headers, body = self.api_handler.dispatch(
            method="GET",
            path=f"/api/v1/contracts/{cid}/hold",
            headers={"X-Actor-Id": self.buyer.id}
        )

        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/json")

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(payload["contract_id"], cid)
        self.assertEqual(payload["authorization_id"], "8BA1234567890123")
        self.assertEqual(payload["amount"], "2500.00")
        self.assertEqual(payload["currency"], "USD")
        self.assertIn(payload["status"], ["HELD", "EXPIRING_SOON", "EXPIRED"])
        self.assertIn("authorized_at", payload)
        self.assertIn("expires_at", payload)
        self.assertIn("days_remaining", payload)
        self.assertIn("seconds_remaining", payload)
        self.assertIn("is_expired", payload)

    def test_api_get_hold_bearer_auth(self):
        """Authorization: Bearer <actor_id> header is accepted."""
        contract = self._create_funded_contract(amount=1200.0)
        cid = contract["id"]

        status, headers, body = self.api_handler.dispatch(
            method="GET",
            path=f"/api/v1/contracts/{cid}/hold",
            headers={"Authorization": f"Bearer {self.seller.id}"}
        )

        self.assertEqual(status, 200)
        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(payload["contract_id"], cid)

    def test_api_get_hold_unauthorized_missing_actor(self):
        """Missing auth headers returns 401 Unauthorized."""
        contract = self._create_funded_contract()
        cid = contract["id"]

        status, headers, body = self.api_handler.dispatch(
            method="GET",
            path=f"/api/v1/contracts/{cid}/hold",
            headers={}
        )

        self.assertEqual(status, 401)
        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(payload["error"], "UNAUTHORIZED")

    def test_api_get_hold_forbidden_stranger(self):
        """Unrelated user returns 403 Forbidden."""
        contract = self._create_funded_contract()
        cid = contract["id"]

        status, headers, body = self.api_handler.dispatch(
            method="GET",
            path=f"/api/v1/contracts/{cid}/hold",
            headers={"X-Actor-Id": self.stranger.id}
        )

        self.assertEqual(status, 403)
        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(payload["error"], "FORBIDDEN")

    def test_api_get_hold_not_found(self):
        """Non-existent contract ID returns 404 Not Found."""
        status, headers, body = self.api_handler.dispatch(
            method="GET",
            path="/api/v1/contracts/non-existent-uuid/hold",
            headers={"X-Actor-Id": self.buyer.id}
        )

        self.assertEqual(status, 404)
        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(payload["error"], "NOT_FOUND")

    def test_api_get_hold_bad_request_unfunded(self):
        """Unfunded draft contract returns 400 Bad Request."""
        draft = self.repo.create_contract(
            buyer=self.buyer,
            seller_id=self.seller.id,
            title="Draft Contract",
            description="Desc",
            total_amount=500.0,
            deadline=(datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        )

        status, headers, body = self.api_handler.dispatch(
            method="GET",
            path=f"/api/v1/contracts/{draft['id']}/hold",
            headers={"X-Actor-Id": self.buyer.id}
        )

        self.assertEqual(status, 400)
        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(payload["error"], "BAD_REQUEST")

    def test_api_get_hold_method_not_allowed(self):
        """Attempting POST to /hold endpoint returns 405 Method Not Allowed."""
        contract = self._create_funded_contract()
        cid = contract["id"]

        status, headers, body = self.api_handler.dispatch(
            method="POST",
            path=f"/api/v1/contracts/{cid}/hold",
            headers={"X-Actor-Id": self.buyer.id}
        )

        self.assertEqual(status, 405)
        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(payload["error"], "METHOD_NOT_ALLOWED")

    def test_wsgi_app_callable(self):
        """Ensure create_payments_app returns a valid WSGI callable that responds to requests."""
        contract = self._create_funded_contract(amount=1800.0)
        cid = contract["id"]

        wsgi_app = create_payments_app(service=self.service)

        captured_status = []
        captured_headers = []

        def start_response(status, headers):
            captured_status.append(status)
            captured_headers.append(headers)

        import io
        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": f"/api/v1/contracts/{cid}/hold",
            "HTTP_X_ACTOR_ID": self.buyer.id,
            "wsgi.input": io.BytesIO(b""),
            "CONTENT_LENGTH": "0"
        }

        response_chunks = wsgi_app(environ, start_response)
        response_body = b"".join(response_chunks)

        self.assertEqual(captured_status[0], "200 OK")
        payload = json.loads(response_body.decode("utf-8"))
        self.assertEqual(payload["amount"], "1800.00")
        self.assertEqual(payload["status"], "HELD")

if __name__ == "__main__":
    unittest.main()

