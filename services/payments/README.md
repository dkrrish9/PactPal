# Subsystem: Payment Rails & PayPal Escrow (`services/payments`)
**Stream Branch**: `feature/payments`  
**Stream Lead / Owner**: 4 - Payments (PAY)

## Overview
Connects to PayPal sandbox APIs to implement zero-trust milestone escrow.
- Locks funds up front using PayPal Orders API with `intent: "AUTHORIZE"`.
- Releases passed feature amounts via `Capture` and PayPal `Payouts API`.
- Voids or refunds unpassed amounts back to the buyer.
- Tracks the 29-day PayPal authorization holding window and monitors re-authorization thresholds.

## Structure
- `paypal_client/`: OAuth2 token caching, Orders API, Authorizations, Captures, Payouts client.
- `escrow/`: Mathematical split calculator ensuring sum of payout + refund == 100% of contract total.
- `webhooks/`: Cryptographic signature verification of incoming PayPal webhook events.
- `expiry/`: Background cron / scheduler monitoring authorization expiration.

