"""
PactPal Verification Pipeline - Stage A Models
Data models matching services/core-api/db/schema.sql for submissions and intake records.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import uuid

@dataclass
class AIIntakeAnalysis:
    """AI analysis of seller build notes, instructions, and commit message."""
    detected_framework: str
    build_commands: List[str]
    safety_flags: List[str]
    summary_of_changes: str
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    ai_provider_used: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class IntakeRequest:
    """Request payload received when a seller submits deliverable code."""
    contract_id: str
    seller_id: str
    repo_url: str
    commit_sha: str
    build_notes: Optional[str] = ""
    deadline: Optional[datetime] = None
    submission_time: Optional[datetime] = None
    previous_submissions_count: int = 0

@dataclass
class SubmissionRecord:
    """Immutable submission record matching database schema."""
    id: str
    contract_id: str
    seller_id: str
    repo_url: str
    commit_sha: str
    build_notes: str
    submission_number: int
    is_late: bool
    delay_seconds: int
    submitted_at: str
    deadline: Optional[str]
    ai_analysis: Optional[Dict[str, Any]] = None
    git_metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def create(
        cls,
        contract_id: str,
        seller_id: str,
        repo_url: str,
        commit_sha: str,
        build_notes: str,
        submission_number: int,
        is_late: bool,
        delay_seconds: int,
        submitted_at: datetime,
        deadline: Optional[datetime] = None,
        ai_analysis: Optional[AIIntakeAnalysis] = None,
        git_metadata: Optional[Dict[str, Any]] = None
    ) -> "SubmissionRecord":
        return cls(
            id=str(uuid.uuid4()),
            contract_id=contract_id,
            seller_id=seller_id,
            repo_url=repo_url,
            commit_sha=commit_sha,
            build_notes=build_notes or "",
            submission_number=submission_number,
            is_late=is_late,
            delay_seconds=delay_seconds,
            submitted_at=submitted_at.isoformat(),
            deadline=deadline.isoformat() if deadline else None,
            ai_analysis=ai_analysis.to_dict() if ai_analysis else None,
            git_metadata=git_metadata or {}
        )
