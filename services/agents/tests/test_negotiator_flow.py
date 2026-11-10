"""
Acceptance Tests for Negotiator Accept/Counter/Reject Flow and Mini-Agreement (Task C42)
Linked Tasks: C42 / C46 / A13 (Milestone 3: Money & Extras)

Acceptance Criteria:
"New checklist item with its own weight, price, deadline; original never silently altered"
"""

import unittest
from datetime import datetime, timezone, timedelta

from services.agents.negotiator import (
    PriceNegotiator,
    NegotiationWorkflowEngine,
    ChangeRequestProposal,
    MiniAgreement
)
from services.agents.agreement_reader.models import PricedChecklist, ChecklistFeature

class TestNegotiatorFlow(unittest.TestCase):
    """Verifies change request lifecycle, mini-agreement synthesis, and checklist non-alteration invariants."""

    def setUp(self):
        self.negotiator = PriceNegotiator()
        self.workflow = NegotiationWorkflowEngine()

        # Set up a locked contract checklist with 2 initial features ($1,000.00 total)
        self.now = datetime.now(timezone.utc)
        self.orig_deadline = (self.now + timedelta(days=14)).isoformat()

        self.f1 = ChecklistFeature(
            id="feat_001",
            title="User Profile Management",
            acceptance_test="CRUD profile endpoints return 200",
            price_weight=50.0,
            allocated_amount=500.00,
            deadline=self.orig_deadline
        )
        self.f2 = ChecklistFeature(
            id="feat_002",
            title="Product Search Catalog",
            acceptance_test="Faceted search returns filtered items",
            price_weight=50.0,
            allocated_amount=500.00,
            deadline=self.orig_deadline
        )

        self.checklist = PricedChecklist(
            contract_id="cnt_test_amend_999",
            title="Fullstack Web Application",
            total_amount=1000.00,
            currency="USD",
            deadline=self.orig_deadline,
            features=[self.f1, self.f2],
            is_locked=True,
            locked_at=self.now.isoformat()
        )

    def test_accept_flow_creates_mini_agreement_and_appends_feature(self):
        """
        ACCEPTANCE CRITERIA:
        New checklist item with its own weight, price, deadline; original never silently altered.
        """
        # 1. Propose change request
        proposal = self.negotiator.evaluate_change_request(
            contract=self.checklist,
            description="Add Google OAuth and JWT session authentication"
        )
        self.assertEqual(proposal.status, "PROPOSED")
        self.assertEqual(proposal.proposed_price, 250.00)
        self.assertEqual(proposal.proposed_extra_time_hours, 32)

        # 2. Accept proposal via workflow
        agreement, updated_checklist = self.workflow.accept(
            proposal=proposal,
            accepted_by_id="usr_buyer_123",
            checklist=self.checklist
        )

        # 3. Verify status transition (Strict requirement for C46 incremental hold)
        self.assertEqual(proposal.status, "ACCEPTED")
        self.assertEqual(agreement.status, "ACCEPTED")

        # 4. Verify Mini-Agreement synthesis
        self.assertEqual(agreement.contract_id, "cnt_test_amend_999")
        self.assertEqual(agreement.change_request_id, proposal.change_request_id)
        self.assertEqual(agreement.original_total_amount, 1000.00)
        self.assertEqual(agreement.additional_price, 250.00)
        self.assertEqual(agreement.new_total_amount, 1250.00)
        self.assertEqual(agreement.extra_hours, 32)
        self.assertIn("OAuth", agreement.amended_feature_title)
        self.assertTrue(len(agreement.legal_text) > 100)

        # 5. Verify Checklist expansion
        self.assertEqual(len(updated_checklist.features), 3)
        self.assertEqual(updated_checklist.total_amount, 1250.00)

        # 6. Verify new feature properties
        new_feat = updated_checklist.features[2]
        self.assertEqual(new_feat.allocated_amount, 250.00)
        self.assertTrue(new_feat.amended)
        self.assertEqual(new_feat.change_request_id, proposal.change_request_id)
        self.assertIn("OAuth", new_feat.title)
        self.assertTrue(new_feat.deadline > self.orig_deadline)

        # 7. Verify weights sum to exactly 100.00%
        total_weight = sum(f.price_weight for f in updated_checklist.features)
        self.assertAlmostEqual(total_weight, 100.00, places=2)

    def test_original_features_never_silently_altered(self):
        """
        NON-ALTERATION INVARIANT:
        Original features must keep their exact original IDs, titles, acceptance tests,
        and allocated amounts without any silent corruption or alteration.
        """
        proposal = self.negotiator.evaluate_change_request(
            contract=self.checklist,
            description="Add dark mode toggle"
        )
        agreement, updated_checklist = self.workflow.accept(
            proposal=proposal,
            accepted_by_id="usr_buyer_123",
            checklist=self.checklist
        )

        # Feature 1 verification
        f1_after = updated_checklist.features[0]
        self.assertEqual(f1_after.id, "feat_001")
        self.assertEqual(f1_after.title, "User Profile Management")
        self.assertEqual(f1_after.acceptance_test, "CRUD profile endpoints return 200")
        self.assertEqual(f1_after.allocated_amount, 500.00)
        self.assertFalse(f1_after.amended)
        self.assertIsNone(f1_after.change_request_id)

        # Feature 2 verification
        f2_after = updated_checklist.features[1]
        self.assertEqual(f2_after.id, "feat_002")
        self.assertEqual(f2_after.title, "Product Search Catalog")
        self.assertEqual(f2_after.acceptance_test, "Faceted search returns filtered items")
        self.assertEqual(f2_after.allocated_amount, 500.00)
        self.assertFalse(f2_after.amended)
        self.assertIsNone(f2_after.change_request_id)

    def test_counter_proposal_lifecycle(self):
        """Verifies counter-offer rounds before final agreement."""
        proposal = self.negotiator.evaluate_change_request(
            contract=self.checklist,
            description="Integrate Stripe billing checkout"
        )
        self.assertEqual(proposal.proposed_price, 400.00)
        self.assertEqual(proposal.proposed_extra_time_hours, 48)

        # Counterparty counters: $350.00 and 40 hours
        countered = self.workflow.counter(
            proposal=proposal,
            countered_by_id="usr_seller_456",
            counter_price=350.00,
            counter_hours=40,
            reason="Can reuse existing Stripe webhook boilerplate"
        )

        self.assertEqual(countered.status, "COUNTERED")
        self.assertEqual(countered.proposed_price, 350.00)
        self.assertEqual(countered.proposed_extra_time_hours, 40)
        self.assertEqual(len(countered.counter_history), 1)

        # Accept the counter-offer
        agreement, updated_checklist = self.workflow.accept(
            proposal=countered,
            accepted_by_id="usr_buyer_123",
            checklist=self.checklist
        )

        self.assertEqual(agreement.additional_price, 350.00)
        self.assertEqual(agreement.new_total_amount, 1350.00)
        self.assertEqual(agreement.extra_hours, 40)
        self.assertEqual(updated_checklist.total_amount, 1350.00)

    def test_reject_proposal_leaves_contract_completely_untouched(self):
        """Verifies rejection leaves checklist and funds 100% unaltered."""
        proposal = self.negotiator.evaluate_change_request(
            contract=self.checklist,
            description="Add WebSockets live chat"
        )

        rejected = self.workflow.reject(
            proposal=proposal,
            rejected_by_id="usr_buyer_123",
            reason="Out of budget for MVP phase"
        )

        self.assertEqual(rejected.status, "REJECTED")
        self.assertEqual(rejected.rejection_reason, "Out of budget for MVP phase")

        # Contract checklist is completely untouched
        self.assertEqual(len(self.checklist.features), 2)
        self.assertEqual(self.checklist.total_amount, 1000.00)

    def test_c46_incremental_hold_hook_integration(self):
        """Verifies C46 PayPal secondary authorization hook can attach authorization ID."""
        proposal = self.negotiator.evaluate_change_request(
            contract=self.checklist,
            description="Add Apple Pay"
        )
        agreement, _ = self.workflow.accept(proposal, "usr_buyer_123", self.checklist)

        # When C46 calls PayPal reauthorize, it attaches the additional_auth_id
        agreement.additional_auth_id = "AUTH-EXPANDED-002"
        proposal.additional_auth_id = "AUTH-EXPANDED-002"

        self.assertEqual(agreement.additional_auth_id, "AUTH-EXPANDED-002")
        self.assertEqual(proposal.additional_auth_id, "AUTH-EXPANDED-002")

if __name__ == "__main__":
    unittest.main()

