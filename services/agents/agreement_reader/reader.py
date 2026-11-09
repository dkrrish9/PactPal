"""
Agreement Reader: Form-to-Priced-Checklist Engine
Linked Tasks: C12 / A3 / A4
Converts contract form inputs into an immutable, priced checklist
where each feature has an acceptance test, price weight, allocated price, and deadline.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .models import ChecklistFeature, PricedChecklist, ValidationResult
from .validator import validate_contract_form

class AgreementValidationError(Exception):
    """Raised when contract form fields fail auto-validation."""
    def __init__(self, message: str, validation_result: ValidationResult):
        super().__init__(message)
        self.validation_result = validation_result
        self.errors = validation_result.errors
        self.clarifications = validation_result.clarifications

def generate_uuid() -> str:
    return str(uuid.uuid4())

def parse_contract_form(
    form_data: Dict[str, Any],
    contract_id: Optional[str] = None,
    reference_now: Optional[datetime] = None
) -> PricedChecklist:
    """
    Parses contract form fields into a priced checklist.
    Auto-validates rules (weights sum to 100%, tests present, future deadlines).
    Allocates exact monetary amounts per feature with penny-rounding protection.
    """
    # 1. Run Auto-Validation
    validation = validate_contract_form(form_data, reference_now=reference_now)
    if not validation.is_valid:
        error_summary = "; ".join(validation.errors)
        raise AgreementValidationError(
            f"Contract validation failed: {error_summary}",
            validation_result=validation
        )

    contract_id = contract_id or form_data.get("id") or generate_uuid()
    title = form_data.get("title", "Untitled Milestone")
    total_amount = round(float(form_data.get("total_amount", 0.0)), 2)
    currency = form_data.get("currency", "USD")
    milestone_deadline = form_data.get("deadline")
    raw_features = form_data.get("features", [])

    # 2. Build Priced Features with Penny-Rounding Conservation
    parsed_features: List[ChecklistFeature] = []
    running_allocated_sum = 0.0

    for idx, f in enumerate(raw_features):
        feature_id = f.get("id") or generate_uuid()
        feature_title = f.get("title") or f.get("name") or f"Feature #{idx + 1}"
        acceptance_test = f.get("acceptance_test") or f.get("test") or ""
        weight = round(float(f.get("price_weight", f.get("weight", 0.0))), 2)

        # Calculate preliminary dollar allocation
        allocated = round(total_amount * (weight / 100.0), 2)
        running_allocated_sum += allocated

        # Feature deadline defaults to contract milestone deadline if not specifically set
        feature_deadline = f.get("deadline") or milestone_deadline

        parsed_features.append(ChecklistFeature(
            id=feature_id,
            title=feature_title,
            acceptance_test=acceptance_test,
            price_weight=weight,
            allocated_amount=allocated,
            deadline=feature_deadline,
            status="PENDING",
            sort_order=f.get("sort_order", idx + 1)
        ))

    # 3. Exact Penny Reconciliation on Final Feature
    rounding_diff = round(total_amount - running_allocated_sum, 2)
    if rounding_diff != 0.0 and len(parsed_features) > 0:
        # Assign remainder cents to the last feature so sum matches total_amount exactly
        last_feature = parsed_features[-1]
        adjusted_amount = round(last_feature.allocated_amount + rounding_diff, 2)
        parsed_features[-1] = ChecklistFeature(
            id=last_feature.id,
            title=last_feature.title,
            acceptance_test=last_feature.acceptance_test,
            price_weight=last_feature.price_weight,
            allocated_amount=adjusted_amount,
            deadline=last_feature.deadline,
            status=last_feature.status,
            sort_order=last_feature.sort_order
        )

    now_iso = datetime.now(timezone.utc).isoformat()
    return PricedChecklist(
        contract_id=contract_id,
        title=title,
        total_amount=total_amount,
        currency=currency,
        deadline=milestone_deadline,
        features=parsed_features,
        is_locked=False,
        created_at=now_iso
    )

