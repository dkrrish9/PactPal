"""
Unit and Integration Tests for Master Report Assembly (C32)
Validates Done Criteria:
  - Every feature has passed/failed/partial with evidence
  - Security findings are aggregated and highlighted
  - Code coverage metrics (global summary and per-feature) are computed
  - Merges Stage A through Stage E into a unified multi-modal VerificationReport
  - Formulates objective settlement recommendations for the AI Referee
"""

import sys
import unittest
import uuid
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.verification.src.report_assembler import ReportAssembler, CoverageAnalyzer
from services.verification.src.models import SubmissionRecord, VerificationReport
from services.verification.src.runner import VerificationPipelineRunner


class TestMasterReportAssembly(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.good_repo_dir = PROJECT_ROOT / "demo-assets" / "good-repo"
        cls.bad_repo_dir = PROJECT_ROOT / "demo-assets" / "bad-repo"
        cls.figma_dir = PROJECT_ROOT / "demo-assets" / "figma"

    def setUp(self):
        self.assembler = ReportAssembler()
        self.runner = VerificationPipelineRunner(figma_reference_dir=self.figma_dir)

    def test_coverage_analyzer_computes_metrics(self):
        """Verify CoverageAnalyzer calculates executable line coverage."""
        analyzer = CoverageAnalyzer(target_coverage_threshold=80.0)
        mock_test_results = {
            "test_suites": [
                {"name": "profile.test.js", "status": "PASSED"},
                {"name": "catalog.test.js", "status": "PASSED"},
                {"name": "calculator.test.js", "status": "PASSED"},
                {"name": "contact.test.js", "status": "PASSED"}
            ],
            "passed_tests": 4,
            "failed_tests": 0
        }

        coverage = analyzer.analyze_coverage(self.good_repo_dir, mock_test_results)

        self.assertGreater(coverage["total_lines"], 0)
        self.assertGreater(coverage["covered_lines"], 0)
        self.assertGreaterEqual(coverage["coverage_percentage"], 80.0)
        self.assertEqual(coverage["status"], "SATISFACTORY")
        self.assertIn("src/profile.js", coverage["modules"])
        self.assertIn("src/catalog.js", coverage["modules"])

    def test_good_repo_report_assembly_all_features_passed_with_evidence(self):
        """Verify good repo deliverable produces all PASSED features with rich evidence."""
        submission = SubmissionRecord(
            id=str(uuid.uuid4()),
            contract_id=f"cnt_{uuid.uuid4().hex[:8]}",
            seller_id="seller_alice",
            repo_url=str(self.good_repo_dir),
            commit_sha="good123",
            build_notes="Good repo submission for report assembly",
            submission_number=1,
            is_late=False,
            delay_seconds=0,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            deadline=None
        )

        features = [
            {"id": "feat_profile", "title": "Feature 1: User Profile Header", "price_weight": 25.0, "allocated_amount": 250.0},
            {"id": "feat_catalog", "title": "Feature 2: Product Catalog & Filter", "price_weight": 25.0, "allocated_amount": 250.0},
            {"id": "feat_calculator", "title": "Feature 3: Escrow Milestone Calculator", "price_weight": 25.0, "allocated_amount": 250.0},
            {"id": "feat_contact", "title": "Feature 4: Dispute & Feedback Form", "price_weight": 25.0, "allocated_amount": 250.0}
        ]

        report = self.runner.run_pipeline(
            submission=submission,
            features=features,
            capture_screenshots=True
        )

        # 1. Verification of Report Structure
        self.assertTrue(report.build_succeeded)
        self.assertEqual(report.recommendation, "FULL_RELEASE")
        self.assertGreaterEqual(report.overall_score, 0.95)

        # 2. Every feature must have PASSED status with evidence and coverage
        per_feature = report.per_feature_results
        self.assertEqual(len(per_feature), 4)

        for feat_id, feat_data in per_feature.items():
            self.assertEqual(feat_data["status"], "PASSED", f"Feature {feat_id} should be PASSED in good repo!")
            self.assertEqual(feat_data["score"], 1.0)
            self.assertIn("evidence", feat_data)
            self.assertIn("coverage", feat_data)

            # Check evidence fields
            ev = feat_data["evidence"]
            self.assertIn("test_evidence", ev)
            self.assertIn("cheat_evidence", ev)
            self.assertIn("visual_evidence", ev)
            self.assertIn("coverage", ev)
            self.assertIsNotNone(ev["summary"])

        # 3. Security Findings
        self.assertEqual(len(report.security_findings), 0)

        # 4. Coverage Summary
        self.assertIsNotNone(report.coverage_summary)
        self.assertGreaterEqual(report.coverage_summary["coverage_percentage"], 80.0)

    def test_bad_repo_report_assembly_passed_and_failed_features_with_evidence(self):
        """Verify bad repo deliverable produces FAILED and PASSED features with high-severity cheat evidence."""
        submission = SubmissionRecord(
            id=str(uuid.uuid4()),
            contract_id=f"cnt_{uuid.uuid4().hex[:8]}",
            seller_id="seller_bob",
            repo_url=str(self.bad_repo_dir),
            commit_sha="bad456",
            build_notes="Bad repo submission for report assembly",
            submission_number=1,
            is_late=False,
            delay_seconds=0,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            deadline=None
        )

        features = [
            {"id": "feat_profile", "title": "Feature 1: User Profile Header", "price_weight": 25.0, "allocated_amount": 250.0},
            {"id": "feat_catalog", "title": "Feature 2: Product Catalog & Filter", "price_weight": 25.0, "allocated_amount": 250.0},
            {"id": "feat_calculator", "title": "Feature 3: Escrow Milestone Calculator", "price_weight": 25.0, "allocated_amount": 250.0},
            {"id": "feat_contact", "title": "Feature 4: Dispute & Feedback Form", "price_weight": 25.0, "allocated_amount": 250.0}
        ]

        report = self.runner.run_pipeline(
            submission=submission,
            features=features,
            capture_screenshots=True
        )

        per_feature = report.per_feature_results
        self.assertEqual(len(per_feature), 4)

        # Feature 3 (Calculator) must fail due to math test bug
        self.assertEqual(per_feature["feat_calculator"]["status"], "FAILED")
        self.assertEqual(per_feature["feat_calculator"]["score"], 0.0)
        self.assertIn("test failed", per_feature["feat_calculator"]["reason"].lower())

        # Feature 2 (Catalog) must fail due to high-severity hardcoded fake answer cheat
        self.assertEqual(per_feature["feat_catalog"]["status"], "FAILED")
        self.assertEqual(per_feature["feat_catalog"]["score"], 0.0)
        self.assertIn("cheat", per_feature["feat_catalog"]["reason"].lower())

        # Feature 1 (Profile) has visual divergence on bad-repo landing page -> PARTIAL
        self.assertEqual(per_feature["feat_profile"]["status"], "PARTIAL")
        self.assertEqual(per_feature["feat_profile"]["score"], 0.5)

        # Feature 4 (Contact) has clean logic and tests -> PASSED
        self.assertEqual(per_feature["feat_contact"]["status"], "PASSED")
        self.assertEqual(per_feature["feat_contact"]["score"], 1.0)

        # Every feature must have evidence attached
        for f_id, f_data in per_feature.items():
            self.assertIn("evidence", f_data)
            self.assertIn("coverage", f_data)

        # Security findings must be present
        self.assertGreater(len(report.security_findings), 0)
        cheat_rules = [f["rule_id"] for f in report.security_findings]
        self.assertTrue(any("CHEAT" in r for r in cheat_rules))

        # Overall score reflects partial release (Contact full weight 0.25 + Profile partial weight 0.125 = 0.375)
        self.assertAlmostEqual(report.overall_score, 0.375, delta=0.05)
        self.assertEqual(report.recommendation, "PARTIAL_RELEASE")

    def test_partial_feature_verdict_when_visual_diff_diverges(self):
        """Verify deliverable with visual divergence yields PARTIAL feature status."""
        test_results = {
            "test_suites": [{"name": "landing.test.js", "status": "PASSED"}],
            "passed_tests": 1,
            "failed_tests": 0
        }
        cheat_report = {"findings": []}
        visual_diff = {
            "status": "COMPLETED",
            "passed": False,
            "similarity_score": 0.55,
            "threshold": 0.85,
            "mismatches_detected": ["Severe color divergence"]
        }
        features = [
            {"id": "feat_landing_ui", "title": "Landing UI Viewport", "price_weight": 100.0, "allocated_amount": 1000.0}
        ]

        submission = SubmissionRecord(
            id=str(uuid.uuid4()),
            contract_id="cnt_test_partial",
            seller_id="seller_carol",
            repo_url=str(self.good_repo_dir),
            commit_sha="part123",
            build_notes="Partial test",
            submission_number=1,
            is_late=False,
            delay_seconds=0,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            deadline=None
        )

        report = self.assembler.assemble_report(
            submission=submission,
            repo_dir=self.good_repo_dir,
            build_succeeded=True,
            build_logs="Build OK",
            test_suite_results=test_results,
            cheat_scan_report=cheat_report,
            visual_diff_summary=visual_diff,
            features=features
        )

        landing_feat = report.per_feature_results["feat_landing_ui"]
        self.assertEqual(landing_feat["status"], "PARTIAL")
        self.assertEqual(landing_feat["score"], 0.5)
        self.assertIn("deviates from figma", landing_feat["reason"].lower())
        self.assertIn("evidence", landing_feat)
        self.assertEqual(landing_feat["evidence"]["visual_evidence"]["visual_status"], "MISMATCH_DETECTED")


if __name__ == "__main__":
    unittest.main()
