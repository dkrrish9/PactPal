#!/usr/bin/env python3
"""
PactPal Unified Backend Gateway Server
Port: 8000
Bridges all PactPal subsystems:
  - Contracts & Agreement Reader (/api/v1/contracts)
  - Payments & PayPal Escrow Holds (/api/v1/payments/*, /api/v1/contracts/{id}/hold, /api/v1/contracts/{id}/receipt, etc.)
  - Render Verification Pipeline (/api/v1/verification/*)
  - AI Referee & Negotiated Release (/api/v1/referee/*)
  - AI Price Negotiator (/api/v1/negotiator/*)
  - System Health & Diagnostics (/api/v1/health)
"""

import os
import sys
import json
import re
import uuid
import http.client
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List
from wsgiref.simple_server import make_server

# Dynamic imports for core-api module with hyphenated name
import importlib
repo_mod = importlib.import_module("services.core-api.db.repository")
roles_mod = importlib.import_module("services.core-api.auth.roles")
sm_mod = importlib.import_module("services.core-api.state_machine.engine")

ContractRepository = repo_mod.ContractRepository
User = roles_mod.User
UserRole = roles_mod.UserRole
ContractState = sm_mod.ContractState

from services.payments.service import EscrowPaymentService
from services.payments.api import PaymentsAPIHandler
from services.verification.src.runner import VerificationPipelineRunner
from services.verification.src.models import IntakeRequest
from services.agents.referee.decision_engine import RefereeDecisionEngine
from services.agents.referee.models import RefereeDecision, DecisionOutcome, FeatureDecision
from services.agents.referee.negotiated_release import NegotiatedReleaseEngine, SellerChoice, SettlementOffer
from services.agents.negotiator.price_negotiator import PriceNegotiator
from services.agents.agreement_reader.reader import parse_contract_form, AgreementValidationError

# Endpoint matching regex patterns
HEALTH_REGEX = re.compile(r"^/api/v1/health/?$")
CONTRACTS_REGEX = re.compile(r"^/api/v1/contracts/?$")
CONTRACT_DETAIL_REGEX = re.compile(r"^/api/v1/contracts/([^/]+)/?$")
CONTRACT_SUBMIT_REVIEW_REGEX = re.compile(r"^/api/v1/contracts/([^/]+)/submit-review/?$")
CONTRACT_SIGN_REGEX = re.compile(r"^/api/v1/contracts/([^/]+)/sign/?$")
CONTRACT_FUND_REGEX = re.compile(r"^/api/v1/contracts/([^/]+)/fund/?$")
CONTRACT_MESSAGES_REGEX = re.compile(r"^/api/v1/contracts/([^/]+)/messages/?$")
VERIFICATION_SUBMIT_REGEX = re.compile(r"^/api/v1/verification/submit/?$")
VERIFICATION_REPORT_REGEX = re.compile(r"^/api/v1/verification/reports/([^/]+)/?$")
REFEREE_DECISION_REGEX = re.compile(r"^/api/v1/referee/decisions/([^/]+)/?$")
REFEREE_NEGOTIATE_REGEX = re.compile(r"^/api/v1/referee/negotiate/?$")
PRICE_NEGOTIATOR_REGEX = re.compile(r"^/api/v1/negotiator/change-request/?$")

# Routes handled directly by PaymentsAPIHandler
PAYMENTS_ROUTE_PREFIXES = (
    "/api/v1/payments/",
)
PAYMENTS_EXPLICIT_SUFFIXES = (
    "/hold",
    "/settlement-summary",
    "/receipt",
    "/split-preview",
    "/payment-approval",
    "/notifications",
    "/notifications/dispatch",
    "/simulate-deadline",
    "/reauthorize",
)

def is_payments_endpoint(path: str) -> bool:
    clean = path.split("?")[0]
    if any(clean.startswith(prefix) for prefix in PAYMENTS_ROUTE_PREFIXES):
        return True
    if clean.startswith("/api/v1/contracts/"):
        for suffix in PAYMENTS_EXPLICIT_SUFFIXES:
            if clean.endswith(suffix):
                return True
    return False

