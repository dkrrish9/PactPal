"""
AI Orchestrator Engine: Event Routing Skeleton
Linked Tasks: C21 / A6
Routes lifecycle events (Signed, Funded, Submitted, Change Requests) to the 4 specialized agents:
- Agreement Agent
- Payment Agent
- Verification Agent
- Negotiation Agent
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from .events import OrchestratorEvent, AgentTarget, EventPayload, DispatchResult
from .agents_stubs import (
    AgreementAgentStub,
    PaymentAgentStub,
    VerificationAgentStub,
    NegotiationAgentStub,
)

def generate_uuid() -> str:
    return str(uuid.uuid4())

class OrchestratorRoutingError(Exception):
    """Raised when an unroutable or invalid event is dispatched."""
    pass

class EventOrchestrator:
    """Central event router / switchboard connecting PactPal subsystems."""

    ROUTING_TABLE: Dict[OrchestratorEvent, AgentTarget] = {
        OrchestratorEvent.CONTRACT_DRAFTED: AgentTarget.AGREEMENT_AGENT,
        OrchestratorEvent.CONTRACT_SIGNED: AgentTarget.PAYMENT_AGENT,
        OrchestratorEvent.CONTRACT_FUNDED: AgentTarget.AGREEMENT_AGENT,
        OrchestratorEvent.WORK_SUBMITTED: AgentTarget.VERIFICATION_AGENT,
        OrchestratorEvent.CHANGE_REQUESTED: AgentTarget.NEGOTIATION_AGENT,
        OrchestratorEvent.VERIFICATION_COMPLETED: AgentTarget.PAYMENT_AGENT,
        OrchestratorEvent.DISPUTE_RAISED: AgentTarget.AGREEMENT_AGENT,
    }

    def __init__(self):
        # Register the 4 agent handlers
        self.agents = {
            AgentTarget.AGREEMENT_AGENT: AgreementAgentStub(),
            AgentTarget.PAYMENT_AGENT: PaymentAgentStub(),
            AgentTarget.VERIFICATION_AGENT: VerificationAgentStub(),
            AgentTarget.NEGOTIATION_AGENT: NegotiationAgentStub(),
        }
        self.history: List[DispatchResult] = []

    def dispatch(self, event: EventPayload) -> DispatchResult:
        """
        Routes an event envelope to its designated agent.
        """
        target_agent = self.ROUTING_TABLE.get(event.event_type)
        if not target_agent:
            raise OrchestratorRoutingError(f"No agent route defined for event type '{event.event_type.value}'.")

        handler = self.agents.get(target_agent)
        if not handler:
            raise OrchestratorRoutingError(f"Agent handler for '{target_agent.value}' is not registered.")

        try:
            response = handler.handle_event(event)
            status = "HANDLED"
        except Exception as e:
            response = {"error": str(e)}
            status = "ERROR"

        result = DispatchResult(
            event_id=event.event_id,
            event_type=event.event_type,
            target_agent=target_agent,
            status=status,
            agent_response=response,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        self.history.append(result)
        return result

    # --- Convenience Event Emitters ---
    def emit_signed(self, contract_id: str, actor_id: str, total_amount: float = 1000.0, currency: str = "USD") -> DispatchResult:
        """Emits CONTRACT_SIGNED -> Routes to Payment Agent for PayPal Authorization."""
        event = EventPayload(
            event_id=generate_uuid(),
            event_type=OrchestratorEvent.CONTRACT_SIGNED,
            contract_id=contract_id,
            actor_id=actor_id,
            data={"total_amount": total_amount, "currency": currency}
        )
        return self.dispatch(event)

    def emit_funded(self, contract_id: str, actor_id: str, auth_expires_at: Optional[str] = None) -> DispatchResult:
        """Emits CONTRACT_FUNDED -> Routes to Agreement Agent to start delivery clock."""
        event = EventPayload(
            event_id=generate_uuid(),
            event_type=OrchestratorEvent.CONTRACT_FUNDED,
            contract_id=contract_id,
            actor_id=actor_id,
            data={"auth_expires_at": auth_expires_at}
        )
        return self.dispatch(event)

    def emit_submitted(self, contract_id: str, seller_id: str, repo_url: str, commit_sha: str) -> DispatchResult:
        """Emits WORK_SUBMITTED -> Routes to Verification Agent to launch Render container."""
        event = EventPayload(
            event_id=generate_uuid(),
            event_type=OrchestratorEvent.WORK_SUBMITTED,
            contract_id=contract_id,
            actor_id=seller_id,
            data={"repo_url": repo_url, "commit_sha": commit_sha}
        )
        return self.dispatch(event)

    def emit_change_requested(self, contract_id: str, buyer_id: str, proposed_scope: str, proposed_price: float) -> DispatchResult:
        """Emits CHANGE_REQUESTED -> Routes to Negotiation Agent for scope evaluation."""
        event = EventPayload(
            event_id=generate_uuid(),
            event_type=OrchestratorEvent.CHANGE_REQUESTED,
            contract_id=contract_id,
            actor_id=buyer_id,
            data={"proposed_scope": proposed_scope, "proposed_price": proposed_price}
        )
        return self.dispatch(event)

