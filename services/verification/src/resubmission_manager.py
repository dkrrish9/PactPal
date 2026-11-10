"""
PactPal Verification Pipeline - Resubmission Manager & Version Tracking (C39)
Handles the lifecycle of seller deliverable resubmissions:
  - Enforces strict contract limit of 3 submissions (Attempts 1, 2, 3)
  - Refuses 4th resubmissions with structured refusal records and escrow hold transitions
  - Manages sequential semantic versioning (v1, v2, v3)
  - Tracks historical submission versions with per-version verification verdicts, scores, and evidence
  - Provides version comparison and diff progress tracking across iterations
"""

import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path

from .models import IntakeRequest, SubmissionRecord, VerificationReport
from .intake import StageAIntakeProcessor, SubmissionLimitExceededError, MAX_RESUBMISSION_ATTEMPTS


@dataclass
class SubmissionVersion:
    """Represents a discrete, immutable submission version for a contract."""
    version_label: str       # 'v1', 'v2', 'v3'
    submission_number: int   # 1, 2, 3
    submission_id: str
    contract_id: str
    seller_id: str
    repo_url: str
    commit_sha: str
    submitted_at: str
    is_late: bool
    delay_seconds: int
    build_notes: str
    report_id: Optional[str] = None
    build_succeeded: Optional[bool] = None
    overall_score: Optional[float] = None
    verdict: Optional[str] = None
    is_active: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ResubmissionManager:
    """
    Manages seller resubmission workflows, maximum attempt enforcement,
    and contract version tracking.
    """

    MAX_LIMIT = MAX_RESUBMISSION_ATTEMPTS  # 3

    def __init__(self, intake_processor: Optional[StageAIntakeProcessor] = None):
        self.intake = intake_processor or StageAIntakeProcessor()

    def check_resubmission_eligibility(
        self,
        contract_id: str,
        existing_submissions: Union[int, List[Union[SubmissionRecord, Dict[str, Any]]]]
    ) -> Tuple[bool, int, str]:
        """
        Evaluates whether a seller is eligible to submit deliverable code.
        Accepts either an integer count of previous submissions or a list of submission objects.
        Returns:
            (eligible: bool, next_submission_number: int, reason: str)
        """
        count = existing_submissions if isinstance(existing_submissions, int) else len(existing_submissions)
        next_num = count + 1

        if next_num > self.MAX_LIMIT:
            reason = (
                f"Fourth resubmission is refused: Contract '{contract_id}' has already reached the maximum "
                f"allowable limit of {self.MAX_LIMIT} submissions. Further submissions are locked pending dispute review."
            )
            return False, next_num, reason

        remaining = self.MAX_LIMIT - next_num
        reason = f"Resubmission attempt #{next_num} permitted. {remaining} attempt(s) remaining."
        return True, next_num, reason

    def handle_submission_request(
        self,
        request: IntakeRequest,
        existing_submissions: List[Union[SubmissionRecord, Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Entrypoint for processing a deliverable submission or resubmission:
          - Validates attempt limit.
          - If count >= 3, REFUSES the 4th resubmission with structured refusal response.
          - If count < 3, completes Stage A intake and returns new version record.
        """
        eligible, attempt_num, reason = self.check_resubmission_eligibility(
            contract_id=request.contract_id,
            existing_submissions=existing_submissions
        )

        if not eligible:
            # Done Criteria: Fourth resubmission is refused
            return {
                "status": "REFUSED",
                "accepted": False,
                "error": "SUBMISSION_LIMIT_EXCEEDED",
                "message": reason,
                "attempt_number": attempt_num,
                "max_allowed": self.MAX_LIMIT,
                "contract_id": request.contract_id,
                "refusal_timestamp": datetime.now(timezone.utc).isoformat(),
                "next_action": "DISPUTE_REVIEW"
            }

        # Ensure previous_submissions_count reflects existing history
        request.previous_submissions_count = len(existing_submissions)

        # Process intake
        submission_record = self.intake.process_submission(request)

        version_label = f"v{submission_record.submission_number}"
        return {
            "status": "ACCEPTED",
            "accepted": True,
            "version_label": version_label,
            "submission": submission_record,
            "attempt_number": submission_record.submission_number,
            "attempts_remaining": self.MAX_LIMIT - submission_record.submission_number,
            "message": f"Submission #{submission_record.submission_number} ({version_label}) successfully registered."
        }

    def list_contract_submission_versions(
        self,
        contract_id: str,
        submissions: List[Union[SubmissionRecord, Dict[str, Any]]],
        reports: Optional[List[Union[VerificationReport, Dict[str, Any]]]] = None
    ) -> Dict[str, Any]:
        """
        Done Criteria: Versions are listed.
        Builds a comprehensive version history for the contract, correlating
        each submission version with its verification report and verdict.
        """
        report_map = {}
        if reports:
            for rep in reports:
                sub_id = getattr(rep, "submission_id", None) or (rep.get("submission_id") if isinstance(rep, dict) else None)
                if sub_id:
                    report_map[sub_id] = rep

        versions: List[SubmissionVersion] = []
        total_count = len(submissions)

        for idx, sub in enumerate(submissions):
            # Normalize submission record across dataclass, dict, and sqlite row
            if isinstance(sub, SubmissionRecord):
                s_id = sub.id
                c_id = sub.contract_id
                seller_id = sub.seller_id
                repo = sub.repo_url
                sha = sub.commit_sha
                submitted_at = sub.submitted_at
                is_late = sub.is_late
                delay = sub.delay_seconds
                notes = sub.build_notes
                num = sub.submission_number
            elif isinstance(sub, dict):
                s_id = str(sub.get("id", f"sub_{idx+1}"))
                c_id = str(sub.get("contract_id", contract_id))
                seller_id = str(sub.get("seller_id", "unknown"))
                repo = str(sub.get("repo_url", ""))
                sha = str(sub.get("commit_sha", ""))
                submitted_at = str(sub.get("submitted_at", datetime.now(timezone.utc).isoformat()))
                is_late = bool(sub.get("is_late", False))
                delay = int(sub.get("delay_seconds", 0))
                notes = str(sub.get("build_notes", ""))
                num = int(sub.get("submission_number", idx + 1))
            else:
                # Handle sqlite3.Row or generic attribute object
                s_id = str(getattr(sub, "id", None) or (sub["id"] if hasattr(sub, "__getitem__") else f"sub_{idx+1}"))
                c_id = str(getattr(sub, "contract_id", None) or (sub["contract_id"] if hasattr(sub, "__getitem__") else contract_id))
                seller_id = str(getattr(sub, "seller_id", None) or (sub["seller_id"] if hasattr(sub, "__getitem__") else "unknown"))
                repo = str(getattr(sub, "repo_url", None) or (sub["repo_url"] if hasattr(sub, "__getitem__") else ""))
                sha = str(getattr(sub, "commit_sha", None) or (sub["commit_sha"] if hasattr(sub, "__getitem__") else ""))
                submitted_at = str(getattr(sub, "submitted_at", None) or (sub["submitted_at"] if hasattr(sub, "__getitem__") else datetime.now(timezone.utc).isoformat()))
                is_late = bool(getattr(sub, "is_late", None) or (sub["is_late"] if hasattr(sub, "__getitem__") else False))
                delay = int(getattr(sub, "delay_seconds", None) or (sub["delay_seconds"] if hasattr(sub, "__getitem__") else 0))
                notes = str(getattr(sub, "build_notes", None) or (sub["build_notes"] if hasattr(sub, "__getitem__") else ""))
                num = int(getattr(sub, "submission_number", None) or (sub["submission_number"] if hasattr(sub, "__getitem__") else idx + 1))

            label = f"v{num}"
            is_active = (idx == total_count - 1)  # Latest is active version

            # Check matching report
            matching_report = report_map.get(s_id)
            report_id = None
            build_ok = None
            score = None
            verdict = None

            if matching_report:
                if isinstance(matching_report, VerificationReport):
                    report_id = matching_report.id
                    build_ok = matching_report.build_succeeded
                    score = matching_report.overall_score
                    verdict = matching_report.recommendation or ("FULL_RELEASE" if score >= 0.95 else ("PARTIAL_RELEASE" if score >= 0.25 else "REJECT_AND_HOLD"))
                elif isinstance(matching_report, dict):
                    report_id = str(matching_report.get("id", ""))
                    build_ok = bool(matching_report.get("build_succeeded", True))
                    score = float(matching_report.get("overall_score", 0.0))
                    verdict = str(matching_report.get("recommendation", "FULL_RELEASE" if score >= 0.95 else "PARTIAL_RELEASE"))
                else:
                    report_id = str(getattr(matching_report, "id", None) or (matching_report["id"] if hasattr(matching_report, "__getitem__") else ""))
                    build_ok = bool(getattr(matching_report, "build_succeeded", None) or (matching_report["build_succeeded"] if hasattr(matching_report, "__getitem__") else True))
                    score = float(getattr(matching_report, "overall_score", None) or (matching_report["overall_score"] if hasattr(matching_report, "__getitem__") else 0.0))
                    verdict = str(getattr(matching_report, "recommendation", None) or ("FULL_RELEASE" if score >= 0.95 else "PARTIAL_RELEASE"))

            versions.append(SubmissionVersion(
                version_label=label,
                submission_number=num,
                submission_id=s_id,
                contract_id=c_id,
                seller_id=seller_id,
                repo_url=repo,
                commit_sha=sha,
                submitted_at=submitted_at,
                is_late=is_late,
                delay_seconds=delay,
                build_notes=notes,
                report_id=report_id,
                build_succeeded=build_ok,
                overall_score=score,
                verdict=verdict,
                is_active=is_active
            ))

        return {
            "contract_id": contract_id,
            "total_versions": len(versions),
            "max_allowed_submissions": self.MAX_LIMIT,
            "remaining_submissions": max(0, self.MAX_LIMIT - len(versions)),
            "can_resubmit": len(versions) < self.MAX_LIMIT,
            "active_version": versions[-1].version_label if versions else None,
            "versions": [v.to_dict() for v in versions]
        }

    def compute_version_progress_summary(
        self,
        versions_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyzes score progression and changes between versions.
        Useful for seller feedback and AI Referee settlement deliberation.
        """
        versions = versions_summary.get("versions", [])
        if not versions:
            return {"status": "NO_VERSIONS", "progression": []}

        progression = []
        for i in range(len(versions)):
            curr = versions[i]
            curr_score = curr.get("overall_score")
            prev = versions[i - 1] if i > 0 else None
            prev_score = prev.get("overall_score") if prev else None

            delta = None
            if curr_score is not None and prev_score is not None:
                delta = round(curr_score - prev_score, 3)

            progression.append({
                "from_version": prev.get("version_label") if prev else None,
                "to_version": curr.get("version_label"),
                "score_before": prev_score,
                "score_after": curr_score,
                "score_delta": delta,
                "improved": (delta > 0) if delta is not None else None,
                "verdict": curr.get("verdict")
            })

        init_s = versions[0].get("overall_score")
        last_s = versions[-1].get("overall_score")
        overall_delta = round(last_s - init_s, 3) if (last_s is not None and init_s is not None) else None

        return {
            "contract_id": versions_summary.get("contract_id"),
            "initial_score": init_s,
            "latest_score": last_s,
            "overall_delta": overall_delta,
            "progression": progression
        }
