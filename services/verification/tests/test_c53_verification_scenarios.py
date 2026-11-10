"""
Comprehensive Verification Tests for Failed Build, Late Submission, and Resubmission Limit (C53)
Milestone 4 - Task C53
Validates Done Criteria:
  "Each produces the expected report and decision"
  1. Failed Build:
     - Expected Report: build_succeeded=False, overall_score=0.0, per_feature_results FAILED, downstream skipped.
     - Expected Decision: next_state='DECISION', recommendation='REJECT_AND_HOLD' (escrow payout blocked).
  2. Late Submission:
     - Expected Report: is_late=True, delay_seconds > 0, timing_compliance status='LATE', metadata records delay.
     - Expected Decision: captures delivery timing status and feedback flags '⚠️ Late Submission'.
  3. Resubmission Limit:
     - Expected Report & Decision for 1..3: Accepted with version labels v1, v2, v3 and corresponding reports.
     - Expected Decision for 4th attempt: Refused with status='REFUSED', error='SUBMISSION_LIMIT_EXCEEDED',
       and next_action='DISPUTE_REVIEW'.
"""

import sys
import unittest
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.verification.src.models import IntakeRequest, SubmissionRecord, VerificationReport
from services.verification.src.intake import StageAIntakeProcessor, SubmissionLimitExceededError
from services.verification.src.runner import VerificationPipelineRunner
from services.verification.src.resubmission_manager import ResubmissionManager
from services.verification.src.github_notifier import GitHubFeedbackNotifier


