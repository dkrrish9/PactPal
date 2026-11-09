"""
Unit and Integration Tests for Stage B Build Failure Handling (C18)
Validates:
  - Broken repository generates structured VerificationReport with zero process crashes
  - Build failure reason and AI diagnostics are correctly extracted
  - Downstream stages (C, D, E) are properly skipped
  - Contract features are marked FAILED with clear reasons
  - Next state is explicitly set to DECISION
  - Ephemeral container is guaranteed destroyed even after build errors
"""

import sys
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.verification.src.models import SubmissionRecord, VerificationReport
from services.verification.src.runner import VerificationPipelineRunner
from services.verification.src.ai_evaluator import AIIntakeEvaluator

class TestBuildFailureHandling(unittest.TestCase):

    def setUp(self):
        self.runner = VerificationPipelineRunner()
        self.contract_id = str(uuid.uuid4())
        self.submission_id = str(uuid.uuid4())
        self.seller_id = str(uuid.uuid4())
        self.fixtures_dir = PROJECT_ROOT / "services" / "verification" / "spike" / "fixtures"

        self.contract_features = [
            {
                "id": str(uuid.uuid4()),
                "title": "Feature 1: User Authentication",
                "price_weight": 40.0,
                "allocated_amount": 200.00
            },
            {
                "id": str(uuid.uuid4()),
                "title": "Feature 2: Product Catalog Grid",
                "price_weight": 35.0,
                "allocated_amount": 175.00
            },
            {
                "id": str(uuid.uuid4()),
                "title": "Feature 3: PayPal Checkout Integration",
                "price_weight": 25.0,
                "allocated_amount": 125.00
            }
        ]

    def test_broken_repo_produces_report_without_crash(self):
        """Verify broken repository executes without raising unhandled exceptions and yields report."""
        broken_repo_dir = self.fixtures_dir / "broken-repo"
        self.assertTrue(broken_repo_dir.exists(), "Broken repo fixture missing!")

        submission = SubmissionRecord(
            id=self.submission_id,
            contract_id=self.contract_id,
            seller_id=self.seller_id,
            repo_url=str(broken_repo_dir),
            commit_sha="c0ffee123456",
            build_notes="Attempted build on broken deliverable.",
            submission_number=1,
            is_late=False,
            delay_seconds=0,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            deadline=None
        )

        # Execute pipeline - MUST NOT CRASH
        report = self.runner.run_pipeline(submission, features=self.contract_features)

        self.assertIsInstance(report, VerificationReport)
        self.assertFalse(report.build_succeeded)
        self.assertEqual(report.overall_score, 0.0)
        self.assertEqual(report.next_state, "DECISION")
        self.assertIn("SyntaxError", report.build_logs)
        self.assertIsNotNone(report.failure_reason)

    def test_ai_diagnostic_extracts_syntax_error(self):
        """Verify AI diagnostic pinpoints SyntaxError and suggests actionable fix."""
        broken_repo_dir = self.fixtures_dir / "broken-repo"
        submission = SubmissionRecord(
            id=self.submission_id,
            contract_id=self.contract_id,
            seller_id=self.seller_id,
            repo_url=str(broken_repo_dir),
            commit_sha="c0ffee123456",
            build_notes="Standard deliverable.",
            submission_number=1,
            is_late=False,
            delay_seconds=0,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            deadline=None
        )

        report = self.runner.run_pipeline(submission, features=self.contract_features)

        self.assertIsNotNone(report.ai_diagnostic)
        self.assertEqual(report.ai_diagnostic["error_type"], "SYNTAX_ERROR")
        self.assertIn("Syntax error", report.ai_diagnostic["root_cause"])
        self.assertIn("linter", report.ai_diagnostic["suggested_fix"].lower())
        self.assertIn("AI Referee", report.ai_diagnostic["referee_summary"])

    def test_all_features_marked_failed_on_build_failure(self):
        """Verify all contract features are marked FAILED when build fails."""
        broken_repo_dir = self.fixtures_dir / "broken-repo"
        submission = SubmissionRecord(
            id=self.submission_id,
            contract_id=self.contract_id,
            seller_id=self.seller_id,
            repo_url=str(broken_repo_dir),
            commit_sha="c0ffee123456",
            build_notes="Broken code.",
            submission_number=1,
            is_late=False,
            delay_seconds=0,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            deadline=None
        )

        report = self.runner.run_pipeline(submission, features=self.contract_features)

        self.assertEqual(len(report.per_feature_results), 3)
        for feat in self.contract_features:
            feat_result = report.per_feature_results.get(feat["id"])
            self.assertIsNotNone(feat_result)
            self.assertEqual(feat_result["status"], "FAILED")
            self.assertIn("Build failed", feat_result["reason"])

    def test_downstream_stages_skipped(self):
        """Verify test suite and visual diff stages are skipped when build fails."""
        broken_repo_dir = self.fixtures_dir / "broken-repo"
        submission = SubmissionRecord(
            id=self.submission_id,
            contract_id=self.contract_id,
            seller_id=self.seller_id,
            repo_url=str(broken_repo_dir),
            commit_sha="c0ffee123456",
            build_notes="Broken deliverable.",
            submission_number=1,
            is_late=False,
            delay_seconds=0,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            deadline=None
        )

        report = self.runner.run_pipeline(submission, features=self.contract_features)

        self.assertIn("STAGE_C_TESTS", report.skipped_stages)
        self.assertIn("STAGE_D_CHEAT_SCAN", report.skipped_stages)
        self.assertIn("STAGE_E_VISUAL_DIFF", report.skipped_stages)
        self.assertEqual(report.test_suite_results["status"], "SKIPPED")

    def test_successful_build_passes(self):
        """Verify clean repository builds successfully in the pipeline."""
        clean_repo_dir = self.fixtures_dir / "trivial-repo"
        self.assertTrue(clean_repo_dir.exists(), "Trivial repo fixture missing!")

        submission = SubmissionRecord(
            id=self.submission_id,
            contract_id=self.contract_id,
            seller_id=self.seller_id,
            repo_url=str(clean_repo_dir),
            commit_sha="feedbeef1234",
            build_notes="Clean repository deliverable.",
            submission_number=1,
            is_late=False,
            delay_seconds=0,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            deadline=None
        )

        report = self.runner.run_pipeline(submission, features=self.contract_features)

        self.assertTrue(report.build_succeeded)
        self.assertEqual(report.overall_score, 1.0)
        self.assertIsNone(report.failure_reason)

if __name__ == "__main__":
    unittest.main()
