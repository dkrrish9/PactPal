"""
PactPal Payments REST API Router & HTTP Dispatcher
Exposes payment rails endpoints matching shared/docs/SHARED_API_CONTRACT.md:
  - GET  /api/v1/contracts/{id}/hold: Exposes authorization expiry countdown data (C14)
  - POST /api/v1/payments/orders/create-hold: Creates PayPal order with AUTHORIZE intent (C10)
  - POST /api/v1/payments/orders/authorize: Executes authorization & marks contract FUNDED (C10)
"""

import re
import os
import json
import http.client
import urllib.parse
from typing import Dict, Any, Optional, Tuple
from wsgiref.simple_server import make_server

from .client import PayPalAPIError
from .service import (
    EscrowPaymentService,
    PaymentApprovalService,
    PaymentApprovalError,
    ApprovalVerdict,
    ContractRepository,
    User,
    UserRole,
    ContractState,
    ForbiddenActionError,
    UnauthorizedRoleError,
    StateValidationError,
    WebhookVerificationError,
    ProportionalSplitResult,
    SettlementSummary,
    ProofOfWorkReceipt,
    canonicalize_proof_of_work_summary,
    generate_proof_of_work_hash,
    verify_receipt_hash,
    assert_can_view_receipt,
    assert_can_view_split_preview,
    assert_can_view_settlement_summary,
    assert_can_apply_incremental_hold,
    assert_can_trigger_deadline_watcher,
    assert_can_view_notifications,
    assert_can_dispatch_notification,
    DeadlineWatcherService,
    SweepResult,
    EmailNotificationService,
    InMemoryEmailProvider,
    SMTPEmailProvider,
    SendGridEmailProvider,
    get_email_provider
)

HOLD_ENDPOINT_REGEX = re.compile(r"^/api/v1/contracts/([^/]+)/hold/?$")
SETTLEMENT_SUMMARY_REGEX = re.compile(r"^/api/v1/contracts/([^/]+)/settlement-summary/?$")
RECEIPT_ENDPOINT_REGEX = re.compile(r"^/api/v1/contracts/([^/]+)/receipt/?$")
VERIFY_RECEIPT_REGEX = re.compile(r"^/api/v1/payments/(?:receipts/verify|verify-receipt)/?$")
SPLIT_PREVIEW_CONTRACT_REGEX = re.compile(r"^/api/v1/contracts/([^/]+)/split-preview/?$")
SPLIT_PREVIEW_PAYMENTS_REGEX = re.compile(r"^/api/v1/payments/split-preview/?$")
APPROVAL_CHECK_REGEX = re.compile(r"^/api/v1/payments/approval-check/?$")
CONTRACT_APPROVAL_REGEX = re.compile(r"^/api/v1/contracts/([^/]+)/payment-approval/?$")
CREATE_HOLD_REGEX = re.compile(r"^/api/v1/payments/orders/create-hold/?$")
AUTHORIZE_HOLD_REGEX = re.compile(r"^/api/v1/payments/orders/authorize/?$")
INCREMENTAL_HOLD_CONTRACT_REGEX = re.compile(r"^/api/v1/contracts/([^/]+)/incremental-hold/?$")
INCREMENTAL_HOLD_PAYMENTS_REGEX = re.compile(r"^/api/v1/payments/orders/incremental-hold/?$")
DEADLINE_SWEEP_REGEX = re.compile(r"^/api/v1/payments/deadline-watcher/sweep/?$")
SIMULATE_DEADLINE_REGEX = re.compile(r"^/api/v1/contracts/([^/]+)/simulate-deadline/?$")
SETTLE_REGEX = re.compile(r"^/api/v1/payments/settle/?$")
WEBHOOK_REGEX = re.compile(r"^/api/v1/payments/webhooks(?:/paypal)?/?$")
NOTIFICATIONS_DISPATCH_REGEX = re.compile(r"^/api/v1/payments/notifications/dispatch/?$")
CONTRACT_NOTIFICATIONS_REGEX = re.compile(r"^/api/v1/contracts/([^/]+)/notifications/?$")
CONTRACT_NOTIFICATIONS_DISPATCH_REGEX = re.compile(r"^/api/v1/contracts/([^/]+)/notifications/dispatch/?$")

