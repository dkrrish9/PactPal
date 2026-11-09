"""
PactPal Escrow Payment Service
Bridges PayPal REST Rails with Core Relational Persistence & State Machine.
Fulfills Done criteria for C10:
  - Creates order with AUTHORIZE intent
  - Directs buyer to approve in PayPal sandbox
  - Captures authorization_id and stores against the contract record
  - Strictly transitions contract from SIGNED -> FUNDED
"""

import os
import math
import json
import hashlib
import importlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from .client import PayPalClient, PayPalAPIError

# Escrow & Hold Limits (matching PayPal Orders & Authorizations specifications)
PAYPAL_HOLD_DURATION_DAYS = 29
PAYPAL_HONOR_PERIOD_SECONDS = 3 * 86400  # 3 days (259,200s) honor period window

# Dynamic imports to handle hyphenated directory name 'core-api'
_repo_mod = importlib.import_module("services.core-api.db.repository")
ContractRepository = _repo_mod.ContractRepository

_roles_mod = importlib.import_module("services.core-api.auth.roles")
User = _roles_mod.User
UserRole = _roles_mod.UserRole
ForbiddenActionError = _roles_mod.ForbiddenActionError
UnauthorizedRoleError = getattr(_roles_mod, "UnauthorizedRoleError", ForbiddenActionError)
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

def assert_can_settle_contract(actor: User, contract: Dict[str, Any]) -> None:
    """Only platform ADMIN or AI Referee can settle contract escrow."""
    is_admin = (actor.role == UserRole.ADMIN)
    is_referee = (getattr(actor, "id", None) == "AI_REFEREE" or getattr(actor, "name", None) == "AI Referee")
    if not (is_admin or is_referee):
        raise ForbiddenActionError(
            f"User '{actor.id}' with role '{actor.role.value}' is not authorized to settle contract '{contract.get('id')}'. "
            f"Only platform ADMIN or AI Referee can execute escrow settlement."
        )


