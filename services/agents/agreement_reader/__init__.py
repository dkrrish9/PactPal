"""
Agreement Reader Package
Linked Tasks: C12 / C16 / C19 / A3 / A4 / A5
"""

from .models import (
    ChecklistFeature,
    PricedChecklist,
    ValidationResult,
    ClarificationPrompt,
    ClarificationRequest
)
from .validator import validate_contract_form
from .reader import parse_contract_form, read_or_clarify, AgreementValidationError
from .lock import (
    lock_checklist,
    confirm_party,
    assert_can_modify_checklist,
    assert_checklist_is_unlocked,
    apply_negotiated_amendment,
    ChecklistLockError
)
from .clarifier import (
    generate_clarification_request,
    apply_clarification,
    build_conversational_message
)

__all__ = [
    "ChecklistFeature",
    "PricedChecklist",
    "ValidationResult",
    "ClarificationPrompt",
    "ClarificationRequest",
    "validate_contract_form",
    "parse_contract_form",
    "read_or_clarify",
    "AgreementValidationError",
    "lock_checklist",
    "confirm_party",
    "assert_can_modify_checklist",
    "apply_negotiated_amendment",
    "ChecklistLockError",
    "generate_clarification_request",
    "apply_clarification",
    "build_conversational_message",
]
