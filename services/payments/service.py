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
import uuid
import hashlib
import importlib
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

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

def assert_can_view_split_preview(actor: User, contract: Dict[str, Any]) -> None:
    """Only participant BUYER, SELLER, platform ADMIN, or AI Referee can inspect split preview."""
    if actor.role == UserRole.ADMIN:
        return
    if getattr(actor, "id", None) == "AI_REFEREE" or getattr(actor, "name", None) == "AI Referee":
        return
    if actor.id != contract.get("buyer_id") and actor.id != contract.get("seller_id"):
        raise ForbiddenActionError(
            f"User '{actor.id}' with role '{actor.role.value}' is not authorized to view split preview for contract '{contract.get('id')}'. "
            f"Access restricted to contract buyer, seller, admin, or AI referee."
        )


class ProportionalSplitResult(dict):
    """
    Structured result of proportional split calculation (Commit C37).
    Inherits from dict for 100% dict compatibility (JSON serialization, dict unpacking),
    while also providing property/attribute access.
    """
    def __init__(
        self,
        contract_id: str,
        total_amount: float,
        passed_amount: float,
        refund_amount: float,
        passed_weight: float,
        failed_weight: float,
        currency: str,
        itemized_features: List[Dict[str, Any]],
        rounding_adjustment_cents: int,
        rule_applied: str,
        metadata: Optional[Dict[str, Any]] = None,
        **extra
    ):
        data = {
            "contract_id": contract_id,
            "total_amount": round(float(total_amount), 2),
            "passed_amount": round(float(passed_amount), 2),
            "refund_amount": round(float(refund_amount), 2),
            "passed_weight": round(float(passed_weight), 2),
            "failed_weight": round(float(failed_weight), 2),
            "currency": currency,
            "itemized_features": itemized_features,
            "rounding_adjustment_cents": int(rounding_adjustment_cents),
            "rule_applied": rule_applied,
            "metadata": metadata or {},
            **extra
        }
        super().__init__(data)

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'ProportionalSplitResult' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value

    def to_dict(self) -> Dict[str, Any]:
        return dict(self)


class WebhookVerificationError(Exception):
    """Raised when incoming PayPal webhook transmission signature verification fails."""
    pass


@dataclass
class ApprovalVerdict:
    approved: bool
    action: str
    contract_id: str
    reasons: List[str] = field(default_factory=list)
    checks_passed: List[str] = field(default_factory=list)
    checks_failed: List[str] = field(default_factory=list)
    actor_id: Optional[str] = None
    actor_role: Optional[str] = None
    approval_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "contract_id": self.contract_id,
            "action": self.action,
            "actor_id": self.actor_id,
            "actor_role": self.actor_role,
            "approved": self.approved,
            "reasons": self.reasons,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


class PaymentApprovalError(Exception):
    """Raised when an automated payment approval policy check fails."""
    def __init__(self, message: str, verdict: Optional[ApprovalVerdict] = None):
        super().__init__(message)
        self.message = message
        self.verdict = verdict