class TestVerificationScenariosC53(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.good_repo_dir = PROJECT_ROOT / "demo-assets" / "good-repo"
        cls.bad_repo_dir = PROJECT_ROOT / "demo-assets" / "bad-repo"
        cls.broken_repo_dir = PROJECT_ROOT / "services" / "verification" / "spike" / "fixtures" / "broken-repo"
        cls.figma_dir = PROJECT_ROOT / "demo-assets" / "figma"

    def setUp(self):
        self.runner = VerificationPipelineRunner(figma_reference_dir=self.figma_dir)
        self.intake = StageAIntakeProcessor()
        self.resubmission_mgr = ResubmissionManager()
        self.notifier = GitHubFeedbackNotifier()

        self.contract_id = f"cnt_{uuid.uuid4().hex[:8]}"
        self.seller_id = f"usr_{uuid.uuid4().hex[:8]}"
        self.now = datetime.now(timezone.utc)

        self.features = [
            {"id": "feat_auth", "title": "Feature 1: User Authentication", "price_weight": 50.0, "allocated_amount": 500.0},
            {"id": "feat_payments", "title": "Feature 2: Escrow Checkout", "price_weight": 50.0, "allocated_amount": 500.0}
        ]

    # =========================================================================
    # SCENARIO 1: FAILED BUILD
    # Done Criteria: Failed build produces the expected report and decision
    # =========================================================================
    def test_failed_build_produces_expected_report_and_decision(self):
        """
        Scenario 1: Deliverable compilation fails in isolated workspace.
        Expected Report:
          - build_succeeded = False
          - overall_score = 0.0
          - features marked FAILED with severity HIGH
          - downstream stages skipped (tests, cheat scan, visual diff)
          - failure_reason and ai_diagnostic pinpoint compile error
        Expected Decision:
          - next_state = 'DECISION'
          - recommendation = 'REJECT_AND_HOLD' (escrow release blocked)
        """
        submission = SubmissionRecord(
            id=str(uuid.uuid4()),
            contract_id=self.contract_id,
            seller_id=self.seller_id,
            repo_url=str(self.broken_repo_dir),
            commit_sha="fail_build_sha_123",
            build_notes="Attempted delivery with syntax error in build.js",
            submission_number=1,
            is_late=False,
            delay_seconds=0,
            submitted_at=self.now.isoformat(),
            deadline=(self.now + timedelta(days=2)).isoformat()
        )

        report = self.runner.run_pipeline(
            submission=submission,
            features=self.features,
            capture_screenshots=False,
            notify_seller=False
        )

        # 1. Assert Expected Report Structure
        self.assertIsInstance(report, VerificationReport)
        self.assertFalse(report.build_succeeded, "Build status must be False for broken repo")
        self.assertEqual(report.overall_score, 0.0, "Score must be 0.0 when build fails")
        self.assertIsNotNone(report.failure_reason)
        self.assertIn("SyntaxError", report.build_logs)
        self.assertIn("syntax error", report.failure_reason.lower())

        # Assert skipped downstream stages
        self.assertIn("STAGE_C_TESTS", report.skipped_stages)
        self.assertIn("STAGE_D_CHEAT_SCAN", report.skipped_stages)
        self.assertIn("STAGE_E_VISUAL_DIFF", report.skipped_stages)

        # Assert per-feature status
        for feat in self.features:
            feat_result = report.per_feature_results[feat["id"]]
            self.assertEqual(feat_result["status"], "FAILED")
            self.assertEqual(feat_result["severity"], "HIGH")
            self.assertIn("Build failed", feat_result["reason"])

        # Assert container hardening is attached
        self.assertIsNotNone(report.container_hardening)
        self.assertTrue(report.container_hardening["container_hardened"])

        # 2. Assert Expected Decision
        self.assertEqual(report.next_state, "DECISION")
        self.assertEqual(report.recommendation, "REJECT_AND_HOLD", "Decision must reject payout and hold escrow funds")

        # 3. Assert Seller Notification Reflects Build Failure Decision
        md = self.notifier.format_referee_feedback_markdown(report=report, submission=submission)
        self.assertIn("ESCROW SETTLEMENT PLACED ON HOLD", md)
        self.assertIn("❌ Build Failed", md)
        self.assertIn("REJECT_AND_HOLD", md)

    # =========================================================================
    # SCENARIO 2: LATE SUBMISSION
    # Done Criteria: Late submission produces the expected report and decision
    # =========================================================================
    def test_late_submission_produces_expected_report_and_decision(self):
        """
        Scenario 2: Deliverable is submitted past contractual deadline.
        Expected Report:
          - is_late = True
          - delay_seconds > 0, matching exact elapsed overdue seconds
          - timing_compliance records status='LATE' and delay breakdown
          - git_metadata deadline_evaluation records delay in hours/minutes
          - pipeline verification completes and assesses technical quality
        Expected Decision:
          - feedback comment flags '⚠️ Late Submission'
          - decision captures delivery timing compliance
        """
        # Contract deadline was 5 hours and 15 minutes ago
        deadline_time = self.now - timedelta(hours=5, minutes=15)

        intake_req = IntakeRequest(
            contract_id=self.contract_id,
            seller_id=self.seller_id,
            repo_url=str(self.good_repo_dir),
            commit_sha="e0f1d2c3b4a5",
            build_notes="Final deliverables submitted overdue",
            deadline=deadline_time,
            submission_time=self.now,
            previous_submissions_count=0
        )

        # Process intake
        submission = self.intake.process_submission(intake_req)

        # 1. Assert Intake Record Late Properties
        self.assertTrue(submission.is_late)
        expected_delay = 5 * 3600 + 15 * 60  # 18,900s
        self.assertAlmostEqual(submission.delay_seconds, expected_delay, delta=5)
        self.assertIn("LATE", submission.git_metadata["deadline_evaluation"])
        self.assertIn("5h 15m", submission.git_metadata["deadline_evaluation"])

        # Execute Verification Pipeline
        report = self.runner.run_pipeline(
            submission=submission,
            features=self.features,
            capture_screenshots=False,
            notify_seller=False
        )

        # 2. Assert Expected Report Reflects Late Timing
        self.assertIsNotNone(report.timing_compliance)
        self.assertTrue(report.timing_compliance["is_late"])
        self.assertEqual(report.timing_compliance["status"], "LATE")
        self.assertGreater(report.timing_compliance["delay_seconds"], 18000)
        self.assertEqual(report.timing_compliance["deadline"], deadline_time.isoformat())

        # Assert Code Quality was still verified
        self.assertTrue(report.build_succeeded)
        self.assertGreaterEqual(report.overall_score, 0.95)

        # 3. Assert Seller Notification Reflects Late Status
        md = self.notifier.format_referee_feedback_markdown(report=report, submission=submission)
        self.assertIn("⚠️ Late Submission", md)
        self.assertNotIn("✅ On-Time Delivery", md)

    # =========================================================================
    # SCENARIO 3: RESUBMISSION LIMIT
    # Done Criteria: Resubmission limit produces expected report and decision
    # =========================================================================
    def test_resubmission_limit_produces_expected_report_and_decision(self):
        """
        Scenario 3: Deliverable resubmission quota enforcement.
        Expected Report & Decision:
          - Attempts 1, 2, 3: Accepted, tagged v1, v2, v3 with full reports.
          - Attempt 4: Refused with structured refusal response:
              status = 'REFUSED'
              accepted = False
              error = 'SUBMISSION_LIMIT_EXCEEDED'
              next_action = 'DISPUTE_REVIEW'
              attempt_number = 4
              max_allowed = 3
        """
        deadline = self.now + timedelta(days=5)
        existing_submissions = []

        # Iterations 1, 2, 3
        for attempt in [1, 2, 3]:
            req = IntakeRequest(
                contract_id=self.contract_id,
                seller_id=self.seller_id,
                repo_url=str(self.good_repo_dir),
                commit_sha=f"11112222333{attempt}",
                build_notes=f"Revision #{attempt}",
                deadline=deadline,
                submission_time=self.now,
                previous_submissions_count=attempt - 1
            )

            result = self.runner.handle_contract_submission(
                request=req,
                existing_submissions=existing_submissions,
                features=self.features,
                execute_verification=True
            )

            # Assert Accepted Report & Decision
            self.assertEqual(result["status"], "ACCEPTED")
            self.assertTrue(result["accepted"])
            self.assertEqual(result["version_label"], f"v{attempt}")
            self.assertEqual(result["attempt_number"], attempt)
            self.assertEqual(result["attempts_remaining"], 3 - attempt)
            self.assertIn("report", result)
            self.assertIsInstance(result["report"], VerificationReport)

            existing_submissions.append(result["submission"])

        self.assertEqual(len(existing_submissions), 3)

        # ATTEMPT 4: EXCEEDS LIMIT
        req_fourth = IntakeRequest(
            contract_id=self.contract_id,
            seller_id=self.seller_id,
            repo_url=str(self.good_repo_dir),
            commit_sha="444455556666",
            build_notes="Fourth submission attempt should be refused",
            deadline=deadline,
            submission_time=self.now,
            previous_submissions_count=3
        )

        refusal = self.runner.handle_contract_submission(
            request=req_fourth,
            existing_submissions=existing_submissions,
            features=self.features,
            execute_verification=True
        )

        # Assert Expected Refusal Report and Decision
        self.assertEqual(refusal["status"], "REFUSED")
        self.assertFalse(refusal["accepted"])
        self.assertEqual(refusal["error"], "SUBMISSION_LIMIT_EXCEEDED")
        self.assertEqual(refusal["attempt_number"], 4)
        self.assertEqual(refusal["max_allowed"], 3)
        self.assertEqual(refusal["next_action"], "DISPUTE_REVIEW", "Decision must transition to DISPUTE_REVIEW")
        self.assertIn("Fourth resubmission is refused", refusal["message"])
        self.assertIn("refusal_timestamp", refusal)
        self.assertNotIn("report", refusal, "No pipeline report should be generated on refused attempt")

        # Assert Version Listing Contains All Historical Iterations
        versions_summary = self.runner.list_contract_versions(
            contract_id=self.contract_id,
            submissions=existing_submissions
        )
        self.assertEqual(versions_summary["total_versions"], 3)
        self.assertFalse(versions_summary["can_resubmit"])
        self.assertEqual(versions_summary["remaining_submissions"], 0)
        self.assertEqual(versions_summary["active_version"], "v3")

    # =========================================================================
    # END-TO-END INTERPLAY: Build Failure -> Late Resubmission -> Refusal
    # =========================================================================
    def test_combined_lifecycle_failed_build_to_late_resubmission_to_limit(self):
        """
        Validates the complete lifecycle combining all three scenarios:
          1. v1 fails build -> REJECT_AND_HOLD decision.
          2. v2 is submitted late with fixes -> Verified, is_late=True.
          3. v3 submitted -> Verified, quota reaches 0.
          4. v4 attempted -> Refused, transitions to DISPUTE_REVIEW.
        """
        deadline = self.now + timedelta(hours=1)
        submissions = []

        # 1. First Submission: Broken Repo (Failed Build)
        req1 = IntakeRequest(
            contract_id=self.contract_id,
            seller_id=self.seller_id,
            repo_url=str(self.broken_repo_dir),
            commit_sha="a1a1a1a1a1a1",
            build_notes="First try",
            deadline=deadline,
            submission_time=self.now,
            previous_submissions_count=0
        )
        res1 = self.runner.handle_contract_submission(req1, existing_submissions=submissions, features=self.features)
        self.assertEqual(res1["status"], "ACCEPTED")
        self.assertEqual(res1["version_label"], "v1")
        self.assertFalse(res1["report"].build_succeeded)
        self.assertEqual(res1["report"].recommendation, "REJECT_AND_HOLD")
        submissions.append(res1["submission"])

        # 2. Second Submission: Late Submission with Fixed Code
        late_time = self.now + timedelta(hours=3)  # 2 hours past deadline
        req2 = IntakeRequest(
            contract_id=self.contract_id,
            seller_id=self.seller_id,
            repo_url=str(self.good_repo_dir),
            commit_sha="b2b2b2b2b2b2",
            build_notes="Fixed compiler errors but submitted late",
            deadline=deadline,
            submission_time=late_time,
            previous_submissions_count=1
        )
        res2 = self.runner.handle_contract_submission(req2, existing_submissions=submissions, features=self.features)
        self.assertEqual(res2["status"], "ACCEPTED")
        self.assertEqual(res2["version_label"], "v2")
        self.assertTrue(res2["submission"].is_late)
        self.assertTrue(res2["report"].build_succeeded)
        self.assertTrue(res2["report"].timing_compliance["is_late"])
        submissions.append(res2["submission"])

        # 3. Third Submission: Final Polish
        req3 = IntakeRequest(
            contract_id=self.contract_id,
            seller_id=self.seller_id,
            repo_url=str(self.good_repo_dir),
            commit_sha="c3c3c3c3c3c3",
            build_notes="Final polish",
            deadline=deadline,
            submission_time=late_time + timedelta(hours=1),
            previous_submissions_count=2
        )
        res3 = self.runner.handle_contract_submission(req3, existing_submissions=submissions, features=self.features)
        self.assertEqual(res3["version_label"], "v3")
        self.assertEqual(res3["attempts_remaining"], 0)
        submissions.append(res3["submission"])

        # 4. Fourth Submission: Refused
        req4 = IntakeRequest(
            contract_id=self.contract_id,
            seller_id=self.seller_id,
            repo_url=str(self.good_repo_dir),
            commit_sha="d4d4d4d4d4d4",
            build_notes="Exceeded attempt",
            deadline=deadline,
            submission_time=late_time + timedelta(hours=2),
            previous_submissions_count=3
        )
        res4 = self.runner.handle_contract_submission(req4, existing_submissions=submissions, features=self.features)
        self.assertEqual(res4["status"], "REFUSED")
        self.assertEqual(res4["error"], "SUBMISSION_LIMIT_EXCEEDED")
        self.assertEqual(res4["next_action"], "DISPUTE_REVIEW")


if __name__ == "__main__":
    unittest.main()
