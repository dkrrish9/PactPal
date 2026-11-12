"""
Data Models for Agreement Reader & Priced Checklist
Linked Tasks: C12 / C16 / C19 / A3 / A4 / A5
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class ChecklistFeature:
    """A single priced checklist item derived from contract form fields."""
    id: str
    title: str
    acceptance_test: str
    price_weight: float  # Percentage of contract total (0.0 to 100.0)
    allocated_amount: float  # Exact monetary value
    deadline: str  # ISO 8601 formatted timestamp in the future
    status: str = "PENDING"  # PENDING | PASSED | FAILED | DISPUTED
    sort_order: int = 0
    change_request_id: Optional[str] = None  # Populated only if added via Price Negotiator amendment
    amended: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "acceptance_test": self.acceptance_test,
            "price_weight": self.price_weight,
            "allocated_amount": self.allocated_amount,
            "deadline": self.deadline,
            "status": self.status,
            "sort_order": self.sort_order,
            "change_request_id": self.change_request_id,
            "amended": self.amended
        }

@dataclass
class ClarificationPrompt:
    """Actionable feedback generated when contract validation fails."""
    field: str
    feature_title: Optional[str]
    issue: str
    suggested_action: str
    options: List[str] = field(default_factory=list)

@dataclass
class ValidationResult:
    """Outcome of contract form auto-validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    clarifications: List[ClarificationPrompt] = field(default_factory=list)

@dataclass
class ClarificationRequest:
    """
    User-facing clarification request dispatched to the buyer
    when contract terms fail auto-validation. Prohibits AI guessing.
    """
    contract_id: Optional[str]
    status: str  # NEEDS_CLARIFICATION
    summary: str
    conversational_message: str
    clarifications: List[ClarificationPrompt]
    raw_errors: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "status": self.status,
            "summary": self.summary,
            "conversational_message": self.conversational_message,
            "clarifications": [
                {
                    "field": c.field,
                    "feature_title": c.feature_title,
                    "issue": c.issue,
                    "suggested_action": c.suggested_action,
                    "options": c.options
                }
                for c in self.clarifications
            ],
            "raw_errors": self.raw_errors
        }

@dataclass
class PricedChecklist:
    """The locked, immutable single source of truth for milestone verification."""
    contract_id: str
    title: str
    total_amount: float
    currency: str
    deadline: str
    features: List[ChecklistFeature]
    is_locked: bool = False
    locked_at: Optional[str] = None
    buyer_confirmed_at: Optional[str] = None
    seller_confirmed_at: Optional[str] = None
    created_at: Optional[str] = None
    locked_by_dual_confirmation: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "title": self.title,
            "total_amount": self.total_amount,
            "currency": self.currency,
            "deadline": self.deadline,
            "features": [f.to_dict() for f in self.features],
            "is_locked": self.is_locked,
            "locked_at": self.locked_at,
            "buyer_confirmed_at": self.buyer_confirmed_at,
            "seller_confirmed_at": self.seller_confirmed_at,
            "created_at": self.created_at,
            "locked_by_dual_confirmation": self.locked_by_dual_confirmation
        }
