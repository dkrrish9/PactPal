#!/usr/bin/env python3
"""
PactPal FastAPI Server
Port: 8000
Interactive Swagger Docs: http://localhost:8000/docs
Alternative Redoc: http://localhost:8000/redoc
"""

import os
import sys
import json
import uuid
import importlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response, HTTPException, status, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Dynamic imports for core-api module with hyphenated name
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

app = FastAPI(
    title="PactPal AI Escrow Referee API",
    description="Zero-Trust Multimodal Escrow Referee for Digital Freelancing with PayPal rails, isolated Render verification, and AI dispute arbitration.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Subsystem Initializations
DB_PATH = os.environ.get("DB_PATH", "pactpal.db")
repository = ContractRepository(db_path=DB_PATH, seed_demo=True)
payment_service = EscrowPaymentService(repository=repository)
payments_handler = PaymentsAPIHandler(service=payment_service)
verification_runner = VerificationPipelineRunner()
referee_engine = RefereeDecisionEngine()
negotiated_release = NegotiatedReleaseEngine()
price_negotiator = PriceNegotiator()

# --- Pydantic Request Models ---
class FeatureInput(BaseModel):
    title: str
    acceptance_test: str
    price_weight: float = 0.0
    allocated_amount: float = 0.0

class CreateContractRequest(BaseModel):
    title: str
    description: str = ""
    total_amount: float
    deadline: str
    currency: str = "USD"
    seller_id: str = "usr_seller_01"
    figma_url: Optional[str] = None
    repo_url: Optional[str] = None
    features: List[FeatureInput] = []

class SignContractRequest(BaseModel):
    role: str = "SELLER"

class FundContractRequest(BaseModel):
    paypal_order_id: Optional[str] = None
    paypal_auth_id: Optional[str] = None

class SendMessageRequest(BaseModel):
    content: str
    sender_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class VerificationSubmitRequest(BaseModel):
    contract_id: str
    repo_url: str
    commit_sha: Optional[str] = "main-head"
    build_notes: Optional[str] = ""

class NegotiateRequest(BaseModel):
    contract_id: str = "pct_099e77"
    action: str = "offer"  # "offer" | "resolve"
    passed_weight: Optional[float] = 80.0
    choice: Optional[str] = "ACCEPT_PARTIAL_PAYOUT"
    offer_id: Optional[str] = "OFFER-DEMO"
    decision_id: Optional[str] = "DEC-DEMO"
    note: Optional[str] = ""
    fix_window_hours: Optional[int] = 48
    failed_features: Optional[List[Dict[str, Any]]] = []

class ChangeRequestInput(BaseModel):
    description: str
    contract_id: Optional[str] = "pct_099e77"
    requested_price: Optional[float] = None
    user_proposed_hours: Optional[int] = None
    currency: Optional[str] = "USD"
    proposed_by_id: Optional[str] = "usr_buyer_01"

def extract_actor(x_actor_id: Optional[str] = None, default_role: UserRole = UserRole.BUYER) -> User:
    if x_actor_id:
        user = repository.get_user(x_actor_id)
        if user:
            return user
        if x_actor_id == "AI_REFEREE":
            return User(id="AI_REFEREE", name="AI Referee", email="referee@pactpal.internal", role=UserRole.ADMIN)

    if default_role == UserRole.SELLER:
        return repository.get_user("usr_seller_01") or User(
            id="usr_seller_01", name="Bob Developer", email="bob.dev@example.com", role=UserRole.SELLER
        )
    return repository.get_user("usr_buyer_01") or User(
        id="usr_buyer_01", name="Alice Buyer", email="alice.buyer@example.com", role=UserRole.BUYER
    )

# --- Routes ---

@app.get("/api/v1/health", summary="System Health & Diagnostics")
def health():
    return {
        "status": "healthy",
        "service": "pactpal-fastapi",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "connected",
        "contracts_count": len(repository.get_contracts_by_status(None)),
        "subsystems": {
            "core_api": "active",
            "payments": "active",
            "verification": "active",
            "referee": "active",
            "negotiator": "active"
        }
    }

@app.get("/api/v1/contracts", summary="List All Contracts")
def list_contracts(status: Optional[str] = Query(None)):
    statuses = [s.strip() for s in status.split(",") if s.strip()] if status else None
    contracts = repository.get_contracts_by_status(statuses)
    return {"data": contracts, "total": len(contracts)}

@app.post("/api/v1/contracts", status_code=status.HTTP_201_CREATED, summary="Create a Contract Draft")
def create_contract(payload: CreateContractRequest, x_actor_id: Optional[str] = Header(None)):
    actor = extract_actor(x_actor_id, default_role=UserRole.BUYER)
    if not payload.title or payload.total_amount <= 0 or not payload.deadline:
        raise HTTPException(status_code=400, detail="Title, total_amount > 0, and deadline are required.")

    created = repository.create_contract(
        buyer=actor,
        seller_id=payload.seller_id,
        title=payload.title,
        description=payload.description,
        total_amount=payload.total_amount,
        deadline=payload.deadline,
        figma_url=payload.figma_url,
        repo_url=payload.repo_url
    )
    cid = created["id"]

    for idx, feat in enumerate(payload.features):
        repository.add_feature(
            contract_id=cid,
            title=feat.title,
            acceptance_test=feat.acceptance_test,
            price_weight=feat.price_weight,
            allocated_amount=feat.allocated_amount,
            sort_order=idx + 1
        )

    return repository.get_contract(cid)

@app.get("/api/v1/contracts/{contract_id}", summary="Get Contract Detail")
def get_contract(contract_id: str):
    contract = repository.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail=f"Contract '{contract_id}' not found.")
    return contract

