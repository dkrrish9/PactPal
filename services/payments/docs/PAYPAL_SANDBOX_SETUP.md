# PayPal Sandbox Environment & Setup Guide

## Overview
PactPal uses the **PayPal REST APIs (Sandbox Mode)** to implement zero-trust escrow rails for digital freelancing milestones. This document defines the sandbox testing architecture, account personas, and credential distribution guidelines for all teammates.

---

## 1. What is the Shared Vault & Secret Management Policy?

### The Principle: Zero Secrets in Version Control
In accordance with `BRANCH_RULES.md` and repository CI checks (`.github/workflows/ci.yml`), **no API keys, client secrets, passwords, or `.env` files are ever committed to Git**. Committing credentials can lead to automated account compromise, credential invalidation, and CI build rejection.

### How the Shared Vault Works
* **What it is**: The team's encrypted out-of-band store (e.g., shared Bitwarden/1Password vault, private team Notion credentials page, or secure pinned communication channel).
* **Where to find it**: Accessible only to verified PactPal team members (contact the Payment Lead for access).
* **Local Developer Setup**:
  1. Clone the repository.
  2. Copy the template: `cp .env.example .env`.
  3. Fetch `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` from the team shared vault.
  4. Paste the credentials into your local `.env`.
  5. The `.env` file is ignored by `.gitignore` and strictly scanned by pre-commit / CI hooks.

---

## 2. Sandbox Testing Personas

Two dedicated sandbox accounts have been provisioned in the PayPal Developer Dashboard for testing milestone contracts:

### A. Client / Buyer Persona (Personal Sandbox Account)
* **Role**: The project commissioner who funds the escrow milestone upfront.
* **Sandbox Email**: Stored in shared vault (`sb-zzudl53771742@personal.example.com`)
* **Simulated Balance**: $5,000.00 USD
* **Usage**: Log into PayPal Checkout redirect to approve the `AUTHORIZE` intent order.

### B. Freelancer / Seller Persona (Business Sandbox Account)
* **Role**: The freelancer who delivers deliverables and receives automated milestone payouts upon verification approval.
* **Sandbox Email**: Stored in shared vault (`sb-1pu8h53656646@business.example.com`)
* **Simulated Balance**: $5,000.00 USD
* **Usage**: Receives releases via PayPal Payouts API; inspects transaction receipts in the sandbox merchant portal.

---

## 3. PayPal Developer Application Configuration

* **App Name**: `PactPal-Escrow`
* **App Type**: Merchant (Sandbox)
* **Base URL**: `https://api-m.sandbox.paypal.com`
* **Enabled Scopes & Permissions**:
  - `Orders & Checkout` (Supports `intent: "AUTHORIZE"`)
  - `Authorizations & Captures` (Proportional release of verified features)
  - `Payouts API` (`https://uri.paypal.com/payments/payouts` enabled for instant feature payouts)
  - `Refunds & Voids` (Automatic return of unpassed milestone balances)

---

## 4. Verification Checklist (Done Criteria for C02)
- [x] Sandbox Business (Seller) account provisioned and accessible at [sandbox.paypal.com](https://sandbox.paypal.com).
- [x] Sandbox Personal (Buyer) account provisioned and accessible.
- [x] REST App created and credentials (`Client ID` + `Secret`) generated.
- [x] Credentials verified against `POST /v1/oauth2/token` (Bearer token generated successfully).
- [x] Credentials deposited in shared team vault.
- [x] Local `.env` verified against `.gitignore` to prevent secret leaks.
