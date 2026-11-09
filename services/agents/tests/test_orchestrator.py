#!/usr/bin/env python3
"""
PactPal Milestone 1: AI Orchestrator Acceptance Test (Task C21)
Validates that:
1. CONTRACT_SIGNED events route to the Payment Agent.
2. CONTRACT_FUNDED events route to the Agreement Agent.
3. WORK_SUBMITTED events route to the Verification Agent.
4. CHANGE_REQUESTED events route to the Negotiation Agent.
5. All 4 agents receive their designated event payloads cleanly.
"""

import unittest
from datetime import datetime, timezone, timedelta

from ..orchestrator.events import OrchestratorEvent, AgentTarget, EventPayload, DispatchResult
from ..orchestrator.engine import EventOrchestrator, OrchestratorRoutingError

class TestOrchestrator(unittest.TestCase):

    def setUp(self):
        self.orchestrator = EventOrchestrator()
        self.contract_id = "contract_demo_101"
        self.buyer_id = "user_buyer_01"
        self.seller_id = "user_seller_02"

    def test_contract_signed_routes_to_payment_agent(self):
        """
        Checklist Acceptance Test:
        CONTRACT_SIGNED event must route to the Payment Agent to trigger PayPal Authorization.
        """
        result: DispatchResult = self.orchestrator.emit_signed(
            contract_id=self.contract_id,
            actor_id=self.seller_id,
            total_amount=1500.00,
            currency="USD"
        )

        self.assertEqual(result.event_type, OrchestratorEvent.CONTRACT_SIGNED)
        self.assertEqual(result.target_agent, AgentTarget.PAYMENT_AGENT)
        self.assertEqual(result.status, "HANDLED")

        # Verify Payment Agent responded with PayPal Authorize intent
        response = result.agent_response
        self.assertEqual(response["agent"], "PaymentAgent")
        self.assertEqual(response["action"], "PROMPT_PAYPAL_AUTHORIZATION")
        self.assertEqual(response["intent"], "AUTHORIZE")
        self.assertEqual(response["amount"], 1500.00)
        self.assertIn("AUTHORIZE", response["message"])

    def test_contract_funded_routes_to_agreement_agent(self):
        """
        Checklist Acceptance Test:
        CONTRACT_FUNDED event must route to the Agreement Agent to start delivery clock.
        """
        future_cutoff = (datetime.now(timezone.utc) + timedelta(days=29)).isoformat()
        result: DispatchResult = self.orchestrator.emit_funded(
            contract_id=self.contract_id,
            actor_id=self.buyer_id,
            auth_expires_at=future_cutoff
        )

        self.assertEqual(result.event_type, OrchestratorEvent.CONTRACT_FUNDED)
        self.assertEqual(result.target_agent, AgentTarget.AGREEMENT_AGENT)
        self.assertEqual(result.status, "HANDLED")

        # Verify Agreement Agent activated milestone timeline
        response = result.agent_response
        self.assertEqual(response["agent"], "AgreementAgent")
        self.assertEqual(response["action"], "START_MILESTONE_CLOCK")
        self.assertEqual(response["status"], "TIMELINE_ACTIVE")
        self.assertEqual(response["hold_expires_at"], future_cutoff)

    def test_work_submitted_routes_to_verification_agent(self):
        """
        Checklist Acceptance Test:
        WORK_SUBMITTED event must route to the Verification Agent to launch Render container.
        """
        repo_url = "https://github.com/freelancer/pactpal-website"
        commit_sha = "8f3b2a19c4d"

        result: DispatchResult = self.orchestrator.emit_submitted(
            contract_id=self.contract_id,
            seller_id=self.seller_id,
            repo_url=repo_url,
            commit_sha=commit_sha
        )

        self.assertEqual(result.event_type, OrchestratorEvent.WORK_SUBMITTED)
        self.assertEqual(result.target_agent, AgentTarget.VERIFICATION_AGENT)
        self.assertEqual(result.status, "HANDLED")

        # Verify Verification Agent prepared Render Workflows container run
        response = result.agent_response
        self.assertEqual(response["agent"], "VerificationAgent")
        self.assertEqual(response["action"], "SPAWN_RENDER_CONTAINER")
        self.assertEqual(response["repo_url"], repo_url)
        self.assertEqual(response["commit_sha"], commit_sha)
        self.assertIn("isolated_ephemeral_worker", response["workspace"])
        self.assertEqual(len(response["pipeline_stages"]), 6)  # Stages A through F

    def test_change_requested_routes_to_negotiation_agent(self):
        """
        Checklist Acceptance Test:
        CHANGE_REQUESTED event must route to the Negotiation Agent for scope diff evaluation.
        """
        result: DispatchResult = self.orchestrator.emit_change_requested(
            contract_id=self.contract_id,
            buyer_id=self.buyer_id,
            proposed_scope="Add Google OAuth login button",
            proposed_price=200.00
        )

        self.assertEqual(result.event_type, OrchestratorEvent.CHANGE_REQUESTED)
        self.assertEqual(result.target_agent, AgentTarget.NEGOTIATION_AGENT)
        self.assertEqual(result.status, "HANDLED")

        # Verify Negotiation Agent responded with evaluation stub
        response = result.agent_response
        self.assertEqual(response["agent"], "NegotiationAgent")
        self.assertEqual(response["action"], "EVALUATE_SCOPE_DIFF")
        self.assertEqual(response["proposed_price"], 200.00)

    def test_orchestrator_history_audit_trail(self):
        """Ensures all dispatched events are recorded in orchestrator history."""
        self.orchestrator.emit_signed(self.contract_id, self.seller_id)
        self.orchestrator.emit_funded(self.contract_id, self.buyer_id)
        self.orchestrator.emit_submitted(self.contract_id, self.seller_id, "https://repo.git", "sha123")

        self.assertEqual(len(self.orchestrator.history), 3)
        self.assertEqual(self.orchestrator.history[0].event_type, OrchestratorEvent.CONTRACT_SIGNED)
        self.assertEqual(self.orchestrator.history[1].event_type, OrchestratorEvent.CONTRACT_FUNDED)
        self.assertEqual(self.orchestrator.history[2].event_type, OrchestratorEvent.WORK_SUBMITTED)

if __name__ == "__main__":
    unittest.main()

