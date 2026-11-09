"""
Unit and Integration Tests for Stage C Automated Tests & Feature Mapping (C23)
Validates:
  - Discovery and execution of native test suites inside isolated sandboxes
  - Per-feature pass/fail mapping produced for the good repo deliverable
  - Accurate proportional weighted release score calculation
  - Clear evidence logs and error traces attached to each feature verdict
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
from services.verification.src.test_runner import StageCTestSuiteProcessor
from services.verification.src.sandbox import IsolatedWorkspace

class TestStageCTestSuite(unittest.TestCase):

    def setUp(self):
        self.runner = VerificationPipelineRunner()
        self.processor = StageCTestSuiteProcessor()
        self.contract_id = str(uuid.uuid4())
        self.submission_id = str(uuid.uuid4())
        self.seller_id = str(uuid.uuid4())
        self.good_repo_dir = PROJECT_ROOT / "demo-assets" / "good-repo"

        # 4 Contract features matching the benchmark freelance milestone
        self.features = [
            {
                "id": "feat_001_profile",
                "title": "User Profile Header & Verified Badge",
                "acceptance_test": "getUserProfile returns Alex Morgan with rating 4.95 and escrowVerified true.",
                "price_weight": 25.0,
                "allocated_amount": 250.00
            },
            {
                "id": "feat_002_catalog",
                "title": "Product Catalog Search & Category Filter",
                "acceptance_test": "filterProducts filters products by category and minimum rating.",
                "price_weight": 30.0,
                "allocated_amount": 300.00
            },
            {
                "id": "feat_003_calculator",
                "title": "Escrow Milestone Proportional Calculator",
                "acceptance_test": "calculateMilestoneRelease calculates payout and refund settling to exact cent.",
                "price_weight": 25.0,
                "allocated_amount": 250.00
            },
            {
                "id": "feat_004_contact",
                "title": "Client Feedback & Dispute Modal Form",
                "acceptance_test": "validateFeedbackForm validates email, subject, and message length.",
                "price_weight": 20.0,
                "allocated_amount": 200.00
            }
        ]

    def test_good_repo_native_tests_pass(self):
        """Verify native test runner executes all 4 suites in good-repo cleanly."""
        self.assertTrue(self.good_repo_dir.exists(), "good-repo fixture missing!")

        with IsolatedWorkspace() as ws:
            clone_dest = ws.workspace_path / "repo"
            import shutil
            shutil.copytree(self.good_repo_dir, clone_dest)

            test_results, per_feature, score = self.processor.execute_stage_c(
                workspace=ws,
                repo_dir=clone_dest,
                features=self.features
            )

            self.assertEqual(test_results["status"], "COMPLETED")
            self.assertEqual(test_results["total_tests"], 4)
            self.assertEqual(test_results["passed_tests"], 4)
            self.assertEqual(test_results["failed_tests"], 0)
            self.assertIn("All 4 native feature test suites passed", test_results["raw_output"])

    def test_per_feature_pass_produced_for_good_repo(self):
        """
        C23 Core Done Criteria:
        Verify per-feature pass/fail produced for the good repo deliverable.
        All 4 features must produce status=PASSED with 100% overall weighted release score.
        """
        submission = SubmissionRecord(
            id=self.submission_id,
            contract_id=self.contract_id,
            seller_id=self.seller_id,
            repo_url=str(self.good_repo_dir),
            commit_sha="a1b2c3d4e5f6",
            build_notes="Clean reference deliverable with all 4 milestone features implemented.",
            submission_number=1,
            is_late=False,
            delay_seconds=0,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            deadline=None
        )

        report = self.runner.run_pipeline(submission, features=self.features)

        self.assertTrue(report.build_succeeded)
        self.assertEqual(report.test_suite_results["status"], "COMPLETED")
        self.assertEqual(report.overall_score, 1.0)  # 100% score

        # Verify every individual feature passed with detailed evidence
        self.assertEqual(len(report.per_feature_results), 4)

        for feat in self.features:
            feat_id = feat["id"]
            feat_res = report.per_feature_results.get(feat_id)
            self.assertIsNotNone(feat_res, f"Feature {feat_id} missing from report!")
            self.assertEqual(feat_res["status"], "PASSED", f"Feature {feat_id} failed!")
            self.assertEqual(feat_res["severity"], "NONE")
            self.assertIsNotNone(feat_res["evidence"])
            self.assertIsNone(feat_res["reason"])
            self.assertEqual(feat_res["price_weight"], feat["price_weight"])
            self.assertEqual(feat_res["allocated_amount"], feat["allocated_amount"])

    def test_proportional_weighted_score_on_partial_failure(self):
        """
        Verify that if 1 feature fails (e.g. 20% weight), the other 3 features pass
        and overall score strictly equals 80.0% (0.80).
        """
        with IsolatedWorkspace() as ws:
            clone_dest = ws.workspace_path / "repo"
            import shutil
            shutil.copytree(self.good_repo_dir, clone_dest)

            # Break Feature 4 in the cloned deliverable
            contact_test_file = clone_dest / "test" / "contact.test.js"
            contact_test_file.write_text(
                "function testContact() { throw new Error('Simulated regression in contact validation'); }\nmodule.exports = { testContact };",
                encoding="utf-8"
            )

            test_results, per_feature, score = self.processor.execute_stage_c(
                workspace=ws,
                repo_dir=clone_dest,
                features=self.features
            )

            # Feature 4 should be FAILED
            feat_4_res = per_feature["feat_004_contact"]
            self.assertEqual(feat_4_res["status"], "FAILED")
            self.assertEqual(feat_4_res["severity"], "HIGH")
            self.assertIn("failed", feat_4_res["reason"].lower())

            # Features 1, 2, 3 should be PASSED
            self.assertEqual(per_feature["feat_001_profile"]["status"], "PASSED")
            self.assertEqual(per_feature["feat_002_catalog"]["status"], "PASSED")
            self.assertEqual(per_feature["feat_003_calculator"]["status"], "PASSED")

            # Score must equal (25 + 30 + 25) / 100 = 0.80
            self.assertEqual(score, 0.80)

if __name__ == "__main__":
    unittest.main()
