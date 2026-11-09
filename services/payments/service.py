"""
PactPal Escrow Payment Service
Bridges PayPal REST Rails with Core Relational Persistence & State Machine.
Fulfills Done criteria for C10:
  - Creates order with AUTHORIZE intent
  - Directs buyer to approve in PayPal sandbox
  - Captures authorization_id and stores against the contract record
  - Strictly transitions contract from SIGNED -> FUNDED
"""

import math
import importlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from .client import PayPalClient, PayPalAPIError

# Dynamic imports to handle hyphenated directory name 'core-api'
_repo_mod = importlib.import_module("services.core-api.db.repository")
ContractRepository = _repo_mod.ContractRepository

_roles_mod = importlib.import_module("services.core-api.auth.roles")
User = _roles_mod.User
UserRole = _roles_mod.UserRole
ForbiddenActionError = _roles_mod.ForbiddenActionError
assert_can_fund_contract = _roles_mod.assert_can_fund_contract

_sm_mod = importlib.import_module("services.core-api.state_machine.engine")
ContractState = _sm_mod.ContractState
StateValidationError = _sm_mod.StateValidationError

def assert_can_view_contract_hold(actor: User, contract: Dict[str, Any]) -> None:
    """Only participant BUYER, SELLER, or platform ADMIN can inspect escrow hold data."""
    if actor.role == UserRole.ADMIN:
        return
    if actor.id != contract.get("buyer_id") and actor.id != contract.get("seller_id"):
        raise ForbiddenActionError(
            f"User '{actor.id}' with role '{actor.role.value}' is not authorized to view hold details for contract '{contract.get('id')}'. "
            f"Access restricted to contract buyer, seller, or admin."
        )