class PaymentApprovalService:
    """
    Automated Backend Approval Policy Engine for PactPal Payment Rails (Commit C31).
    Enforces that NO payment rail fires without satisfying:
      1. Checklist Lock Guard: Contract checklist must be dual-confirmed and locked (is_locked=True).
      2. Pre-Settlement Verification Guard: Verified deliverable report exists, zero unresolved
         high-severity cheat scan findings, and amounts match feature results (or ADMIN dispute override).
      3. State Machine Consistency: Action conforms to allowed 10-state lifecycle graph.
      4. Role & Identity Guard: Actor is authorized (Buyer for funding, Admin/Referee for settlement).
    Logs all verdicts immutably into the compliance messages ledger.
    """

    def __init__(self, repository: Optional[Any] = None):
        self.repository = repository or ContractRepository()

    def validate_payment_approval(
        self,
        contract_id: str,
        action: str,
        actor: User,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ApprovalVerdict:
        metadata = metadata or {}
        norm_action = str(action).upper().strip()
        checks_passed: List[str] = []
        checks_failed: List[str] = []
        reasons: List[str] = []

        contract = self.repository.get_contract(contract_id) if hasattr(self.repository, "get_contract") else None
        if not contract:
            checks_failed.append("CONTRACT_EXISTS")
            reasons.append(f"Contract '{contract_id}' does not exist.")
            verdict = ApprovalVerdict(
                approved=False,
                action=norm_action,
                contract_id=contract_id,
                actor_id=getattr(actor, "id", None),
                actor_role=getattr(actor.role, "value", str(actor.role)) if hasattr(actor, "role") else None,
                reasons=reasons,
                checks_passed=checks_passed,
                checks_failed=checks_failed,
                metadata=metadata
            )
            return verdict

        actor_role_val = getattr(actor.role, "value", str(actor.role)) if hasattr(actor, "role") else "UNKNOWN"
        actor_id_val = getattr(actor, "id", None)
        contract_status = contract.get("status")

        # 1. Role & Identity Guard
        is_buyer = (actor.role == UserRole.BUYER and actor_id_val == contract.get("buyer_id"))
        is_admin = (actor.role == UserRole.ADMIN)
        is_referee = (actor_id_val == "AI_REFEREE" or getattr(actor, "name", None) == "AI Referee")

        if norm_action in ("CREATE_HOLD", "INITIATE_HOLD", "AUTHORIZE_HOLD", "AUTHORIZE"):
            if not is_buyer:
                checks_failed.append("ROLE_AUTHORIZED")
                reasons.append(
                    f"User '{actor_id_val}' with role '{actor_role_val}' is not authorized to fund contract '{contract_id}'. "
                    f"Assigned buyer is '{contract.get('buyer_id')}'."
                )
            else:
                checks_passed.append("ROLE_AUTHORIZED")
        elif norm_action in ("SETTLE_ESCROW", "SETTLE", "CAPTURE", "PAYOUT", "VOID", "REFUND"):
            if not (is_admin or is_referee):
                checks_failed.append("ROLE_AUTHORIZED")
                reasons.append(
                    f"User '{actor_id_val}' with role '{actor_role_val}' is not authorized to settle contract '{contract_id}'. "
                    f"Only platform ADMIN or AI Referee can execute escrow settlement."
                )
            else:
                checks_passed.append("ROLE_AUTHORIZED")
        else:
            checks_failed.append("VALID_ACTION")
            reasons.append(f"Unrecognized payment action '{action}'.")

        # 2. State Machine Consistency Guard
        if norm_action in ("CREATE_HOLD", "INITIATE_HOLD"):
            if contract_status != ContractState.SIGNED.value:
                checks_failed.append("STATE_MACHINE_CONSISTENT")
                reasons.append(
                    f"Cannot initiate escrow hold on contract in '{contract_status}' state. Contract must be 'SIGNED'."
                )
            else:
                checks_passed.append("STATE_MACHINE_CONSISTENT")
        elif norm_action in ("AUTHORIZE_HOLD", "AUTHORIZE"):
            if contract_status not in (ContractState.SIGNED.value, ContractState.FUNDED.value):
                checks_failed.append("STATE_MACHINE_CONSISTENT")
                reasons.append(
                    f"Cannot execute authorization on contract in '{contract_status}' state. Contract must be 'SIGNED'."
                )
            else:
                checks_passed.append("STATE_MACHINE_CONSISTENT")
        elif norm_action in ("SETTLE_ESCROW", "SETTLE", "CAPTURE", "PAYOUT", "VOID", "REFUND"):
            unfunded_states = {
                ContractState.DRAFT.value,
                ContractState.REVIEW.value,
                ContractState.SIGNED.value
            }
            if contract_status == ContractState.SETTLED.value:
                checks_failed.append("STATE_MACHINE_CONSISTENT")
                reasons.append(f"Contract '{contract_id}' is already SETTLED.")
            elif contract_status in unfunded_states:
                checks_failed.append("STATE_MACHINE_CONSISTENT")
                reasons.append(f"Cannot settle contract in '{contract_status}' state. Contract has not been funded.")
            elif not contract.get("paypal_auth_id"):
                checks_failed.append("HOLD_EXISTS")
                reasons.append(f"Contract '{contract_id}' does not have an active PayPal authorization hold to settle.")
            else:
                checks_passed.append("STATE_MACHINE_CONSISTENT")

        # 3. Checklist Lock Guard (Commit C19 & Gate 1 Invariant)
        # Contract checklist must be dual-confirmed and locked (is_locked=True)
        is_locked = bool(contract.get("is_locked"))
        if not is_locked:
            checks_failed.append("CHECKLIST_LOCKED")
            reasons.append(
                f"Contract checklist for '{contract_id}' is not locked. "
                f"Dual-confirmation from buyer and seller is required before payment actions can proceed."
            )
        else:
            checks_passed.append("CHECKLIST_LOCKED")

        # 4. Pre-Settlement Verification & Invariant Guards (only for settlement actions)
        if norm_action in ("SETTLE_ESCROW", "SETTLE", "CAPTURE", "PAYOUT", "VOID", "REFUND"):
            # Check for explicit platform ADMIN dispute resolution override
            admin_override = bool(
                is_admin and (
                    metadata.get("admin_override") or
                    metadata.get("is_admin_override") or
                    metadata.get("dispute_override")
                )
            )

            # Amount Invariant Guard
            passed_amt = metadata.get("passed_amount")
            refund_amt = metadata.get("refund_amount")
            if passed_amt is not None and refund_amt is not None:
                try:
                    p = round(float(passed_amt), 2)
                    r = round(float(refund_amt), 2)
                    tot = round(float(contract.get("total_amount", 0.0)), 2)
                    if p < 0 or r < 0:
                        checks_failed.append("NON_NEGATIVE_AMOUNTS")
                        reasons.append("passed_amount and refund_amount must be non-negative.")
                    elif round(p + r, 2) != tot:
                        checks_failed.append("AMOUNT_INVARIANT")
                        reasons.append(
                            f"Amount invariant violation: passed_amount ({p:.2f}) + refund_amount ({r:.2f}) = "
                            f"{round(p + r, 2):.2f} does not equal contract total_amount ({tot:.2f})."
                        )
                    else:
                        checks_passed.append("AMOUNT_INVARIANT")
                except (ValueError, TypeError):
                    checks_failed.append("AMOUNT_INVARIANT")
                    reasons.append("passed_amount and refund_amount must be valid numerical amounts.")

            if admin_override:
                checks_passed.append("ADMIN_OVERRIDE")
                checks_passed.append("VERIFICATION_REPORT_EXISTS")
                checks_passed.append("CHEAT_SCAN_CLEARED")
            else:
                # Pre-Settlement Verification Report Check
                report = None
                if hasattr(self.repository, "get_latest_verification_report"):
                    report = self.repository.get_latest_verification_report(contract_id)

                if not report:
                    checks_failed.append("VERIFICATION_REPORT_EXISTS")
                    reasons.append(
                        f"Pre-settlement verification report missing for contract '{contract_id}'. "
                        f"Settlement requires completed verification report or platform ADMIN dispute resolution override."
                    )
                else:
                    checks_passed.append("VERIFICATION_REPORT_EXISTS")

                    # Check build status
                    if not report.get("build_succeeded", False) and passed_amt is not None and float(passed_amt) > 0:
                        checks_failed.append("BUILD_SUCCEEDED")
                        reasons.append(
                            f"Deliverable build failed: {report.get('failure_reason', 'Unbuildable source')}. "
                            f"Funds cannot be released to seller for unbuildable deliverable."
                        )
                    else:
                        checks_passed.append("BUILD_SUCCEEDED")

                    # Check cheat & loophole scan findings (no unresolved HIGH severity)
                    findings = report.get("cheat_scan_findings") or []
                    if isinstance(findings, str):
                        try:
                            findings = json.loads(findings)
                        except Exception:
                            findings = []
                    high_findings = [
                        f for f in findings
                        if isinstance(f, dict) and str(f.get("severity", "")).upper() == "HIGH"
                    ]
                    if high_findings:
                        f_names = ", ".join(f.get("title") or f.get("finding") or "High Severity Risk" for f in high_findings)
                        checks_failed.append("CHEAT_SCAN_CLEARED")
                        reasons.append(
                            f"Unresolved high-severity cheat/loophole scan findings detected: [{f_names}]. "
                            f"Settlement blocked until resolved or overridden by ADMIN."
                        )
                    else:
                        checks_passed.append("CHEAT_SCAN_CLEARED")

                    # Amount alignment with feature evaluation
                    if passed_amt is not None:
                        per_feat = report.get("per_feature_results") or {}
                        if isinstance(per_feat, str):
                            try:
                                per_feat = json.loads(per_feat)
                            except Exception:
                                per_feat = {}
                        if per_feat:
                            expected_passed = round(sum(
                                float(f_res.get("allocated_amount", 0.0))
                                for f_res in per_feat.values()
                                if isinstance(f_res, dict) and f_res.get("status") == "PASSED"
                            ), 2)
                            if expected_passed == 0.0 and any(f.get("status") == "PASSED" for f in per_feat.values() if isinstance(f, dict)):
                                passed_weights = sum(
                                    float(f_res.get("price_weight", 0.0))
                                    for f_res in per_feat.values()
                                    if isinstance(f_res, dict) and f_res.get("status") == "PASSED"
                                )
                                expected_passed = round(float(contract.get("total_amount", 0.0)) * (passed_weights / 100.0), 2)

                            if expected_passed > 0.0 and abs(round(float(passed_amt), 2) - expected_passed) > 0.01:
                                checks_failed.append("AMOUNT_ALIGNMENT")
                                reasons.append(
                                    f"Settlement passed_amount (${float(passed_amt):.2f}) does not match verified feature results "
                                    f"(expected ${expected_passed:.2f} based on verified passed features)."
                                )
                            else:
                                checks_passed.append("AMOUNT_ALIGNMENT")

        approved = (len(checks_failed) == 0)
        if approved:
            reasons.append("All policy criteria met.")

        verdict = ApprovalVerdict(
            approved=approved,
            action=norm_action,
            contract_id=contract_id,
            actor_id=actor_id_val,
            actor_role=actor_role_val,
            reasons=reasons,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            metadata=metadata
        )

        # Log audit entry into immutable messages table
        self._log_approval_audit(contract_id, actor, norm_action, verdict)

        return verdict

    def _log_approval_audit(self, contract_id: str, actor: User, action: str, verdict: ApprovalVerdict) -> None:
        """Writes an immutable policy audit record into the messages table."""
        if hasattr(self.repository, "conn") and self.repository.conn:
            try:
                cursor = self.repository.conn.cursor()
                sender_type = "AI_REFEREE" if (getattr(actor, "id", None) == "AI_REFEREE" or getattr(actor, "name", None) == "AI Referee") else getattr(actor.role, "value", "ADMIN")
                sender_id = getattr(actor, "id", None)
                content = (
                    f"Payment approval check for '{action}' on contract '{contract_id}': "
                    f"{'APPROVED' if verdict.approved else 'REJECTED'}. "
                    f"Reasons: {'; '.join(verdict.reasons)}"
                )
                cursor.execute("""
                    INSERT INTO messages (id, contract_id, sender_id, sender_type, content, metadata, sent_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()),
                    contract_id,
                    sender_id if self.repository.get_user(sender_id) else None,
                    sender_type,
                    content,
                    json.dumps(verdict.to_dict()),
                    verdict.timestamp
                ))
                self.repository.conn.commit()
            except Exception:
                pass


class EscrowPaymentService:
    """
    Manages milestone escrow lifecycle for contracts:
    order creation, buyer authorization approval, and persistence.
    """

    def __init__(
        self,
        repository: Optional[Any] = None,
        paypal_client: Optional[PayPalClient] = None,
        approval_service: Optional[PaymentApprovalService] = None
    ):
        self.repository = repository or ContractRepository()
        self.paypal = paypal_client or PayPalClient()
        self.approval_service = approval_service or PaymentApprovalService(repository=self.repository)
        self.validate_payment_approval = self.approval_service.validate_payment_approval

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

        # 3. Automated Backend Approval Policy Check (Commit C31)
        verdict = self.approval_service.validate_payment_approval(
            contract_id=contract_id,
            action="CREATE_HOLD",
            actor=actor,
            metadata={"idempotency_key": idempotency_key}
        )
        if not verdict.approved:
            raise PaymentApprovalError(
                f"Payment action 'CREATE_HOLD' blocked by approval policy: {'; '.join(verdict.reasons)}",
                verdict=verdict
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

        # 2. Automated Backend Approval Policy Check (Commit C31)
        verdict = self.approval_service.validate_payment_approval(
            contract_id=contract_id,
            action="AUTHORIZE_HOLD",
            actor=actor,
            metadata={"paypal_order_id": paypal_order_id, "idempotency_key": idempotency_key}
        )
        if not verdict.approved:
            raise PaymentApprovalError(
                f"Payment action 'AUTHORIZE_HOLD' blocked by approval policy: {'; '.join(verdict.reasons)}",
                verdict=verdict
            )

        # 3. Execute Authorization on PayPal Rails
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

    def _resolve_feature_status(
        self,
        feature: Dict[str, Any],
        feature_results: Optional[Any],
        verification_report: Optional[Dict[str, Any]]
    ) -> str:
        """
        Resolves whether a feature is PASSED or FAILED using:
          1. Explicit feature_results parameter (if provided).
          2. Latest verification report per_feature_results (if report exists).
          3. Underlying feature record status in repository.
        Any status other than PASSED (e.g. FAILED, PENDING, DISPUTED) is treated as unpassed (FAILED).
        """
        feat_id = str(feature.get("id", ""))
        feat_title = str(feature.get("title", ""))

        # 1. Check explicit feature_results
        if feature_results is not None:
            if isinstance(feature_results, dict):
                # Handle wrapped "per_feature_results"
                if "per_feature_results" in feature_results and isinstance(feature_results["per_feature_results"], dict):
                    feature_results = feature_results["per_feature_results"]

                # Handle passed/failed lists
                if "passed" in feature_results and isinstance(feature_results["passed"], (list, set, tuple)):
                    passed_ids = {str(x) for x in feature_results["passed"]}
                    if feat_id in passed_ids or (feat_title and feat_title in passed_ids):
                        return "PASSED"
                    return "FAILED"

                target = feature_results.get(feat_id)
                if target is None and feat_title:
                    target = feature_results.get(feat_title)

                if target is not None:
                    if isinstance(target, dict):
                        st = target.get("status")
                        return "PASSED" if str(st).upper() == "PASSED" else "FAILED"
                    elif isinstance(target, bool):
                        return "PASSED" if target else "FAILED"
                    return "PASSED" if str(target).upper() == "PASSED" else "FAILED"

            elif isinstance(feature_results, (list, tuple, set)):
                for item in feature_results:
                    if isinstance(item, dict):
                        item_id = str(item.get("id") or item.get("feature_id") or "")
                        item_title = str(item.get("title") or item.get("feature_title") or "")
                        if (item_id and item_id == feat_id) or (item_title and item_title == feat_title):
                            st = item.get("status")
                            return "PASSED" if str(st).upper() == "PASSED" else "FAILED"
                    elif isinstance(item, str):
                        if item == feat_id or (feat_title and item == feat_title):
                            return "PASSED"
                return "FAILED"

        # 2. Check verification report if present
        if verification_report:
            per_feat = verification_report.get("per_feature_results") or {}
            if isinstance(per_feat, str):
                try:
                    per_feat = json.loads(per_feat)
                except Exception:
                    per_feat = {}
            if isinstance(per_feat, dict):
                rep_feat = per_feat.get(feat_id)
                if rep_feat is None and feat_title:
                    rep_feat = per_feat.get(feat_title)
                if rep_feat is not None:
                    if isinstance(rep_feat, dict):
                        st = rep_feat.get("status")
                        return "PASSED" if str(st).upper() == "PASSED" else "FAILED"
                    return "PASSED" if str(rep_feat).upper() == "PASSED" else "FAILED"

        # 3. Fallback to feature database status
        curr_st = feature.get("status")
        return "PASSED" if str(curr_st).upper() == "PASSED" else "FAILED"

    def calculate_proportional_split(
        self,
        contract_id: str,
        feature_results: Optional[Any] = None,
        actor: Optional[User] = None
    ) -> ProportionalSplitResult:
        """
        Calculates proportional escrow split math matching Phase 7 & Commit C37:
          - Sums weights of features marked PASSED vs FAILED.
          - Calculates itemized feature allocations based on price_weights.
          - Deterministic Remainder Rule: Dynamically allocates the rounding delta (+- 0.01)
            to the last feature (by sort_order / last index) so that sum(allocated_amount) == total_amount
            exactly to the cent.
          - Guarantees mathematical invariant: round(passed_amount + refund_amount, 2) == round(total_amount, 2)
            with zero lost cents under any combination of weights and prices.
        """
        contract = self.repository.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract '{contract_id}' not found.")

        # Permission check if actor is provided
        if actor is not None:
            assert_can_view_split_preview(actor, contract)

        total_amount = round(float(contract.get("total_amount", 0.0)), 2)
        currency = contract.get("currency", "USD")

        features = None
        if hasattr(self.repository, "get_features"):
            features = self.repository.get_features(contract_id)
        if not features and "features" in contract:
            features = contract["features"]
        features = features or []

        # Sort features deterministically by sort_order ASC, then by feature ID
        sorted_features = sorted(
            features,
            key=lambda f: (int(f.get("sort_order", 0) if f.get("sort_order") is not None else 0), str(f.get("id", "")))
        )
        N = len(sorted_features)

        if N == 0:
            return ProportionalSplitResult(
                contract_id=contract_id,
                total_amount=total_amount,
                passed_amount=0.0,
                refund_amount=total_amount,
                passed_weight=0.0,
                failed_weight=0.0,
                currency=currency,
                itemized_features=[],
                rounding_adjustment_cents=0,
                rule_applied="NO_FEATURES_FULL_REFUND",
                metadata={"contract_title": contract.get("title")}
            )

        # Resolve verification report if available and feature_results is None
        verification_report = None
        if feature_results is None and hasattr(self.repository, "get_latest_verification_report"):
            verification_report = self.repository.get_latest_verification_report(contract_id)

        # 1. Weights extraction
        raw_weights = [float(f.get("price_weight", 0.0) or 0.0) for f in sorted_features]
        sum_weights = sum(raw_weights)

        # 2. Compute unadjusted allocation for each feature
        unadjusted_amounts: List[float] = []
        for i, w in enumerate(raw_weights):
            if sum_weights > 0:
                # If weights sum close to 100% (e.g. 99.99% from 33.33 x 3) and not exactly 100.0,
                # normalize against sum_weights so recurring decimals (e.g. 1/3) divide cleanly.
                if abs(sum_weights - 100.0) < 0.05 and sum_weights != 100.0:
                    fraction = w / sum_weights
                elif sum_weights == 100.0:
                    fraction = w / 100.0
                else:
                    fraction = w / sum_weights
            else:
                fraction = 1.0 / N
            unadjusted_amounts.append(round(total_amount * fraction, 2))

        sum_unadjusted = round(sum(unadjusted_amounts), 2)
        delta = round(total_amount - sum_unadjusted, 2)
        rounding_adjustment_cents = int(round(delta * 100))

        # 3. Deterministic Remainder Rule: allocate rounding delta (+- 0.01) to the last feature
        allocated_amounts = list(unadjusted_amounts)
        allocated_amounts[-1] = round(allocated_amounts[-1] + delta, 2)

        # 4. Resolve feature statuses and build itemized features
        itemized_features: List[Dict[str, Any]] = []
        for i, feat in enumerate(sorted_features):
            st = self._resolve_feature_status(feat, feature_results, verification_report)
            is_last = (i == N - 1)
            adj = delta if is_last else 0.0
            feat_id = feat.get("id") or f"feat_{i+1}"
            feat_title = feat.get("title") or f"Feature {i+1}"

            itemized_features.append({
                "id": feat_id,
                "feature_id": feat_id,
                "title": feat_title,
                "feature_title": feat_title,
                "price_weight": round(raw_weights[i], 4),
                "unadjusted_amount": unadjusted_amounts[i],
                "allocated_amount": allocated_amounts[i],
                "status": st,
                "sort_order": feat.get("sort_order", i),
                "is_last_feature": is_last,
                "adjustment_applied": round(adj, 2)
            })

        # 5. Calculate totals
        passed_features = [f for f in itemized_features if f["status"] == "PASSED"]
        failed_features = [f for f in itemized_features if f["status"] == "FAILED"]

        passed_weight = round(sum(f["price_weight"] for f in passed_features), 2)
        failed_weight = round(sum(f["price_weight"] for f in failed_features), 2)

        if len(passed_features) == N:
            passed_amount = total_amount
            refund_amount = 0.0
            rule_applied = "FULL_RELEASE_100_PERCENT"
        elif len(passed_features) == 0:
            passed_amount = 0.0
            refund_amount = total_amount
            rule_applied = "FULL_REFUND_0_PERCENT"
        else:
            passed_amount = round(sum(f["allocated_amount"] for f in passed_features), 2)
            refund_amount = round(total_amount - passed_amount, 2)
            rule_applied = "PROPORTIONAL_PARTIAL_SPLIT"

        # Verify mathematical invariant
        assert round(passed_amount + refund_amount, 2) == round(total_amount, 2), (
            f"Invariant violation: passed ({passed_amount}) + refund ({refund_amount}) != total ({total_amount})"
        )

        return ProportionalSplitResult(
            contract_id=contract_id,
            total_amount=total_amount,
            passed_amount=passed_amount,
            refund_amount=refund_amount,
            passed_weight=passed_weight,
            failed_weight=failed_weight,
            currency=currency,
            itemized_features=itemized_features,
            rounding_adjustment_cents=rounding_adjustment_cents,
            rule_applied=rule_applied,
            metadata={
                "contract_title": contract.get("title"),
                "features_total": N,
                "features_passed": len(passed_features),
                "features_failed": len(failed_features),
                "rounding_adjustment_amount": round(delta, 2)
            }
        )

    def settle_contract_escrow(
        self,
        contract_id: str,
        passed_amount: Optional[float] = None,
        refund_amount: Optional[float] = None,
        seller_paypal_email: Optional[str] = None,
        actor: Optional[User] = None,
        idempotency_key: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
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

        # 3. Amount Invariant Guard & Split Math Integration
        split_calc = None
        try:
            split_calc = self.calculate_proportional_split(
                contract_id=contract_id,
                feature_results=metadata.get("feature_results") if metadata else None
            )
        except Exception:
            split_calc = None

        if passed_amount is None and split_calc:
            passed_amount = split_calc.passed_amount
        if refund_amount is None and split_calc:
            refund_amount = split_calc.refund_amount

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

        # 4. Automated Backend Approval Policy Check (Commit C31)
        settle_meta = {
            "passed_amount": passed,
            "refund_amount": refund,
            "seller_paypal_email": target_email,
            "idempotency_key": idempotency_key,
            "split_breakdown": split_calc.to_dict() if split_calc else None,
            **(metadata or {})
        }
        verdict = self.approval_service.validate_payment_approval(
            contract_id=contract_id,
            action="SETTLE_ESCROW",
            actor=actor,
            metadata=settle_meta
        )
        if not verdict.approved:
            raise PaymentApprovalError(
                f"Payment action 'SETTLE_ESCROW' blocked by approval policy: {'; '.join(verdict.reasons)}",
                verdict=verdict
            )

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
            "receipt_hash": receipt_hash,
            "split_breakdown": split_calc.to_dict() if split_calc else None
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


