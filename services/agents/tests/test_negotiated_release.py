"""
Acceptance Tests for Negotiated Partial Release & Seller Choice Logging (Task C47)
Linked Tasks: C47 / A14 (Milestone 3: Money & Extras)

Acceptance Criteria:
"Seller choice is stored and triggers the right payout or re-verification"
"""

import unittest
from datetime import datetime, timezone, timedelta

from services.agents.referee import (
    RefereeDecision,
    DecisionOutcome,
    FeatureDecision,
    SellerChoice,
    SettlementOffer,
    ChoiceResolution,
    NegotiatedReleaseEngine
)

class TestNegotiatedPartialRelease(unittest.TestCase):
    """Verifies agentic compromise offer generation and seller choice routing."""

    def setUp(self):
        self.engine = NegotiatedReleaseEngine()
        self.contract = {
            "id": "cnt_partial_888",
            "title": "E-Commerce Web Application",
            "seller_id": "usr_seller_bob",
            "buyer_id": "usr_buyer_alice",
            "total_amount": 1000.00,
            "currency": "USD"
        }

        # Simulated partial verification decision (80% pass, 20% fail)
        self.partial_decision = RefereeDecision(
            contract_id="cnt_partial_888",
            outcome=DecisionOutcome.PARTIAL_RELEASE,
            rule_triggered="RULE_PARTIAL_RELEASE_PROPORTIONAL",
            total_amount=1000.00,
            currency="USD",
            passed_amount=800.00,
            refund_amount=200.00,
            passed_weight=80.0,
            failed_weight=20.0,
            feature_decisions=[
                FeatureDecision(feature_id="f1", feature_title="User Auth", status="PASSED", price_weight=40.0, allocated_amount=400.00),
                FeatureDecision(feature_id="f2", feature_title="Product Catalog", status="PASSED", price_weight=40.0, allocated_amount=400.00),
                FeatureDecision(feature_id="f3", feature_title="Escrow Calculator", status="FAILED", price_weight=20.0, allocated_amount=200.00, reason="Over-release calculation bug")
            ]
        )

    def test_generate_compromise_settlement_offer(self):
        """Verifies referee generates an informative 'fix it or accept 80% now' offer."""
        offer = self.engine.generate_offer(self.partial_decision, self.contract, fix_window_hours=48)

        self.assertEqual(offer.contract_id, "cnt_partial_888")
        self.assertEqual(offer.passed_amount, 800.00)
        self.assertEqual(offer.refund_amount, 200.00)
        self.assertEqual(offer.passed_weight, 80.0)
        self.assertEqual(offer.failed_weight, 20.0)
        self.assertEqual(len(offer.failed_features), 1)
        self.assertEqual(offer.fix_window_hours, 48)

        # Verify conversational rationale
        self.assertIn("Fix It or Accept 80% Now", offer.conversational_offer)
        self.assertIn("Option A (Accept Partial Payout)", offer.conversational_offer)
        self.assertIn("Option B (Fix and Resubmit)", offer.conversational_offer)
        self.assertIn("Escrow Calculator", offer.conversational_offer)

    def test_seller_accepts_partial_payout_triggers_settled_state(self):
        """
        ACCEPTANCE CRITERIA:
        Seller chooses to accept partial release now -> choice logged, triggers payout, moves DECISION -> SETTLED.
        """
        offer = self.engine.generate_offer(self.partial_decision, self.contract)

        resolution = self.engine.process_seller_choice(
            offer=offer,
            choice=SellerChoice.ACCEPT_PARTIAL_PAYOUT,
            seller_id="usr_seller_bob",
            contract=self.contract,
            note="Accepting 80% payout to close project today."
        )

        # 1. State transition
        self.assertEqual(resolution.previous_state, "DECISION")
        self.assertEqual(resolution.next_state, "SETTLED")

        # 2. Payout instruction generated for Payments team
        self.assertIsNotNone(resolution.payout_instruction)
        self.assertEqual(resolution.payout_instruction["action"], "CAPTURE_AND_DISBURSE")
        self.assertEqual(resolution.payout_instruction["passed_amount"], 800.00)
        self.assertEqual(resolution.payout_instruction["refund_amount"], 200.00)
        self.assertEqual(resolution.payout_instruction["seller_id"], "usr_seller_bob")

        # 3. No re-verification needed
        self.assertIsNone(resolution.reverification_schedule)

        # 4. Audit trail stored with timestamp
        self.assertTrue(len(resolution.timestamp) > 0)
        self.assertIn("accepted partial release", resolution.audit_log_entry.lower())
        self.assertIn("SETTLED", resolution.audit_log_entry)

    def test_seller_chooses_fix_and_resubmit_triggers_in_progress(self):
        """
        ACCEPTANCE CRITERIA:
        Seller chooses to fix flaws -> choice logged, grants extension, moves DECISION -> IN_PROGRESS for re-verification.
        """
        offer = self.engine.generate_offer(self.partial_decision, self.contract, fix_window_hours=24)

        resolution = self.engine.process_seller_choice(
            offer=offer,
            choice=SellerChoice.FIX_AND_RESUBMIT,
            seller_id="usr_seller_bob",
            contract=self.contract,
            note="Pushing fix for calculator formula tonight."
        )

        # 1. State transition
        self.assertEqual(resolution.previous_state, "DECISION")
        self.assertEqual(resolution.next_state, "IN_PROGRESS")

        # 2. Re-verification scheduled
        self.assertIsNotNone(resolution.reverification_schedule)
        self.assertEqual(resolution.reverification_schedule["action"], "REVERIFY_SANDBOX")
        self.assertEqual(resolution.reverification_schedule["fix_window_hours"], 24)
        self.assertEqual(resolution.reverification_schedule["next_submission_attempt"], 2)
        self.assertIn("f3", resolution.reverification_schedule["failed_features_to_fix"])

        # 3. Zero immediate payouts while in revision
        self.assertIsNone(resolution.payout_instruction)

        # 4. Audit trail stored
        self.assertIn("chose to fix and resubmit", resolution.audit_log_entry.lower())
        self.assertIn("IN_PROGRESS", resolution.audit_log_entry)

    def test_seller_chooses_dispute(self):
        """Verifies dispute choice escalates to DISPUTE state."""
        offer = self.engine.generate_offer(self.partial_decision, self.contract)

        resolution = self.engine.process_seller_choice(
            offer=offer,
            choice=SellerChoice.DISPUTE,
            seller_id="usr_seller_bob",
            contract=self.contract,
            note="Test runner had faulty environment setup."
        )

        self.assertEqual(resolution.next_state, "DISPUTE")
        self.assertIn("disputed", resolution.audit_log_entry.lower())

    def test_unauthorized_user_cannot_submit_choice(self):
        """Verifies only the assigned seller (or admin) can choose a resolution."""
        offer = self.engine.generate_offer(self.partial_decision, self.contract)

        with self.assertRaises(PermissionError):
            self.engine.process_seller_choice(
                offer=offer,
                choice=SellerChoice.ACCEPT_PARTIAL_PAYOUT,
                seller_id="usr_intruder_eve",
                contract=self.contract
            )

if __name__ == "__main__":
    unittest.main()