class EscrowPaymentService:
    """
    Manages milestone escrow lifecycle for contracts:
    order creation, buyer authorization approval, and persistence.
    """

    def __init__(
        self,
        repository: Optional[Any] = None,
        paypal_client: Optional[PayPalClient] = None
    ):
        self.repository = repository or ContractRepository()
        self.paypal = paypal_client or PayPalClient()

    def initiate_contract_hold(
        self,
        contract_id: str,
        actor: User,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates a PayPal Order with AUTHORIZE intent for a SIGNED contract.
        Returns the order ID and approval URL for buyer redirection.
        """
        contract = self.repository.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract '{contract_id}' not found.")

        # 1. Permission Guard: Only assigned buyer can fund
        assert_can_fund_contract(actor, contract)

        # 2. State Guard: Contract must be in SIGNED state
        if contract["status"] != ContractState.SIGNED.value:
            raise StateValidationError(
                f"Cannot initiate escrow hold on contract in '{contract['status']}' state. Contract must be 'SIGNED'."
            )

        total_amount = float(contract["total_amount"])
        currency = contract.get("currency", "USD")

        # 3. Call PayPal to generate AUTHORIZE intent order
        default_return = f"http://localhost:3000/contracts/{contract_id}/funded"
        default_cancel = f"http://localhost:3000/contracts/{contract_id}"

        order_res = self.paypal.create_authorize_order(
            reference_id=contract_id,
            amount=total_amount,
            currency=currency,
            description=f"PactPal Escrow: {contract['title']}",
            return_url=return_url or default_return,
            cancel_url=cancel_url or default_cancel
        )

        return {
            "contract_id": contract_id,
            "paypal_order_id": order_res["order_id"],
            "approve_url": order_res["approve_url"],
            "amount": total_amount,
            "currency": currency,
            "status": order_res["status"]
        }

    def confirm_and_store_authorization(
        self,
        contract_id: str,
        paypal_order_id: str,
        actor: User
    ) -> Dict[str, Any]:
        """
        Executes authorization against approved PayPal order, stores the live
        authorization ID against the contract in the database, and transitions state to FUNDED.
        """
        contract = self.repository.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract '{contract_id}' not found.")

        # 1. Permission Guard
        assert_can_fund_contract(actor, contract)

        # 2. Execute Authorization on PayPal Rails
        auth_res = self.paypal.execute_authorization(paypal_order_id)
        auth_id = auth_res["authorization_id"]

        # 3. Deterministic State Machine Transition (SIGNED -> FUNDED)
        updated_contract = self.repository.transition_contract(
            contract_id=contract_id,
            actor=actor,
            target_state=ContractState.FUNDED,
            metadata={
                "paypal_order_id": paypal_order_id,
                "paypal_auth_id": auth_id
            }
        )

        return updated_contract

    def get_contract_hold(
        self,
        contract_id: str,
        actor: Optional[User] = None,
        current_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculates and returns the escrow authorization expiry metrics (29-day limit)
        for a funded contract, matching shared REST API contract (GET /api/v1/contracts/{id}/hold).

        - Computes:
            expires_at = authorized_at + 29 days
            seconds_remaining = max(0, int((expires_at - now).total_seconds()))
            days_remaining = ceil(seconds_remaining / 86400) if seconds_remaining > 0 else 0
            is_expired = (seconds_remaining == 0)
        - Determines status:
            EXPIRED: seconds_remaining == 0
            EXPIRING_SOON: 0 < seconds_remaining <= 3 days (259200s, honor period / re-authorization warning)
            HELD: seconds_remaining > 3 days
        """
        contract = self.repository.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract '{contract_id}' not found.")

        # 1. Permission Guard (BUYER, SELLER, or ADMIN)
        if actor is not None:
            assert_can_view_contract_hold(actor, contract)

        # 2. State & Hold Existence Guard
        paypal_auth_id = contract.get("paypal_auth_id")
        status = contract.get("status")
        unfunded_states = {
            ContractState.DRAFT.value,
            ContractState.REVIEW.value,
            ContractState.SIGNED.value
        }

        if not paypal_auth_id or status in unfunded_states:
            raise StateValidationError(
                f"Contract '{contract_id}' does not have an active escrow hold (current status: '{status}')."
            )

        # 3. Resolve Timestamps
        # Determine authorization expiration target (29 days from authorization)
        raw_expires_at = contract.get("auth_expires_at")
        raw_funded_at = contract.get("funded_at") or contract.get("updated_at")

        if raw_expires_at:
            expires_at = datetime.fromisoformat(raw_expires_at.replace("Z", "+00:00"))
        elif raw_funded_at:
            funded_dt = datetime.fromisoformat(raw_funded_at.replace("Z", "+00:00"))
            expires_at = funded_dt + timedelta(days=29)
        else:
            raise StateValidationError(f"Contract '{contract_id}' is missing authorization timestamp metadata.")

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        # Current time resolution
        now = current_time or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # 4. Countdown Calculations
        delta_seconds = int((expires_at - now).total_seconds())
        seconds_remaining = max(0, delta_seconds)

        if seconds_remaining == 0:
            days_remaining = 0
            is_expired = True
            hold_status = "EXPIRED"
        else:
            days_remaining = math.ceil(seconds_remaining / 86400)
            is_expired = False
            # Within 3 days (259,200 seconds) flags re-authorization urgency
            if seconds_remaining <= 3 * 86400:
                hold_status = "EXPIRING_SOON"
            else:
                hold_status = "HELD"

        authorized_at_iso = raw_funded_at if raw_funded_at else (expires_at - timedelta(days=29)).isoformat()
        total_amount = float(contract.get("total_amount", 0.0))
        currency = contract.get("currency", "USD")

        return {
            "contract_id": contract_id,
            "authorization_id": paypal_auth_id,
            "amount": f"{total_amount:.2f}",
            "currency": currency,
            "status": hold_status,
            "authorized_at": authorized_at_iso,
            "expires_at": expires_at.isoformat(),
            "days_remaining": days_remaining,
            "seconds_remaining": seconds_remaining,
            "is_expired": is_expired
        }

    # Alias for flexibility
    get_hold_expiry = get_contract_hold

