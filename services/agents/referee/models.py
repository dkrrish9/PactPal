"""
Referee Data Models & Decision Structures
Linked Task: C34 / A10 (Milestone 2: Verify & Decide)
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

class DecisionOutcome(str, Enum):
    """Possible outcomes decided by the AI Referee based on verification results."""
    FULL_RELEASE = "FULL_RELEASE"         # 100% of funds released to seller
    PARTIAL_RELEASE = "PARTIAL_RELEASE"   # Proportional split (seller payout + buyer refund)
    HOLD = "HOLD"                         # Broken build or cheat blocks payout; frozen in escrow
    DEADLINE_EXPIRED = "DEADLINE_EXPIRED" # Deadline expired with zero deliverable; 100% buyer refund
    DISPUTE = "DISPUTE"                   # Explicit dispute triggered

@dataclass
class FeatureDecision:
    """Itemized ruling for an individual contract feature."""
    feature_id: str
    feature_title: str
    status: str  # PASSED | FAILED
    price_weight: float  # Percentage of contract (e.g. 25.0)
    allocated_amount: float  # Dollar value (e.g. 250.00)
    severity: str = "NONE"  # NONE | LOW | MEDIUM | HIGH | CRITICAL
    evidence: Optional[str] = None
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class RefereeDecision:
    """
    Legally binding settlement decision emitted by the AI Referee.
    Consumes verification report and produces disburse/refund instructions with plain-language rationale.
    """
    contract_id: str
    outcome: DecisionOutcome
    rule_triggered: str
    total_amount: float
    currency: str
    passed_amount: float
    refund_amount: float
    passed_weight: float
    failed_weight: float
    feature_decisions: List[FeatureDecision] = field(default_factory=list)
    conversational_explanation: str = ""
    plain_text_summary: str = ""
    next_state: str = "SETTLED"  # SETTLED | IN_PROGRESS | DECISION | DISPUTE
    can_dispute: bool = True
    dispute_grace_hours: int = 48
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["outcome"] = self.outcome.value
        data["feature_decisions"] = [f.to_dict() for f in self.feature_decisions]
        return data

