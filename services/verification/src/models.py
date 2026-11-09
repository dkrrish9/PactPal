"""
PactPal Verification Pipeline Models
Data models matching services/core-api/db/schema.sql for submissions, intake, and verification reports.
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

@dataclass
class VerificationReport:
    """
    Structured multi-modal verification report matching core-api database schema.
    Generated upon pipeline completion or fast-tracked when a build fails.
    """
    id: str
    submission_id: str
    contract_id: str
    render_job_id: Optional[str]
    build_succeeded: bool
    build_logs: str
    test_suite_results: Dict[str, Any]
    cheat_scan_findings: List[Dict[str, Any]]
    visual_diff_summary: Dict[str, Any]
    per_feature_results: Dict[str, Any]
    overall_score: float
    completed_at: str
    failure_reason: Optional[str] = None
    ai_diagnostic: Optional[Dict[str, Any]] = None
    skipped_stages: Optional[List[str]] = None
    next_state: str = "DECISION"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def create_build_failure_report(
        cls,
        submission_id: str,
        contract_id: str,
        build_logs: str,
        failure_reason: str,
        features: Optional[List[Dict[str, Any]]] = None,
        render_job_id: Optional[str] = None,
        ai_diagnostic: Optional[Dict[str, Any]] = None
    ) -> "VerificationReport":
        """
        Creates a fast-tracked failure report when a deliverable fails Stage B Build.
        Marks features as FAILED due to unbuildable source, skips test/vision stages,
        and hands the report directly to the AI Referee in DECISION state.
        """
        per_feature = {}
        if features:
            for feat in features:
                feat_id = feat.get("id", str(uuid.uuid4()))
                per_feature[feat_id] = {
                    "feature_id": feat_id,
                    "feature_title": feat.get("title", "Unknown Feature"),
                    "status": "FAILED",
                    "reason": f"Build failed: {failure_reason}",
                    "evidence": failure_reason,
                    "severity": "HIGH",
                    "allocated_amount": feat.get("allocated_amount", 0.0),
                    "price_weight": feat.get("price_weight", 0.0)
                }

        return cls(
            id=str(uuid.uuid4()),
            submission_id=submission_id,
            contract_id=contract_id,
            render_job_id=render_job_id,
            build_succeeded=False,
            build_logs=build_logs,
            test_suite_results={"status": "SKIPPED", "reason": "Build failure"},
            cheat_scan_findings=[],
            visual_diff_summary={"status": "SKIPPED", "reason": "Build failure"},
            per_feature_results=per_feature,
            overall_score=0.0,
            completed_at=datetime.now(timezone.utc).isoformat(),
            failure_reason=failure_reason,
            ai_diagnostic=ai_diagnostic or {},
            skipped_stages=["STAGE_C_TESTS", "STAGE_D_CHEAT_SCAN", "STAGE_E_VISUAL_DIFF"],
            next_state="DECISION"
        )
