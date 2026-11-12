#!/usr/bin/env python3
"""
Test Unified Backend Gateway Endpoints & Routing.
"""

import unittest
import json
from services.gateway import UnifiedGateway

class TestUnifiedGateway(unittest.TestCase):
    def setUp(self):
        # Use isolated in-memory DB with seed_demo=True
        self.gateway = UnifiedGateway(db_path=":memory:", seed_demo=True)

    def test_health_endpoint(self):
        status, headers, body = self.gateway.dispatch("GET", "/api/v1/health", {})
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "healthy")
        self.assertGreaterEqual(data["contracts_count"], 4)

    def test_list_contracts(self):
        status, headers, body = self.gateway.dispatch("GET", "/api/v1/contracts", {})
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("data", data)
        self.assertGreaterEqual(data["total"], 4)

    def test_get_contract_detail(self):
        status, headers, body = self.gateway.dispatch("GET", "/api/v1/contracts/pct_099e77", {})
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["id"], "pct_099e77")
        self.assertEqual(data["status"], "FUNDED")
        self.assertEqual(len(data["features"]), 3)

    def test_payments_hold_delegation(self):
        status, headers, body = self.gateway.dispatch("GET", "/api/v1/contracts/pct_099e77/hold", {})
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertIn("contract_id", data)
        self.assertEqual(data["contract_id"], "pct_099e77")
        self.assertIn("days_remaining", data)
        self.assertIn("seconds_remaining", data)
        self.assertFalse(data["is_expired"])

    def test_price_negotiator_change_request(self):
        payload = json.dumps({
            "description": "Add dark mode toggle and persistence",
            "requested_price": 200.0,
            "currency": "USD"
        }).encode("utf-8")
        status, headers, body = self.gateway.dispatch("POST", "/api/v1/negotiator/change-request", {}, payload)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["complexity"], "LOW")
        self.assertEqual(data["proposed_price"], 200.0)
        self.assertIn("suggested_acceptance_test", data)

    def test_referee_negotiate_offer(self):
        payload = json.dumps({
            "contract_id": "pct_099e77",
            "action": "offer",
            "passed_weight": 80.0
        }).encode("utf-8")
        status, headers, body = self.gateway.dispatch("POST", "/api/v1/referee/negotiate", {}, payload)
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["contract_id"], "pct_099e77")
        self.assertEqual(data["passed_weight"], 80.0)
        self.assertEqual(data["passed_amount"], 1200.0)

    def test_contract_messages(self):
        # 1. Post message
        payload = json.dumps({
            "content": "Hello referee and buyer!",
            "sender_type": "SELLER"
        }).encode("utf-8")
        status, headers, body = self.gateway.dispatch("POST", "/api/v1/contracts/pct_099e77/messages", {}, payload)
        self.assertEqual(status, 201)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["content"], "Hello referee and buyer!")

        # 2. Get messages
        status, headers, body = self.gateway.dispatch("GET", "/api/v1/contracts/pct_099e77/messages", {})
        self.assertEqual(status, 200)
        msg_data = json.loads(body.decode("utf-8"))
        self.assertGreaterEqual(msg_data["total"], 1)

if __name__ == "__main__":
    unittest.main()
