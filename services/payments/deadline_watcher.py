"""
PactPal Scheduled Deadline Watcher Service
Milestone 3: Commit C49 (feat(deadline): scheduled deadline watcher triggers final verification and partial payout)

Monitors active contracts (status IN ('IN_PROGRESS', 'SUBMITTED', 'VERIFYING')).
When a contract's deadline timestamp expires:
  1. Detects expiry automatically.
  2. Evaluates deliverable submissions:
     - If submissions exist: fetches latest verification report and evaluates proportional split math (C37).
     - If zero submissions exist: treats as abandonment / 100% full refund to buyer.
  3. Executes automated escrow settlement and PayPal partial/full captures, void refunds, and seller payouts (C24).
  4. Generates cryptographic proof-of-work receipts and dual summaries (C41, C44).
  5. Immutably records audit events (event='DEADLINE_EXPIRED_SETTLEMENT_TRIGGERED') in relational messages table.
  6. Supports background daemon loop, on-demand scheduled sweeps, and admin simulation triggers.
"""

import os
import json
import time
import uuid
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union

from .service import (
    EscrowPaymentService,
    PaymentApprovalService,
    PaymentApprovalError,
    ContractRepository,
    User,
    UserRole,
    ContractState,
    ForbiddenActionError,
    UnauthorizedRoleError,
    StateValidationError,
    ProportionalSplitResult,
    assert_can_settle_contract
)

try:
    from services.core_api.auth.roles import assert_can_trigger_deadline_watcher
except ImportError:
    try:
        from ..auth.roles import assert_can_trigger_deadline_watcher
    except ImportError:
        def assert_can_trigger_deadline_watcher(actor: User) -> None:
            if getattr(actor, "role", None) == UserRole.ADMIN or getattr(actor, "id", None) in ("AI_REFEREE", "ADMIN"):
                return
            raise ForbiddenActionError("Only platform ADMIN or AI Referee can execute deadline actions.")


def parse_datetime(dt_val: Union[str, datetime, None]) -> datetime:
    """Parses an ISO string or datetime object into a timezone-aware UTC datetime."""
    if dt_val is None:
        return datetime.now(timezone.utc)
    if isinstance(dt_val, datetime):
        if dt_val.tzinfo is None:
            return dt_val.replace(tzinfo=timezone.utc)
        return dt_val.astimezone(timezone.utc)
    if isinstance(dt_val, str):
        cleaned = dt_val.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    raise ValueError(f"Cannot parse datetime value: {dt_val!r}")


class SweepResult(list):
    """
    Dual list-and-dict result object for deadline sweeps.
    Inherits from list for backwards compatibility with List[Dict[str, Any]],
    while also exposing summary metrics and dict-like access.
    """
    def __init__(self, items: Optional[List[Dict[str, Any]]] = None, summary: Optional[Dict[str, Any]] = None):
        super().__init__(items or [])
        self.summary = summary or {}
        self._data: Dict[str, Any] = {
            "contracts_inspected": self.summary.get("contracts_inspected", len(self)),
            "contracts_expired": self.summary.get("contracts_expired", len(self)),
            "contracts_settled": self.summary.get("contracts_settled", len(self)),
            "results": list(items or []),
            "processed_contracts": list(items or []),
            **(summary or {})
        }

    def __getitem__(self, item: Any) -> Any:
        if isinstance(item, (int, slice)):
            return super().__getitem__(item)
        return self._data[item]

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)


