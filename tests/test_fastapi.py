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

if __name__ == "__main__":
    unittest.main()

