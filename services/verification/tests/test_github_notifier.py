"""
Unit and Integration Tests for GitHub Referee Feedback Notifier (C36)
Validates Done Criteria:
  - Seller gets feedback on the repo
  - Generates comprehensive, audit-ready Markdown feedback with per-feature breakdown
  - Highlights security and cheat scan findings with remediation steps
  - Parses GitHub repository URLs (HTTPS, SSH)
  - Dispatches feedback comments to GitHub API and captures comment URLs
  - Persists tamper-evident notification receipts and markdown evidence
  - Full VerificationPipelineRunner integration populates report.notifications
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

from services.verification.src.github_notifier import GitHubFeedbackNotifier
from services.verification.src.models import SubmissionRecord, VerificationReport
from services.verification.src.runner import VerificationPipelineRunner


class TestGitHubFeedbackNotifier(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.good_repo_dir = PROJECT_ROOT / "demo-assets" / "good-repo"
        cls.bad_repo_dir = PROJECT_ROOT / "demo-assets" / "bad-repo"
        cls.figma_dir = PROJECT_ROOT / "demo-assets" / "figma"

    def setUp(self):
        self.notifier = GitHubFeedbackNotifier()
        self.temp_evidence_dir = Path(tempfile.mkdtemp(prefix="pactpal_notify_test_"))
        self.runner = VerificationPipelineRunner(figma_reference_dir=self.figma_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_evidence_dir, ignore_errors=True)

    def test_parse_github_repo_info(self):
        """Verify URL parser extracts owner and repo across HTTPS, SSH, and skips local paths."""
        # HTTPS
        info1 = self.notifier.parse_github_repo_info("https://github.com/dkrrish9/PactPal.git")
        self.assertEqual(info1, ("dkrrish9", "PactPal"))

        info2 = self.notifier.parse_github_repo_info("https://github.com/alice-seller/escrow-frontend")
        self.assertEqual(info2, ("alice-seller", "escrow-frontend"))

        # SSH
        info3 = self.notifier.parse_github_repo_info("git@github.com:bob-freelancer/api-backend.git")
        self.assertEqual(info3, ("bob-freelancer", "api-backend"))

        # Local path
        info4 = self.notifier.parse_github_repo_info("C:/Users/DELL/demo-assets/good-repo")
        self.assertIsNone(info4)

    def test_format_referee_feedback_markdown_good_repo(self):
        """
        DONE CRITERIA (C36):
        Verify generated markdown delivers clear feedback for the good repo.
        """
        submission = SubmissionRecord(
            id="sub_test_good_001",
            contract_id="cnt_pactpal_benchmark",
            seller_id="seller_alice",
            repo_url=str(self.good_repo_dir),
            commit_sha="0745dacaca767b934916dc9bf8a6806bada3a605",
            build_notes="Milestone complete deliverable",
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
            capture_screenshots=False,
            notify_seller=False
        )

        md = self.notifier.format_referee_feedback_markdown(report, submission)

        # Assertions on feedback content
        self.assertIn("PactPal AI Escrow Referee", md)
        self.assertIn("FULL ESCROW RELEASE APPROVED", md)
        self.assertIn("100.0%", md)
        self.assertIn("Feature 1: User Profile Header", md)
        self.assertIn("Feature 2: Product Catalog & Filter", md)
        self.assertIn("Clean Deliverable", md)
        self.assertIn("Actionable Next Steps for Seller", md)
        self.assertIn("Congratulations", md)

    def test_format_referee_feedback_markdown_bad_repo(self):
        """
        DONE CRITERIA (C36):
        Verify generated markdown delivers actionable feedback highlighting failed features and cheats on bad repo.
        """
        submission = SubmissionRecord(
            id="sub_test_bad_002",
            contract_id="cnt_pactpal_benchmark",
            seller_id="seller_bob",
            repo_url="https://github.com/dkrrish9/PactPal",
            commit_sha="6a06754000000000000000000000000000000000",
            build_notes="Deliverable with known defects",
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

        # Temporarily run bad repo through runner
        bad_submission = SubmissionRecord(
            id="sub_test_bad_002",
            contract_id="cnt_pactpal_benchmark",
            seller_id="seller_bob",
            repo_url=str(self.bad_repo_dir),
            commit_sha="badrepo123",
            build_notes="Bad repo deliverable",
            submission_number=1,
            is_late=False,
            delay_seconds=0,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            deadline=None
        )

        report = self.runner.run_pipeline(
            submission=bad_submission,
            features=features,
            capture_screenshots=False,
            notify_seller=False
        )

        md = self.notifier.format_referee_feedback_markdown(report, submission)

        self.assertIn("PARTIAL ESCROW RELEASE APPROVED", md)
        self.assertIn("FAILED ❌", md)
        self.assertIn("Security & Cheat Scan Findings", md)
        self.assertIn("Remediation Guidance", md)
        self.assertIn("Fix Failing Features", md)

    def test_notify_seller_on_repo_persists_evidence(self):
        """Verify notification creates markdown feedback and json delivery receipt."""
        submission = SubmissionRecord(
            id="sub_test_evidence",
            contract_id="cnt_evidence_101",
            seller_id="seller_dave",
            repo_url=str(self.good_repo_dir),
            commit_sha="abc12345678",
            build_notes="Testing evidence generation",
            submission_number=1,
            is_late=False,
            delay_seconds=0,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            deadline=None
        )

        report = self.runner.run_pipeline(
            submission=submission,
            features=[],
            capture_screenshots=False,
            notify_seller=False
        )

        record = self.notifier.notify_seller_on_repo(
            report=report,
            submission=submission,
            evidence_dir=self.temp_evidence_dir,
            force_mock_post=True
        )

        self.assertEqual(record["status"], "COMPLETED")
        self.assertTrue(record["posted_to_github"])
        self.assertIsNotNone(record["evidence_markdown"])
        self.assertIsNotNone(record["evidence_receipt"])

        md_path = Path(record["evidence_markdown"])
        json_path = Path(record["evidence_receipt"])

        self.assertTrue(md_path.exists())
        self.assertTrue(json_path.exists())
        self.assertGreater(md_path.stat().st_size, 200)

    def test_live_github_comment_dispatch_on_commit(self):
        """
        Verify real GitHub REST API dispatch by posting feedback on an existing commit
        in the target repository dkrrish9/PactPal.
        """
        sample_md = "🤖 **PactPal Verification Test**: Automated feedback delivery verification for C36."
        result = self.notifier.post_feedback_comment(
            repo_url="https://github.com/dkrrish9/PactPal",
            commit_sha="0745dacaca767b934916dc9bf8a6806bada3a605",
            body_markdown=sample_md
        )

        self.assertEqual(result["status"], "DELIVERED")
        self.assertTrue(result["posted"])
        self.assertIn("https://github.com/dkrrish9/PactPal/commit/0745dac", result["comment_url"])
        self.assertIsNotNone(result["comment_id"])

    def test_pipeline_runner_full_integration_with_notification(self):
        """Verify full verification pipeline runner executes Stage A through Stage G including notification."""
        submission = SubmissionRecord(
            id=str(uuid.uuid4()),
            contract_id=f"cnt_{uuid.uuid4().hex[:8]}",
            seller_id="seller_integration",
            repo_url=str(self.good_repo_dir),
            commit_sha="integ123456",
            build_notes="Full integration test with seller feedback",
            submission_number=1,
            is_late=False,
            delay_seconds=0,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            deadline=None
        )

        report = self.runner.run_pipeline(
            submission=submission,
            features=[
                {"id": "feat_profile", "title": "Feature 1: User Profile Header", "price_weight": 100.0, "allocated_amount": 1000.0}
            ],
            capture_screenshots=False,
            notify_seller=True
        )

        self.assertTrue(report.build_succeeded)
        self.assertIsNotNone(report.notifications)
        self.assertEqual(len(report.notifications), 1)
        self.assertEqual(report.notifications[0]["status"], "COMPLETED")


if __name__ == "__main__":
    unittest.main()
