"""
Auto-Validator for Agreement Reader
Linked Tasks: C12 / C16 / A4
Rules:
1. Weights sum to exactly 100%.
2. Every feature has a non-empty measurable acceptance test.
3. Deadlines are in the future.
4. Total amount is greater than zero and matches sum of explicit feature prices (if provided).
5. On failure, triggers a clarify request to the buyer instead of guessing.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List
from .models import ValidationResult, ClarificationPrompt

def parse_iso_datetime(dt_str: str) -> datetime:
    """Parses an ISO format string into a UTC datetime object."""
    dt_str = dt_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

def validate_contract_form(form_data: Dict[str, Any], reference_now: datetime = None) -> ValidationResult:
    """
    Auto-validates the submitted contract form against all 4 invariants:
    1. weights = 100%
    2. every feature has a test
    3. deadline in future
    4. totals match
    Returns ValidationResult with errors and user-facing clarification prompts.
    """
    now = reference_now or datetime.now(timezone.utc)
    errors: List[str] = []
    clarifications: List[ClarificationPrompt] = []

    # 1. Total amount check
    try:
        total_amount = float(form_data.get("total_amount", 0.0))
    except (ValueError, TypeError):
        total_amount = 0.0

    if total_amount <= 0:
        err = "Total contract amount must be greater than zero."
        errors.append(err)
        clarifications.append(ClarificationPrompt(
            field="total_amount",
            feature_title=None,
            issue=err,
            suggested_action="Please set a valid positive payment amount for this escrow milestone.",
            options=["Specify a positive total amount (e.g. $1,000.00)"]
        ))

    # 2. Contract milestone deadline check (Must be in future)
    contract_deadline_str = form_data.get("deadline")
    if not contract_deadline_str:
        err = "Contract must define an overall milestone deadline."
        errors.append(err)
        clarifications.append(ClarificationPrompt(
            field="deadline",
            feature_title=None,
            issue=err,
            suggested_action="Please select a delivery cutoff date for this contract.",
            options=["Set delivery deadline to 7 days from now", "Set delivery deadline to 14 days from now", "Set delivery deadline to 30 days from now"]
        ))
    else:
        try:
            contract_dt = parse_iso_datetime(contract_deadline_str)
            if contract_dt <= now:
                err = f"Contract deadline '{contract_deadline_str}' is in the past."
                errors.append(err)
                clarifications.append(ClarificationPrompt(
                    field="deadline",
                    feature_title=None,
                    issue=err,
                    suggested_action="Please choose a future deadline date for milestone delivery.",
                    options=["Extend deadline by 7 days", "Extend deadline by 14 days", "Extend deadline by 30 days"]
                ))
        except Exception as e:
            err = f"Invalid deadline format: {str(e)}"
            errors.append(err)
            clarifications.append(ClarificationPrompt(
                field="deadline",
                feature_title=None,
                issue=err,
                suggested_action="Please provide a valid ISO-8601 date (e.g. '2026-12-01T00:00:00Z')."
            ))

    # 3. Features list check
    features = form_data.get("features", [])
    if not features:
        err = "Contract must contain at least one feature item in the checklist."
        errors.append(err)
        clarifications.append(ClarificationPrompt(
            field="features",
            feature_title=None,
            issue=err,
            suggested_action="Please add at least one deliverable feature to the checklist.",
            options=["Define core milestone deliverables"]
        ))
        return ValidationResult(is_valid=False, errors=errors, clarifications=clarifications)

    # 4. Feature Weights Check (Must equal exactly 100.0%)
    total_weight = 0.0
    for idx, f in enumerate(features):
        try:
            weight = float(f.get("price_weight", f.get("weight", 0.0)))
        except (ValueError, TypeError):
            weight = 0.0

        if weight <= 0:
            err = f"Feature '{f.get('title', f.get('name', f'Item {idx+1}'))}' must have a positive price weight."
            errors.append(err)
            clarifications.append(ClarificationPrompt(
                field="features[].price_weight",
                feature_title=f.get("title", f.get("name")),
                issue=err,
                suggested_action="Assign a positive percentage weight (e.g., 25%).",
                options=["Distribute remaining weights equally"]
            ))
        total_weight += weight

    if round(total_weight, 2) != 100.00:
        diff = round(100.00 - total_weight, 2)
        diff_str = f"+{diff}%" if diff > 0 else f"{diff}%"
        err = f"Feature price weights must sum to exactly 100.0% (Current sum: {round(total_weight, 2)}%, Difference: {diff_str})."
        errors.append(err)
        
        clarification_options = [
            f"Adjust feature weights proportionally to equal 100.0%",
            f"Allocate remaining {diff_str} to final feature",
            f"Manually specify custom weights for each feature"
        ]
        clarifications.append(ClarificationPrompt(
            field="features[].price_weight",
            feature_title=None,
            issue=err,
            suggested_action=f"Please adjust feature weights by {diff_str} so that the total sum equals 100.0%.",
            options=clarification_options
        ))

    # 5. Totals Match Check (If features have explicit prices, sum must equal total_amount)
    has_explicit_prices = any(
        f.get("price") is not None or f.get("amount") is not None or f.get("allocated_amount") is not None
        for f in features
    )
    if has_explicit_prices and total_amount > 0:
        explicit_sum = 0.0
        for f in features:
            val = f.get("price") or f.get("amount") or f.get("allocated_amount") or 0.0
            try:
                explicit_sum += float(val)
            except (ValueError, TypeError):
                pass
        
        explicit_sum = round(explicit_sum, 2)
        if round(explicit_sum, 2) != round(total_amount, 2):
            diff_amount = round(total_amount - explicit_sum, 2)
            err = f"Sum of feature prices (${explicit_sum:.2f}) does not match total contract amount (${total_amount:.2f}). Discrepancy: ${diff_amount:.2f}."
            errors.append(err)
            clarifications.append(ClarificationPrompt(
                field="total_amount",
                feature_title=None,
                issue=err,
                suggested_action=f"Update contract total amount to ${explicit_sum:.2f} or adjust feature prices to match ${total_amount:.2f}.",
                options=[
                    f"Update total contract amount to ${explicit_sum:.2f}",
                    f"Recalculate feature prices from weights to match ${total_amount:.2f}",
                    f"Add/subtract ${abs(diff_amount):.2f} on feature prices"
                ]
            ))

    # 6. Individual Feature Acceptance Tests & Deadlines
    for idx, f in enumerate(features):
        title = f.get("title") or f.get("name") or f"Feature #{idx + 1}"
        test = f.get("acceptance_test") or f.get("test") or ""

        if not str(test).strip():
            err = f"Feature '{title}' is missing a measurable acceptance test."
            errors.append(err)
            clarifications.append(ClarificationPrompt(
                field="features[].acceptance_test",
                feature_title=title,
                issue=err,
                suggested_action=f"Please specify a plain-language pass/fail condition for '{title}'.",
                options=[
                    f"Define automated test condition: 'User can trigger {title} and receive expected response.'",
                    f"Define UI condition: '{title} renders matching Figma mockups with no errors.'"
                ]
            ))

        # Optional feature-specific deadline check
        feat_deadline_str = f.get("deadline")
        if feat_deadline_str:
            try:
                feat_dt = parse_iso_datetime(feat_deadline_str)
                if feat_dt <= now:
                    err = f"Feature '{title}' deadline '{feat_deadline_str}' is in the past."
                    errors.append(err)
                    clarifications.append(ClarificationPrompt(
                        field="features[].deadline",
                        feature_title=title,
                        issue=err,
                        suggested_action=f"Please assign a future delivery date for '{title}'.",
                        options=["Match overall contract deadline", "Set to 7 days from now"]
                    ))
            except Exception as e:
                err = f"Feature '{title}' has invalid deadline format: {str(e)}"
                errors.append(err)
                clarifications.append(ClarificationPrompt(
                    field="features[].deadline",
                    feature_title=title,
                    issue=err,
                    suggested_action="Use a valid ISO-8601 date format."
                ))

    is_valid = len(errors) == 0
    return ValidationResult(is_valid=is_valid, errors=errors, clarifications=clarifications)
