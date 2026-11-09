# PactPal Core REST API Contract (v1)

## Overview
This document specifies the REST API endpoints exposed by `services/core-api` for the Frontend team (`feature/frontend`), Bryntum Gantt timelines, and backend services.

Base URL: `http://localhost:8000/api/v1`

---

## 1. Authentication & Role Context
Requests must supply the authenticated actor's credentials via Bearer token or headers:
```http
Authorization: Bearer <jwt_or_user_session_token>
X-Actor-Id: 9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d
```

Roles supported: `BUYER`, `SELLER`, `ADMIN`.

---

## 2. Contract Lifecycle Endpoints

### 2.1 Create Contract (Initial State: `DRAFT`)
* **Endpoint**: `POST /api/v1/contracts`
* **Role Allowed**: `BUYER` only
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

---

### 2.2 Submit Contract for Review (`DRAFT` ➔ `REVIEW`)
* **Endpoint**: `POST /api/v1/contracts/{id}/submit-review`
* **Role Allowed**: Assigned `BUYER` only
* **Response (200 OK)**:
```json
{
  "id": "e3a89172-1b6c-4820-a6e5-4a5c53147819",
  "status": "REVIEW",
  "updated_at": "2026-11-09T23:46:00Z"
}
```

---

### 2.3 Sign / Accept Contract (`REVIEW` ➔ `SIGNED`)
* **Endpoint**: `POST /api/v1/contracts/{id}/sign`
* **Role Allowed**: Assigned `SELLER` only
* **Request Body**:
```json
{
  "acceptance_confirmed": true
}
```
* **Response (200 OK)**:
```json
{
  "id": "e3a89172-1b6c-4820-a6e5-4a5c53147819",
  "status": "SIGNED",
  "signed_at": "2026-11-09T23:47:00Z"
}
```

---

### 2.4 Fund Escrow Hold (`SIGNED` ➔ `FUNDED`)
* **Endpoint**: `POST /api/v1/contracts/{id}/fund`
* **Role Allowed**: Assigned `BUYER` only
* **Request Body**:
```json
{
  "paypal_order_id": "17M76648VK7664316",
  "paypal_auth_id": "8BA1234567890123"
}
```
* **Response (200 OK)**:
```json
{
  "id": "e3a89172-1b6c-4820-a6e5-4a5c53147819",
  "status": "FUNDED",
  "paypal_order_id": "17M76648VK7664316",
  "paypal_auth_id": "8BA1234567890123",
  "auth_expires_at": "2026-12-09T01:30:00Z",
  "funded_at": "2026-11-10T01:30:00Z"
}
```

---

### 2.5 Get Contract Details
* **Endpoint**: `GET /api/v1/contracts/{id}`
* **Role Allowed**: Participant `BUYER`, `SELLER`, or `ADMIN`
* **Response (200 OK)**: Returns full contract object including feature list, timestamps, and PayPal holding metadata.

---

## 3. Verification Report Specification
The verification pipeline outputs a standardized report conforming to `shared/schemas/verification_report.json`.
Each feature evaluation in `per_feature_results` strictly includes:
* `feature_id`: UUID
* `title`: string
* `status`: `"passed" | "failed" | "partially_met"`
* `price_weight`: numeric (0-100)
* `allocated_amount`: numeric
* `severity`: `"none" | "low" | "medium" | "high"`
* `evidence`: string

See sample mock payload: `shared/mock/verification_report.mock.json`.
Full master contract across all services: `shared/docs/SHARED_API_CONTRACT.md`.

---

## 4. Standard Error Responses

### 403 Forbidden (Unauthorized Role):
```json
{
  "error": "UNAUTHORIZED_ROLE",
  "message": "User 'bob-seller' with role 'SELLER' cannot fund contracts. Only BUYER can fund escrow."
}
```

### 400 Bad Request (Illegal State Jump):
```json
{
  "error": "INVALID_STATE_TRANSITION",
  "message": "Illegal state jump: Cannot transition from 'DRAFT' to 'FUNDED'. Allowed next states: ['REVIEW']"
}
```
