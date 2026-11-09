"""
Agent Stubs for AI Orchestrator Event Routing
Linked Tasks: C21 / A6
Provides clean interfaces for Agreement, Payment, Verification, and Negotiation agents.
"""

from typing import Dict, Any
from .events import EventPayload

class AgreementAgentStub:
    """Agent responsible for contract checklists, deadlines, and milestone timelines."""

    def handle_event(self, event: EventPayload) -> Dict[str, Any]:
        data = event.data or {}
        if event.event_type.value == "CONTRACT_DRAFTED":
            return {
                "agent": "AgreementAgent",
                "action": "PARSE_CHECKLIST",
                "contract_id": event.contract_id,
                "status": "CHECKLIST_PARSED",
                "message": "Agreement Reader generated priced checklist."
            }
        elif event.event_type.value == "CONTRACT_FUNDED":
            return {
                "agent": "AgreementAgent",
                "action": "START_MILESTONE_CLOCK",
                "contract_id": event.contract_id,
                "status": "TIMELINE_ACTIVE",
                "hold_expires_at": data.get("auth_expires_at"),
                "message": "Funds locked. Milestone delivery clock started for seller."
            }
        return {
            "agent": "AgreementAgent",
            "action": "ACKNOWLEDGE",
            "contract_id": event.contract_id,
            "status": "PROCESSED"
        }

class PaymentAgentStub:
    """Agent responsible for PayPal Orders API (Authorize, Capture, Payouts, Refunds)."""

    def handle_event(self, event: EventPayload) -> Dict[str, Any]:
        data = event.data or {}
        if event.event_type.value == "CONTRACT_SIGNED":
            return {
                "agent": "PaymentAgent",
                "action": "PROMPT_PAYPAL_AUTHORIZATION",
                "contract_id": event.contract_id,
                "intent": "AUTHORIZE",
                "amount": data.get("total_amount", 0.0),
                "currency": data.get("currency", "USD"),
                "message": "Both parties signed. Triggering PayPal Orders API with intent=AUTHORIZE."
            }
        elif event.event_type.value == "VERIFICATION_COMPLETED":
            return {
                "agent": "PaymentAgent",
                "action": "EXECUTE_PARTIAL_PAYOUT",
                "contract_id": event.contract_id,
                "passed_weight": data.get("passed_weight", 100.0),
                "message": "Verification finished. Calculating capture and buyer refund."
            }
        return {
            "agent": "PaymentAgent",
            "action": "ACKNOWLEDGE",
            "contract_id": event.contract_id,
            "status": "PROCESSED"
        }

class VerificationAgentStub:
    """Agent responsible for Render Workflows isolated containers and Stage A-F verification."""

    def handle_event(self, event: EventPayload) -> Dict[str, Any]:
        data = event.data or {}
        if event.event_type.value == "WORK_SUBMITTED":
            return {
                "agent": "VerificationAgent",
                "action": "SPAWN_RENDER_CONTAINER",
                "contract_id": event.contract_id,
                "repo_url": data.get("repo_url"),
                "commit_sha": data.get("commit_sha"),
                "workspace": "isolated_ephemeral_worker",
                "pipeline_stages": ["Stage A Intake", "Stage B Build", "Stage C Tests", "Stage D Cheat Scan", "Stage E Visual Diff", "Stage F Report"],
                "message": "Deliverable received. Dispatching ephemeral job to Render Workflows."
            }
        return {
            "agent": "VerificationAgent",
            "action": "ACKNOWLEDGE",
            "contract_id": event.contract_id,
            "status": "PROCESSED"
        }

class NegotiationAgentStub:
    """Agent responsible for mid-project change requests and scope diff pricing."""

    def handle_event(self, event: EventPayload) -> Dict[str, Any]:
        data = event.data or {}
        if event.event_type.value == "CHANGE_REQUESTED":
            return {
                "agent": "NegotiationAgent",
                "action": "EVALUATE_SCOPE_DIFF",
                "contract_id": event.contract_id,
                "proposed_scope": data.get("proposed_scope"),
                "proposed_price": data.get("proposed_price"),
                "status": "MINI_AGREEMENT_GENERATED",
                "message": "Change request evaluated. Proposing fair market price and timeline adjustment."
            }
        return {
            "agent": "NegotiationAgent",
            "action": "ACKNOWLEDGE",
            "contract_id": event.contract_id,
            "status": "PROCESSED"
        }

