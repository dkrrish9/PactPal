"""
AI Referee Clarification Engine
Linked Tasks: C16 / A4
Zero-Trust Rule:
The AI Referee NEVER guesses ambiguous weights, deadlines, or tests.
When auto-validation fails, this engine formats a structured ClarificationRequest
and conversational prompt for the buyer.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from .models import ValidationResult, ClarificationRequest, ClarificationPrompt
from .validator import validate_contract_form

def build_conversational_message(errors: List[str], clarifications: List[ClarificationPrompt]) -> str:
    """
    Builds an authoritative yet helpful message from the AI Escrow Referee
    explaining why the contract cannot proceed without buyer clarification.
    """
    lines = [
        "🤝 AI Escrow Referee Notice:",
        "I cannot lock this contract into escrow because zero-trust rules require exact, measurable terms before freezing funds.",
        "Under our impartial referee policy, I will NEVER guess your milestone prices, deadlines, or acceptance criteria.",
        "",
        "Please clarify the following item(s) before we can proceed:"
    ]

    for idx, c in enumerate(clarifications, 1):
        subject = f"Feature '{c.feature_title}'" if c.feature_title else f"Field '{c.field}'"
        lines.append(f"{idx}. {subject}: {c.issue}")
        lines.append(f"   👉 Suggested Action: {c.suggested_action}")
        if c.options:
            lines.append(f"   💡 Options: {' | '.join(c.options[:2])}")

    lines.append("")
    lines.append("Once you update these terms, I will re-validate and generate your locked milestone checklist.")
    return "\n".join(lines)

def generate_clarification_request(
    form_data: Dict[str, Any],
    validation_result: ValidationResult
) -> ClarificationRequest:
    """
    Constructs a formal ClarificationRequest object from validation errors.
    """
    contract_id = form_data.get("id") or form_data.get("contract_id")
    summary = f"Contract validation failed with {len(validation_result.errors)} issue(s). Clarification required from buyer."
    message = build_conversational_message(validation_result.errors, validation_result.clarifications)

    return ClarificationRequest(
        contract_id=contract_id,
        status="NEEDS_CLARIFICATION",
        summary=summary,
        conversational_message=message,
        clarifications=validation_result.clarifications,
        raw_errors=validation_result.errors
    )

def apply_clarification(
    form_data: Dict[str, Any],
    answers: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Applies buyer clarification corrections to form data:
    Supported answer keys:
    - 'weights': Dict[str, float] (title -> new weight)
    - 'tests': Dict[str, str] (title -> new acceptance test)
    - 'deadlines': Dict[str, str] (title/overall -> new deadline)
    - 'total_amount': float (updated total amount)
    """
    updated_form = dict(form_data)
    features = [dict(f) for f in updated_form.get("features", [])]

    # Update overall total if specified
    if "total_amount" in answers:
        updated_form["total_amount"] = float(answers["total_amount"])

    # Update overall deadline if specified
    if "deadline" in answers:
        updated_form["deadline"] = answers["deadline"]

    # Update feature-specific answers
    weight_fixes = answers.get("weights", {})
    test_fixes = answers.get("tests", {})
    deadline_fixes = answers.get("deadlines", {})

    for f in features:
        title = f.get("title") or f.get("name")
        if title in weight_fixes:
            f["price_weight"] = float(weight_fixes[title])
            f["weight"] = float(weight_fixes[title])
        if title in test_fixes:
            f["acceptance_test"] = test_fixes[title]
            f["test"] = test_fixes[title]
        if title in deadline_fixes:
            f["deadline"] = deadline_fixes[title]

    updated_form["features"] = features
    return updated_form

