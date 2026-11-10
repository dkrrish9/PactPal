"""
Unit and Integration Tests for Resubmission Handling and Version Tracking (C39)
Validates Done Criteria:
  1. "Fourth resubmission is refused":
     - Attempts 1, 2, 3 are accepted with sequential labels (v1, v2, v3).
     - Attempt 4 is refused with structured refusal record (status: REFUSED, error: SUBMISSION_LIMIT_EXCEEDED).
  2. "versions are listed":
     - Versions list returns discrete version records with scores, verdicts, active version indicator,
       and remaining quota.
"""

import unittest
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from services.verification.src.models import IntakeRequest, SubmissionRecord, VerificationReport
from services.verification.src.intake import (
    StageAIntakeProcessor,
    SubmissionLimitExceededError,
    MAX_RESUBMISSION_ATTEMPTS
)
from services.verification.src.resubmission_manager import (
    ResubmissionManager,
    SubmissionVersion
)
from services.verification.src.runner import VerificationPipelineRunner


class TestResubmissionAndVersioning(unittest.TestCase):

    def setUp(self):
        self.manager = ResubmissionManager()
        self.contract_id = f"cnt_{uuid.uuid4().hex[:8]}"
        self.seller_id = f"usr_{uuid.uuid4().hex[:8]}"
        self.now = datetime.now(timezone.utc)
        self.deadline = self.now + timedelta(days=3)

    def _create_sample_request(self, sha: str = "commit_1111", notes: str = "Initial submission") -> IntakeRequest:
        return IntakeRequest(
            contract_id=self.contract_id,
            seller_id=self.seller_id,
            repo_url="https://github.com/seller/pactpal-demo.git",
            commit_sha=sha,
            build_notes=notes,
            deadline=self.deadline,
            submission_time=self.now,
            previous_submissions_count=0
        )

    def _create_sample_submission(self, sub_num: int, sha: str = "sha123") -> SubmissionRecord:
        return SubmissionRecord(
            id=f"sub_{sub_num}_{uuid.uuid4().hex[:6]}",
            contract_id=self.contract_id,
            seller_id=self.seller_id,
            repo_url="https://github.com/seller/pactpal-demo.git",
            commit_sha=sha,
            build_notes=f"Submission iteration #{sub_num}",
            submission_number=sub_num,
            is_late=False,
            delay_seconds=0,
            submitted_at=self.now.isoformat(),
            deadline=self.deadline.isoformat()
        )

    def _create_sample_report(
        self,
        submission_id: str,
        overall_score: float = 1.0,
        recommendation: str = "FULL_RELEASE",
        report_id: Optional[str] = None
    ) -> VerificationReport:
        rep_id = report_id or f"rep_{uuid.uuid4().hex[:6]}"
        return VerificationReport(
            id=rep_id,
            submission_id=submission_id,
            contract_id=self.contract_id,
            render_job_id=f"job_{rep_id[:8]}",
            build_succeeded=True,
            build_logs="Build completed successfully",
            test_suite_results={"tests_passed": 5, "tests_failed": 0},
            cheat_scan_findings=[],
            visual_diff_summary={"matched": 1, "similarity": 0.99},
            per_feature_results={"F1": "PASSED"},
            overall_score=overall_score,
            completed_at=self.now.isoformat(),
            recommendation=recommendation
        )

    # -------------------------------------------------------------------------
    # Done Criteria 1: Resubmission Eligibility & 4th Resubmission Refusal
    # -------------------------------------------------------------------------
    def test_check_resubmission_eligibility_first_three_attempts(self):
        """Attempts 1, 2, and 3 are permitted with decreasing remaining quota."""
        # 0 prior submissions -> Attempt 1
        ok, num, reason = self.manager.check_resubmission_eligibility(self.contract_id, existing_submissions=[])
        self.assertTrue(ok)
        self.assertEqual(num, 1)
        self.assertIn("Resubmission attempt #1 permitted", reason)
        self.assertIn("2 attempt(s) remaining", reason)

        # 1 prior submission -> Attempt 2
        sub1 = self._create_sample_submission(1)
        ok, num, reason = self.manager.check_resubmission_eligibility(self.contract_id, existing_submissions=[sub1])
        self.assertTrue(ok)
        self.assertEqual(num, 2)
        self.assertIn("Resubmission attempt #2 permitted", reason)
        self.assertIn("1 attempt(s) remaining", reason)

        # 2 prior submissions -> Attempt 3
        sub2 = self._create_sample_submission(2)
        ok, num, reason = self.manager.check_resubmission_eligibility(self.contract_id, existing_submissions=[sub1, sub2])
        self.assertTrue(ok)
        self.assertEqual(num, 3)
        self.assertIn("Resubmission attempt #3 permitted", reason)
        self.assertIn("0 attempt(s) remaining", reason)

    def test_check_resubmission_eligibility_fourth_refused(self):
        """Done Criteria: Fourth resubmission is refused when 3 submissions already exist."""
        sub1 = self._create_sample_submission(1)
        sub2 = self._create_sample_submission(2)
        sub3 = self._create_sample_submission(3)
        existing = [sub1, sub2, sub3]

        ok, num, reason = self.manager.check_resubmission_eligibility(self.contract_id, existing_submissions=existing)
        self.assertFalse(ok)
        self.assertEqual(num, 4)
        self.assertIn("Fourth resubmission is refused", reason)
        self.assertIn("maximum allowable limit of 3 submissions", reason)

    def test_handle_submission_request_progression_up_to_limit(self):
        """Attempts 1, 2, and 3 successfully register with version labels v1, v2, v3."""
        existing = []

        # Attempt 1
        req1 = self._create_sample_request(sha="111111111111", notes="v1 delivery")
        res1 = self.manager.handle_submission_request(req1, existing_submissions=existing)
        self.assertEqual(res1["status"], "ACCEPTED")
        self.assertTrue(res1["accepted"])
        self.assertEqual(res1["version_label"], "v1")
        self.assertEqual(res1["attempt_number"], 1)
        self.assertEqual(res1["attempts_remaining"], 2)
        self.assertEqual(res1["submission"].submission_number, 1)
        existing.append(res1["submission"])

        # Attempt 2 (Resubmission #1)
        req2 = self._create_sample_request(sha="222222222222", notes="v2 fixes")
        res2 = self.manager.handle_submission_request(req2, existing_submissions=existing)
        self.assertEqual(res2["status"], "ACCEPTED")
        self.assertTrue(res2["accepted"])
        self.assertEqual(res2["version_label"], "v2")
        self.assertEqual(res2["attempt_number"], 2)
        self.assertEqual(res2["attempts_remaining"], 1)
        self.assertEqual(res2["submission"].submission_number, 2)
        existing.append(res2["submission"])

        # Attempt 3 (Resubmission #2)
        req3 = self._create_sample_request(sha="333333333333", notes="v3 final touches")
        res3 = self.manager.handle_submission_request(req3, existing_submissions=existing)
        self.assertEqual(res3["status"], "ACCEPTED")
        self.assertTrue(res3["accepted"])
        self.assertEqual(res3["version_label"], "v3")
        self.assertEqual(res3["attempt_number"], 3)
        self.assertEqual(res3["attempts_remaining"], 0)
        self.assertEqual(res3["submission"].submission_number, 3)
        existing.append(res3["submission"])

    def test_handle_submission_request_fourth_resubmission_refused(self):
        """Done Criteria: Fourth resubmission is refused with structured refusal payload."""
        existing = [
            self._create_sample_submission(1, "sha_v1"),
            self._create_sample_submission(2, "sha_v2"),
            self._create_sample_submission(3, "sha_v3")
        ]

        req4 = self._create_sample_request(sha="444444444444", notes="v4 illegal attempt")
        res4 = self.manager.handle_submission_request(req4, existing_submissions=existing)

        self.assertEqual(res4["status"], "REFUSED")
        self.assertFalse(res4["accepted"])
        self.assertEqual(res4["error"], "SUBMISSION_LIMIT_EXCEEDED")
        self.assertEqual(res4["attempt_number"], 4)
        self.assertEqual(res4["max_allowed"], 3)
        self.assertIn("Fourth resubmission is refused", res4["message"])
        self.assertEqual(res4["next_action"], "DISPUTE_REVIEW")
        self.assertIn("refusal_timestamp", res4)

    # -------------------------------------------------------------------------
    # Done Criteria 2: Versions are Listed
    # -------------------------------------------------------------------------
    def test_list_contract_submission_versions_empty(self):
        """Contract with zero submissions lists zero versions."""
        result = self.manager.list_contract_submission_versions(self.contract_id, submissions=[])
        self.assertEqual(result["contract_id"], self.contract_id)
        self.assertEqual(result["total_versions"], 0)
        self.assertEqual(result["remaining_submissions"], 3)
        self.assertTrue(result["can_resubmit"])
        self.assertIsNone(result["active_version"])
        self.assertEqual(result["versions"], [])

    def test_list_contract_submission_versions_with_reports(self):
        """Done Criteria: Versions are listed with version_label, report details, verdict, and active flag."""
        sub1 = self._create_sample_submission(1, "commit_v1")
        sub2 = self._create_sample_submission(2, "commit_v2")
        sub3 = self._create_sample_submission(3, "commit_v3")
        submissions = [sub1, sub2, sub3]

        # Correlated reports
        rep1 = self._create_sample_report(sub1.id, overall_score=0.65, recommendation="PARTIAL_RELEASE", report_id="rep_1")
        rep2 = self._create_sample_report(sub2.id, overall_score=0.88, recommendation="PARTIAL_RELEASE", report_id="rep_2")
        rep3 = self._create_sample_report(sub3.id, overall_score=0.98, recommendation="FULL_RELEASE", report_id="rep_3")
        reports = [rep1, rep2, rep3]

        result = self.manager.list_contract_submission_versions(
            contract_id=self.contract_id,
            submissions=submissions,
            reports=reports
        )

        self.assertEqual(result["contract_id"], self.contract_id)
        self.assertEqual(result["total_versions"], 3)
        self.assertEqual(result["remaining_submissions"], 0)
        self.assertFalse(result["can_resubmit"])
        self.assertEqual(result["active_version"], "v3")

        versions = result["versions"]
        self.assertEqual(len(versions), 3)

        # Version 1 check
        v1 = versions[0]
        self.assertEqual(v1["version_label"], "v1")
        self.assertEqual(v1["submission_number"], 1)
        self.assertEqual(v1["submission_id"], sub1.id)
        self.assertEqual(v1["commit_sha"], "commit_v1")
        self.assertEqual(v1["report_id"], "rep_1")
        self.assertEqual(v1["overall_score"], 0.65)
        self.assertEqual(v1["verdict"], "PARTIAL_RELEASE")
        self.assertFalse(v1["is_active"])

        # Version 2 check
        v2 = versions[1]
        self.assertEqual(v2["version_label"], "v2")
        self.assertEqual(v2["submission_number"], 2)
        self.assertEqual(v2["submission_id"], sub2.id)
        self.assertEqual(v2["commit_sha"], "commit_v2")
        self.assertEqual(v2["overall_score"], 0.88)
        self.assertFalse(v2["is_active"])

        # Version 3 check (Active)
        v3 = versions[2]
        self.assertEqual(v3["version_label"], "v3")
        self.assertEqual(v3["submission_number"], 3)
        self.assertEqual(v3["submission_id"], sub3.id)
        self.assertEqual(v3["overall_score"], 0.98)
        self.assertEqual(v3["verdict"], "FULL_RELEASE")
        self.assertTrue(v3["is_active"])

    def test_list_contract_versions_from_dictionaries(self):
        """Validates that versions can be listed from raw database dictionary records."""
        sub_dicts = [
            {
                "id": "sub_dict_1",
                "contract_id": self.contract_id,
                "seller_id": self.seller_id,
                "repo_url": "https://github.com/seller/repo",
                "commit_sha": "sha_dict_1",
                "build_notes": "First try",
                "submission_number": 1,
                "is_late": False,
                "delay_seconds": 0,
                "submitted_at": self.now.isoformat()
            },
            {
                "id": "sub_dict_2",
                "contract_id": self.contract_id,
                "seller_id": self.seller_id,
                "repo_url": "https://github.com/seller/repo",
                "commit_sha": "sha_dict_2",
                "build_notes": "Second try",
                "submission_number": 2,
                "is_late": False,
                "delay_seconds": 0,
                "submitted_at": self.now.isoformat()
            }
        ]
        rep_dicts = [
            {
                "id": "rep_dict_1",
                "submission_id": "sub_dict_1",
                "contract_id": self.contract_id,
                "build_succeeded": 1,
                "overall_score": 0.50,
                "recommendation": "PARTIAL_RELEASE"
            },
            {
                "id": "rep_dict_2",
                "submission_id": "sub_dict_2",
                "contract_id": self.contract_id,
                "build_succeeded": 1,
                "overall_score": 0.96,
                "recommendation": "FULL_RELEASE"
            }
        ]

        result = self.manager.list_contract_submission_versions(
            contract_id=self.contract_id,
            submissions=sub_dicts,
            reports=rep_dicts
        )

        self.assertEqual(result["total_versions"], 2)
        self.assertEqual(result["active_version"], "v2")
        self.assertEqual(result["remaining_submissions"], 1)
        self.assertTrue(result["can_resubmit"])
        self.assertEqual(result["versions"][0]["version_label"], "v1")
        self.assertEqual(result["versions"][1]["version_label"], "v2")
        self.assertTrue(result["versions"][1]["is_active"])

    # -------------------------------------------------------------------------
    # Version Progression & Score Deltas
    # -------------------------------------------------------------------------
    def test_compute_version_progress_summary(self):
        """Verifies delta calculations across successive submission versions."""
        sub1 = self._create_sample_submission(1)
        sub2 = self._create_sample_submission(2)
        sub3 = self._create_sample_submission(3)

        rep1 = self._create_sample_report(sub1.id, overall_score=0.40, recommendation="REJECT_AND_HOLD")
        rep2 = self._create_sample_report(sub2.id, overall_score=0.75, recommendation="PARTIAL_RELEASE")
        rep3 = self._create_sample_report(sub3.id, overall_score=0.95, recommendation="FULL_RELEASE")

        summary = self.manager.list_contract_submission_versions(
            contract_id=self.contract_id,
            submissions=[sub1, sub2, sub3],
            reports=[rep1, rep2, rep3]
        )

        progress = self.manager.compute_version_progress_summary(summary)
        self.assertEqual(progress["contract_id"], self.contract_id)
        self.assertEqual(progress["initial_score"], 0.40)
        self.assertEqual(progress["latest_score"], 0.95)
        self.assertEqual(progress["overall_delta"], 0.55)

        deltas = progress["progression"]
        self.assertEqual(len(deltas), 3)

        # v1 progression item
        self.assertIsNone(deltas[0]["from_version"])
        self.assertEqual(deltas[0]["to_version"], "v1")
        self.assertEqual(deltas[0]["score_after"], 0.40)
        self.assertIsNone(deltas[0]["score_delta"])

        # v2 progression item (v1 -> v2)
        self.assertEqual(deltas[1]["from_version"], "v1")
        self.assertEqual(deltas[1]["to_version"], "v2")
        self.assertEqual(deltas[1]["score_before"], 0.40)
        self.assertEqual(deltas[1]["score_after"], 0.75)
        self.assertEqual(deltas[1]["score_delta"], 0.35)
        self.assertTrue(deltas[1]["improved"])

        # v3 progression item (v2 -> v3)
        self.assertEqual(deltas[2]["from_version"], "v2")
        self.assertEqual(deltas[2]["to_version"], "v3")
        self.assertEqual(deltas[2]["score_before"], 0.75)
        self.assertEqual(deltas[2]["score_after"], 0.95)
        self.assertEqual(deltas[2]["score_delta"], 0.20)
        self.assertTrue(deltas[2]["improved"])

    # -------------------------------------------------------------------------
    # Pipeline Runner Integration
    # -------------------------------------------------------------------------
    def test_runner_handle_contract_submission_refuses_fourth(self):
        """Runner's handle_contract_submission refuses fourth attempt without executing pipeline."""
        runner = VerificationPipelineRunner()

        existing = [
            self._create_sample_submission(1),
            self._create_sample_submission(2),
            self._create_sample_submission(3)
        ]
        req4 = self._create_sample_request(sha="fourth_attempt_sha")

        result = runner.handle_contract_submission(
            request=req4,
            existing_submissions=existing,
            execute_verification=True
        )

        self.assertFalse(result["accepted"])
        self.assertEqual(result["status"], "REFUSED")
        self.assertEqual(result["error"], "SUBMISSION_LIMIT_EXCEEDED")
        self.assertIn("Fourth resubmission is refused", result["message"])
        self.assertNotIn("report", result)

    def test_runner_list_contract_versions(self):
        """Runner's list_contract_versions delegates to resubmission manager cleanly."""
        runner = VerificationPipelineRunner()

        sub1 = self._create_sample_submission(1)
        res = runner.list_contract_versions(
            contract_id=self.contract_id,
            submissions=[sub1],
            reports=[]
        )

        self.assertEqual(res["total_versions"], 1)
        self.assertEqual(res["active_version"], "v1")
        self.assertEqual(res["remaining_submissions"], 2)
        self.assertTrue(res["can_resubmit"])


if __name__ == "__main__":
    unittest.main()
