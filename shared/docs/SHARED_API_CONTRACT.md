# PactPal Shared REST API Contract & Verification Specification (v1)

## Overview
This document specifies the authoritative API contract across all 4 PactPal engineering streams:
1. **Frontend (`feature/frontend`)**: Next.js client, Bryntum Gantt, contract wizard, referee dashboards.
2. **Core API & State Machine (`feature/agents`)**: Relational PostgreSQL persistence, auth roles, 10-state lifecycle engine.
3. **Verification Pipeline (`feature/verification`)**: Render container runner, Stages A–F verification, report generation.
4. **Payment Rails (`feature/payments`)**: PayPal Orders `AUTHORIZE`, 29-day expiry countdown, capture, and payouts.

Base URL: `http://localhost:8000/api/v1`

---

## 1. Authentication & Role Context
All requests supply actor context via header or Bearer JWT token:
```http
Authorization: Bearer <jwt_or_user_session_token>
X-Actor-Id: 9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d
```
Roles: `BUYER`, `SELLER`, `ADMIN`.

---

## 2. Core Contract Lifecycle Endpoints

### 2.1 Create Contract (`DRAFT`)
* **Endpoint**: `POST /api/v1/contracts`
* **Role**: `BUYER`
* **Request Body**:
```json
{
  "seller_id": "4a7c8e9b-0123-4567-89ab-cdef01234567",
  "title": "Portfolio Web Application",
  "description": "Develop 4-feature responsive website matching Figma mockup.",
  "total_amount": 1500.00,
  "currency": "USD",
  "deadline": "2026-12-01T00:00:00Z",
  "figma_url": "https://figma.com/file/sample-design",
  "repo_url": "https://github.com/freelancer/repo",
  "features": [
    {
      "title": "Landing Page & Navigation",
      "acceptance_test": "Responsive nav with 4 working links and logo",
      "price_weight": 25.00,
      "allocated_amount": 375.00,
      "sort_order": 1
    },
    {
      "title": "Dashboard UI & Charts",
      "acceptance_test": "Bryntum Gantt chart renders tasks and milestones",
      "price_weight": 30.00,
      "allocated_amount": 450.00,
      "sort_order": 2
    },
    {
      "title": "Authentication & OAuth",
      "acceptance_test": "Working NextAuth session with hashed credentials",
      "price_weight": 20.00,
      "allocated_amount": 300.00,
      "sort_order": 3
    },
    {
      "title": "PayPal Escrow Webhook Listeners",
      "acceptance_test": "Validates PayPal sandbox webhook signatures",
      "price_weight": 25.00,
      "allocated_amount": 375.00,
      "sort_order": 4
    }
  ]
}
```
* **Success Response (201 Created)**: Returns contract object with `status: "DRAFT"`.

### 2.2 Submit for Review (`DRAFT` ➔ `REVIEW`)
* **Endpoint**: `POST /api/v1/contracts/{id}/submit-review`
* **Role**: `BUYER`
* **Response (200 OK)**: Returns contract with `status: "REVIEW"`.

### 2.3 Sign / Accept Contract (`REVIEW` ➔ `SIGNED`)
* **Endpoint**: `POST /api/v1/contracts/{id}/sign`
* **Role**: Assigned `SELLER`
* **Request**: `{ "acceptance_confirmed": true }`
* **Response (200 OK)**: Returns contract with `status: "SIGNED"`, locking feature checklist.

### 2.4 Get Contract Details
* **Endpoint**: `GET /api/v1/contracts/{id}`
* **Role**: `BUYER`, `SELLER`, `ADMIN`
* **Response (200 OK)**: Full contract JSON, features array, timestamps, and PayPal holding metadata.

---

## 3. Payments & Escrow Rails Endpoints (`feature/payments`)

### 3.1 Create PayPal Escrow Hold Order
* **Endpoint**: `POST /api/v1/payments/orders/create-hold`
* **Role**: `BUYER`
* **Request Body**:
```json
{
  "contract_id": "e3a89172-1b6c-4820-a6e5-4a5c53147819"
}
```
* **Response (200 OK)**:
```json
{
  "paypal_order_id": "17M76648VK7664316",
  "approve_url": "https://www.sandbox.paypal.com/checkoutnow?token=17M76648VK7664316",
  "intent": "AUTHORIZE",
  "amount": "1500.00",
  "currency": "USD"
}
```

### 3.2 Authorize Order & Mark Contract Funded (`SIGNED` ➔ `FUNDED`)
* **Endpoint**: `POST /api/v1/payments/orders/authorize`
* **Role**: `BUYER`
* **Request Body**:
```json
{
  "contract_id": "e3a89172-1b6c-4820-a6e5-4a5c53147819",
  "paypal_order_id": "17M76648VK7664316"
}
```
* **Response (200 OK)**:
```json
{
  "contract_id": "e3a89172-1b6c-4820-a6e5-4a5c53147819",
  "status": "FUNDED",
  "paypal_order_id": "17M76648VK7664316",
  "paypal_auth_id": "8BA1234567890123",
  "auth_expires_at": "2026-12-09T01:30:00Z",
  "funded_at": "2026-11-10T01:30:00Z"
}
```

