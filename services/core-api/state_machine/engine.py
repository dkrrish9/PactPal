"""
PactPal 10-State Contract State Machine Engine
Enforces deterministic lifecycle transitions, role gating, and required data guards.
Linked Tasks: C09 / A2
"""

from enum import Enum
from typing import Dict, Set, Any, Optional
from datetime import datetime, timezone, timedelta

from ..auth.roles import (
    User,
    UserRole,
    UnauthorizedRoleError,
    assert_can_submit_for_review,
    assert_can_sign_contract,
    assert_can_request_revision,
    assert_can_fund_contract,
)

class ContractState(str, Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    SIGNED = "SIGNED"
    FUNDED = "FUNDED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    VERIFYING = "VERIFYING"
    DECISION = "DECISION"
    SETTLED = "SETTLED"
    DISPUTE = "DISPUTE"

# Valid state transitions lookup table
VALID_TRANSITIONS: Dict[ContractState, Set[ContractState]] = {
    ContractState.DRAFT: {ContractState.REVIEW},
    ContractState.REVIEW: {ContractState.SIGNED, ContractState.DRAFT},
    ContractState.SIGNED: {ContractState.FUNDED},
    ContractState.FUNDED: {ContractState.IN_PROGRESS, ContractState.SETTLED, ContractState.DISPUTE},
    ContractState.IN_PROGRESS: {ContractState.SUBMITTED, ContractState.IN_PROGRESS, ContractState.DECISION, ContractState.SETTLED, ContractState.DISPUTE},
    ContractState.SUBMITTED: {ContractState.VERIFYING, ContractState.DECISION, ContractState.SETTLED, ContractState.DISPUTE},
    ContractState.VERIFYING: {ContractState.DECISION, ContractState.SETTLED, ContractState.DISPUTE},
    ContractState.DECISION: {ContractState.SETTLED, ContractState.IN_PROGRESS, ContractState.DISPUTE},
    ContractState.DISPUTE: {ContractState.SETTLED},
    ContractState.SETTLED: set(),  # Terminal state
}

class StateMachineError(Exception):
    """Base exception for state machine violations."""
    pass

class InvalidStateTransitionError(StateMachineError):
    """Raised when an illegal transition is attempted."""
    pass

class StateValidationError(StateMachineError):
    """Raised when required data for a transition is missing or invalid."""
    pass

class ContractStateMachine:
    """Deterministic 10-state transition engine."""

    @staticmethod
    def validate_transition(
        contract: Dict[str, Any],
        actor: User,
        target_state: ContractState,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validates transition from contract['status'] to target_state:
        1. Checks transition legality in VALID_TRANSITIONS graph.
        2. Enforces actor role permissions.
        3. Enforces data guards (e.g. PayPal auth IDs when moving to FUNDED).
        Returns sanitized payload updates to apply to the contract.
        """
        metadata = metadata or {}
        raw_current = contract.get("status")
        try:
            current_state = ContractState(raw_current)
        except ValueError:
            raise InvalidStateTransitionError(f"Current contract state '{raw_current}' is unrecognized.")

        # 1. State Graph Check
        allowed_targets = VALID_TRANSITIONS.get(current_state, set())
        if target_state not in allowed_targets:
            raise InvalidStateTransitionError(
                f"Illegal state jump: Cannot transition from '{current_state.value}' to '{target_state.value}'. "
                f"Allowed next states: {[s.value for s in allowed_targets]}"
            )

        updates: Dict[str, Any] = {
            "status": target_state.value,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        # 2. Role & Data Guards per Transition
        if current_state == ContractState.DRAFT and target_state == ContractState.REVIEW:
            assert_can_submit_for_review(actor, contract)
            if not contract.get("title"):
                raise StateValidationError("Contract must have a title before submitting for review.")
            if float(contract.get("total_amount", 0)) <= 0:
                raise StateValidationError("Contract total amount must be greater than zero.")
            if not contract.get("seller_id"):
                raise StateValidationError("Contract must have an assigned seller before submitting for review.")

        elif current_state == ContractState.REVIEW and target_state == ContractState.SIGNED:
            assert_can_sign_contract(actor, contract)

        elif current_state == ContractState.REVIEW and target_state == ContractState.DRAFT:
            assert_can_request_revision(actor, contract)

        elif current_state == ContractState.SIGNED and target_state == ContractState.FUNDED:
            assert_can_fund_contract(actor, contract)
            paypal_order_id = metadata.get("paypal_order_id")
            paypal_auth_id = metadata.get("paypal_auth_id")

            if not paypal_order_id or not paypal_auth_id:
                raise StateValidationError(
                    "Funding requires valid 'paypal_order_id' and 'paypal_auth_id' from PayPal Authorization."
                )

            now = datetime.now(timezone.utc)
            auth_expires_at = (now + timedelta(days=29)).isoformat()

            updates["paypal_order_id"] = str(paypal_order_id)
            updates["paypal_auth_id"] = str(paypal_auth_id)
            updates["auth_expires_at"] = auth_expires_at
            updates["funded_at"] = now.isoformat()

        elif target_state == ContractState.SETTLED:
            is_admin = (actor.role == UserRole.ADMIN)
            is_referee = (getattr(actor, "id", None) == "AI_REFEREE" or getattr(actor, "name", None) == "AI Referee")
            if not (is_admin or is_referee):
                raise UnauthorizedRoleError(
                    f"User '{actor.id}' with role '{actor.role.value}' cannot settle contracts. "
                    "Only platform ADMIN or AI Referee can settle contract."
                )

        return updates