@app.post("/api/v1/contracts/{contract_id}/submit-review", summary="Submit Contract for Seller Review")
def submit_review(contract_id: str, x_actor_id: Optional[str] = Header(None)):
    actor = extract_actor(x_actor_id, default_role=UserRole.BUYER)
    try:
        return repository.transition_contract(
            contract_id=contract_id,
            actor=actor,
            target_state=ContractState.REVIEW
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/contracts/{contract_id}/sign", summary="Sign / Confirm Checklist")
def sign_contract(contract_id: str, payload: SignContractRequest, x_actor_id: Optional[str] = Header(None)):
    default_role = UserRole.SELLER if payload.role.upper() == "SELLER" else UserRole.BUYER
    actor = extract_actor(x_actor_id, default_role=default_role)
    try:
        confirmed = repository.confirm_checklist(contract_id, actor)
        if confirmed.get("buyer_confirmed_at") and confirmed.get("seller_confirmed_at"):
            if confirmed.get("status") in (ContractState.REVIEW.value, ContractState.DRAFT.value):
                confirmed = repository.transition_contract(
                    contract_id=contract_id,
                    actor=actor,
                    target_state=ContractState.SIGNED
                )
        return confirmed
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/contracts/{contract_id}/fund", summary="Mark Contract Funded")
def fund_contract(contract_id: str, payload: FundContractRequest, x_actor_id: Optional[str] = Header(None)):
    actor = extract_actor(x_actor_id, default_role=UserRole.BUYER)
    try:
        cursor = repository.conn.cursor()
        if payload.paypal_order_id:
            cursor.execute("UPDATE contracts SET paypal_order_id = ? WHERE id = ?", (payload.paypal_order_id, contract_id))
        if payload.paypal_auth_id:
            cursor.execute("UPDATE contracts SET paypal_auth_id = ? WHERE id = ?", (payload.paypal_auth_id, contract_id))
        repository.conn.commit()

        return repository.transition_contract(
            contract_id=contract_id,
            actor=actor,
            target_state=ContractState.FUNDED,
            metadata=payload.model_dump()
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/contracts/{contract_id}/messages", summary="Get Chat Messages")
def get_messages(contract_id: str):
    cursor = repository.conn.cursor()
    cursor.execute("SELECT * FROM messages WHERE contract_id = ? ORDER BY sent_at ASC", (contract_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    return {"data": rows, "total": len(rows)}

@app.post("/api/v1/contracts/{contract_id}/messages", status_code=status.HTTP_201_CREATED, summary="Send Chat Message")
def send_message(contract_id: str, payload: SendMessageRequest, x_actor_id: Optional[str] = Header(None)):
    actor = extract_actor(x_actor_id, default_role=UserRole.BUYER)
    msg_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    sender_type = payload.sender_type or actor.role.value

    cursor = repository.conn.cursor()
    cursor.execute("""
        INSERT INTO messages (id, contract_id, sender_id, sender_type, content, metadata, sent_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (msg_id, contract_id, actor.id, sender_type, payload.content, json.dumps(payload.metadata), timestamp))
    repository.conn.commit()

    return {
        "id": msg_id,
        "contract_id": contract_id,
        "sender_id": actor.id,
        "sender_type": sender_type,
        "content": payload.content,
        "metadata": payload.metadata,
        "sent_at": timestamp
    }

@app.post("/api/v1/verification/submit", summary="Submit Deliverable for Automated Verification")
def submit_verification(payload: VerificationSubmitRequest, x_actor_id: Optional[str] = Header(None)):
    contract = repository.get_contract(payload.contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail=f"Contract '{payload.contract_id}' not found.")

    actor = extract_actor(x_actor_id, default_role=UserRole.SELLER)

    # 1. Update contract to SUBMITTED
    current_state = ContractState(contract["status"])
    if current_state in (ContractState.FUNDED, ContractState.IN_PROGRESS):
        repository.transition_contract(
            contract_id=payload.contract_id,
            actor=actor,
            target_state=ContractState.SUBMITTED
        )

    # 2. Record submission
    submission_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    cursor = repository.conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM submissions WHERE contract_id = ?", (payload.contract_id,))
    count_row = cursor.fetchone()
    submission_num = (count_row["count"] if count_row else 0) + 1

    cursor.execute("""
        INSERT INTO submissions (id, contract_id, seller_id, repo_url, commit_sha, build_notes, submission_number, is_late, submitted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
    """, (submission_id, payload.contract_id, actor.id, payload.repo_url, payload.commit_sha, payload.build_notes, submission_num, timestamp))

    # 3. Transition to VERIFYING
    repository.transition_contract(
        contract_id=payload.contract_id,
        actor=actor,
        target_state=ContractState.VERIFYING
    )

    # 4. Verification runner execution
    intake_req = IntakeRequest(
        contract_id=payload.contract_id,
        seller_id=actor.id,
        repo_url=payload.repo_url,
        commit_sha=payload.commit_sha or "head",
        build_notes=payload.build_notes or ""
    )
    report_dict = verification_runner.handle_contract_submission(
        request=intake_req,
        existing_submissions=[],
        features=contract.get("features", []),
        execute_verification=True
    )

    # 5. Persist report
    rep_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT OR REPLACE INTO verification_reports (
            id, submission_id, contract_id, render_job_id, build_succeeded,
            build_logs, test_suite_results, cheat_scan_findings,
            visual_diff_summary, per_feature_results, overall_score, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        rep_id, submission_id, payload.contract_id,
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
    repository.conn.commit()

    # 6. Transition to DECISION
    repository.transition_contract(
        contract_id=payload.contract_id,
        actor=actor,
        target_state=ContractState.DECISION
    )

    return {
        "submission_id": submission_id,
        "report_id": rep_id,
        "contract_id": payload.contract_id,
        "status": "DECISION",
        "report": report_dict
    }

@app.get("/api/v1/verification/reports/{contract_id}", summary="Get Latest Verification Report")
def get_verification_report(contract_id: str):
    cursor = repository.conn.cursor()
    cursor.execute("SELECT * FROM verification_reports WHERE contract_id = ? ORDER BY completed_at DESC LIMIT 1", (contract_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"No verification report found for '{contract_id}'.")

    rep = dict(row)
    for k in ("test_suite_results", "cheat_scan_findings", "visual_diff_summary", "per_feature_results"):
        try:
            rep[k] = json.loads(rep[k])
        except Exception:
            pass
    return rep

@app.get("/api/v1/referee/decisions/{contract_id}", summary="Get AI Referee Decision")
def get_referee_decision(contract_id: str):
    contract = repository.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail=f"Contract '{contract_id}' not found.")

    cursor = repository.conn.cursor()
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

    decision = referee_engine.evaluate(contract, report_data)
    return decision.to_dict()

@app.post("/api/v1/referee/negotiate", summary="AI Referee Negotiated Release (80% Compromise)")
def negotiate(payload: NegotiateRequest, x_actor_id: Optional[str] = Header(None)):
    contract = repository.get_contract(payload.contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail=f"Contract '{payload.contract_id}' not found.")

    if payload.action == "resolve":
        actor = extract_actor(x_actor_id, default_role=UserRole.SELLER)
        choice = SellerChoice(payload.choice or "ACCEPT_PARTIAL_PAYOUT")
        passed_weight = payload.passed_weight or 80.0
        total_amt = float(contract.get("total_amount", 1500.0))
        passed_amt = round(total_amt * (passed_weight / 100.0), 2)
        refund_amt = round(total_amt - passed_amt, 2)
        offer = SettlementOffer(
            contract_id=payload.contract_id,
            decision_id=payload.decision_id or "DEC-DEMO",
            total_amount=total_amt,
            currency=contract.get("currency", "USD"),
            passed_amount=passed_amt,
            refund_amount=refund_amt,
            passed_weight=passed_weight,
            failed_weight=100.0 - passed_weight,
            failed_features=[],
            offer_id=payload.offer_id or "OFFER-DEMO"
        )
        resolution = negotiated_release.process_seller_choice(
            offer=offer,
            choice=choice,
            seller_id=actor.id,
            contract=contract,
            note=payload.note or ""
        )
        return resolution.to_dict()
    else:
        passed_weight = payload.passed_weight or 80.0
        total_amt = float(contract.get("total_amount", 1500.0))
        passed_amt = round(total_amt * (passed_weight / 100.0), 2)
        refund_amt = round(total_amt - passed_amt, 2)
        currency = contract.get("currency", "USD")

        decision = RefereeDecision(
            contract_id=payload.contract_id,
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
        offer = negotiated_release.generate_offer(
            decision=decision,
            contract=contract,
            fix_window_hours=payload.fix_window_hours or 48
        )
        return offer.to_dict()

@app.post("/api/v1/negotiator/change-request", summary="AI Price Negotiator Scope Assessment")
def change_request(payload: ChangeRequestInput):
    contract = repository.get_contract(payload.contract_id or "pct_099e77") or {
        "id": payload.contract_id or "pct_099e77",
        "title": "Digital Deliverable",
        "total_amount": 1500.0,
        "features": []
    }
    proposal = price_negotiator.evaluate_change_request(
        contract=contract,
        description=payload.description,
        proposed_by_id=payload.proposed_by_id or "usr_buyer_01",
        user_proposed_price=payload.requested_price,
        user_proposed_hours=payload.user_proposed_hours
    )
    return proposal.to_dict()

# --- Payments Dedicated Gateway Handlers ---
async def _forward_to_payments(request: Request) -> Response:
    method = request.method
    path = request.url.path
    query = request.url.query
    full_path = f"{path}?{query}" if query else path

    headers = dict(request.headers)
    if "x-actor-id" not in {k.lower() for k in headers}:
        headers["X-Actor-Id"] = "usr_buyer_01"

    body = await request.body()
    status_code, resp_headers, resp_bytes = payments_handler.dispatch(
        method=method,
        path=full_path,
        headers=headers,
        body=body if len(body) > 0 else None
    )

    # Filter out manual content-length so Starlette/Uvicorn computes the exact byte count
    clean_headers = {
        k: v for k, v in resp_headers.items()
        if k.lower() not in ("content-length", "content-encoding", "transfer-encoding")
    }
    media_type = clean_headers.pop("Content-Type", "application/json; charset=utf-8")
    return Response(
        content=resp_bytes,
        status_code=status_code,
        headers=clean_headers,
        media_type=media_type
    )

@app.api_route(
    "/api/v1/payments/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    summary="Payments Subsystem Rails",
    include_in_schema=False
)
async def dispatch_payments_rails(request: Request, path: str):
    return await _forward_to_payments(request)

@app.get(
    "/api/v1/contracts/{contract_id}/hold",
    summary="PayPal Authorization Expiry Countdown"
)
async def get_contract_hold(request: Request, contract_id: str):
    return await _forward_to_payments(request)

@app.get(
    "/api/v1/contracts/{contract_id}/receipt",
    summary="Proof-of-Work Hashed Receipt"
)
async def get_contract_receipt(request: Request, contract_id: str):
    return await _forward_to_payments(request)

@app.get(
    "/api/v1/contracts/{contract_id}/settlement-summary",
    summary="Settlement Summary & Payout Breakdown"
)
async def get_contract_settlement_summary(request: Request, contract_id: str):
    return await _forward_to_payments(request)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting PactPal FastAPI on http://0.0.0.0:{port} (Swagger docs: http://0.0.0.0:{port}/docs) ...")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