class WebhookVerificationError(Exception):
    """Raised when incoming PayPal webhook transmission signature verification fails."""
    pass


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
        cancel_url: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates a PayPal Order with AUTHORIZE intent for a SIGNED contract.
        Returns the order ID and approval URL for buyer redirection.
        Includes idempotency key check to prevent duplicate order generation.
        """
        scope = f"create_hold:{contract_id}"
        if idempotency_key and hasattr(self.repository, "get_idempotency_key"):
            cached = self.repository.get_idempotency_key(idempotency_key, scope=scope)
            if cached:
                return cached["response_data"]

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
        frontend_base = os.environ.get("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")
        default_return = f"{frontend_base}/contracts/{contract_id}/funded"
        default_cancel = f"{frontend_base}/contracts/{contract_id}"

        order_kwargs = {
            "reference_id": contract_id,
            "amount": total_amount,
            "currency": currency,
            "description": f"PactPal Escrow: {contract['title']}",
            "return_url": return_url or default_return,
            "cancel_url": cancel_url or default_cancel
        }
        if idempotency_key:
            order_kwargs["idempotency_key"] = idempotency_key

        order_res = self.paypal.create_authorize_order(**order_kwargs)

        res = {
            "contract_id": contract_id,
            "paypal_order_id": order_res["order_id"],
            "approve_url": order_res["approve_url"],
            "intent": "AUTHORIZE",
            "amount": total_amount,
            "currency": currency,
            "status": order_res["status"]
        }

        if idempotency_key and hasattr(self.repository, "save_idempotency_key"):
            self.repository.save_idempotency_key(idempotency_key, scope=scope, response_data=res)

        return res

    def confirm_and_store_authorization(
        self,
        contract_id: str,
        paypal_order_id: str,
        actor: User,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes authorization against approved PayPal order, stores the live
        authorization ID against the contract in the database, and transitions state to FUNDED.
        Includes idempotency checks to prevent duplicate authorizations.
        """
        scope = f"authorize:{contract_id}"
        if idempotency_key and hasattr(self.repository, "get_idempotency_key"):
            cached = self.repository.get_idempotency_key(idempotency_key, scope=scope)
            if cached:
                return cached["response_data"]

        contract = self.repository.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract '{contract_id}' not found.")

        # Idempotent replay: if contract is already FUNDED with this order ID, return existing
        if contract.get("status") == ContractState.FUNDED.value and contract.get("paypal_order_id") == paypal_order_id:
            return contract

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

        if idempotency_key and hasattr(self.repository, "save_idempotency_key"):
            self.repository.save_idempotency_key(idempotency_key, scope=scope, response_data=updated_contract)

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

        total_amount = float(contract.get("total_amount", 0.0))
        currency = contract.get("currency", "USD")
        raw_expires_at = contract.get("auth_expires_at")
        raw_funded_at = contract.get("funded_at") or contract.get("updated_at")

        # If contract has completed and settled, hold is concluded
        if status == ContractState.SETTLED.value:
            return {
                "contract_id": contract_id,
                "authorization_id": paypal_auth_id,
                "amount": f"{total_amount:.2f}",
                "currency": currency,
                "status": "SETTLED",
                "authorized_at": raw_funded_at or contract.get("updated_at"),
                "expires_at": raw_expires_at or contract.get("updated_at"),
                "days_remaining": 0,
                "seconds_remaining": 0,
                "is_expired": True
            }

        # 3. Resolve Timestamps
        # Determine authorization expiration target (29 days from authorization)
        if raw_expires_at:
            expires_at = datetime.fromisoformat(raw_expires_at.replace("Z", "+00:00"))
        elif raw_funded_at:
            funded_dt = datetime.fromisoformat(raw_funded_at.replace("Z", "+00:00"))
            expires_at = funded_dt + timedelta(days=PAYPAL_HOLD_DURATION_DAYS)
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
            if seconds_remaining <= PAYPAL_HONOR_PERIOD_SECONDS:
                hold_status = "EXPIRING_SOON"
            else:
                hold_status = "HELD"

        authorized_at_iso = raw_funded_at if raw_funded_at else (expires_at - timedelta(days=PAYPAL_HOLD_DURATION_DAYS)).isoformat()
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

    def settle_contract_escrow(
        self,
        contract_id: str,
        passed_amount: float,
        refund_amount: float,
        seller_paypal_email: str,
        actor: User,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Settles contract escrow matching Phase 7 (Partial Payouts) and SHARED_API_CONTRACT.md Section 3.4.
        
        1. Checks idempotency cache to prevent duplicate captures/payouts.
        2. Validates permissions: Only platform ADMIN or AI Referee can settle.
        3. Validates contract existence and active escrow state.
        4. Enforces amount invariant: round(passed_amount + refund_amount, 2) == round(total_amount, 2).
        5. If passed_amount > 0:
           - Executes capture_authorization (with is_final_capture=True if refund_amount == 0 else False).
           - Executes create_payout to seller_paypal_email.
        6. If refund_amount > 0:
           - Executes void_authorization to release uncaptured hold amount back to buyer.
        7. Inserts payment ledger records (CAPTURE, PAYOUT, VOID) into relational payments table.
        8. Transitions contract to SETTLED state in repository.
        9. Generates cryptographic SHA-256 receipt hash, caches response under idempotency_key, and returns settlement summary.
        """
        scope = f"settle:{contract_id}"
        if idempotency_key and hasattr(self.repository, "get_idempotency_key"):
            cached = self.repository.get_idempotency_key(idempotency_key, scope=scope)
            if cached:
                return cached["response_data"]

        contract = self.repository.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract '{contract_id}' not found.")

        # 1. Permission Guard
        assert_can_settle_contract(actor, contract)

        # 2. State Guard
        current_status = contract.get("status")
        if current_status == ContractState.SETTLED.value:
            raise StateValidationError(f"Contract '{contract_id}' is already SETTLED.")

        unfunded_states = {
            ContractState.DRAFT.value,
            ContractState.REVIEW.value,
            ContractState.SIGNED.value
        }
        if current_status in unfunded_states:
            raise StateValidationError(
                f"Cannot settle contract in '{current_status}' state. Contract has not been funded."
            )

        auth_id = contract.get("paypal_auth_id")
        if not auth_id:
            raise StateValidationError(
                f"Contract '{contract_id}' does not have an active PayPal authorization hold to settle."
            )

        # 3. Amount Invariant Guard
        try:
            passed = round(float(passed_amount), 2)
            refund = round(float(refund_amount), 2)
        except (ValueError, TypeError):
            raise ValueError("passed_amount and refund_amount must be valid numerical values.")

        if passed < 0 or refund < 0:
            raise ValueError("passed_amount and refund_amount must be non-negative.")

        total_amount = round(float(contract.get("total_amount", 0.0)), 2)
        if round(passed + refund, 2) != total_amount:
            raise ValueError(
                f"Amount invariant violation: passed_amount ({passed:.2f}) + refund_amount ({refund:.2f}) = "
                f"{round(passed + refund, 2):.2f} does not equal contract total_amount ({total_amount:.2f})."
            )

        # Validate seller PayPal email if payout is positive
        target_email = seller_paypal_email or ""
        if not target_email and hasattr(self.repository, "get_user"):
            seller_user = self.repository.get_user(contract.get("seller_id"))
            if seller_user and getattr(seller_user, "paypal_email", None):
                target_email = seller_user.paypal_email

        if passed > 0 and not target_email:
            raise ValueError("seller_paypal_email is required when passed_amount > 0.")

        currency = contract.get("currency", "USD")
        capture_id: Optional[str] = None
        payout_batch_id: Optional[str] = None
        void_id: Optional[str] = None

        # 4. Partial / Full Capture
        if passed > 0:
            is_final = (refund == 0.0)
            capture_kwargs = {
                "authorization_id": auth_id,
                "amount": passed,
                "currency": currency,
                "is_final_capture": is_final
            }
            if idempotency_key:
                capture_kwargs["idempotency_key"] = f"{idempotency_key}:capture"
            capture_res = self.paypal.capture_authorization(**capture_kwargs)
            capture_id = capture_res.get("capture_id")
            if hasattr(self.repository, "record_payment"):
                self.repository.record_payment(
                    contract_id=contract_id,
                    payment_type="CAPTURE",
                    paypal_reference_id=str(capture_id),
                    amount=passed,
                    currency=currency,
                    status="COMPLETED",
                    metadata=capture_res
                )

            # Disburse Payout to Seller
            payout_kwargs = {
                "receiver_email": target_email,
                "amount": passed,
                "currency": currency,
                "note": f"PactPal Milestone Release for '{contract.get('title')}'"
            }
            if idempotency_key:
                payout_kwargs["idempotency_key"] = f"{idempotency_key}:payout"
            payout_res = self.paypal.create_payout(**payout_kwargs)
            payout_batch_id = payout_res.get("payout_batch_id")
            if hasattr(self.repository, "record_payment"):
                self.repository.record_payment(
                    contract_id=contract_id,
                    payment_type="PAYOUT",
                    paypal_reference_id=str(payout_batch_id),
                    amount=passed,
                    currency=currency,
                    status="COMPLETED",
                    metadata=payout_res
                )

        # 5. Void / Refund remainder
        if refund > 0:
            void_kwargs = {"authorization_id": auth_id}
            if idempotency_key:
                void_kwargs["idempotency_key"] = f"{idempotency_key}:void"
            void_res = self.paypal.void_authorization(**void_kwargs)
            void_id = void_res.get("authorization_id") or auth_id
            if hasattr(self.repository, "record_payment"):
                self.repository.record_payment(
                    contract_id=contract_id,
                    payment_type="VOID",
                    paypal_reference_id=str(void_id),
                    amount=refund,
                    currency=currency,
                    status="COMPLETED",
                    metadata=void_res
                )

        # 6. State Machine Transition to SETTLED
        settle_meta = {
            "capture_id": capture_id,
            "payout_batch_id": payout_batch_id,
            "void_id": void_id,
            "passed_amount": passed,
            "refund_amount": refund,
            "seller_paypal_email": target_email,
            "settled_at": datetime.now(timezone.utc).isoformat()
        }
        self.repository.transition_contract(
            contract_id=contract_id,
            actor=actor,
            target_state=ContractState.SETTLED,
            metadata=settle_meta
        )

        # 7. Cryptographic SHA-256 Receipt Fingerprint
        receipt_payload = {
            "contract_id": str(contract_id),
            "passed_amount": f"{passed:.2f}",
            "refund_amount": f"{refund:.2f}",
            "currency": currency,
            "seller_paypal_email": str(target_email),
            "capture_id": str(capture_id or ""),
            "payout_batch_id": str(payout_batch_id or ""),
            "refund_id": str(void_id or "")
        }
        receipt_hash = hashlib.sha256(json.dumps(receipt_payload, sort_keys=True).encode()).hexdigest()

        response = {
            "contract_id": contract_id,
            "status": "SETTLED",
            "capture_id": capture_id,
            "payout_batch_id": payout_batch_id,
            "refund_id": void_id,
            "passed_amount": passed,
            "refund_amount": refund,
            "currency": currency,
            "receipt_hash": receipt_hash
        }

        if idempotency_key and hasattr(self.repository, "save_idempotency_key"):
            self.repository.save_idempotency_key(idempotency_key, scope=scope, response_data=response)

        return response

    def process_paypal_webhook(
        self,
        headers: Dict[str, str],
        raw_body: bytes,
        webhook_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validates cryptographic transmission signature headers of an incoming PayPal webhook
        and dispatches verified event processing.
        """
        norm_headers = {k.lower(): v for k, v in headers.items()}
        auth_algo = norm_headers.get("paypal-auth-algo")
        cert_url = norm_headers.get("paypal-cert-url")
        transmission_id = norm_headers.get("paypal-transmission-id")
        transmission_sig = norm_headers.get("paypal-transmission-sig")
        transmission_time = norm_headers.get("paypal-transmission-time")

        if not all([auth_algo, cert_url, transmission_id, transmission_sig, transmission_time]):
            raise WebhookVerificationError(
                "Missing required PayPal transmission signature headers "
                "(paypal-auth-algo, paypal-cert-url, paypal-transmission-id, paypal-transmission-sig, paypal-transmission-time)."
            )

        try:
            event_payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except Exception as e:
            raise ValueError(f"Malformed webhook JSON body: {str(e)}")

        is_valid = self.paypal.verify_webhook_signature(
            auth_algo=auth_algo,
            cert_url=cert_url,
            transmission_id=transmission_id,
            transmission_sig=transmission_sig,
            transmission_time=transmission_time,
            webhook_event=event_payload,
            webhook_id=webhook_id
        )

        if not is_valid:
            raise WebhookVerificationError("PayPal webhook signature verification failed.")

        event_id = event_payload.get("id")
        event_type = event_payload.get("event_type", "UNKNOWN")
        resource = event_payload.get("resource", {})

        action_taken = self._handle_webhook_resource(event_type, resource, event_payload)

        return {
            "status": "SUCCESS",
            "verified": True,
            "event_id": event_id,
            "event_type": event_type,
            "action_taken": action_taken
        }

    def _handle_webhook_resource(
        self,
        event_type: str,
        resource: Dict[str, Any],
        event_payload: Dict[str, Any]
    ) -> str:
        """
        Dispatches verified PayPal webhook event types to internal audit messages and state updates.
        """
        ref_id = resource.get("reference_id") or resource.get("custom_id") or resource.get("invoice_id")
        
        # Check purchase_units reference if present
        if not ref_id and "purchase_units" in resource:
            units = resource.get("purchase_units", [])
            if units:
                ref_id = units[0].get("reference_id")

        if ref_id and hasattr(self.repository, "get_contract"):
            contract = self.repository.get_contract(ref_id)
            if contract and hasattr(self.repository, "conn"):
                try:
                    cursor = self.repository.conn.cursor()
                    cursor.execute("""
                        INSERT INTO messages (id, contract_id, sender_id, sender_type, content, metadata, sent_at)
                        VALUES (?, ?, NULL, 'AI_REFEREE', ?, ?, ?)
                    """, (
                        importlib.import_module("services.core-api.db.repository").generate_uuid(),
                        ref_id,
                        f"PayPal Webhook verified: {event_type} for contract {ref_id}",
                        json.dumps({"event_type": event_type, "event_id": event_payload.get("id")}),
                        importlib.import_module("services.core-api.db.repository").now_iso()
                    ))
                    self.repository.conn.commit()
                except Exception:
                    pass

        return f"PROCESSED_{event_type}"


