"""
Event Definitions & Data Models for the AI Orchestrator
Linked Tasks: C21 / A6
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime, timezone

class OrchestratorEvent(str, Enum):
    CONTRACT_DRAFTED = "CONTRACT_DRAFTED"
    CONTRACT_SIGNED = "CONTRACT_SIGNED"
    CONTRACT_FUNDED = "CONTRACT_FUNDED"
    WORK_SUBMITTED = "WORK_SUBMITTED"
    CHANGE_REQUESTED = "CHANGE_REQUESTED"
    VERIFICATION_COMPLETED = "VERIFICATION_COMPLETED"
    DISPUTE_RAISED = "DISPUTE_RAISED"

class AgentTarget(str, Enum):
    AGREEMENT_AGENT = "AGREEMENT_AGENT"
    PAYMENT_AGENT = "PAYMENT_AGENT"
    VERIFICATION_AGENT = "VERIFICATION_AGENT"
    NEGOTIATION_AGENT = "NEGOTIATION_AGENT"

@dataclass
class EventPayload:
    """Standardized event envelope dispatched across the platform."""
    event_id: str
    event_type: OrchestratorEvent
    contract_id: str
    actor_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class DispatchResult:
    """Outcome of an event routed to an agent."""
    event_id: str
    event_type: OrchestratorEvent
    target_agent: AgentTarget
    status: str  # DISPATCHED | HANDLED | ERROR
    agent_response: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

