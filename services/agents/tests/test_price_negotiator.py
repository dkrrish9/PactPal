"""
PactPal Milestone 3: AI Price Negotiator Acceptance Tests (Task C38)
Linked Task: C38 / A12

Acceptance Criteria:
"Proposes extra price and extra time with an explanation"
"""

import unittest
from datetime import datetime, timezone, timedelta

from services.agents.negotiator import PriceNegotiator, ComplexityLevel, ChangeRequestProposal
from services.agents.agreement_reader.models import PricedChecklist, ChecklistFeature

class TestPriceNegotiator(unittest.TestCase):
    """Verifies that the AI Price Negotiator computes objective price, timeline, and reasoning."""

    def setUp(self):
        self.negotiator = PriceNegotiator()
        self.mock_contract = {
            "id": "cnt_negotiate_001",
            "title": "SaaS Platform MVP",
            "total_amount": 1000.00,
            "currency": "USD",
            "deadline": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
            "features": [
                {"id": "f1", "title": "Landing Page", "price_weight": 50.0, "allocated_amount": 500.00},
                {"id": "f2", "title": "Dashboard UI", "price_weight": 50.0, "allocated_amount": 500.00}
            ]
        }

    def test_oauth_scope_change_proposal(self):
        """
        ACCEPTANCE CRITERIA:
        Proposes extra price, extra time, and an explanation for OAuth addition.
        """
        desc = "Add Google OAuth and JWT session authentication"
        proposal = self.negotiator.evaluate_change_request(self.mock_contract, desc)

        # 1. Proposes extra price > 0
        self.assertGreater(proposal.proposed_price, 0)
        self.assertEqual(proposal.proposed_price, 250.00)

        # 2. Proposes extra time > 0
        self.assertGreater(proposal.proposed_extra_time_hours, 0)
        self.assertEqual(proposal.proposed_extra_time_hours, 32)

        # 3. Provides objective explanation / reasoning
        self.assertTrue(len(proposal.ai_reasoning) > 100)
        self.assertIn("AI Price Negotiator Scope Assessment", proposal.ai_reasoning)
        self.assertIn("Authentication & Session Security", proposal.ai_reasoning)
        self.assertIn("250.00", proposal.ai_reasoning)
        self.assertIn("OAuth2 provider configuration", proposal.ai_reasoning)

        # 4. Valid feature title and test generated
        self.assertTrue(len(proposal.suggested_feature_title) > 0)
        self.assertIn("OAuth", proposal.suggested_feature_title)
        self.assertTrue(len(proposal.suggested_acceptance_test) > 0)

    def test_dark_mode_styling_proposal(self):
        """Evaluates low complexity UI theme changes with fair proportional pricing."""
        desc = "Add dark mode toggle with Tailwind CSS variable theme"
        proposal = self.negotiator.evaluate_change_request(self.mock_contract, desc)

        self.assertEqual(proposal.complexity, ComplexityLevel.LOW)
        self.assertEqual(proposal.proposed_price, 120.00)
        self.assertEqual(proposal.proposed_extra_time_hours, 16)
        self.assertIn("UI Design & Responsive Styling", proposal.ai_reasoning)
        self.assertIn("CSS variable theme", proposal.ai_reasoning)

    def test_payment_gateway_integration_proposal(self):
        """Evaluates high complexity payment gateway additions with appropriate escrow funding."""
        desc = "Integrate Stripe subscription checkout and recurring billing portal"
        proposal = self.negotiator.evaluate_change_request(self.mock_contract, desc)

        self.assertEqual(proposal.complexity, ComplexityLevel.HIGH)
        self.assertEqual(proposal.proposed_price, 400.00)
        self.assertEqual(proposal.proposed_extra_time_hours, 48)
        self.assertIn("Payment Processing & Financial Rails", proposal.ai_reasoning)
        self.assertIn("Webhook signature verification", proposal.ai_reasoning)

    def test_trivial_copy_text_change_proposal(self):
        """Evaluates trivial string/copy changes with minimal fee and time."""
        desc = "Update landing page footer text and fix typos"
        proposal = self.negotiator.evaluate_change_request(self.mock_contract, desc)

        self.assertEqual(proposal.complexity, ComplexityLevel.TRIVIAL)
        self.assertEqual(proposal.proposed_price, 40.00)
        self.assertEqual(proposal.proposed_extra_time_hours, 4)
        self.assertIn("Content & Minor Presentation", proposal.ai_reasoning)

    def test_user_proposed_custom_pricing_bounds(self):
        """Verifies that when a party submits a custom bid, the negotiator evaluates market variance."""
        desc = "Integrate Stripe subscription checkout"
        # User proposes $450 instead of baseline $400
        proposal = self.negotiator.evaluate_change_request(
            contract=self.mock_contract,
            description=desc,
            user_proposed_price=450.00,
            user_proposed_hours=50
        )

        self.assertEqual(proposal.proposed_price, 450.00)
        self.assertEqual(proposal.proposed_extra_time_hours, 50)
        self.assertIn("Evaluation of User Proposal", proposal.ai_reasoning)
        self.assertIn("450.00", proposal.ai_reasoning)

    def test_priced_checklist_dataclass_input(self):
        """Verifies engine consumes formal PricedChecklist dataclass instances seamlessly."""
        checklist = PricedChecklist(
            contract_id="cnt_dc_002",
            title="Formally Locked Checklist",
            total_amount=2000.00,
            currency="USD",
            deadline=(datetime.now(timezone.utc) + timedelta(days=20)).isoformat(),
            features=[
                ChecklistFeature(
                    id="feat_a",
                    title="Core API",
                    acceptance_test="Status 200",
                    price_weight=100.0,
                    allocated_amount=2000.00,
                    deadline=(datetime.now(timezone.utc) + timedelta(days=20)).isoformat()
                )
            ]
        )

        proposal = self.negotiator.evaluate_change_request(
            checklist,
            "Add PostgreSQL database migration for user preferences"
        )
        self.assertEqual(proposal.contract_id, "cnt_dc_002")
        self.assertEqual(proposal.complexity, ComplexityLevel.MEDIUM)
        self.assertEqual(proposal.proposed_price, 200.00)
        self.assertEqual(proposal.proposed_extra_time_hours, 24)
        self.assertTrue(len(proposal.ai_reasoning) > 0)

if __name__ == "__main__":
    unittest.main()