### 3.3 Get Hold Expiry Countdown (Powers Frontend Timer & Badge)
* **Endpoint**: `GET /api/v1/contracts/{id}/hold`
* **Role**: `BUYER`, `SELLER`, `ADMIN`
* **Response (200 OK)**:
```json
{
  "contract_id": "e3a89172-1b6c-4820-a6e5-4a5c53147819",
  "authorization_id": "8BA1234567890123",
  "amount": "1500.00",
  "currency": "USD",
  "status": "HELD",
  "authorized_at": "2026-11-10T01:30:00Z",
  "expires_at": "2026-12-09T01:30:00Z",
  "days_remaining": 29,
  "seconds_remaining": 2505600,
  "is_expired": false
}
```

### 3.4 Settle Contract & Disburse Payout (`DECISION` ➔ `SETTLED`)
* **Endpoint**: `POST /api/v1/payments/settle`
* **Role**: `ADMIN` or triggered by AI Referee
* **Request Body**:
```json
{
  "contract_id": "e3a89172-1b6c-4820-a6e5-4a5c53147819",
  "passed_amount": 1200.00,
  "refund_amount": 300.00,
  "seller_paypal_email": "sb-1pu8h53656646@business.example.com"
}
```
* **Response (200 OK)**: Returns capture ID, payout batch ID, refund ID, and receipt hash.

---

## 4. Verification Pipeline Endpoints (`feature/verification`)

### 4.1 Submit Deliverable (`IN_PROGRESS` ➔ `SUBMITTED` ➔ `VERIFYING`)
* **Endpoint**: `POST /api/v1/verification/submit`
* **Role**: Assigned `SELLER`
* **Schema**: Matches `shared/schemas/submission.json`
* **Request Body**:
```json
{
  "contract_id": "e3a89172-1b6c-4820-a6e5-4a5c53147819",
  "seller_id": "4a7c8e9b-0123-4567-89ab-cdef01234567",
  "repo_url": "https://github.com/freelancer/sample-app",
  "commit_sha": "4a7c8e9",
  "build_notes": "Built with Node 20. Run npm install && npm run build."
}
```
* **Response (202 Accepted)**:
```json
{
  "submission_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "render_job_id": "rnd_job_live_884920482",
  "status": "VERIFYING",
  "estimated_duration_seconds": 60
}
```

### 4.2 Get Verification Report (`VERIFYING` ➔ `DECISION`)
* **Endpoint**: `GET /api/v1/verification/reports/{contract_id}`
* **Role**: `BUYER`, `SELLER`, `ADMIN`
* **Schema**: Matches `shared/schemas/verification_report.json`
* **Sample Payload**: See `shared/mock/verification_report.mock.json`

---

## 5. AI Referee Endpoints (`feature/agents`)

### 5.1 Get Referee Decision & Explanation
* **Endpoint**: `GET /api/v1/referee/decisions/{contract_id}`
* **Response (200 OK)**:
```json
{
  "contract_id": "e3a89172-1b6c-4820-a6e5-4a5c53147819",
  "recommendation": "PARTIAL_RELEASE_80_PERCENT",
  "passed_features_count": 3,
  "total_features_count": 4,
  "passed_amount": 1200.00,
  "refund_amount": 300.00,
  "summary_text": "3 of 4 features passed. Feature 3 (Authentication) failed cheat scan. AI Referee offers 80% immediate payout ($1,200.00) or 48-hour fix window.",
  "receipt_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
}
```

### 5.2 Seller Response to Negotiated Partial Release
* **Endpoint**: `POST /api/v1/referee/negotiate`
* **Role**: Assigned `SELLER`
* **Request Body**:
```json
{
  "contract_id": "e3a89172-1b6c-4820-a6e5-4a5c53147819",
  "action": "ACCEPT_PARTIAL_PAYOUT" 
}
```
* `action` options: `"ACCEPT_PARTIAL_PAYOUT"` (triggers immediate $1,200 release & $300 refund) OR `"REQUEST_RESUBMISSION"` (allows re-upload within attempt limit).

---

## 6. Standard Error Responses

### 400 Bad Request (Validation or Invalid State Transition):
```json
{
  "error": "INVALID_STATE_TRANSITION",
  "message": "Illegal state jump: Cannot transition from 'DRAFT' to 'FUNDED'. Allowed next states: ['REVIEW']"
}
```

### 403 Forbidden:
```json
{
  "error": "UNAUTHORIZED_ROLE",
  "message": "Role 'SELLER' cannot fund escrow. Action permitted for 'BUYER' only."
}
```

