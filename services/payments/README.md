# Subsystem: Payment Rails & PayPal Escrow (`services/payments`)
**Stream Branch**: `feature/payments`  
**Stream Lead / Owner**: 4 - Payments (PAY)

## Overview
Connects to PayPal sandbox APIs to implement zero-trust milestone escrow.
- Locks funds up front using PayPal Orders API with `intent: "AUTHORIZE"`.
- Releases passed feature amounts via `Capture` and PayPal `Payouts API`.
- Voids or refunds unpassed amounts back to the buyer.
- Tracks the 29-day PayPal authorization holding window and monitors re-authorization thresholds.

## Endpoints Implemented

### 1. `POST /api/v1/payments/orders/create-hold` (Commit `C10`)
* **Role**: `BUYER`
* **Action**: Creates a PayPal Order with `intent: "AUTHORIZE"` and returns `approve_url`.

### 2. `POST /api/v1/payments/orders/authorize` (Commit `C10`)
* **Role**: `BUYER`
* **Action**: Executes the PayPal authorization, captures `paypal_auth_id`, stores `auth_expires_at` (29 days), and advances contract `SIGNED` ➔ `FUNDED`.

### 3. `GET /api/v1/contracts/{id}/hold` (Commit `C14`)
* **Roles**: `BUYER`, `SELLER`, `ADMIN`
* **Action**: Exposes live 29-day authorization hold countdown data for the frontend timer and hold badges.
* **Response Sample**:
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
* **Status Progression**:
  - `HELD`: `seconds_remaining > 259,200` (> 3 days remaining)
  - `EXPIRING_SOON`: `0 < seconds_remaining <= 259,200` (<= 3 days remaining; triggers re-authorization warning)
  - `EXPIRED`: `seconds_remaining == 0` (is_expired: true)

### 4. `POST /api/v1/payments/settle` (Commit `C24`)
* **Roles**: `ADMIN`, `AI_REFEREE`
* **Action**: Executes partial/full capture from PayPal authorization, dispatches seller payouts via PayPal Payouts API, voids remaining hold, records ledger entries, and generates SHA-256 tamper-evident proof receipt.

### 5. `POST /api/v1/payments/webhooks` (Commit `C28`)
* **Roles**: PayPal Webhook Dispatcher
* **Action**: Cryptographically validates PayPal webhook transmission signature headers (`paypal-auth-algo`, `paypal-cert-url`, `paypal-transmission-id`, `paypal-transmission-sig`, `paypal-transmission-time`) against PayPal REST API `/v1/notifications/verify-webhook-signature` and dispatches verified event processing.

### 6. `POST /api/v1/payments/approval-check` & `GET /api/v1/contracts/{id}/payment-approval` (Commit `C31`)
* **Roles**: `BUYER` (for hold creation), `ADMIN` / `AI_REFEREE` (for settlement)
* **Action**: Automated backend approval policy check before executing payment rails. Validates:
  1. **Checklist Lock Guard**: Contract checklist must be dual-confirmed and locked (`is_locked=True`).
  2. **Pre-Settlement Verification Guard**: Verification report exists, zero high-severity loophole/cheat scan findings, and amounts match verified feature weights/scores (or platform `ADMIN` dispute resolution override).
  3. **State Machine Consistency**: Action matches allowed lifecycle transitions.
  4. **Role & Identity Guard**: Actor is authorized.
* **Response Sample**:
```json
{
  "approval_id": "673f5509-f9c3-424a-9775-7634ca3a9e5b",
  "contract_id": "e3a89172-1b6c-4820-a6e5-4a5c53147819",
  "action": "SETTLE_ESCROW",
  "approved": true,
  "reasons": ["All policy criteria met."],
  "checks_passed": [
    "ROLE_AUTHORIZED",
    "STATE_MACHINE_CONSISTENT",
    "CHECKLIST_LOCKED",
    "VERIFICATION_REPORT_EXISTS",
    "BUILD_SUCCEEDED",
    "CHEAT_SCAN_CLEARED",
    "AMOUNT_ALIGNMENT",
    "AMOUNT_INVARIANT"
  ],
  "checks_failed": [],
  "timestamp": "2026-11-10T12:00:00Z"
}
```

## PayPal Model Context Protocol (MCP) Integration
Detailed specification of MCP tool schemas (`paypal_get_authorization`, `paypal_capture_authorization`, `paypal_void_authorization`, `paypal_create_payout`, `paypal_list_disputes`), agent workflow patterns, and security guardrails can be found in:
* `services/payments/docs/PAYPAL_MCP_INTEGRATION.md`

## Testing
```bash
# Run all payments tests
python3 -m unittest discover -s services/payments/tests -t .

# Run hold expiry test suite specifically
python3 -m unittest services/payments/tests/test_hold_expiry.py
```