class DeadlineWatcherService:
    """
    Autonomous Scheduled Deadline Watcher Engine (Commit C49).
    Monitors active contracts, detects expired deadlines, and executes
    verification pipeline evaluation and proportional escrow settlement.
    """

    DEFAULT_ACTIVE_STATUSES = ["IN_PROGRESS", "SUBMITTED", "VERIFYING"]

    def __init__(
        self,
        repository: Optional[ContractRepository] = None,
        payment_service: Optional[EscrowPaymentService] = None,
        decision_engine: Optional[Any] = None
    ):
        self.repository = repository or ContractRepository()
        self.payment_service = payment_service or EscrowPaymentService(repository=self.repository)
        self.decision_engine = decision_engine

        # Daemon thread state
        self._daemon_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_running = False

    def is_deadline_expired(
        self,
        contract: Dict[str, Any],
        now: Optional[Union[str, datetime]] = None
    ) -> bool:
        """
        Evaluates whether a contract's deadline has arrived or passed (now >= contract.deadline).
        """
        raw_deadline = contract.get("deadline")
        if not raw_deadline:
            return False

        try:
            deadline_dt = parse_datetime(raw_deadline)
            current_dt = parse_datetime(now)
            return current_dt >= deadline_dt
        except Exception:
            return False

    def check_and_process_contract(
        self,
        contract_id: str,
        now: Optional[Union[str, datetime]] = None,
        force: bool = False,
        actor: Optional[User] = None
    ) -> Dict[str, Any]:
        """
        Checks a single contract's deadline and triggers automated settlement if expired.
        
        Args:
            contract_id: UUID of contract to check.
            now: Optional simulated current timestamp (datetime or ISO string).
            force: If True (e.g. admin simulation), triggers expiry settlement immediately regardless of deadline.
            actor: Calling user context (defaults to platform AI Referee).
            
        Returns:
            Dict containing processing status, rule applied, and settlement execution summary.
        """
        contract = self.repository.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract '{contract_id}' not found.")

        current_status = contract.get("status")

        # 1. Terminal / Settled Guard
        if current_status == ContractState.SETTLED.value:
            return {
                "contract_id": contract_id,
                "status": "SKIPPED",
                "reason": f"Contract '{contract_id}' is already SETTLED.",
                "processed": False
            }

        # 2. Unfunded Guard
        unfunded_states = {
            ContractState.DRAFT.value,
            ContractState.REVIEW.value,
            ContractState.SIGNED.value
        }
        if current_status in unfunded_states:
            return {
                "contract_id": contract_id,
                "status": "SKIPPED",
                "reason": f"Contract is in unfunded state '{current_status}'.",
                "processed": False
            }

        # 3. Expiry Check (unless force simulated)
        current_time = parse_datetime(now)
        trigger_time_iso = current_time.isoformat()

        if not force and not self.is_deadline_expired(contract, now=current_time):
            return {
                "contract_id": contract_id,
                "status": "SKIPPED",
                "reason": "Contract deadline has not expired yet.",
                "deadline": contract.get("deadline"),
                "current_time": trigger_time_iso,
                "processed": False
            }

        # 4. Auto-Trigger Verification Pipeline Evaluation
        total_amount = round(float(contract.get("total_amount", 0.0)), 2)
        currency = contract.get("currency", "USD")

        # Check deliverable submissions
        submission = None
        if hasattr(self.repository, "get_latest_submission"):
            submission = self.repository.get_latest_submission(contract_id)

        report = None
        if hasattr(self.repository, "get_latest_verification_report"):
            report = self.repository.get_latest_verification_report(contract_id)

        split_calc: Optional[ProportionalSplitResult] = None
        rule_applied: str

        if submission is not None:
            # Seller submitted deliverable code
            if report is not None:
                # Evaluate feature checklist verdicts using proportional split engine
                per_feature_results = report.get("per_feature_results")
                split_calc = self.payment_service.calculate_proportional_split(
                    contract_id=contract_id,
                    feature_results=per_feature_results
                )
                passed_amount = split_calc.passed_amount
                refund_amount = split_calc.refund_amount
                rule_applied = split_calc.rule_applied
            else:
                # Submission exists without pre-compiled report: calculate default split
                split_calc = self.payment_service.calculate_proportional_split(contract_id=contract_id)
                passed_amount = split_calc.passed_amount
                refund_amount = split_calc.refund_amount
                rule_applied = split_calc.rule_applied
        else:
            # Seller failed to submit anything by deadline: full abandonment
            passed_amount = 0.0
            refund_amount = total_amount
            split_calc = None
            rule_applied = "FULL_REFUND_ABANDONMENT_NO_SUBMISSION"

        # 5. Auto-Trigger Escrow Settlement Rails (AI Referee Actor)
        effective_actor = actor or User(
            id="AI_REFEREE",
            name="AI Referee",
            email="referee@pactpal.internal",
            role=UserRole.ADMIN
        )

        settlement_metadata = {
            "deadline_expired": True,
            "triggered_by": "DEADLINE_WATCHER",
            "deadline": contract.get("deadline"),
            "triggered_at": trigger_time_iso,
            "submission_id": submission.get("id") if submission else None,
            "has_submission": bool(submission),
            "split_breakdown": split_calc.to_dict() if split_calc else None,
            "admin_override": (submission is None),
            "rule_applied": rule_applied
        }

        settle_result = self.payment_service.settle_contract_escrow(
            contract_id=contract_id,
            passed_amount=passed_amount,
            refund_amount=refund_amount,
            actor=effective_actor,
            idempotency_key=f"deadline_settle:{contract_id}",
            metadata=settlement_metadata
        )

        # 6. Immutable Audit Logging in Messages Table
        message_content = (
            f"Deadline Watcher: Contract deadline '{contract.get('deadline')}' expired. "
            f"Automated settlement executed ({rule_applied}): "
            f"${passed_amount:.2f} released to seller, ${refund_amount:.2f} refunded to buyer."
        )
        message_metadata = {
            "event": "DEADLINE_EXPIRED_SETTLEMENT_TRIGGERED",
            "contract_id": contract_id,
            "deadline": contract.get("deadline"),
            "triggered_at": trigger_time_iso,
            "rule_applied": rule_applied,
            "has_submission": bool(submission),
            "submission_id": submission.get("id") if submission else None,
            "passed_amount": passed_amount,
            "refund_amount": refund_amount,
            "total_amount": total_amount,
            "currency": currency,
            "capture_id": settle_result.get("capture_id"),
            "payout_batch_id": settle_result.get("payout_batch_id"),
            "void_id": settle_result.get("void_id"),
            "receipt_hash": settle_result.get("receipt_hash"),
            "split_details": split_calc.to_dict() if split_calc else None
        }

        if hasattr(self.repository, "record_message"):
            self.repository.record_message(
                contract_id=contract_id,
                sender_id=None,
                sender_type="AI_REFEREE",
                content=message_content,
                metadata=message_metadata
            )

        return {
            "contract_id": contract_id,
            "status": "SETTLED",
            "processed": True,
            "rule_applied": rule_applied,
            "deadline": contract.get("deadline"),
            "triggered_at": trigger_time_iso,
            "has_submission": bool(submission),
            "submission_id": submission.get("id") if submission else None,
            "passed_amount": passed_amount,
            "refund_amount": refund_amount,
            "total_amount": total_amount,
            "currency": currency,
            "settlement": settle_result,
            "receipt_hash": settle_result.get("receipt_hash"),
            "payout_batch_id": settle_result.get("payout_batch_id"),
            "capture_id": settle_result.get("capture_id"),
            "void_id": settle_result.get("void_id"),
            "buyer_summary": settle_result.get("buyer_summary"),
            "seller_summary": settle_result.get("seller_summary")
        }

    def sweep_expired_deadlines(
        self,
        now: Optional[Union[str, datetime]] = None,
        statuses: Optional[List[str]] = None
    ) -> SweepResult:
        """
        Executes a scheduled sweep inspecting all active contracts in relational database.
        Detects expired deadlines and executes automated settlement.
        
        Args:
            now: Optional current timestamp override (datetime or ISO string).
            statuses: List of contract statuses to inspect. Defaults to ('IN_PROGRESS', 'SUBMITTED', 'VERIFYING').
            
        Returns:
            SweepResult containing processed contract settlement summaries.
        """
        target_statuses = statuses or self.DEFAULT_ACTIVE_STATUSES
        current_time = parse_datetime(now)
        timestamp_iso = current_time.isoformat()

        if hasattr(self.repository, "get_contracts_by_status"):
            active_contracts = self.repository.get_contracts_by_status(target_statuses)
        elif hasattr(self.repository, "get_active_contracts"):
            active_contracts = self.repository.get_active_contracts(target_statuses)
        else:
            active_contracts = []

        inspected_count = len(active_contracts)
        processed_results: List[Dict[str, Any]] = []

        for contract in active_contracts:
            cid = contract.get("id")
            if not cid:
                continue

            if self.is_deadline_expired(contract, now=current_time):
                try:
                    res = self.check_and_process_contract(
                        contract_id=cid,
                        now=current_time,
                        force=False
                    )
                    if res.get("processed"):
                        processed_results.append(res)
                except Exception as e:
                    processed_results.append({
                        "contract_id": cid,
                        "status": "ERROR",
                        "processed": False,
                        "error": str(e)
                    })

        summary = {
            "timestamp": timestamp_iso,
            "contracts_inspected": inspected_count,
            "contracts_expired": len(processed_results),
            "contracts_settled": sum(1 for r in processed_results if r.get("status") == "SETTLED"),
            "statuses_inspected": target_statuses
        }

        return SweepResult(items=processed_results, summary=summary)

    def simulate_deadline(
        self,
        contract_id: str,
        actor: Optional[User] = None,
        now: Optional[Union[str, datetime]] = None
    ) -> Dict[str, Any]:
        """
        Forces simulation of deadline expiry for testing and UI unblocking (Commit C50).
        Enforces permission guard (assert_can_trigger_deadline_watcher).
        """
        if actor is not None:
            assert_can_trigger_deadline_watcher(actor)

        return self.check_and_process_contract(
            contract_id=contract_id,
            now=now,
            force=True,
            actor=actor
        )

    # --- Background Daemon Controls ---
    def start_background_daemon(self, interval_seconds: float = 60.0) -> threading.Thread:
        """Starts periodic background watcher daemon thread."""
        if self._is_running:
            return self._daemon_thread

        self._stop_event.clear()
        self._is_running = True

        def _run():
            while not self._stop_event.is_set():
                try:
                    self.sweep_expired_deadlines()
                except Exception:
                    pass
                self._stop_event.wait(interval_seconds)
            self._is_running = False

        self._daemon_thread = threading.Thread(target=_run, daemon=True, name="PactPal-DeadlineWatcher")
        self._daemon_thread.start()
        return self._daemon_thread

    def stop_background_daemon(self) -> None:
        """Stops running background watcher daemon."""
        self._stop_event.set()
        if self._daemon_thread and self._daemon_thread.is_alive():
            self._daemon_thread.join(timeout=2.0)
        self._is_running = False

    def is_daemon_running(self) -> bool:
        """Checks if background daemon is currently active."""
        return self._is_running and (self._daemon_thread is not None and self._daemon_thread.is_alive())

