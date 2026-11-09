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

## Testing
```bash
# Run all payments tests
python3 -m unittest discover -s services/payments/tests -t .

# Run hold expiry test suite specifically
python3 -m unittest services/payments/tests/test_hold_expiry.py
```


