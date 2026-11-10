"""
PactPal Milestone 2: AI Referee Decision Engine Acceptance Tests (Task C34)
Linked Tasks: C34 / A10 / C07
"""

import unittest
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

from services.agents.referee import (
    RefereeDecisionEngine,
    DecisionOutcome,
    RefereeDecision,
    FeatureDecision
)
from services.agents.agreement_reader.models import PricedChecklist, ChecklistFeature

class TestRefereeDecisionEngine(unittest.TestCase):
    """Verifies impartial referee decision rules and plain-language explanations."""

    def setUp(self):
        self.engine = RefereeDecisionEngine()
        self.mock_contract = {
            "id": "cnt_test_001",
            "title": "Fullstack Freelance Deliverable",
            "total_amount": 1000.00,
            "currency": "USD",
            "deadline": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "features": [
                {"id": "feat_1", "title": "User Profile Header", "price_weight": 25.0, "allocated_amount": 250.00},
                {"id": "feat_2", "title": "Product Catalog & Filter", "price_weight": 25.0, "allocated_amount": 250.00},
                {"id": "feat_3", "title": "Escrow Milestone Calculator", "price_weight": 25.0, "allocated_amount": 250.00},
                {"id": "feat_4", "title": "Dispute & Feedback Form", "price_weight": 25.0, "allocated_amount": 250.00}
            ]
        }

    def test_good_repo_triggers_full_release(self):
        """Rule 1: Flawless good-repo deliverable triggers 100% full release to seller."""
        report = {
            "id": "rep_good_001",
            "contract_id": "cnt_test_001",
            "build_succeeded": True,
            "build_logs": "Compiled successfully in 2.1s.",
            "overall_score": 1.0,
            "test_suite_results": {"status": "COMPLETED", "passed_tests": 4, "failed_tests": 0},
            "cheat_scan_findings": [],
            "visual_diff_summary": {"similarity_score": 0.98, "passed": True},
            "per_feature_results": {
                "feat_1": {"feature_id": "feat_1", "feature_title": "User Profile Header", "status": "PASSED", "price_weight": 25.0, "allocated_amount": 250.00, "evidence": "All tests pass"},
                "feat_2": {"feature_id": "feat_2", "feature_title": "Product Catalog & Filter", "status": "PASSED", "price_weight": 25.0, "allocated_amount": 250.00, "evidence": "All tests pass"},
                "feat_3": {"feature_id": "feat_3", "feature_title": "Escrow Milestone Calculator", "status": "PASSED", "price_weight": 25.0, "allocated_amount": 250.00, "evidence": "All tests pass"},
                "feat_4": {"feature_id": "feat_4", "feature_title": "Dispute & Feedback Form", "status": "PASSED", "price_weight": 25.0, "allocated_amount": 250.00, "evidence": "All tests pass"}
            }
        }

        decision = self.engine.evaluate(self.mock_contract, report)

        self.assertEqual(decision.outcome, DecisionOutcome.FULL_RELEASE)
        self.assertEqual(decision.passed_amount, 1000.00)
        self.assertEqual(decision.refund_amount, 0.00)
        self.assertEqual(decision.passed_weight, 100.0)
        self.assertEqual(decision.failed_weight, 0.0)
        self.assertEqual(decision.next_state, "SETTLED")
        self.assertIn("FULL ESCROW RELEASE APPROVED", decision.conversational_explanation)
        self.assertIn("all 4 deliverables passed", decision.plain_text_summary.lower())

    def test_bad_repo_triggers_partial_release(self):
        """Rule 2: Flawed bad-repo (Feature 3 broken) triggers proportional partial payout."""
        report = {
            "id": "rep_bad_001",
            "contract_id": "cnt_test_001",
            "build_succeeded": True,
            "build_logs": "Compiled successfully.",
            "overall_score": 0.75,
            "test_suite_results": {"status": "COMPLETED", "passed_tests": 3, "failed_tests": 1},
            "cheat_scan_findings": [],
            "visual_diff_summary": {"similarity_score": 0.38, "passed": False},
            "per_feature_results": {
                "feat_1": {"feature_id": "feat_1", "feature_title": "User Profile Header", "status": "PASSED", "price_weight": 25.0, "allocated_amount": 250.00, "evidence": "Unit test pass"},
                "feat_2": {"feature_id": "feat_2", "feature_title": "Product Catalog & Filter", "status": "PASSED", "price_weight": 25.0, "allocated_amount": 250.00, "evidence": "Unit test pass"},
                "feat_3": {"feature_id": "feat_3", "feature_title": "Escrow Milestone Calculator", "status": "FAILED", "price_weight": 25.0, "allocated_amount": 250.00, "reason": "Expected sellerPayout 800.00, got 8000"},
                "feat_4": {"feature_id": "feat_4", "feature_title": "Dispute & Feedback Form", "status": "PASSED", "price_weight": 25.0, "allocated_amount": 250.00, "evidence": "Unit test pass"}
            }
        }

        decision = self.engine.evaluate(self.mock_contract, report)

        self.assertEqual(decision.outcome, DecisionOutcome.PARTIAL_RELEASE)
        self.assertEqual(decision.passed_amount, 750.00)
        self.assertEqual(decision.refund_amount, 250.00)
        self.assertEqual(decision.passed_weight, 75.0)
        self.assertEqual(decision.failed_weight, 25.0)
        self.assertEqual(decision.next_state, "SETTLED")
        self.assertIn("PARTIAL ESCROW SETTLEMENT APPROVED", decision.conversational_explanation)
        self.assertIn("Expected sellerPayout 800.00, got 8000", decision.conversational_explanation)
        self.assertIn("750.00 released to seller", decision.plain_text_summary)
        self.assertIn("250.00 refunded to buyer", decision.plain_text_summary)

    def test_failed_build_triggers_hold(self):
        """Rule 3: Unbuildable deliverable freezes escrow on HOLD with zero payouts."""
        report = {
            "id": "rep_broken_001",
            "contract_id": "cnt_test_001",
            "build_succeeded": False,
            "failure_reason": "SyntaxError: Unexpected token 'export' in src/index.js:14",
            "build_logs": "npm ERR! Build exited with status 1.",
            "per_feature_results": {}
        }

        decision = self.engine.evaluate(self.mock_contract, report)

        self.assertEqual(decision.outcome, DecisionOutcome.HOLD)
        self.assertEqual(decision.passed_amount, 0.00)
        self.assertEqual(decision.refund_amount, 0.00)
        self.assertEqual(decision.next_state, "IN_PROGRESS")
        self.assertIn("ESCROW SETTLEMENT PLACED ON HOLD", decision.conversational_explanation)
        self.assertIn("SyntaxError: Unexpected token", decision.conversational_explanation)
        self.assertIn("HOLD", decision.plain_text_summary)

    def test_deadline_expired_triggers_full_refund(self):
        """Rule 4: Expired contract deadline without passing submission refunds 100% to buyer."""
        past_deadline = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        expired_contract = {
            "id": "cnt_expired_001",
            "title": "Overdue Mobile App",
            "total_amount": 2500.00,
            "currency": "USD",
            "deadline": past_deadline,
            "features": []
        }
        # Empty unverified report
        empty_report = {
            "id": "rep_empty",
            "build_succeeded": True,
            "per_feature_results": {}
        }

        decision = self.engine.evaluate(expired_contract, empty_report)

        self.assertEqual(decision.outcome, DecisionOutcome.DEADLINE_EXPIRED)
        self.assertEqual(decision.passed_amount, 0.00)
        self.assertEqual(decision.refund_amount, 2500.00)
        self.assertEqual(decision.next_state, "SETTLED")
        self.assertIn("CONTRACT DEADLINE EXPIRED", decision.conversational_explanation)
        self.assertIn("2,500.00) refunded to buyer", decision.plain_text_summary)

    def test_shared_mock_verification_report_shape(self):
        """Rule 5: Evaluates the exact JSON mock report defined in shared/mock/verification_report.mock.json."""
        mock_file = Path("shared/mock/verification_report.mock.json")
        self.assertTrue(mock_file.exists(), "shared/mock/verification_report.mock.json is missing!")

        with open(mock_file, "r") as f:
            shared_report = json.load(f)

        contract = {
            "id": shared_report["contract_id"],
            "title": "Interactive SaaS Platform & Gantt Milestone",
            "total_amount": 1500.00,
            "currency": "USD",
            "deadline": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
            "features": []
        }

        decision = self.engine.evaluate(contract, shared_report)

        self.assertEqual(decision.outcome, DecisionOutcome.PARTIAL_RELEASE)
        self.assertEqual(decision.passed_amount, 1200.00)
        self.assertEqual(decision.refund_amount, 300.00)
        self.assertEqual(decision.passed_weight, 80.0)
        self.assertEqual(decision.failed_weight, 20.0)
        self.assertEqual(len(decision.feature_decisions), 4)

        # Check that auth feature failed with cheat reason
        auth_decision = next(f for f in decision.feature_decisions if "Authentication" in f.feature_title)
        self.assertEqual(auth_decision.status, "FAILED")
        self.assertEqual(auth_decision.allocated_amount, 300.00)
        self.assertEqual(auth_decision.severity, "HIGH")

    def test_priced_checklist_model_input(self):
        """Verifies engine consumes PricedChecklist dataclass instances natively."""
        checklist = PricedChecklist(
            contract_id="cnt_dc_001",
            title="Dataclass Model Milestone",
            total_amount=500.00,
            currency="USD",
            deadline=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            features=[
                ChecklistFeature(
                    id="f1",
                    title="API Endpoint",
                    acceptance_test="Status code 200",
                    price_weight=100.0,
                    allocated_amount=500.00,
                    deadline=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
                )
            ]
        )

        report = {
            "build_succeeded": True,
            "per_feature_results": {
                "f1": {"feature_id": "f1", "status": "PASSED", "allocated_amount": 500.00, "price_weight": 100.0}
            }
        }

        decision = self.engine.evaluate(checklist, report)
        self.assertEqual(decision.outcome, DecisionOutcome.FULL_RELEASE)
        self.assertEqual(decision.passed_amount, 500.00)

if __name__ == "__main__":
    unittest.main()

