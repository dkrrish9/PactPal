"""
PactPal Verification Pipeline - Stage A: Intake Processor
Responsible for receiving code deliverables from freelancers:
  - Repository URL & commit SHA validation
  - Submission timestamp vs. contract deadline comparison (is_late flag)
  - Submission attempt tracking (max 3 resubmissions)
  - Git commit verification & metadata extraction
  - AI analysis of build notes & security flags
  - Assembly of immutable SubmissionRecord
"""

import re
import os
import sys
import subprocess
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

from .models import IntakeRequest, SubmissionRecord, AIIntakeAnalysis
from .ai_evaluator import AIIntakeEvaluator

MAX_RESUBMISSION_ATTEMPTS = 3

class IntakeValidationError(ValueError):
    """Raised when intake parameters fail validation."""
    pass

class SubmissionLimitExceededError(RuntimeError):
    """Raised when submission count exceeds the maximum allowable attempts."""
    pass

class StageAIntakeProcessor:
    """Orchestrates Stage A of the PactPal verification pipeline."""

    def __init__(self, ai_evaluator: Optional[AIIntakeEvaluator] = None):
        self.ai = ai_evaluator or AIIntakeEvaluator()

    @staticmethod
    def validate_repo_url(repo_url: str) -> str:
        """Validate repository URL format (HTTPS, SSH, or local path)."""
        if not repo_url or not isinstance(repo_url, str):
            raise IntakeValidationError("Repository URL must be a non-empty string.")
        
        url = repo_url.strip()
        # Accept http(s)://, git@, or local file system path for fixtures
        is_http = re.match(r"^https?://[^\s/$.?#].[^\s]*$", url)
        is_ssh = re.match(r"^git@[a-zA-Z0-9._-]+:[a-zA-Z0-9._/-]+\.git$", url)
        is_local = Path(url).exists()

        if not (is_http or is_ssh or is_local):
            raise IntakeValidationError(f"Invalid repository URL format: '{repo_url}'")
        return url

    @staticmethod
    def validate_commit_sha(commit_sha: str) -> str:
        """Validate commit hash syntax (7-64 hexadecimal characters or HEAD)."""
        if not commit_sha or not isinstance(commit_sha, str):
            raise IntakeValidationError("Commit SHA must be a non-empty string.")
        
        sha = commit_sha.strip()
        if sha.upper() == "HEAD":
            return sha
        
        if not re.match(r"^[0-9a-fA-F]{7,64}$", sha):
            raise IntakeValidationError(
                f"Invalid commit SHA '{commit_sha}'. Must be 7-64 hexadecimal characters or 'HEAD'."
            )
        return sha.lower()

    @staticmethod
    def evaluate_deadline(
        submission_time: datetime,
        deadline: Optional[datetime]
    ) -> Tuple[bool, int, str]:
        """
        Compare submission timestamp with contract deadline.
        Returns:
            (is_late: bool, delay_seconds: int, human_readable_note: str)
        """
        # Ensure UTC timezone awareness
        if submission_time.tzinfo is None:
            submission_time = submission_time.replace(tzinfo=timezone.utc)

        if deadline is None:
            return False, 0, "No deadline specified for contract."

        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)

        time_diff = submission_time - deadline
        delay_seconds = int(time_diff.total_seconds())

        if delay_seconds > 0:
            is_late = True
            hours, remainder = divmod(delay_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            note = f"LATE: Submitted {hours}h {minutes}m {seconds}s after deadline."
        else:
            is_late = False
            early_seconds = abs(delay_seconds)
            hours, remainder = divmod(early_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            note = f"ON TIME: Submitted {hours}h {minutes}m before deadline."

        return is_late, max(0, delay_seconds), note

    @staticmethod
    def calculate_submission_number(previous_count: int) -> int:
        """Calculate next submission number and enforce resubmission limits."""
        if previous_count < 0:
            previous_count = 0
            
        next_number = previous_count + 1
        if next_number > MAX_RESUBMISSION_ATTEMPTS:
            raise SubmissionLimitExceededError(
                f"Maximum submission limit ({MAX_RESUBMISSION_ATTEMPTS}) reached. "
                f"Cannot process attempt #{next_number}. Escrow requires dispute review."
            )
        return next_number

    def verify_git_commit(self, repo_url: str, commit_sha: str) -> Dict[str, Any]:
        """
        Query repository to verify the commit exists and extract commit metadata.
        Supports remote git repositories and local fixtures.
        """
        metadata = {
            "verified": False,
            "resolved_sha": commit_sha,
            "author": "Unknown",
            "commit_message": "Initial milestone submission",
            "commit_date": datetime.now(timezone.utc).isoformat()
        }

        # Check local path fixture first
        local_path = Path(repo_url)
        if local_path.exists() and (local_path / ".git").exists():
            try:
                # Resolve full SHA
                rev_cmd = ["git", "rev-parse", commit_sha]
                res_rev = subprocess.run(rev_cmd, cwd=local_path, capture_output=True, text=True, check=True)
                full_sha = res_rev.stdout.strip()

                # Get log info
                log_cmd = ["git", "log", "-1", "--format=%an|%ae|%ad|%s", full_sha]
                res_log = subprocess.run(log_cmd, cwd=local_path, capture_output=True, text=True, check=True)
                parts = res_log.stdout.strip().split("|", 3)
                
                metadata["verified"] = True
                metadata["resolved_sha"] = full_sha
                if len(parts) >= 4:
                    metadata["author"] = f"{parts[0]} <{parts[1]}>"
                    metadata["commit_date"] = parts[2]
                    metadata["commit_message"] = parts[3]
                return metadata
            except Exception as e:
                metadata["error"] = str(e)
                return metadata

        # Remote git check using git ls-remote if git is available
        if repo_url.startswith("http") or repo_url.startswith("git@"):
            try:
                cmd = ["git", "ls-remote", repo_url]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                if res.returncode == 0:
                    metadata["verified"] = True
                    # Check if commit_sha exists in ls-remote output (or prefix)
                    if commit_sha != "HEAD" and commit_sha not in res.stdout:
                        # Remote doesn't list individual non-ref SHAs in ls-remote,
                        # but repository accessibility is verified
                        metadata["notes"] = "Repository accessible. SHA will be verified on full clone in Stage B."
            except Exception as e:
                metadata["network_warning"] = str(e)

        return metadata

    def process_submission(self, req: IntakeRequest) -> SubmissionRecord:
        """
        Executes full Stage A Intake lifecycle:
          1. Validates repository URL and commit SHA syntax.
          2. Evaluates submission time against deadline (sets is_late flag).
          3. Enforces version numbering and checks max resubmission limit (<= 3).
          4. Verifies git repository & commit metadata.
          5. Invokes AI Intake Evaluator to analyze build notes and safety risks.
          6. Returns immutable SubmissionRecord.
        """
        # 1. Validation
        valid_repo = self.validate_repo_url(req.repo_url)
        valid_sha = self.validate_commit_sha(req.commit_sha)

        # 2. Version numbering & Resubmission guard
        submission_number = self.calculate_submission_number(req.previous_submissions_count)

        # 3. Deadline Check
        submitted_at = req.submission_time or datetime.now(timezone.utc)
        is_late, delay_seconds, deadline_note = self.evaluate_deadline(submitted_at, req.deadline)

        # 4. Git Metadata
        git_meta = self.verify_git_commit(valid_repo, valid_sha)
        if git_meta.get("commit_message") == "Initial milestone submission" and submission_number > 1:
            git_meta["commit_message"] = f"Milestone resubmission #{submission_number} (commit {valid_sha[:8]})" 

        # 5. AI Safety & Build Analysis
        ai_analysis = self.ai.evaluate_submission(
            repo_url=valid_repo,
            commit_sha=git_meta.get("resolved_sha", valid_sha),
            build_notes=req.build_notes or "",
            commit_message=git_meta.get("commit_message"),
            submission_number=submission_number
        )

        # 6. Assembly
        record = SubmissionRecord.create(
            contract_id=req.contract_id,
            seller_id=req.seller_id,
            repo_url=valid_repo,
            commit_sha=git_meta.get("resolved_sha", valid_sha),
            build_notes=req.build_notes or "",
            submission_number=submission_number,
            is_late=is_late,
            delay_seconds=delay_seconds,
            submitted_at=submitted_at,
            deadline=req.deadline,
            ai_analysis=ai_analysis,
            git_metadata={**git_meta, "deadline_evaluation": deadline_note}
        )

        return record
