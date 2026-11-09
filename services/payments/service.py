"""
PactPal Escrow Payment Service
Bridges PayPal REST Rails with Core Relational Persistence & State Machine.
Fulfills Done criteria for C10:
  - Creates order with AUTHORIZE intent
  - Directs buyer to approve in PayPal sandbox
  - Captures authorization_id and stores against the contract record
  - Strictly transitions contract from SIGNED -> FUNDED
"""

import importlib
from typing import Dict, Any, Optional

from .client import PayPalClient, PayPalAPIError

# Dynamic imports to handle hyphenated directory name 'core-api'
_repo_mod = importlib.import_module("services.core-api.db.repository")
ContractRepository = _repo_mod.ContractRepository

_roles_mod = importlib.import_module("services.core-api.auth.roles")
User = _roles_mod.User
UserRole = _roles_mod.UserRole
assert_can_fund_contract = _roles_mod.assert_can_fund_contract

_sm_mod = importlib.import_module("services.core-api.state_machine.engine")
ContractState = _sm_mod.ContractState
StateValidationError = _sm_mod.StateValidationError

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
