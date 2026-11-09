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
  "total_amount": 1000.00,
  "currency": "USD",
  "deadline": "2026-12-01T00:00:00Z",
  "figma_url": "https://figma.com/file/sample-design",
  "repo_url": "https://github.com/freelancer/repo",
  "features": [
    {
      "title": "Navigation & Header",
      "acceptance_test": "Responsive nav with 4 working links and logo",
      "price_weight": 40.00,
      "allocated_amount": 400.00,
      "sort_order": 1
    },
    {
      "title": "Contact Form API",
      "acceptance_test": "Submits form data to endpoint and shows confirmation banner",
      "price_weight": 60.00,
      "allocated_amount": 600.00,
      "sort_order": 2
    }
  ]
}
```
* **Success Response (201 Created)**:
```json
{
  "id": "e3a89172-1b6c-4820-a6e5-4a5c53147819",
  "status": "DRAFT",
  "title": "Portfolio Web Application",
  "buyer_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "seller_id": "4a7c8e9b-0123-4567-89ab-cdef01234567",
  "total_amount": 1000.00,
  "currency": "USD",
  "deadline": "2026-12-01T00:00:00Z",
  "features": [ ... ],
  "created_at": "2026-11-09T23:45:00Z",
  "updated_at": "2026-11-09T23:45:00Z"
}
```

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
  "paypal_order_id": "ORDER_PP_12345",
  "paypal_auth_id": "AUTH_PP_67890"
}
```
* **Response (200 OK)**:
```json
{
  "id": "e3a89172-1b6c-4820-a6e5-4a5c53147819",
  "status": "FUNDED",
  "paypal_order_id": "ORDER_PP_12345",
  "paypal_auth_id": "AUTH_PP_67890",
  "auth_expires_at": "2026-12-08T23:48:00Z",
  "funded_at": "2026-11-09T23:48:00Z"
}
```

---

### 2.5 Get Contract Details
* **Endpoint**: `GET /api/v1/contracts/{id}`
* **Role Allowed**: Participant `BUYER`, `SELLER`, or `ADMIN`
* **Response (200 OK)**: Returns full contract object including feature list, timestamps, and PayPal holding metadata.

---

## 3. Standard Error Responses

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