class PaymentsAPIHandler:
    """
    HTTP request dispatcher for Payments & Escrow Subsystem.
    Provides standard JSON REST responses for frontend, webhooks, and referee services.
    """

    def __init__(
        self,
        service: Optional[EscrowPaymentService] = None,
        deadline_watcher: Optional[DeadlineWatcherService] = None,
        notification_service: Optional[EmailNotificationService] = None
    ):
        self.service = service or EscrowPaymentService()
        self.repository = self.service.repository
        self.deadline_watcher = deadline_watcher or DeadlineWatcherService(
            repository=self.repository,
            payment_service=self.service
        )
        self.notification_service = (
            notification_service
            or getattr(self.service, "notification_service", None)
            or EmailNotificationService(repository=self.repository)
        )
        self.deadline_watcher = deadline_watcher or DeadlineWatcherService(
            repository=self.repository,
            payment_service=self.service
        )

    def _extract_actor(self, headers: Dict[str, str]) -> Optional[User]:
        """
        Extracts actor context from X-Actor-Id or Authorization header.
        Supports:
          - X-Actor-Id: <user_id>
          - Authorization: Bearer <user_id_or_token>
        """
        # Normalize header keys to lowercase
        norm_headers = {k.lower(): v for k, v in headers.items()}
        actor_id = norm_headers.get("x-actor-id")

        if not actor_id:
            auth = norm_headers.get("authorization", "")
            if auth.startswith("Bearer "):
                actor_id = auth[7:].strip()

        if not actor_id:
            return None

        # Look up user in repository
        user = self.repository.get_user(actor_id)
        if not user and actor_id == "AI_REFEREE":
            return User(id="AI_REFEREE", name="AI Referee", email="referee@pactpal.internal", role=UserRole.ADMIN)
        return user

    def _extract_idempotency_key(self, headers: Dict[str, str]) -> Optional[str]:
        """Extracts Idempotency-Key or X-Idempotency-Key from headers."""
        norm_headers = {k.lower(): v for k, v in headers.items()}
        return norm_headers.get("idempotency-key") or norm_headers.get("x-idempotency-key")

    def dispatch(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[bytes] = None
    ) -> Tuple[int, Dict[str, str], bytes]:
        """
        Dispatches request and returns (status_code, response_headers, response_body_bytes).
        """
        headers = headers or {}
        method = method.upper()
        clean_path = path.split("?")[0]

        # 1. GET /api/v1/contracts/{id}/hold
        match_hold = HOLD_ENDPOINT_REGEX.match(clean_path)
        if match_hold:
            if method != "GET":
                return self._json_response(405, {"error": "METHOD_NOT_ALLOWED", "message": f"Method {method} not allowed on hold endpoint."})
            contract_id = match_hold.group(1)
            return self._handle_get_hold(contract_id, headers)

        # 2. GET /api/v1/contracts/{id}/settlement-summary (C41 Milestone 3)
        match_settlement_summary = SETTLEMENT_SUMMARY_REGEX.match(clean_path)
        if match_settlement_summary:
            if method != "GET":
                return self._json_response(405, {"error": "METHOD_NOT_ALLOWED", "message": f"Method {method} not allowed on settlement-summary endpoint."})
            contract_id = match_settlement_summary.group(1)
            return self._handle_get_settlement_summary(contract_id, headers)

        # 3. GET /api/v1/contracts/{id}/receipt (C44 Milestone 3)
        match_receipt = RECEIPT_ENDPOINT_REGEX.match(clean_path)
        if match_receipt:
            if method != "GET":
                return self._json_response(405, {"error": "METHOD_NOT_ALLOWED", "message": f"Method {method} not allowed on receipt endpoint."})
            contract_id = match_receipt.group(1)
            return self._handle_get_receipt(contract_id, headers)

        # 4. POST /api/v1/payments/receipts/verify (C44 Milestone 3)
        if VERIFY_RECEIPT_REGEX.match(clean_path):
            if method != "POST":
                return self._json_response(405, {"error": "METHOD_NOT_ALLOWED", "message": f"Method {method} not allowed on verify-receipt endpoint."})
            return self._handle_verify_receipt(headers, body)

        # 2. GET or POST /api/v1/contracts/{id}/split-preview (C37 Milestone 3)
        match_split_preview = SPLIT_PREVIEW_CONTRACT_REGEX.match(clean_path)
        if match_split_preview:
            if method not in ("GET", "POST"):
                return self._json_response(405, {"error": "METHOD_NOT_ALLOWED", "message": f"Method {method} not allowed on split-preview endpoint."})
            contract_id = match_split_preview.group(1)
            return self._handle_contract_split_preview(contract_id, headers, body, method)

        # 3. POST /api/v1/payments/split-preview (C37 Milestone 3)
        if SPLIT_PREVIEW_PAYMENTS_REGEX.match(clean_path):
            if method != "POST":
                return self._json_response(405, {"error": "METHOD_NOT_ALLOWED", "message": f"Method {method} not allowed on payments split-preview."})
            return self._handle_payments_split_preview(headers, body)

        # 4. POST /api/v1/payments/approval-check (C31 Milestone 2)
        if APPROVAL_CHECK_REGEX.match(clean_path):
            if method != "POST":
                return self._json_response(405, {"error": "METHOD_NOT_ALLOWED", "message": f"Method {method} not allowed on approval-check."})
            return self._handle_approval_check(headers, body)

        # 3. GET /api/v1/contracts/{id}/payment-approval (C31 Milestone 2)
        match_contract_approval = CONTRACT_APPROVAL_REGEX.match(clean_path)
        if match_contract_approval:
            if method != "GET":
                return self._json_response(405, {"error": "METHOD_NOT_ALLOWED", "message": f"Method {method} not allowed on contract payment-approval."})
            contract_id = match_contract_approval.group(1)
            return self._handle_get_contract_approval(contract_id, headers, path)

        # 4. POST /api/v1/payments/orders/create-hold
        if CREATE_HOLD_REGEX.match(clean_path):
            if method != "POST":
                return self._json_response(405, {"error": "METHOD_NOT_ALLOWED", "message": f"Method {method} not allowed on create-hold."})
            return self._handle_create_hold(headers, body)

        # 3. POST /api/v1/payments/orders/authorize
        if AUTHORIZE_HOLD_REGEX.match(clean_path):
            if method != "POST":
                return self._json_response(405, {"error": "METHOD_NOT_ALLOWED", "message": f"Method {method} not allowed on authorize."})
            return self._handle_authorize(headers, body)

        # 4. POST /api/v1/contracts/{id}/incremental-hold (C46 Milestone 3)
        match_inc_hold = INCREMENTAL_HOLD_CONTRACT_REGEX.match(clean_path)
        if match_inc_hold:
            if method != "POST":
                return self._json_response(405, {"error": "METHOD_NOT_ALLOWED", "message": f"Method {method} not allowed on incremental-hold endpoint."})
            contract_id = match_inc_hold.group(1)
            return self._handle_incremental_hold(headers, body, contract_id=contract_id)

        # 5. POST /api/v1/payments/orders/incremental-hold (C46 Milestone 3)
        if INCREMENTAL_HOLD_PAYMENTS_REGEX.match(clean_path):
            if method != "POST":
                return self._json_response(405, {"error": "METHOD_NOT_ALLOWED", "message": f"Method {method} not allowed on payments orders incremental-hold."})
            return self._handle_incremental_hold(headers, body, contract_id=None)

        # 6. POST /api/v1/payments/settle (C24 Milestone 2)
        if SETTLE_REGEX.match(clean_path):
            if method != "POST":
                return self._json_response(405, {"error": "METHOD_NOT_ALLOWED", "message": f"Method {method} not allowed on settle."})
            return self._handle_settle(headers, body)

        # 7. POST /api/v1/payments/deadline-watcher/sweep (Commit C49)
        if DEADLINE_SWEEP_REGEX.match(clean_path):
            if method != "POST":
                return self._json_response(405, {"error": "METHOD_NOT_ALLOWED", "message": f"Method {method} not allowed on deadline-watcher sweep endpoint."})
            return self._handle_deadline_sweep(headers, body)

        # 8. POST /api/v1/contracts/{id}/simulate-deadline (Commit C49, C50)
        match_sim = SIMULATE_DEADLINE_REGEX.match(clean_path)
        if match_sim:
            if method != "POST":
                return self._json_response(405, {"error": "METHOD_NOT_ALLOWED", "message": f"Method {method} not allowed on simulate-deadline endpoint."})
            contract_id = match_sim.group(1)
            return self._handle_simulate_deadline(contract_id, headers, body)

        # 5. POST /api/v1/payments/webhooks (C28 Milestone 2)
        if WEBHOOK_REGEX.match(clean_path):
            if method != "POST":
                return self._json_response(405, {"error": "METHOD_NOT_ALLOWED", "message": f"Method {method} not allowed on webhooks."})
            return self._handle_webhook(headers, body)

        # 9. POST /api/v1/payments/notifications/dispatch (Commit C51)
        if NOTIFICATIONS_DISPATCH_REGEX.match(clean_path):
            if method != "POST":
                return self._json_response(405, {"error": "METHOD_NOT_ALLOWED", "message": f"Method {method} not allowed on notifications dispatch endpoint."})
            return self._handle_dispatch_notification(headers, body)

        # 10. POST /api/v1/contracts/{id}/notifications/dispatch (Commit C51)
        match_notif_disp = CONTRACT_NOTIFICATIONS_DISPATCH_REGEX.match(clean_path)
        if match_notif_disp:
            if method != "POST":
                return self._json_response(405, {"error": "METHOD_NOT_ALLOWED", "message": f"Method {method} not allowed on contract notifications dispatch endpoint."})
            contract_id = match_notif_disp.group(1)
            return self._handle_dispatch_notification(headers, body, contract_id=contract_id)

        # 11. GET or POST /api/v1/contracts/{id}/notifications (Commit C51)
        match_notif = CONTRACT_NOTIFICATIONS_REGEX.match(clean_path)
        if match_notif:
            contract_id = match_notif.group(1)
            if method == "GET":
                return self._handle_get_contract_notifications(contract_id, headers)
            elif method == "POST":
                return self._handle_dispatch_notification(headers, body, contract_id=contract_id)
            else:
                return self._json_response(405, {"error": "METHOD_NOT_ALLOWED", "message": f"Method {method} not allowed on contract notifications endpoint."})

        return self._json_response(404, {"error": "NOT_FOUND", "message": f"Endpoint '{clean_path}' not found in Payments API."})

    def _handle_get_hold(self, contract_id: str, headers: Dict[str, str]) -> Tuple[int, Dict[str, str], bytes]:
        """
        Handler for GET /api/v1/contracts/{id}/hold.
        Returns amount, expiry date and time left for the countdown (29-day limit).
        """
        actor = self._extract_actor(headers)
        if actor is None:
            # If actor is not supplied or invalid
            return self._json_response(
                401,
                {"error": "UNAUTHORIZED", "message": "Authentication required. Supply X-Actor-Id or Authorization header."}
            )

        try:
            hold_data = self.service.get_contract_hold(contract_id=contract_id, actor=actor)
            return self._json_response(200, hold_data)
        except ValueError as e:
            # Contract not found
            return self._json_response(404, {"error": "NOT_FOUND", "message": str(e)})
        except ForbiddenActionError as e:
            # Actor not buyer, seller, or admin
            return self._json_response(403, {"error": "FORBIDDEN", "message": str(e)})
        except StateValidationError as e:
            # Contract is not in funded state
            return self._json_response(400, {"error": "BAD_REQUEST", "message": str(e)})
        except Exception as e:
            return self._json_response(500, {"error": "INTERNAL_SERVER_ERROR", "message": str(e)})

    def _handle_get_settlement_summary(
        self,
        contract_id: str,
        headers: Dict[str, str]
    ) -> Tuple[int, Dict[str, str], bytes]:
        """
        Handler for GET /api/v1/contracts/{id}/settlement-summary (Commit C41).
        Returns dual settlement summary for both parties (paid, returned, why).
        RBAC: Contract Buyer, Seller, Platform Admin, or AI Referee.
        """
        actor = self._extract_actor(headers)
        if actor is None:
            return self._json_response(
                401,
                {"error": "UNAUTHORIZED", "message": "Authentication required. Supply X-Actor-Id or Authorization header."}
            )

        try:
            summary = self.service.get_settlement_summary(contract_id=contract_id, actor=actor)
            return self._json_response(200, summary)
        except ValueError as e:
            if "not found" in str(e).lower():
                return self._json_response(404, {"error": "NOT_FOUND", "message": str(e)})
            return self._json_response(400, {"error": "BAD_REQUEST", "message": str(e)})
        except (ForbiddenActionError, UnauthorizedRoleError) as e:
            return self._json_response(403, {"error": "FORBIDDEN", "message": str(e)})
        except StateValidationError as e:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": str(e)})
        except Exception as e:
            return self._json_response(500, {"error": "INTERNAL_SERVER_ERROR", "message": str(e)})

    def _handle_get_receipt(
        self,
        contract_id: str,
        headers: Dict[str, str]
    ) -> Tuple[int, Dict[str, str], bytes]:
        """
        Handler for GET /api/v1/contracts/{id}/receipt (Commit C44).
        Retrieves the cryptographic proof-of-work quality receipt, verification metrics,
        and validation status (is_valid: bool).
        RBAC: Contract Buyer, Seller, Platform Admin, or AI Referee.
        """
        actor = self._extract_actor(headers)
        if actor is None:
            return self._json_response(
                401,
                {"error": "UNAUTHORIZED", "message": "Authentication required. Supply X-Actor-Id or Authorization header."}
            )

        try:
            receipt = self.service.get_contract_receipt(contract_id=contract_id, actor=actor)
            return self._json_response(200, receipt)
        except ValueError as e:
            if "not found" in str(e).lower():
                return self._json_response(404, {"error": "NOT_FOUND", "message": str(e)})
            return self._json_response(400, {"error": "BAD_REQUEST", "message": str(e)})
        except (ForbiddenActionError, UnauthorizedRoleError) as e:
            return self._json_response(403, {"error": "FORBIDDEN", "message": str(e)})
        except StateValidationError as e:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": str(e)})
        except Exception as e:
            return self._json_response(500, {"error": "INTERNAL_SERVER_ERROR", "message": str(e)})

    def _handle_verify_receipt(
        self,
        headers: Dict[str, str],
        body: Optional[bytes]
    ) -> Tuple[int, Dict[str, str], bytes]:
        """
        Handler for POST /api/v1/payments/receipts/verify (Commit C44).
        Verifies if a proof-of-work receipt payload matches the claimed SHA-256 digest.
        """
        if not body:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": "Missing request body."})

        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception as e:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": f"Malformed JSON body: {str(e)}"})

        receipt_payload = payload.get("receipt_payload") or payload.get("summary") or payload.get("evidence_payload")
        receipt_hash = payload.get("receipt_hash")

        if not receipt_payload or not receipt_hash:
            return self._json_response(
                400,
                {"error": "BAD_REQUEST", "message": "Fields 'receipt_payload' (or 'summary') and 'receipt_hash' are required."}
            )

        is_valid = self.service.verify_receipt_hash(receipt_payload, receipt_hash)
        try:
            norm_payload = receipt_payload if isinstance(receipt_payload, dict) else json.loads(receipt_payload)
            recomputed = generate_proof_of_work_hash(norm_payload)
        except Exception:
            recomputed = ""

        return self._json_response(200, {
            "is_valid": is_valid,
            "status": "VERIFIED" if is_valid else "TAMPERED",
            "receipt_hash": receipt_hash,
            "recomputed_hash": recomputed
        })

    def _handle_contract_split_preview(
        self,
        contract_id: str,
        headers: Dict[str, str],
        body: Optional[bytes],
        method: str
    ) -> Tuple[int, Dict[str, str], bytes]:
        """
        Handler for GET & POST /api/v1/contracts/{id}/split-preview (Commit C37).
        Calculates and previews proportional escrow split breakdown, remainder assignment,
        and mathematical invariant guarantee.
        RBAC: Contract Buyer, Seller, Platform Admin, or AI Referee.
        """
        actor = self._extract_actor(headers)
        if actor is None:
            return self._json_response(
                401,
                {"error": "UNAUTHORIZED", "message": "Authentication required. Supply X-Actor-Id or Authorization header."}
            )

        feature_results = None
        if method == "POST" and body:
            try:
                payload = json.loads(body.decode("utf-8"))
                feature_results = payload.get("feature_results")
            except Exception as e:
                return self._json_response(400, {"error": "BAD_REQUEST", "message": f"Malformed JSON body: {str(e)}"})

        try:
            split_result = self.service.calculate_proportional_split(
                contract_id=contract_id,
                feature_results=feature_results,
                actor=actor
            )
            return self._json_response(200, split_result.to_dict())
        except ValueError as e:
            return self._json_response(404, {"error": "NOT_FOUND", "message": str(e)})
        except (ForbiddenActionError, UnauthorizedRoleError) as e:
            return self._json_response(403, {"error": "FORBIDDEN", "message": str(e)})
        except Exception as e:
            return self._json_response(500, {"error": "INTERNAL_SERVER_ERROR", "message": str(e)})

    def _handle_payments_split_preview(
        self,
        headers: Dict[str, str],
        body: Optional[bytes]
    ) -> Tuple[int, Dict[str, str], bytes]:
        """
        Handler for POST /api/v1/payments/split-preview (Commit C37).
        Calculates split preview given contract_id and optional feature_results in request body.
        """
        actor = self._extract_actor(headers)
        if actor is None:
            return self._json_response(
                401,
                {"error": "UNAUTHORIZED", "message": "Authentication required. Supply X-Actor-Id or Authorization header."}
            )

        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception as e:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": f"Malformed JSON body: {str(e)}"})

        contract_id = payload.get("contract_id")
        if not contract_id:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": "contract_id is required."})

        feature_results = payload.get("feature_results")

        try:
            split_result = self.service.calculate_proportional_split(
                contract_id=contract_id,
                feature_results=feature_results,
                actor=actor
            )
            return self._json_response(200, split_result.to_dict())
        except ValueError as e:
            return self._json_response(404, {"error": "NOT_FOUND", "message": str(e)})
        except (ForbiddenActionError, UnauthorizedRoleError) as e:
            return self._json_response(403, {"error": "FORBIDDEN", "message": str(e)})
        except Exception as e:
            return self._json_response(500, {"error": "INTERNAL_SERVER_ERROR", "message": str(e)})

    def _handle_create_hold(self, headers: Dict[str, str], body: Optional[bytes]) -> Tuple[int, Dict[str, str], bytes]:
        """Handler for POST /api/v1/payments/orders/create-hold."""
        actor = self._extract_actor(headers)
        if actor is None:
            return self._json_response(401, {"error": "UNAUTHORIZED", "message": "Authentication required."})

        try:
            data = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": "Invalid JSON body."})

        contract_id = data.get("contract_id")
        if not contract_id:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": "contract_id is required."})

        idempotency_key = self._extract_idempotency_key(headers)

        try:
            res = self.service.initiate_contract_hold(
                contract_id=contract_id,
                actor=actor,
                return_url=data.get("return_url"),
                cancel_url=data.get("cancel_url"),
                idempotency_key=idempotency_key
            )
            return self._json_response(200, res)
        except ValueError as e:
            return self._json_response(404, {"error": "NOT_FOUND", "message": str(e)})
        except ForbiddenActionError as e:
            return self._json_response(403, {"error": "FORBIDDEN", "message": str(e)})
        except StateValidationError as e:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": str(e)})
        except PaymentApprovalError as e:
            return self._json_response(403, {"error": "PAYMENT_APPROVAL_BLOCKED", "message": str(e), "verdict": e.verdict.to_dict() if e.verdict else None})
        except Exception as e:
            return self._json_response(500, {"error": "INTERNAL_SERVER_ERROR", "message": str(e)})

    def _handle_authorize(self, headers: Dict[str, str], body: Optional[bytes]) -> Tuple[int, Dict[str, str], bytes]:
        """Handler for POST /api/v1/payments/orders/authorize."""
        actor = self._extract_actor(headers)
        if actor is None:
            return self._json_response(401, {"error": "UNAUTHORIZED", "message": "Authentication required."})

        try:
            data = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": "Invalid JSON body."})

        contract_id = data.get("contract_id")
        paypal_order_id = data.get("paypal_order_id")

        if not contract_id or not paypal_order_id:
            return self._json_response(
                400,
                {"error": "BAD_REQUEST", "message": "contract_id and paypal_order_id are required."}
            )

        idempotency_key = self._extract_idempotency_key(headers)

        try:
            res = self.service.confirm_and_store_authorization(
                contract_id=contract_id,
                paypal_order_id=paypal_order_id,
                actor=actor,
                idempotency_key=idempotency_key
            )
            return self._json_response(200, res)
        except ValueError as e:
            return self._json_response(404, {"error": "NOT_FOUND", "message": str(e)})
        except ForbiddenActionError as e:
            return self._json_response(403, {"error": "FORBIDDEN", "message": str(e)})
        except StateValidationError as e:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": str(e)})
        except PaymentApprovalError as e:
            return self._json_response(403, {"error": "PAYMENT_APPROVAL_BLOCKED", "message": str(e), "verdict": e.verdict.to_dict() if e.verdict else None})
        except Exception as e:
            return self._json_response(500, {"error": "INTERNAL_SERVER_ERROR", "message": str(e)})

    def _handle_incremental_hold(
        self,
        headers: Dict[str, str],
        body: Optional[bytes],
        contract_id: Optional[str] = None
    ) -> Tuple[int, Dict[str, str], bytes]:
        """
        Handler for:
          - POST /api/v1/contracts/{id}/incremental-hold
          - POST /api/v1/payments/orders/incremental-hold
        Increases escrow authorization hold for an accepted change request (Commit C46).
        """
        actor = self._extract_actor(headers)
        if actor is None:
            return self._json_response(401, {"error": "UNAUTHORIZED", "message": "Authentication required. Provide valid X-Actor-Id or Authorization header."})

        try:
            data = json.loads(body.decode("utf-8")) if body else {}
        except Exception as e:
            return self._json_response(400, {"error": "INVALID_JSON", "message": f"Malformed JSON: {str(e)}"})

        resolved_contract_id = contract_id or data.get("contract_id")
        if not resolved_contract_id:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": "contract_id is required in path or request body."})

        change_request_id = data.get("change_request_id")
        if not change_request_id:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": "Missing required field 'change_request_id'."})

        additional_amount = data.get("additional_amount")
        if additional_amount is not None:
            try:
                additional_amount = float(additional_amount)
                if additional_amount <= 0:
                    return self._json_response(400, {"error": "INVALID_AMOUNT", "message": "additional_amount must be greater than zero."})
            except (ValueError, TypeError):
                return self._json_response(400, {"error": "INVALID_AMOUNT", "message": "additional_amount must be a valid numeric amount."})

        idempotency_key = self._extract_idempotency_key(headers)

        try:
            res = self.service.apply_incremental_hold(
                contract_id=resolved_contract_id,
                change_request_id=change_request_id,
                additional_amount=additional_amount,
                actor=actor,
                idempotency_key=idempotency_key
            )
            return self._json_response(200, res)
        except ValueError as e:
            msg = str(e)
            if "not found" in msg.lower():
                return self._json_response(404, {"error": "NOT_FOUND", "message": msg})
            return self._json_response(400, {"error": "BAD_REQUEST", "message": msg})
        except ForbiddenActionError as e:
            return self._json_response(403, {"error": "FORBIDDEN", "message": str(e)})
        except UnauthorizedRoleError as e:
            return self._json_response(403, {"error": "UNAUTHORIZED_ROLE", "message": str(e)})
        except PaymentApprovalError as e:
            return self._json_response(403, {
                "error": "PAYMENT_APPROVAL_BLOCKED",
                "message": str(e),
                "verdict": e.verdict.to_dict() if hasattr(e, "verdict") and e.verdict else None
            })
        except StateValidationError as e:
            return self._json_response(400, {"error": "INVALID_STATE", "message": str(e)})
        except PayPalAPIError as e:
            return self._json_response(502, {"error": "PAYPAL_API_ERROR", "message": str(e)})
        except Exception as e:
            return self._json_response(500, {"error": "INTERNAL_SERVER_ERROR", "message": str(e)})

    def _handle_settle(self, headers: Dict[str, str], body: Optional[bytes]) -> Tuple[int, Dict[str, str], bytes]:
        """
        Handler for POST /api/v1/payments/settle.
        Executes milestone partial/full capture, void/refund, and seller payouts matching
        SHARED_API_CONTRACT.md Section 3.4.
        """
        actor = self._extract_actor(headers)
        if actor is None:
            return self._json_response(
                401,
                {"error": "UNAUTHORIZED", "message": "Authentication required. Supply X-Actor-Id or Authorization header."}
            )

        try:
            data = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": "Invalid JSON body."})

        contract_id = data.get("contract_id")
        if not contract_id:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": "contract_id is required."})

        if "passed_amount" not in data or "refund_amount" not in data:
            return self._json_response(
                400,
                {"error": "BAD_REQUEST", "message": "Both passed_amount and refund_amount are required."}
            )

        try:
            passed_amount = float(data.get("passed_amount"))
            refund_amount = float(data.get("refund_amount"))
        except (ValueError, TypeError):
            return self._json_response(
                400,
                {"error": "BAD_REQUEST", "message": "passed_amount and refund_amount must be numbers."}
            )

        seller_paypal_email = data.get("seller_paypal_email", "")
        idempotency_key = self._extract_idempotency_key(headers)
        meta = data.get("metadata") or {}
        if data.get("admin_override") or data.get("is_admin_override"):
            meta["admin_override"] = True

        try:
            res = self.service.settle_contract_escrow(
                contract_id=contract_id,
                passed_amount=passed_amount,
                refund_amount=refund_amount,
                seller_paypal_email=seller_paypal_email,
                actor=actor,
                idempotency_key=idempotency_key,
                metadata=meta
            )
            return self._json_response(200, res)
        except ValueError as e:
            if "not found" in str(e).lower():
                return self._json_response(404, {"error": "NOT_FOUND", "message": str(e)})
            return self._json_response(400, {"error": "BAD_REQUEST", "message": str(e)})
        except (ForbiddenActionError, UnauthorizedRoleError) as e:
            return self._json_response(403, {"error": "FORBIDDEN", "message": str(e)})
        except StateValidationError as e:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": str(e)})
        except PaymentApprovalError as e:
            return self._json_response(403, {"error": "PAYMENT_APPROVAL_BLOCKED", "message": str(e), "verdict": e.verdict.to_dict() if e.verdict else None})
        except PayPalAPIError as e:
            return self._json_response(502, {"error": "PAYPAL_API_ERROR", "message": str(e), "details": e.details})
        except Exception as e:
            return self._json_response(500, {"error": "INTERNAL_SERVER_ERROR", "message": str(e)})

    def _handle_approval_check(self, headers: Dict[str, str], body: Optional[bytes]) -> Tuple[int, Dict[str, str], bytes]:
        """
        Handler for POST /api/v1/payments/approval-check (Commit C31).
        Pre-flight policy gate to inspect whether a payment action is eligible to fire.
        Returns HTTP 200 with structured ApprovalVerdict (approved: bool, reasons, checks_passed, checks_failed).
        """
        actor = self._extract_actor(headers)
        if actor is None:
            return self._json_response(401, {"error": "UNAUTHORIZED", "message": "Authentication required. Supply X-Actor-Id or Authorization header."})

        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception as e:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": f"Malformed JSON body: {str(e)}"})

        contract_id = payload.get("contract_id")
        action = payload.get("action")

        if not contract_id or not action:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": "Fields 'contract_id' and 'action' are required."})

        norm_action = str(action).upper().strip()
        allowed_actions = {"CREATE_HOLD", "INITIATE_HOLD", "AUTHORIZE_HOLD", "AUTHORIZE", "SETTLE_ESCROW", "SETTLE"}
        if norm_action not in allowed_actions:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": f"Invalid action '{action}'. Allowed: CREATE_HOLD, AUTHORIZE_HOLD, SETTLE_ESCROW."})

        contract = self.repository.get_contract(contract_id)
        if not contract:
            return self._json_response(404, {"error": "NOT_FOUND", "message": f"Contract '{contract_id}' not found."})

        # Check role permission
        if norm_action in ("CREATE_HOLD", "INITIATE_HOLD", "AUTHORIZE_HOLD", "AUTHORIZE"):
            if actor.role != UserRole.BUYER:
                return self._json_response(403, {"error": "FORBIDDEN", "message": f"User '{actor.id}' with role '{actor.role.value}' is not authorized to perform funding action '{action}'."})
        elif norm_action in ("SETTLE_ESCROW", "SETTLE"):
            is_admin = (actor.role == UserRole.ADMIN)
            is_referee = (getattr(actor, "id", None) == "AI_REFEREE" or getattr(actor, "name", None) == "AI Referee")
            if not (is_admin or is_referee):
                return self._json_response(403, {"error": "FORBIDDEN", "message": f"User '{actor.id}' with role '{actor.role.value}' is not authorized to perform settlement action '{action}'."})

        meta = payload.get("metadata") or {}
        for k in ("passed_amount", "refund_amount", "admin_override", "is_admin_override", "seller_paypal_email"):
            if k in payload:
                meta[k] = payload[k]

        verdict = self.service.approval_service.validate_payment_approval(
            contract_id=contract_id,
            action=norm_action,
            actor=actor,
            metadata=meta
        )

        return self._json_response(200, verdict.to_dict())

    def _handle_get_contract_approval(self, contract_id: str, headers: Dict[str, str], path: str) -> Tuple[int, Dict[str, str], bytes]:
        """
        Handler for GET /api/v1/contracts/{id}/payment-approval (Commit C31).
        Allows inspecting approval status of a contract via GET request.
        """
        actor = self._extract_actor(headers)
        if actor is None:
            return self._json_response(401, {"error": "UNAUTHORIZED", "message": "Authentication required. Supply X-Actor-Id or Authorization header."})

        contract = self.repository.get_contract(contract_id)
        if not contract:
            return self._json_response(404, {"error": "NOT_FOUND", "message": f"Contract '{contract_id}' not found."})

        parsed = urllib.parse.urlparse(path)
        qs = urllib.parse.parse_qs(parsed.query)
        action = qs.get("action", [None])[0]

        if not action:
            status = contract.get("status")
            if status == ContractState.SIGNED.value:
                action = "CREATE_HOLD"
            elif status in (ContractState.FUNDED.value, ContractState.DECISION.value, ContractState.DISPUTE.value):
                action = "SETTLE_ESCROW"
            else:
                action = "CREATE_HOLD"

        norm_action = str(action).upper().strip()
        verdict = self.service.approval_service.validate_payment_approval(
            contract_id=contract_id,
            action=norm_action,
            actor=actor
        )

        return self._json_response(200, verdict.to_dict())

    def _handle_deadline_sweep(
        self,
        headers: Dict[str, str],
        body: Optional[bytes]
    ) -> Tuple[int, Dict[str, str], bytes]:
        """
        Handler for POST /api/v1/payments/deadline-watcher/sweep (Commit C49).
        Triggers scheduled or on-demand sweep across active contracts.
        """
        actor = self._extract_actor(headers)
        if actor is None:
            return self._json_response(
                401,
                {"error": "UNAUTHORIZED", "message": "Authentication required. Supply X-Actor-Id or Authorization header."}
            )

        try:
            assert_can_trigger_deadline_watcher(actor)
        except (ForbiddenActionError, UnauthorizedRoleError) as e:
            return self._json_response(403, {"error": "FORBIDDEN", "message": str(e)})

        data = {}
        if body:
            try:
                data = json.loads(body.decode("utf-8"))
            except Exception as e:
                return self._json_response(400, {"error": "BAD_REQUEST", "message": f"Malformed JSON: {str(e)}"})

        now = data.get("now")
        statuses = data.get("statuses")

        try:
            sweep_result = self.deadline_watcher.sweep_expired_deadlines(now=now, statuses=statuses)
            return self._json_response(200, sweep_result.to_dict())
        except Exception as e:
            return self._json_response(500, {"error": "INTERNAL_SERVER_ERROR", "message": str(e)})

    def _handle_simulate_deadline(
        self,
        contract_id: str,
        headers: Dict[str, str],
        body: Optional[bytes]
    ) -> Tuple[int, Dict[str, str], bytes]:
        """
        Handler for POST /api/v1/contracts/{id}/simulate-deadline (Commit C49, C50).
        Forces simulation of deadline expiry and triggers settlement on PayPal rails.
        """
        actor = self._extract_actor(headers)
        if actor is None:
            return self._json_response(
                401,
                {"error": "UNAUTHORIZED", "message": "Authentication required. Supply X-Actor-Id or Authorization header."}
            )

        try:
            assert_can_trigger_deadline_watcher(actor)
        except (ForbiddenActionError, UnauthorizedRoleError) as e:
            return self._json_response(403, {"error": "FORBIDDEN", "message": str(e)})

        data = {}
        if body:
            try:
                data = json.loads(body.decode("utf-8"))
            except Exception as e:
                return self._json_response(400, {"error": "BAD_REQUEST", "message": f"Malformed JSON: {str(e)}"})

        now = data.get("now")

        try:
            res = self.deadline_watcher.simulate_deadline(
                contract_id=contract_id,
                actor=actor,
                now=now
            )
            return self._json_response(200, res)
        except ValueError as e:
            msg = str(e)
            if "not found" in msg.lower():
                return self._json_response(404, {"error": "NOT_FOUND", "message": msg})
            return self._json_response(400, {"error": "BAD_REQUEST", "message": msg})
        except (ForbiddenActionError, UnauthorizedRoleError) as e:
            return self._json_response(403, {"error": "FORBIDDEN", "message": str(e)})
        except PaymentApprovalError as e:
            return self._json_response(403, {
                "error": "PAYMENT_APPROVAL_BLOCKED",
                "message": str(e),
                "verdict": e.verdict.to_dict() if hasattr(e, "verdict") and e.verdict else None
            })
        except StateValidationError as e:
            return self._json_response(400, {"error": "INVALID_STATE", "message": str(e)})
        except PayPalAPIError as e:
            return self._json_response(502, {"error": "PAYPAL_API_ERROR", "message": str(e)})
        except Exception as e:
            return self._json_response(500, {"error": "INTERNAL_SERVER_ERROR", "message": str(e)})

    def _handle_webhook(self, headers: Dict[str, str], body: Optional[bytes]) -> Tuple[int, Dict[str, str], bytes]:
        """
        Handler for POST /api/v1/payments/webhooks.
        Cryptographically verifies incoming PayPal webhook signature headers
        and dispatches verified event processing.
        """
        try:
            res = self.service.process_paypal_webhook(headers=headers, raw_body=body or b"")
            return self._json_response(200, res)
        except WebhookVerificationError as e:
            return self._json_response(401, {"error": "INVALID_WEBHOOK_SIGNATURE", "message": str(e)})
        except ValueError as e:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": str(e)})
        except Exception as e:
            return self._json_response(500, {"error": "INTERNAL_SERVER_ERROR", "message": str(e)})

    def _handle_dispatch_notification(
        self,
        headers: Dict[str, str],
        body: Optional[bytes],
        contract_id: Optional[str] = None
    ) -> Tuple[int, Dict[str, str], bytes]:
        """
        Handler for POST /api/v1/payments/notifications/dispatch (Commit C51).
        Dispatches role-tailored email notifications for contract milestone transitions.
        """
        actor = self._extract_actor(headers)
        if actor is None:
            return self._json_response(
                401,
                {"error": "UNAUTHORIZED", "message": "Authentication required. Supply X-Actor-Id or Authorization header."}
            )

        data = {}
        if body:
            try:
                data = json.loads(body.decode("utf-8"))
            except Exception as e:
                return self._json_response(400, {"error": "BAD_REQUEST", "message": f"Malformed JSON: {str(e)}"})

        cid = contract_id or data.get("contract_id")
        if not cid:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": "Missing required field 'contract_id'."})

        state = data.get("state") or data.get("state_transition") or data.get("status")
        if not state:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": "Missing required field 'state'."})

        contract = self.repository.get_contract(cid)
        if not contract:
            return self._json_response(404, {"error": "NOT_FOUND", "message": f"Contract '{cid}' not found."})

        try:
            assert_can_dispatch_notification(actor, contract)
        except (ForbiddenActionError, UnauthorizedRoleError) as e:
            return self._json_response(403, {"error": "FORBIDDEN", "message": str(e)})

        metadata = data.get("metadata") or {}

        try:
            dispatched = self.notification_service.notify_state_change(
                contract_id=cid,
                new_state=state,
                metadata=metadata,
                actor=actor,
                force=True
            )
            canonical = self.notification_service.normalize_state(state) or state
            return self._json_response(200, {
                "status": "SUCCESS",
                "contract_id": cid,
                "state": canonical,
                "notifications_sent": len(dispatched),
                "dispatched": dispatched
            })
        except ValueError as e:
            return self._json_response(400, {"error": "BAD_REQUEST", "message": str(e)})
        except Exception as e:
            return self._json_response(500, {"error": "INTERNAL_SERVER_ERROR", "message": str(e)})

    def _handle_get_contract_notifications(
        self,
        contract_id: str,
        headers: Dict[str, str]
    ) -> Tuple[int, Dict[str, str], bytes]:
        """
        Handler for GET /api/v1/contracts/{id}/notifications (Commit C51).
        Retrieves notification audit logs for a contract.
        """
        actor = self._extract_actor(headers)
        if actor is None:
            return self._json_response(
                401,
                {"error": "UNAUTHORIZED", "message": "Authentication required. Supply X-Actor-Id or Authorization header."}
            )

        contract = self.repository.get_contract(contract_id)
        if not contract:
            return self._json_response(404, {"error": "NOT_FOUND", "message": f"Contract '{contract_id}' not found."})

        try:
            assert_can_view_notifications(actor, contract)
        except (ForbiddenActionError, UnauthorizedRoleError) as e:
            return self._json_response(403, {"error": "FORBIDDEN", "message": str(e)})

        try:
            notifications = self.notification_service.get_contract_notifications(contract_id, actor=actor)
            return self._json_response(200, {
                "contract_id": contract_id,
                "total_notifications": len(notifications),
                "notifications": notifications
            })
        except Exception as e:
            return self._json_response(500, {"error": "INTERNAL_SERVER_ERROR", "message": str(e)})

    def _json_response(self, status_code: int, data: Dict[str, Any]) -> Tuple[int, Dict[str, str], bytes]:
        body_bytes = json.dumps(data, indent=2).encode("utf-8")
        resp_headers = {
            "Content-Type": "application/json",
            "Content-Length": str(len(body_bytes)),
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Actor-Id",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
        }
        return status_code, resp_headers, body_bytes


