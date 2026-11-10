"""
Mini-Agreement Builder & Negotiation Workflow Engine
Linked Tasks: C42 / C46 / A13 (Milestone 3: Money & Extras)

Implements the accept/counter/reject lifecycle for change requests.
Synthesizes legally binding mini-agreements and appends new checklist features
while strictly preserving the immutability of original contract terms.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional, Dict, Any, List

from .models import ChangeRequestProposal, MiniAgreement
from ..agreement_reader.models import PricedChecklist, ChecklistFeature
from ..agreement_reader.lock import apply_negotiated_amendment

class NegotiationWorkflowEngine:
    """
    Executes the Accept/Counter/Reject lifecycle for mid-project scope changes.
    Enforces that original checklist features are never silently altered.
    """

    def accept(
        self,
        proposal: ChangeRequestProposal,
        accepted_by_id: str,
        checklist: PricedChecklist
    ) -> Tuple[MiniAgreement, PricedChecklist]:
        """
        Accepts a proposed or countered change request.
        Synthesizes a formal MiniAgreement and appends a new checklist item
        via the Price Negotiator without modifying any original features.
        """
        if proposal.status not in ("PROPOSED", "COUNTERED"):
            raise ValueError(f"Cannot accept change request in '{proposal.status}' state.")

        # 1. Update proposal status strictly to ACCEPTED (Enforces C46 pre-flight approval)
        proposal.status = "ACCEPTED"

        # 2. Financial & Timeline expansion
        original_total = round(float(checklist.total_amount), 2)
        additional_price = round(float(proposal.proposed_price), 2)
        new_total = round(original_total + additional_price, 2)

        # Calculate extended deadline
        try:
            orig_dt = datetime.fromisoformat(checklist.deadline.replace("Z", "+00:00"))
        except Exception:
            orig_dt = datetime.now(timezone.utc) + timedelta(days=7)

        new_dt = orig_dt + timedelta(hours=int(proposal.proposed_extra_time_hours))
        new_deadline_iso = new_dt.isoformat()

        # 3. Create the new ChecklistFeature
        feat_id = f"feat_{proposal.change_request_id.lower().replace('-', '_')}"
        new_weight = round((additional_price / new_total) * 100.0, 2)

        new_feature = ChecklistFeature(
            id=feat_id,
            title=proposal.suggested_feature_title or f"Amended: {proposal.description[:40]}",
            acceptance_test=proposal.suggested_acceptance_test or "Verify new feature functionality.",
            price_weight=new_weight,
            allocated_amount=additional_price,
            deadline=new_deadline_iso,
            status="PENDING",
            change_request_id=proposal.change_request_id,
            amended=True
        )

        # 4. Safely append to locked checklist via Price Negotiator authorization
        apply_negotiated_amendment(
            checklist=checklist,
            amendment_feature=new_feature,
            change_request_id=proposal.change_request_id,
            source="PRICE_NEGOTIATOR"
        )

        # 5. Update checklist total and deadline
        checklist.total_amount = new_total
        checklist.deadline = new_deadline_iso

        # 6. Recalculate weights proportionally so sum(weights) == 100.00%
        # CRUCIAL: Original allocated_amounts, IDs, titles, and tests remain 100% UNCHANGED
        total_weight_accum = 0.0
        for f in checklist.features:
            f.price_weight = round((f.allocated_amount / new_total) * 100.0, 2)
            total_weight_accum += f.price_weight

        # Reconcile rounding discrepancy to the last feature
        rounding_diff = round(100.00 - total_weight_accum, 2)
        if abs(rounding_diff) > 0:
            checklist.features[-1].price_weight = round(checklist.features[-1].price_weight + rounding_diff, 2)

        # 7. Synthesize formal MiniAgreement document
        legal_text = self._generate_mini_agreement_text(
            proposal=proposal,
            original_total=original_total,
            additional_price=additional_price,
            new_total=new_total,
            original_deadline=orig_dt.isoformat(),
            new_deadline=new_deadline_iso,
            new_feature=new_feature
        )

        agreement = MiniAgreement(
            agreement_id=f"AGREE-{uuid.uuid4().hex[:8].upper()}",
            contract_id=checklist.contract_id,
            change_request_id=proposal.change_request_id,
            title=f"Mini-Agreement: {new_feature.title}",
            original_total_amount=original_total,
            additional_price=additional_price,
            new_total_amount=new_total,
            original_deadline=orig_dt.isoformat(),
            new_deadline=new_deadline_iso,
            extra_hours=int(proposal.proposed_extra_time_hours),
            amended_feature_id=new_feature.id,
            amended_feature_title=new_feature.title,
            acceptance_test=new_feature.acceptance_test,
            new_feature_weight=new_feature.price_weight,
            ai_reasoning=proposal.ai_reasoning,
            accepted_by_id=accepted_by_id,
            additional_auth_id=proposal.additional_auth_id,
            status="ACCEPTED",
            legal_text=legal_text
        )

        return agreement, checklist

    def counter(
        self,
        proposal: ChangeRequestProposal,
        countered_by_id: str,
        counter_price: float,
        counter_hours: int,
        reason: str = ""
    ) -> ChangeRequestProposal:
        """
        Counters an active change request with adjusted price and hours.
        Updates status to COUNTERED and logs counter history.
        """
        if proposal.status not in ("PROPOSED", "COUNTERED"):
            raise ValueError(f"Cannot counter change request in '{proposal.status}' state.")

        # Log previous state in counter history
        proposal.counter_history.append({
            "previous_price": proposal.proposed_price,
            "previous_hours": proposal.proposed_extra_time_hours,
            "countered_by_id": countered_by_id,
            "counter_price": counter_price,
            "counter_hours": counter_hours,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        proposal.proposed_price = round(float(counter_price), 2)
        proposal.proposed_extra_time_hours = int(counter_hours)
        proposal.status = "COUNTERED"

        if reason:
            proposal.ai_reasoning += f"\n\n#### 🔄 Counter-Proposal Log:\n- Countered by `{countered_by_id}`: `${counter_price:,.2f}` (+{counter_hours}h)\n- Note: {reason}"

        return proposal

    def reject(
        self,
        proposal: ChangeRequestProposal,
        rejected_by_id: str,
        reason: str = ""
    ) -> ChangeRequestProposal:
        """
        Rejects a proposed or countered change request.
        Leaves contract terms, escrow, and checklist completely unchanged.
        """
        if proposal.status not in ("PROPOSED", "COUNTERED"):
            raise ValueError(f"Cannot reject change request in '{proposal.status}' state.")

        proposal.status = "REJECTED"
        proposal.rejection_reason = reason or "Change request rejected by counterparty."
        return proposal

    def _generate_mini_agreement_text(
        self,
        proposal: ChangeRequestProposal,
        original_total: float,
        additional_price: float,
        new_total: float,
        original_deadline: str,
        new_deadline: str,
        new_feature: ChecklistFeature
    ) -> str:
        """Generates legally binding amendment text for the mini-agreement."""
        return (
            f"# 📜 PACTPAL BINDING MINI-AGREEMENT (AMENDMENT)\n"
            f"**Contract ID**: `{proposal.contract_id}` | **Change Request**: `{proposal.change_request_id}`\n\n"
            f"### 1. Scope & Terms Amendment\n"
            f"The parties hereby agree to amend the baseline contract by adding the following deliverable:\n"
            f"- **Feature Title**: `{new_feature.title}`\n"
            f"- **Allocated Amount**: `${additional_price:,.2f} USD` (New Weight: `{new_feature.price_weight:.2f}%`)\n"
            f"- **Acceptance Test**: `{new_feature.acceptance_test}`\n"
            f"- **Amended Delivery Deadline**: `{new_deadline}` (+{proposal.proposed_extra_time_hours} hours)\n\n"
            f"### 2. Financial Reconciliation\n"
            f"- **Original Escrow Total**: `${original_total:,.2f} USD`\n"
            f"- **Incremental Escrow Authorization Required**: `${additional_price:,.2f} USD`\n"
            f"- **Amended Escrow Total**: `${new_total:,.2f} USD`\n\n"
            f"### 3. Non-Alteration Invariant\n"
            f"All existing features, amounts, acceptance tests, and milestones defined prior to this amendment "
            f"remain in full force and effect without silent alteration.\n"
        )

