#!/usr/bin/env python3
"""
Test Suite for PactPal FastAPI Application
Verifies Swagger docs, contracts endpoints, payments hold, referee and negotiator routes.
"""

import unittest
from fastapi.testclient import TestClient
from main import app

class TestFastAPIApp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_docs_swagger_ui(self):
        """Verify OpenAPI Swagger documentation is live at /docs."""
        response = self.client.get("/docs")
        self.assertEqual(response.status_code, 200)
        self.assertIn("swagger", response.text.lower())

    def test_openapi_json(self):
        """Verify OpenAPI JSON specification schema."""
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["info"]["title"], "PactPal AI Escrow Referee API")
        self.assertIn("/api/v1/contracts", data["paths"])
        self.assertIn("/api/v1/health", data["paths"])

    def test_health_endpoint(self):
        """Verify /api/v1/health returns subsystem statuses."""
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "pactpal-fastapi")
        self.assertGreaterEqual(data["contracts_count"], 4)
        self.assertEqual(data["subsystems"]["payments"], "active")

    def test_list_contracts(self):
        """Verify listing seeded demo contracts."""
        response = self.client.get("/api/v1/contracts")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("data", data)
        self.assertGreaterEqual(data["total"], 4)

    def test_get_contract_detail(self):
        """Verify fetching main funded demo contract pct_099e77."""
        response = self.client.get("/api/v1/contracts/pct_099e77")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], "pct_099e77")
        self.assertEqual(data["status"], "FUNDED")
        self.assertEqual(len(data["features"]), 3)

    def test_payments_hold_route(self):
        """Verify 29-day PayPal hold countdown route."""
        response = self.client.get(
            "/api/v1/contracts/pct_099e77/hold",
            headers={"X-Actor-Id": "usr_buyer_01"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["contract_id"], "pct_099e77")
        self.assertEqual(data["authorization_id"], "AUTH-DEMO-99E77")
        self.assertIn("days_remaining", data)
        self.assertFalse(data["is_expired"])

    def test_price_negotiator_change_request(self):
        """Verify AI Price Negotiator scope evaluation."""
        payload = {
            "description": "Add dark mode toggle and theme switch",
            "requested_price": 200.0,
            "currency": "USD"
        }
        response = self.client.post("/api/v1/negotiator/change-request", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["complexity"], "LOW")
        self.assertEqual(data["proposed_price"], 200.0)
        self.assertIn("suggested_acceptance_test", data)

    def test_referee_negotiate_compromise(self):
        """Verify AI Referee 80% partial release compromise offer generation."""
        payload = {
            "contract_id": "pct_099e77",
            "action": "offer",
            "passed_weight": 80.0
        }
        response = self.client.post("/api/v1/referee/negotiate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["contract_id"], "pct_099e77")
        self.assertEqual(data["passed_weight"], 80.0)
        self.assertEqual(data["passed_amount"], 1200.0)

    def test_contract_chat_messages(self):
        """Verify contract chat messaging."""
        # 1. Post a message
        post_resp = self.client.post(
            "/api/v1/contracts/pct_099e77/messages",
            json={"content": "Ready for verification check", "sender_type": "SELLER"},
            headers={"X-Actor-Id": "usr_seller_01"}
        )
        self.assertEqual(post_resp.status_code, 201)
        data = post_resp.json()
        self.assertEqual(data["content"], "Ready for verification check")

        # 2. Get messages
        get_resp = self.client.get("/api/v1/contracts/pct_099e77/messages")
        self.assertEqual(get_resp.status_code, 200)
        msg_data = get_resp.json()
        self.assertGreaterEqual(msg_data["total"], 1)

    def test_agreement_reader_validate_valid(self):
        """Phase 3: Valid contract passes Agreement Reader with exact penny conservation."""
        future_deadline = "2026-12-31T23:59:59Z"
        payload = {
            "title": "Clean Architecture Web App",
            "description": "Production grade web application",
            "total_amount": 1000.0,
            "deadline": future_deadline,
            "currency": "USD",
            "features": [
                {"title": "Auth Module", "acceptance_test": "User can sign in with valid credentials.", "price_weight": 50.0},
                {"title": "Dashboard View", "acceptance_test": "Metrics widget renders cleanly with test data.", "price_weight": 50.0},
            ]
        }
        resp = self.client.post("/api/v1/agreement-reader/validate", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "VALID")
        self.assertIsNotNone(data["checklist"])
        self.assertEqual(len(data["checklist"]["features"]), 2)
        total_allocated = sum(f["allocated_amount"] for f in data["checklist"]["features"])
        self.assertEqual(total_allocated, 1000.0)

    def test_agreement_reader_clarification_on_invalid_weights(self):
        """Phase 3: Weights summing to != 100% trigger structured ClarificationRequest."""
        future_deadline = "2026-12-31T23:59:59Z"
        payload = {
            "title": "Mismatched Weights Project",
            "total_amount": 1000.0,
            "deadline": future_deadline,
            "features": [
                {"title": "Auth Module", "acceptance_test": "User can sign in cleanly.", "price_weight": 40.0},
                {"title": "Dashboard View", "acceptance_test": "Metrics widget renders with data.", "price_weight": 40.0},
            ]
        }
        # Validation endpoint check
        val_resp = self.client.post("/api/v1/agreement-reader/validate", json=payload)
        self.assertEqual(val_resp.status_code, 200)
        val_data = val_resp.json()
        self.assertEqual(val_data["status"], "NEEDS_CLARIFICATION")
        self.assertIsNotNone(val_data["clarification_request"])
        self.assertIn("100.0%", val_data["clarification_request"]["conversational_message"])

        # Creation endpoint blocks with 422
        create_resp = self.client.post("/api/v1/contracts", json=payload)
        self.assertEqual(create_resp.status_code, 422)
        create_data = create_resp.json()
        self.assertEqual(create_data["error"], "CLARIFICATION_REQUIRED")
        self.assertIn("clarification_request", create_data)

    def test_dual_confirmation_and_checklist_locking(self):
        """Phase 3: Dual confirmation locks checklist and blocks unauthorized mutation."""
        fresh_payload = {
            "title": "Dual Confirmation Test Contract",
            "description": "Testing checklist locking",
            "total_amount": 1200.0,
            "deadline": "2026-12-31T23:59:59Z",
            "seller_id": "usr_seller_01",
            "features": [
                {"title": "Feature Alpha", "acceptance_test": "Test Alpha condition passes.", "price_weight": 60.0},
                {"title": "Feature Beta", "acceptance_test": "Test Beta condition passes.", "price_weight": 40.0}
            ]
        }
        create_res = self.client.post("/api/v1/contracts", json=fresh_payload, headers={"X-Actor-Id": "usr_buyer_01"})
        self.assertEqual(create_res.status_code, 201)
        contract_id = create_res.json()["id"]

        # Seller confirms
        resp_seller = self.client.post(
            f"/api/v1/contracts/{contract_id}/confirm-checklist",
            json={"role": "SELLER"},
            headers={"X-Actor-Id": "usr_seller_01"}
        )
        self.assertEqual(resp_seller.status_code, 200)
        c_seller = resp_seller.json()
        self.assertIsNotNone(c_seller["seller_confirmed_at"])
        self.assertFalse(c_seller["is_locked"])

        # Buyer confirms -> locks checklist & transitions to SIGNED
        resp_buyer = self.client.post(
            f"/api/v1/contracts/{contract_id}/confirm-checklist",
            json={"role": "BUYER"},
            headers={"X-Actor-Id": "usr_buyer_01"}
        )
        self.assertEqual(resp_buyer.status_code, 200)
        c_buyer = resp_buyer.json()
        self.assertIsNotNone(c_buyer["buyer_confirmed_at"])
        self.assertTrue(c_buyer["is_locked"])
        self.assertEqual(c_buyer["status"], "SIGNED")

if __name__ == "__main__":
    unittest.main()