class UnifiedGateway:
    """Unified HTTP Request Dispatcher for PactPal."""

    def __init__(self, db_path: str = "pactpal.db", seed_demo: bool = True):
        self.repository = ContractRepository(db_path=db_path, seed_demo=seed_demo)
        self.payment_service = EscrowPaymentService(repository=self.repository)
        self.payments_handler = PaymentsAPIHandler(service=self.payment_service)
        self.verification_runner = VerificationPipelineRunner()
        self.referee_engine = RefereeDecisionEngine()
        self.negotiated_release = NegotiatedReleaseEngine()
        self.price_negotiator = PriceNegotiator()

    def _extract_actor(self, headers: Dict[str, str], default_role: UserRole = UserRole.BUYER) -> User:
        """Extracts actor from headers or provides a default user context for demo ease."""
        norm_headers = {k.lower(): v for k, v in headers.items()}
        actor_id = norm_headers.get("x-actor-id")
        if not actor_id:
            auth = norm_headers.get("authorization", "")
            if auth.startswith("Bearer "):
                actor_id = auth[7:].strip()

        if actor_id:
            user = self.repository.get_user(actor_id)
            if user:
                return user
            if actor_id == "AI_REFEREE":
                return User(id="AI_REFEREE", name="AI Referee", email="referee@pactpal.internal", role=UserRole.ADMIN)

        # Fallback to demo default based on role
        if default_role == UserRole.SELLER:
            return self.repository.get_user("usr_seller_01") or User(
                id="usr_seller_01", name="Bob Developer", email="bob.dev@example.com", role=UserRole.SELLER
            )
        elif default_role == UserRole.ADMIN:
            return self.repository.get_user("usr_admin_01") or User(
                id="usr_admin_01", name="System Admin", email="admin@pactpal.dev", role=UserRole.ADMIN
            )
        else:
            return self.repository.get_user("usr_buyer_01") or User(
                id="usr_buyer_01", name="Alice Buyer", email="alice.buyer@example.com", role=UserRole.BUYER
            )

    def _json_response(self, status: int, data: Any) -> Tuple[int, Dict[str, str], bytes]:
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Actor-Id, Idempotency-Key",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        }
        body = json.dumps(data, indent=2).encode("utf-8")
        return status, headers, body

    def dispatch(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        body: Optional[bytes] = None
    ) -> Tuple[int, Dict[str, str], bytes]:
        method = method.upper()
        clean_path = path.split("?")[0]
        query_string = path.split("?")[1] if "?" in path else ""

        # 0. CORS preflight
        if method == "OPTIONS":
            return 204, {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Actor-Id, Idempotency-Key",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            }, b""

        # 1. Forward directly to payments API handler if matched
        if is_payments_endpoint(clean_path):
            # Inject default demo actor if not provided to allow smooth frontend preview
            norm_headers = {k.lower(): v for k, v in headers.items()}
            if not norm_headers.get("x-actor-id") and not norm_headers.get("authorization"):
                headers["X-Actor-Id"] = "usr_buyer_01"

            status, resp_headers, resp_bytes = self.payments_handler.dispatch(
                method=method,
                path=path,
                headers=headers,
                body=body
            )
            # Ensure CORS headers are injected
            resp_headers["Access-Control-Allow-Origin"] = "*"
            resp_headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Actor-Id, Idempotency-Key"
            resp_headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            return status, resp_headers, resp_bytes

        # Parse request JSON payload safely
        payload = {}
        if body and len(body) > 0:
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                return self._json_response(400, {"error": "INVALID_JSON", "message": "Malformed JSON in request body."})

        # 2. GET /api/v1/health
        if HEALTH_REGEX.match(clean_path) and method == "GET":
            contracts_count = len(self.repository.get_contracts_by_status(None))
            return self._json_response(200, {
                "status": "healthy",
                "service": "pactpal-unified-gateway",
                "version": "1.0.0",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "contracts_count": contracts_count,
                "subsystems": {
                    "core_api": "active",
                    "payments": "active",
                    "verification": "active",
                    "referee": "active",
                    "negotiator": "active"
                }
            })

        # 3. GET /api/v1/contracts
        if CONTRACTS_REGEX.match(clean_path) and method == "GET":
            statuses = None
            if "status=" in query_string:
                for param in query_string.split("&"):
                    if param.startswith("status="):
                        statuses = [s.strip() for s in param.replace("status=", "").split(",") if s.strip()]
            contracts = self.repository.get_contracts_by_status(statuses)
            return self._json_response(200, {
                "data": contracts,
                "total": len(contracts)
            })

        # 4. POST /api/v1/contracts
        if CONTRACTS_REGEX.match(clean_path) and method == "POST":
            actor = self._extract_actor(headers, default_role=UserRole.BUYER)
            title = payload.get("title")
            description = payload.get("description", "")
            total_amount = float(payload.get("total_amount", 0.0))
            deadline = payload.get("deadline")
            seller_id = payload.get("seller_id", "usr_seller_01")
            figma_url = payload.get("figma_url")
            repo_url = payload.get("repo_url")
            features = payload.get("features", [])

            if not title or total_amount <= 0 or not deadline:
                return self._json_response(400, {
                    "error": "VALIDATION_FAILED",
                    "message": "Title, total_amount > 0, and deadline are required."
                })

            try:
                # Create contract
                created = self.repository.create_contract(
                    buyer=actor,
                    seller_id=seller_id,
                    title=title,
                    description=description,
                    total_amount=total_amount,
                    deadline=deadline,
                    figma_url=figma_url,
                    repo_url=repo_url
                )
                contract_id = created["id"]

                # Add features
                for idx, feat in enumerate(features):
                    f_title = feat.get("title", f"Feature {idx+1}")
                    f_test = feat.get("acceptance_test", "Default acceptance test verification.")
                    f_weight = float(feat.get("price_weight", 100.0 / max(1, len(features))))
                    f_amount = float(feat.get("allocated_amount", round(total_amount * (f_weight / 100.0), 2)))
                    self.repository.add_feature(
                        contract_id=contract_id,
                        title=f_title,
                        acceptance_test=f_test,
                        price_weight=f_weight,
                        allocated_amount=f_amount,
                        sort_order=idx + 1
                    )

                fresh = self.repository.get_contract(contract_id)
                return self._json_response(201, fresh)
            except Exception as e:
                return self._json_response(500, {"error": "INTERNAL_ERROR", "message": str(e)})

        # 5. GET /api/v1/contracts/{id}
        match_contract = CONTRACT_DETAIL_REGEX.match(clean_path)
        if match_contract and method == "GET":
            contract_id = match_contract.group(1)
            contract = self.repository.get_contract(contract_id)
            if not contract:
                return self._json_response(404, {"error": "NOT_FOUND", "message": f"Contract '{contract_id}' not found."})
            return self._json_response(200, contract)

        # 6. POST /api/v1/contracts/{id}/submit-review
        match_review = CONTRACT_SUBMIT_REVIEW_REGEX.match(clean_path)
        if match_review and method == "POST":
            contract_id = match_review.group(1)
            actor = self._extract_actor(headers, default_role=UserRole.BUYER)
            try:
                updated = self.repository.transition_contract(
                    contract_id=contract_id,
                    actor=actor,
                    target_state=ContractState.REVIEW,
                    metadata=payload
                )
                return self._json_response(200, updated)
            except Exception as e:
                return self._json_response(400, {"error": "TRANSITION_FAILED", "message": str(e)})

        # 7. POST /api/v1/contracts/{id}/sign
        match_sign = CONTRACT_SIGN_REGEX.match(clean_path)
        if match_sign and method == "POST":
            contract_id = match_sign.group(1)
            role_hint = payload.get("role", "SELLER").upper()
            default_role = UserRole.SELLER if role_hint == "SELLER" else UserRole.BUYER
            actor = self._extract_actor(headers, default_role=default_role)

            try:
                # 1. Record confirmation
                confirmed = self.repository.confirm_checklist(contract_id, actor)
                # 2. Check if both signed, transition to SIGNED
                if confirmed.get("buyer_confirmed_at") and confirmed.get("seller_confirmed_at"):
                    if confirmed.get("status") in (ContractState.REVIEW.value, ContractState.DRAFT.value):
                        confirmed = self.repository.transition_contract(
                            contract_id=contract_id,
                            actor=actor,
                            target_state=ContractState.SIGNED
                        )
                return self._json_response(200, confirmed)
            except Exception as e:
                return self._json_response(400, {"error": "SIGN_FAILED", "message": str(e)})

        # 8. POST /api/v1/contracts/{id}/fund
        match_fund = CONTRACT_FUND_REGEX.match(clean_path)
        if match_fund and method == "POST":
            contract_id = match_fund.group(1)
            actor = self._extract_actor(headers, default_role=UserRole.BUYER)
            try:
                order_id = payload.get("paypal_order_id")
                auth_id = payload.get("paypal_auth_id")
                if order_id or auth_id:
                    cursor = self.repository.conn.cursor()
                    if order_id:
                        cursor.execute("UPDATE contracts SET paypal_order_id = ? WHERE id = ?", (order_id, contract_id))
                    if auth_id:
                        cursor.execute("UPDATE contracts SET paypal_auth_id = ? WHERE id = ?", (auth_id, contract_id))
                    self.repository.conn.commit()

                updated = self.repository.transition_contract(
                    contract_id=contract_id,
                    actor=actor,
                    target_state=ContractState.FUNDED,
                    metadata=payload
                )
                return self._json_response(200, updated)
            except Exception as e:
                return self._json_response(400, {"error": "FUNDING_FAILED", "message": str(e)})

        # 9. GET & POST /api/v1/contracts/{id}/messages
        match_messages = CONTRACT_MESSAGES_REGEX.match(clean_path)
        if match_messages:
            contract_id = match_messages.group(1)
            if method == "GET":
                cursor = self.repository.conn.cursor()
                cursor.execute("SELECT * FROM messages WHERE contract_id = ? ORDER BY sent_at ASC", (contract_id,))
                rows = [dict(r) for r in cursor.fetchall()]
                return self._json_response(200, {"data": rows, "total": len(rows)})
            elif method == "POST":
                actor = self._extract_actor(headers)
                content = payload.get("content", "").strip()
                sender_type = payload.get("sender_type", actor.role.value if actor else "BUYER")
                if not content:
                    return self._json_response(400, {"error": "EMPTY_MESSAGE", "message": "Message content cannot be empty."})

                msg_id = str(uuid.uuid4())
                timestamp = datetime.now(timezone.utc).isoformat()
                meta_json = json.dumps(payload.get("metadata", {}))

                cursor = self.repository.conn.cursor()
                cursor.execute("""
                    INSERT INTO messages (id, contract_id, sender_id, sender_type, content, metadata, sent_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (msg_id, contract_id, actor.id if actor else None, sender_type, content, meta_json, timestamp))
                self.repository.conn.commit()

                return self._json_response(201, {
                    "id": msg_id,
                    "contract_id": contract_id,
                    "sender_id": actor.id if actor else None,
                    "sender_type": sender_type,
                    "content": content,
                    "metadata": payload.get("metadata", {}),
                    "sent_at": timestamp
                })

        # 10. POST /api/v1/verification/submit
        if VERIFICATION_SUBMIT_REGEX.match(clean_path) and method == "POST":
            contract_id = payload.get("contract_id")
            repo_url = payload.get("repo_url", "")
            commit_sha = payload.get("commit_sha", "main-head")
            build_notes = payload.get("build_notes", "")

            contract = self.repository.get_contract(contract_id)
            if not contract:
                return self._json_response(404, {"error": "NOT_FOUND", "message": f"Contract '{contract_id}' not found."})

            actor = self._extract_actor(headers, default_role=UserRole.SELLER)

            try:
                # 1. Update contract status to SUBMITTED if in IN_PROGRESS or FUNDED
                current_state = ContractState(contract["status"])
                if current_state in (ContractState.FUNDED, ContractState.IN_PROGRESS):
                    self.repository.transition_contract(
                        contract_id=contract_id,
                        actor=actor,
                        target_state=ContractState.SUBMITTED,
                        metadata={"repo_url": repo_url, "commit_sha": commit_sha}
                    )

                # 2. Record submission in DB
                submission_id = str(uuid.uuid4())
                timestamp = datetime.now(timezone.utc).isoformat()
                cursor = self.repository.conn.cursor()
                cursor.execute("SELECT COUNT(*) as count FROM submissions WHERE contract_id = ?", (contract_id,))
                count_row = cursor.fetchone()
                submission_num = (count_row["count"] if count_row else 0) + 1

                cursor.execute("""
                    INSERT INTO submissions (id, contract_id, seller_id, repo_url, commit_sha, build_notes, submission_number, is_late, submitted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
                """, (submission_id, contract_id, actor.id, repo_url, commit_sha, build_notes, submission_num, timestamp))

                # 3. Transition to VERIFYING
                self.repository.transition_contract(
                    contract_id=contract_id,
                    actor=actor,
                    target_state=ContractState.VERIFYING
                )

                # 4. Execute verification runner
                intake_req = IntakeRequest(
                    contract_id=contract_id,
                    seller_id=actor.id,
                    repo_url=repo_url,
                    commit_sha=commit_sha,
                    build_notes=build_notes
                )
                report_dict = self.verification_runner.handle_contract_submission(
                    request=intake_req,
                    existing_submissions=[],
                    features=contract.get("features", []),
                    execute_verification=True
                )

                # 5. Persist report to DB
                rep_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT OR REPLACE INTO verification_reports (
                        id, submission_id, contract_id, render_job_id, build_succeeded,
                        build_logs, test_suite_results, cheat_scan_findings,
                        visual_diff_summary, per_feature_results, overall_score, completed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rep_id, submission_id, contract_id,
                    report_dict.get("render_job_id", "job_local"),
                    1 if report_dict.get("build_succeeded") else 0,
                    report_dict.get("build_logs", ""),
                    json.dumps(report_dict.get("test_suite_results", {})),
                    json.dumps(report_dict.get("cheat_scan_findings", [])),
                    json.dumps(report_dict.get("visual_diff_summary", {})),
                    json.dumps(report_dict.get("per_feature_results", {})),
                    float(report_dict.get("overall_score", 1.0)),
                    timestamp
                ))
                self.repository.conn.commit()

                # 6. Transition to DECISION
                self.repository.transition_contract(
                    contract_id=contract_id,
                    actor=actor,
                    target_state=ContractState.DECISION
                )

                return self._json_response(200, {
                    "submission_id": submission_id,
                    "report_id": rep_id,
                    "contract_id": contract_id,
                    "status": "DECISION",
                    "report": report_dict
                })
            except Exception as e:
                return self._json_response(500, {"error": "VERIFICATION_ERROR", "message": str(e)})

        # 11. GET /api/v1/verification/reports/{contract_id}
        match_rep = VERIFICATION_REPORT_REGEX.match(clean_path)
        if match_rep and method == "GET":
            contract_id = match_rep.group(1)
            cursor = self.repository.conn.cursor()
            cursor.execute("""
                SELECT * FROM verification_reports WHERE contract_id = ? ORDER BY completed_at DESC LIMIT 1
            """, (contract_id,))
            row = cursor.fetchone()
            if not row:
                return self._json_response(404, {"error": "NO_REPORT", "message": f"No verification report found for '{contract_id}'."})

            rep = dict(row)
            for k in ("test_suite_results", "cheat_scan_findings", "visual_diff_summary", "per_feature_results"):
                try:
                    rep[k] = json.loads(rep[k])
                except Exception:
                    pass
            return self._json_response(200, rep)

        # 12. GET /api/v1/referee/decisions/{contract_id}
        match_decision = REFEREE_DECISION_REGEX.match(clean_path)
        if match_decision and method == "GET":
            contract_id = match_decision.group(1)
            contract = self.repository.get_contract(contract_id)
            if not contract:
                return self._json_response(404, {"error": "NOT_FOUND", "message": f"Contract '{contract_id}' not found."})

            cursor = self.repository.conn.cursor()
            cursor.execute("SELECT * FROM verification_reports WHERE contract_id = ? ORDER BY completed_at DESC LIMIT 1", (contract_id,))
            row = cursor.fetchone()
            report_data = dict(row) if row else {
                "build_succeeded": True,
                "per_feature_results": {f["id"]: {"status": "PASSED"} for f in contract.get("features", [])}
            }
            for k in ("test_suite_results", "cheat_scan_findings", "visual_diff_summary", "per_feature_results"):
                if isinstance(report_data.get(k), str):
                    try:
                        report_data[k] = json.loads(report_data[k])
                    except Exception:
                        pass

            decision = self.referee_engine.evaluate(contract, report_data)
            return self._json_response(200, decision.to_dict())

        # 13. POST /api/v1/referee/negotiate
        if REFEREE_NEGOTIATE_REGEX.match(clean_path) and method == "POST":
            contract_id = payload.get("contract_id", "pct_099e77")
            action = payload.get("action", "offer")  # "offer" | "resolve"
            contract = self.repository.get_contract(contract_id)
            if not contract:
                return self._json_response(404, {"error": "NOT_FOUND", "message": f"Contract '{contract_id}' not found."})

            if action == "resolve":
                choice_str = payload.get("choice", "ACCEPT_PARTIAL_PAYOUT")
                actor = self._extract_actor(headers, default_role=UserRole.SELLER)
                choice = SellerChoice(choice_str)
                passed_weight = float(payload.get("passed_weight", 80.0))
                total_amt = float(contract.get("total_amount", 1500.0))
                passed_amt = round(total_amt * (passed_weight / 100.0), 2)
                refund_amt = round(total_amt - passed_amt, 2)
                offer = SettlementOffer(
                    contract_id=contract_id,
                    decision_id=payload.get("decision_id", "DEC-DEMO"),
                    total_amount=total_amt,
                    currency=contract.get("currency", "USD"),
                    passed_amount=passed_amt,
                    refund_amount=refund_amt,
                    passed_weight=passed_weight,
                    failed_weight=100.0 - passed_weight,
                    failed_features=[],
                    offer_id=payload.get("offer_id", "OFFER-DEMO")
                )
                resolution = self.negotiated_release.process_seller_choice(
                    offer=offer,
                    choice=choice,
                    seller_id=actor.id,
                    contract=contract,
                    note=payload.get("note", "")
                )
                return self._json_response(200, resolution.to_dict())
            else:
                passed_weight = float(payload.get("passed_weight", 80.0))
                total_amt = float(contract.get("total_amount", 1500.0))
                passed_amt = round(total_amt * (passed_weight / 100.0), 2)
                refund_amt = round(total_amt - passed_amt, 2)
                currency = contract.get("currency", "USD")

                decision = RefereeDecision(
                    contract_id=contract_id,
                    outcome=DecisionOutcome.PARTIAL_RELEASE,
                    rule_triggered="RULE_PARTIAL_ACCEPTANCE_WITH_COMPROMISE",
                    total_amount=total_amt,
                    currency=currency,
                    passed_amount=passed_amt,
                    refund_amount=refund_amt,
                    passed_weight=passed_weight,
                    failed_weight=100.0 - passed_weight,
                    feature_decisions=[]
                )
                offer = self.negotiated_release.generate_offer(
                    decision=decision,
                    contract=contract,
                    fix_window_hours=int(payload.get("fix_window_hours", 48))
                )
                return self._json_response(200, offer.to_dict())

        # 14. POST /api/v1/negotiator/change-request
        if PRICE_NEGOTIATOR_REGEX.match(clean_path) and method == "POST":
            contract_id = payload.get("contract_id", "pct_099e77")
            contract = self.repository.get_contract(contract_id) or {
                "id": contract_id,
                "title": "Digital Deliverable",
                "total_amount": 1500.0,
                "features": []
            }
            description = payload.get("description", "")
            proposed_by_id = payload.get("proposed_by_id", "usr_buyer_01")
            user_proposed_price = payload.get("requested_price") or payload.get("user_proposed_price")
            if user_proposed_price is not None:
                user_proposed_price = float(user_proposed_price)
            user_proposed_hours = payload.get("user_proposed_hours")
            if user_proposed_hours is not None:
                user_proposed_hours = int(user_proposed_hours)

            proposal = self.price_negotiator.evaluate_change_request(
                contract=contract,
                description=description,
                proposed_by_id=proposed_by_id,
                user_proposed_price=user_proposed_price,
                user_proposed_hours=user_proposed_hours
            )
            return self._json_response(200, proposal.to_dict())

        # Default 404 for unhandled paths
        return self._json_response(404, {
            "error": "NOT_FOUND",
            "message": f"Endpoint '{clean_path}' not recognized by PactPal Unified Gateway."
        })

def create_gateway_app(db_path: str = "pactpal.db", seed_demo: bool = True):
    gateway = UnifiedGateway(db_path=db_path, seed_demo=seed_demo)

    def application(environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "/")

        headers: Dict[str, str] = {}
        for key, value in environ.items():
            if key.startswith("HTTP_"):
                header_name = key[5:].replace("_", "-").title()
                headers[header_name] = value
            elif key in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                headers[key.replace("_", "-").title()] = value

        try:
            content_length = int(environ.get("CONTENT_LENGTH", 0) or 0)
        except ValueError:
            content_length = 0
        body = environ["wsgi.input"].read(content_length) if content_length > 0 else None

        status_code, resp_headers, resp_bytes = gateway.dispatch(
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
    port = int(os.environ.get("PORT", 8000))
    app = create_gateway_app()
    print(f"Starting PactPal Unified Backend Gateway on http://0.0.0.0:{port} ...")
    with make_server("0.0.0.0", port, app) as httpd:
        httpd.serve_forever()