def create_payments_app(
    service: Optional[EscrowPaymentService] = None,
    deadline_watcher: Optional[DeadlineWatcherService] = None,
    notification_service: Optional[EmailNotificationService] = None
):
    """
    Creates a standard WSGI application for the Payments API.
    Compatible with gunicorn, uwsgi, or Python wsgiref.
    """
    handler = PaymentsAPIHandler(
        service=service,
        deadline_watcher=deadline_watcher,
        notification_service=notification_service
    )

    def application(environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "/")

        # Options preflight
        if method == "OPTIONS":
            status_str = "204 No Content"
            headers = [
                ("Access-Control-Allow-Origin", "*"),
                ("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Actor-Id"),
                ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
            ]
            start_response(status_str, headers)
            return [b""]

        # Parse headers
        headers: Dict[str, str] = {}
        for key, value in environ.items():
            if key.startswith("HTTP_"):
                header_name = key[5:].replace("_", "-").title()
                headers[header_name] = value
            elif key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                headers[key.replace("_", "-").title()] = value

        # Read body
        try:
            content_length = int(environ.get("CONTENT_LENGTH", 0) or 0)
        except ValueError:
            content_length = 0
        body = environ["wsgi.input"].read(content_length) if content_length > 0 else None

        status_code, resp_headers, resp_bytes = handler.dispatch(
            method=method,
            path=path,
            headers=headers,
            body=body
        )

        status_desc = http.client.responses.get(status_code, "Status")
        status_line = f"{status_code} {status_desc}"
        start_response(status_line, list(resp_headers.items()))
        return [resp_bytes]

    return application

if __name__ == "__main__":
    app = create_payments_app()
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting PactPal Payments API on http://0.0.0.0:{port} ...")
    with make_server("0.0.0.0", port, app) as httpd:
        httpd.serve_forever()

