"""
Plain-Language Explanations Formatter for Referee Decisions
Linked Task: C34 / A10
"""

from typing import List
from .models import DecisionOutcome, FeatureDecision

def generate_plain_text_summary(
    outcome: DecisionOutcome,
    total_amount: float,
    passed_amount: float,
    refund_amount: float,
    currency: str,
    passed_count: int,
    total_count: int,
    reason: str = ""
) -> str:
    """Produces a concise 1-2 sentence human-readable executive summary."""
    if outcome == DecisionOutcome.FULL_RELEASE:
        return (
            f"Full escrow release approved: all {total_count} deliverables passed verification. "
            f"{currency} {passed_amount:,.2f} disbursed to seller in full."
        )
    elif outcome == DecisionOutcome.PARTIAL_RELEASE:
        return (
            f"Partial escrow release approved: {passed_count} of {total_count} deliverables passed. "
            f"{currency} {passed_amount:,.2f} released to seller; {currency} {refund_amount:,.2f} refunded to buyer."
        )
    elif outcome == DecisionOutcome.HOLD:
        return (
            f"Escrow settlement placed on HOLD. {reason or 'Deliverable failed clean sandbox build.'} "
            f"Funds remain frozen in escrow pending revision or dispute resolution."
        )
    elif outcome == DecisionOutcome.DEADLINE_EXPIRED:
        return (
            f"Contract delivery deadline expired without an approved deliverable. "
            f"100% of escrow funds ({currency} {total_amount:,.2f}) refunded to buyer."
        )
    return f"Referee verdict: {outcome.value}. Funds held pending review."


def generate_conversational_explanation(
    outcome: DecisionOutcome,
    contract_title: str,
    total_amount: float,
    currency: str,
    passed_amount: float,
    refund_amount: float,
    passed_weight: float,
    failed_weight: float,
    features: List[FeatureDecision],
    build_succeeded: bool = True,
    build_logs: str = "",
    failure_reason: str = "",
    cheat_findings_count: int = 0,
    visual_similarity: float = 1.0,
    dispute_grace_hours: int = 48
) -> str:
    """
    Generates a comprehensive, audit-ready markdown explanation detailing
    the exact rationale, financial breakdown, and next steps for both parties.
    """
    outcome_titles = {
        DecisionOutcome.FULL_RELEASE: "🟢 FULL ESCROW RELEASE APPROVED",
        DecisionOutcome.PARTIAL_RELEASE: "🟡 PARTIAL ESCROW SETTLEMENT APPROVED",
        DecisionOutcome.HOLD: "🔴 ESCROW SETTLEMENT PLACED ON HOLD",
        DecisionOutcome.DEADLINE_EXPIRED: "⏰ CONTRACT DEADLINE EXPIRED - FULL BUYER REFUND",
        DecisionOutcome.DISPUTE: "⚠️ ESCROW DISPUTE ESCALATION"
    }

    title = outcome_titles.get(outcome, f"REFEREE VERDICT: {outcome.value}")
    lines = [
        f"### {title}",
        f"**Milestone**: {contract_title or 'Digital Freelancing Milestone'}",
        "",
        "#### 💰 Financial Settlement Breakdown",
        f"- **Total Escrow Amount**: `{currency} {total_amount:,.2f}` (100.0%)",
        f"- **Disbursed to Seller**: `{currency} {passed_amount:,.2f}` ({passed_weight:.1f}%)",
        f"- **Refunded to Buyer**: `{currency} {refund_amount:,.2f}` ({failed_weight:.1f}%)",
        ""
    ]

    # Outcome-specific narrative
    if outcome == DecisionOutcome.HOLD:
        lines.append("#### ⚠️ Why Funds Are Held")
        if not build_succeeded:
            lines.append(
                "- **Sandbox Build Failed**: The submitted repository could not be compiled or bundled cleanly in the isolated container."
            )
            if failure_reason:
                lines.append(f"- **Build Failure Reason**: `{failure_reason}`")
            if build_logs:
                lines.append("```text")
                log_snippet = "\n".join(build_logs.strip().splitlines()[-6:])
                lines.append(log_snippet)
                lines.append("```")
        elif cheat_findings_count > 0:
            lines.append(
                f"- **Zero-Trust Rule Triggered**: Detected {cheat_findings_count} unresolved cheat scan finding(s) that bypass authentic testing."
            )
        lines.append("")
        lines.append(
            "**Action Required**: The seller has been invited to push a corrective commit. Escrow funds remain securely frozen."
        )
    elif outcome == DecisionOutcome.DEADLINE_EXPIRED:
        lines.append("#### ⏰ Why Escrow Was Refunded")
        lines.append(
            "- The agreed contractual delivery deadline passed before a verified deliverable was completed."
        )
        lines.append(
            f"- In accordance with PactPal zero-trust escrow terms, 100% of the funds (`{currency} {total_amount:,.2f}`) are returned to the buyer."
        )
    else:
        lines.append("#### 📋 Itemized Deliverable Verification")
        if not features:
            lines.append("_No individual checklist features recorded._")
        for idx, feat in enumerate(features, 1):
            symbol = "✓" if feat.status == "PASSED" else "✗"
            badge = "PASSED" if feat.status == "PASSED" else "FAILED"
            lines.append(
                f"{idx}. **{symbol} [{badge}] {feat.feature_title}** — `{currency} {feat.allocated_amount:,.2f}` ({feat.price_weight:.1f}%)"
            )
            if feat.status == "PASSED":
                if feat.evidence:
                    lines.append(f"   - **Verification Evidence**: {feat.evidence}")
            else:
                reason = feat.reason or feat.evidence or "Failed automated test assertions or criteria."
                lines.append(f"   - **Failure Reason**: {reason}")
                if feat.severity and feat.severity != "NONE":
                    lines.append(f"   - **Severity**: `{feat.severity}`")

    # Multimodal inspection notes
    lines.append("")
    lines.append("#### 🔍 Multimodal Inspection Summary")
    lines.append(f"- **Container Build**: `{'Passed' if build_succeeded else 'Failed'}`")
    lines.append(f"- **Visual Design Alignment**: `{visual_similarity * 100:.1f}% match against Figma`")
    lines.append(f"- **Cheat & Loophole Scan**: `{'Cleared (0 findings)' if cheat_findings_count == 0 else f'{cheat_findings_count} warning(s)'}`")

    # Next steps & dispute window
    lines.append("")
    lines.append("#### ⚖️ Next Steps & Dispute Window")
    if outcome in (DecisionOutcome.FULL_RELEASE, DecisionOutcome.PARTIAL_RELEASE):
        lines.append(
            f"- PayPal payout and capture settlement instructions have been staged for execution."
        )
        lines.append(
            f"- Either party may review the cryptographic receipt or file a formal dispute within the **{dispute_grace_hours}-hour grace window**."
        )
    elif outcome == DecisionOutcome.HOLD:
        lines.append("- Contract remains in `IN_PROGRESS` or `DECISION` hold state pending revision.")
    elif outcome == DecisionOutcome.DEADLINE_EXPIRED:
        lines.append("- PayPal authorization has been voided/refunded to the buyer's original payment method.")

    return "\n".join(lines)

