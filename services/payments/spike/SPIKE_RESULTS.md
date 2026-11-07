# Milestone 0 Spike Results: PayPal Escrow Rails (C03)

## Objective
Validate manual and programmatic execution of the PayPal REST API sandbox rails before building full application services:
1. OAuth 2.0 Bearer Token generation.
2. Order creation with `intent: "AUTHORIZE"` to hold buyer funds without premature capture.
3. Buyer approval link resolution.
4. Execution of the PayPal Payouts API to disburse funds to a sandbox recipient.
5. Verification that the payout landed in the sandbox account.

---

## 1. Environment & Setup

* **Sandbox Base URL**: `https://api-m.sandbox.paypal.com`
* **App ID**: `APP-7EA40934TJ444822F` (App Name: `PactPal-Escrow`)
* **Spike Runner**: `services/payments/spike/paypal_spike.py`
* **Postman Collection**: `services/payments/spike/PactPal_PayPal_Spike.postman_collection.json`

---

## 2. Execution Log & Verification

### Step 1: OAuth2 Authentication
* **Endpoint**: `POST /v1/oauth2/token`
* **Payload**: `grant_type=client_credentials`
* **Status**: `200 OK`
* **Result**:
  - `token_type`: `Bearer`
  - `expires_in`: `32400` seconds (9 hours)
  - Scopes verified: `https://uri.paypal.com/payments/payouts`, `https://uri.paypal.com/services/payments/payment/authcapture`, `https://uri.paypal.com/services/payments/refund`

### Step 2: Escrow Hold Order Creation (`intent: "AUTHORIZE"`)
* **Endpoint**: `POST /v2/checkout/orders`
* **Intent**: `AUTHORIZE`
* **Amount**: `100.00 USD`
* **Live Sandbox Order ID**: `17M76648VK7664316`
* **Status**: `CREATED`
* **Buyer Approval URL**:
  `https://www.sandbox.paypal.com/checkoutnow?token=17M76648VK7664316`
* **Verification**: Order was successfully generated; ready for buyer redirection to approve the 29-day authorization hold.

### Step 3: Payouts API Execution (Seller Payout)
* **Endpoint**: `POST /v1/payments/payouts`
* **Recipient**: Sandbox Freelancer Persona (`sb-zzudl53771742@personal.example.com`)
* **Amount**: `10.00 USD`
* **Live Sandbox Batch ID**: `TQFEE7Z7MR3QW`
* **Live Sandbox Payout Item ID**: `X7BS48SUUPVXY`
* **Initial Status**: `PENDING`
* **Final Processed Status**: `SUCCESS`
* **Evidence**:
  ```json
  {
    "batch_header": {
      "payout_batch_id": "TQFEE7Z7MR3QW",
      "batch_status": "PROCESSING",
      "amount": { "currency": "USD", "value": "10.00" }
    },
    "items": [
      {
        "payout_item_id": "X7BS48SUUPVXY",
        "transaction_status": "SUCCESS",
        "payout_item": {
          "recipient_type": "EMAIL",
          "amount": { "currency": "USD", "value": "10.00" },
          "receiver": "sb-zzudl53771742@personal.example.com"
        }
      }
    ]
  }
  ```

---

## 3. Key Findings & Architecture Decisions
1. **Self-Pay Guard**: The PayPal Payouts API rejects payouts sent to the exact same account that owns the REST app credentials (`SELF_PAY_NOT_ALLOWED`). The platform app must send payouts to the seller's distinct sandbox email, which matches PactPal's architecture perfectly (Platform holds escrow, freelancer receives payout).
2. **29-Day Hold**: Orders created with `AUTHORIZE` reserve funds and provide an `authorization_id` upon buyer approval, which is valid for up to 29 days (honored period).
3. **Capture & Void Balance**: In Milestone 3, passed feature weights are captured using `POST /v2/payments/authorizations/{id}/capture`, and any remaining balance is refunded via `POST /v2/payments/authorizations/{id}/void`.

---

## 4. Done Checklist for C03
- [x] Authorize intent order created in sandbox.
- [x] Postman collection created and verified.
- [x] Automated spike script created in `services/payments/spike/paypal_spike.py`.
- [x] Payouts API called and confirmed.
- [x] Test payout landed with `Item Status: SUCCESS` in sandbox seller account.
- [x] Gate 0 dependency satisfied.

