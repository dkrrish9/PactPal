#!/usr/bin/env python3
"""
PactPal Milestone 1: Auto-Validation & Clarification Loop Acceptance Test (Task C16)
Validates that:
1. Invalid contract terms (weights != 100%, missing tests, past deadlines, totals mismatch)
   strictly trigger a Clarification Request to the buyer instead of an AI guess.
2. The AI Referee explicitly refuses to fabricate or fudge financial numbers.
3. Applying buyer clarification answers successfully resolves the contract into a valid checklist.
"""

import unittest
from datetime import datetime, timezone, timedelta

from ..agreement_reader.models import PricedChecklist, ClarificationRequest
from ..agreement_reader.reader import parse_contract_form, read_or_clarify, AgreementValidationError
from ..agreement_reader.clarifier import generate_clarification_request, apply_clarification

class TestAutoValidationClarification(unittest.TestCase):

    def setUp(self):
        self.future_date = (datetime.now(timezone.utc) + timedelta(days=21)).isoformat()
        self.base_form = {
            "title": "Fintech Dashboard Contract",
            "total_amount": 1000.00,
            "currency": "USD",
            "deadline": self.future_date,
            "features": [
                {"name": "Auth Flow", "weight": 50.0, "test": "User can login with 2FA"},
                {"name": "Dashboard UI", "weight": 50.0, "test": "Charts render real-time websocket data"}
            ]
        }

    def test_weights_not_100_triggers_clarify_not_guess(self):
        """
        Checklist Acceptance Test (C16 Done When):
        Invalid weights must trigger a clarify request to the buyer instead of an AI guess.
        """
        invalid_form = dict(self.base_form)
        invalid_form["features"] = [
            {"name": "Feature A", "weight": 40.0, "test": "Test condition A"},
            {"name": "Feature B", "weight": 45.0, "test": "Test condition B"}  # Sum = 85.0%, missing 15.0%!
        ]

        result = read_or_clarify(invalid_form)

        # 1. Assert status requires clarification
        self.assertEqual(result["status"], "NEEDS_CLARIFICATION")
        # 2. Assert system DID NOT guess or produce an unverified checklist
        self.assertIsNone(result["checklist"], "System must never guess and produce a checklist when invalid")

        # 3. Assert structured ClarificationRequest is present
        clarify_req: ClarificationRequest = result["clarification_request"]
        self.assertIsNotNone(clarify_req)
        self.assertEqual(clarify_req.status, "NEEDS_CLARIFICATION")

        # 4. Assert conversational prompt explicitly rejects guessing
        self.assertIn("NEVER guess", clarify_req.conversational_message)
        self.assertIn("+15.0%", clarify_req.conversational_message)
        self.assertTrue(any("Feature price weights must sum to exactly 100.0%" in e for e in clarify_req.raw_errors))

    def test_missing_acceptance_test_triggers_clarify_not_guess(self):
        """Missing acceptance test triggers a clarification request naming the feature."""
        invalid_form = dict(self.base_form)
        invalid_form["features"] = [
            {"name": "Auth Flow", "weight": 50.0, "test": "User can login with 2FA"},
            {"name": "Payment Gateway", "weight": 50.0, "test": "   "}  # Missing test!
        ]

        result = read_or_clarify(invalid_form)
        self.assertEqual(result["status"], "NEEDS_CLARIFICATION")
        self.assertIsNone(result["checklist"])

        clarify_req = result["clarification_request"]
        self.assertTrue(any("Payment Gateway" in c.issue for c in clarify_req.clarifications))
        self.assertTrue(any("missing a measurable acceptance test" in c.issue for c in clarify_req.clarifications))

    def test_past_deadline_triggers_clarify_not_guess(self):
        """Past deadline triggers a clarification request asking for future milestone date."""
        invalid_form = dict(self.base_form)
        invalid_form["deadline"] = "2021-05-15T00:00:00Z"

        result = read_or_clarify(invalid_form)
        self.assertEqual(result["status"], "NEEDS_CLARIFICATION")
        self.assertIsNone(result["checklist"])

        clarify_req = result["clarification_request"]
        self.assertTrue(any("is in the past" in c.issue for c in clarify_req.clarifications))

    def test_totals_mismatch_triggers_clarify_not_guess(self):
        """
        Invariant 4: Totals Match.
        If feature explicit prices do not match total_amount, triggers clarify request.
        """
        invalid_form = dict(self.base_form)
        invalid_form["total_amount"] = 1000.00
        invalid_form["features"] = [
            {"name": "Feature 1", "weight": 50.0, "price": 400.00, "test": "Test 1"},
            {"name": "Feature 2", "weight": 50.0, "price": 500.00, "test": "Test 2"}  # Sum = 900.00 != 1000.00!
        ]

        result = read_or_clarify(invalid_form)
        self.assertEqual(result["status"], "NEEDS_CLARIFICATION")
        self.assertIsNone(result["checklist"])

        clarify_req = result["clarification_request"]
        self.assertTrue(any("does not match total contract amount" in c.issue for c in clarify_req.clarifications))
        self.assertTrue(any("$900.00" in c.issue and "$1000.00" in c.issue for c in clarify_req.clarifications))

    def test_buyer_clarification_resolution_cycle(self):
        """
        Proves the complete end-to-end resolution loop:
        1. Buyer submits flawed contract (weights = 85%, missing test).
        2. System triggers Clarification Request.
        3. Buyer responds with corrections.
        4. Contract re-evaluates and generates valid, locked checklist.
        """
        flawed_form = {
            "title": "E-Commerce Integration",
            "total_amount": 2000.00,
            "currency": "USD",
            "deadline": self.future_date,
            "features": [
                {"name": "Cart Service", "weight": 40.0, "test": "Items persist across sessions"},
                {"name": "Checkout API", "weight": 45.0, "test": ""}  # Missing 15% weight & missing test!
            ]
        }

        # Step 1: Initial submission fails auto-validation
        initial_result = read_or_clarify(flawed_form)
        self.assertEqual(initial_result["status"], "NEEDS_CLARIFICATION")
        self.assertIsNone(initial_result["checklist"])
        self.assertEqual(len(initial_result["clarification_request"].clarifications), 2)

        # Step 2: Buyer provides clarification answers
        buyer_answers = {
            "weights": {
                "Cart Service": 40.0,
                "Checkout API": 60.0  # 40 + 60 = 100%!
            },
            "tests": {
                "Checkout API": "Stripe test payment returns 200 and receipt JSON is created."
            }
        }

        # Step 3: Apply buyer answers
        corrected_form = apply_clarification(flawed_form, buyer_answers)

        # Step 4: Re-evaluate
        resolved_result = read_or_clarify(corrected_form)
        self.assertEqual(resolved_result["status"], "VALID")
        self.assertIsNone(resolved_result["clarification_request"])

        checklist: PricedChecklist = resolved_result["checklist"]
        self.assertIsNotNone(checklist)
        self.assertEqual(len(checklist.features), 2)
        self.assertEqual(checklist.features[0].price_weight, 40.0)
        self.assertEqual(checklist.features[0].allocated_amount, 800.00)
        self.assertEqual(checklist.features[1].price_weight, 60.0)
        self.assertEqual(checklist.features[1].allocated_amount, 1200.00)
        self.assertEqual(checklist.features[1].acceptance_test, "Stripe test payment returns 200 and receipt JSON is created.")

if __name__ == "__main__":
    unittest.main()
