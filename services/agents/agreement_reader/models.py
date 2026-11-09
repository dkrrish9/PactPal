"""
Data Models for Agreement Reader & Priced Checklist
Linked Tasks: C12 / A3 / A4
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

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

@dataclass
class ClarificationPrompt:
    """Actionable feedback generated when contract validation fails."""
    field: str
    feature_title: Optional[str]
    issue: str
    suggested_action: str

@dataclass
class ValidationResult:
    """Outcome of contract form auto-validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    clarifications: List[ClarificationPrompt] = field(default_factory=list)

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

