# PayPal Model Context Protocol (MCP) Integration Specification

## 1. Executive Summary & Antigravity MCP Architecture

In **PactPal** (Zero-Trust Multimodal AI Escrow Referee for Digital Freelancing), autonomous AI agents—such as the **AI Referee**, **Payment Agent**, and **Dispute Arbitrator**—require programmatic, standardized, and secure access to PayPal fintech rails.

The **Model Context Protocol (MCP)**, developed by Anthropic and adopted within the Google DeepMind Antigravity framework, provides an open standard for LLMs and agentic systems to interact with external tools and data sources. This document outlines the design, tool schemas, agent workflow patterns, and zero-trust security guardrails for a dedicated **PayPal MCP Server** (`mcp-paypal-escrow`) within the PactPal architecture.

```
       +-------------------------------------------------------------+
       |                  PactPal Agentic Layer                      |
       |  (AI Referee, Payment Agent, Agreement Reader, Arbitrator) |
       +------------------------------+------------------------------+
                                      |
                      JSON-RPC 2.0 / MCP Protocol
                                      |
       +------------------------------v------------------------------+
       |               PayPal MCP Server (`mcp-paypal`)              |
       |  - Schema Validation & Tool Router                          |
       |  - Automated Backend Approval Policy Gate (Commit C31)     |
       |  - Idempotency & Request-Id Manager                         |
       +------------------------------+------------------------------+
                                      |
                      PayPal REST APIs (v1 / v2)
                                      |
       +------------------------------v------------------------------+
       |             PayPal Sandbox / Production Rails               |
       |   - Orders API (v2)           - Authorizations API (v2)     |
       |   - Payments API (v2)         - Payouts API (v1)            |
       |   - Disputes API (v1)         - Webhooks Verification (v1)  |
       +-------------------------------------------------------------+
```

---

## 2. Capabilities Mapped to Agentic Escrow Roles

| Agent Role | Required PayPal Capabilities | MCP Tool |
| :--- | :--- | :--- |
| **Payment Agent** | Create authorization order, verify buyer approval, inspect hold countdown | `paypal_get_authorization`, `paypal_check_approval_policy` |
| **AI Referee** | Verify milestone deliverables, evaluate test/cheat reports, calculate split math, trigger split settlement | `paypal_calculate_split_preview`, `paypal_capture_authorization`, `paypal_create_payout`, `paypal_void_authorization` |
| **Dispute Arbitrator** | Triage claims, inspect buyer chargebacks, review evidence | `paypal_list_disputes`, `paypal_get_dispute_details` |
| **Compliance Auditor** | Cryptographic webhook verification, payout reconciliation | `paypal_verify_webhook`, `paypal_get_payout_status` |

---

## 3. Formal Tool Definitions & JSON Schemas

The PayPal MCP Server registers the following core tools:

### 3.1 `paypal_check_approval_policy` (Pre-flight Gate)
Inspects whether a planned payment action is eligible to execute under PactPal's Gate 2 approval policy before calling any external PayPal rails.

```json
{
  "name": "paypal_check_approval_policy",
  "description": "Validates PactPal backend approval policy for a payment action: checks checklist dual-confirmation lock, verification report presence, loophole scans, and role permissions.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "contract_id": {
        "type": "string",
        "description": "Unique UUID of the contract in PactPal core repository."
      },
      "action": {
        "type": "string",
        "enum": ["CREATE_HOLD", "AUTHORIZE_HOLD", "SETTLE_ESCROW"],
        "description": "The target payment rail action to validate."
      },
      "actor_id": {
        "type": "string",
        "description": "User ID of the entity triggering the action (e.g. buyer UUID or 'AI_REFEREE')."
      },
      "passed_amount": {
        "type": "number",
        "description": "Amount to release to seller (for SETTLE_ESCROW)."
      },
      "refund_amount": {
        "type": "number",
        "description": "Amount to refund/void to buyer (for SETTLE_ESCROW)."
      },
      "admin_override": {
        "type": "boolean",
        "default": false,
        "description": "Whether an explicit platform ADMIN dispute override is attached."
      }
    },
    "required": ["contract_id", "action", "actor_id"]
  }
}
```

### 3.2 `paypal_get_authorization`
Queries real-time status of an escrow hold on PayPal rails, including 29-day expiration limit and 3-day honor window.

```json
{
  "name": "paypal_get_authorization",
  "description": "Fetches current details of a PayPal authorization hold (amount, currency, expiration, status: CREATED, CAPTURED, DENIED, EXPIRED, VOIDED).",
  "inputSchema": {
    "type": "object",
    "properties": {
      "authorization_id": {
        "type": "string",
        "description": "The PayPal Authorization ID (e.g. 'AUTH_PP_445566' or live PayPal ID)."
      }
    },
    "required": ["authorization_id"]
  }
}
```

### 3.3 `paypal_capture_authorization`
Captures funds from an active authorization hold based on milestone completion.

```json
{
  "name": "paypal_capture_authorization",
  "description": "Captures a specific amount from an authorized PayPal escrow hold. Supports final or partial capture.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "authorization_id": {
        "type": "string",
        "description": "PayPal authorization ID to capture from."
      },
      "amount": {
        "type": "number",
        "description": "Numerical amount to capture (must match verified passed milestone value)."
      },
      "currency": {
        "type": "string",
        "default": "USD",
        "description": "Three-letter ISO-4217 currency code."
      },
      "is_final_capture": {
        "type": "boolean",
        "default": true,
        "description": "True if no further captures will occur against this authorization."
      },
      "idempotency_key": {
        "type": "string",
        "description": "Unique key passed as PayPal-Request-Id to guarantee exactly-once processing."
      }
    },
    "required": ["authorization_id", "amount"]
  }
}
```

### 3.4 `paypal_void_authorization`
Releases an uncaptured hold back to the buyer (used for failed features or refunds).

```json
{
  "name": "paypal_void_authorization",
  "description": "Voids an active PayPal authorization, releasing all remaining hold funds immediately to the buyer.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "authorization_id": {
        "type": "string",
        "description": "The PayPal authorization ID to void."
      },
      "idempotency_key": {
        "type": "string",
        "description": "Unique key passed as PayPal-Request-Id."
      }
    },
    "required": ["authorization_id"]
  }
}
```

### 3.5 `paypal_create_payout`
Disburses milestone earnings to the seller's PayPal account via PayPal Payouts API v1.

```json
{
  "name": "paypal_create_payout",
  "description": "Disburses funds directly to a seller's PayPal email using PayPal Payouts API.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "receiver_email": {
        "type": "string",
        "format": "email",
        "description": "Target freelancer PayPal account email address."
      },
      "amount": {
        "type": "number",
        "description": "Payout amount in specified currency."
      },
      "currency": {
        "type": "string",
        "default": "USD",
        "description": "Three-letter ISO-4217 currency code."
      },
      "note": {
        "type": "string",
        "description": "Reference note displayed to freelancer in PayPal transaction."
      },
      "idempotency_key": {
        "type": "string",
        "description": "Sender batch ID ensuring idempotent disbursal."
      }
    },
    "required": ["receiver_email", "amount"]
  }
}
```

### 3.6 `paypal_list_disputes`
Enables the AI Referee or Dispute Arbitrator to monitor buyer disputes and chargebacks.

```json
{
  "name": "paypal_list_disputes",
  "description": "Lists customer disputes, chargebacks, and claims filed against payments in the PayPal Resolution Center.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "dispute_state": {
        "type": "string",
        "enum": ["REQUIRED_ACTION", "REQUIRED_OTHER_PARTY_ACTION", "UNDER_REVIEW", "RESOLVED"],
        "description": "Filter by dispute state."
      },
      "start_time": {
        "type": "string",
        "format": "date-time",
        "description": "ISO-8601 start date."
      }
    }
  }
}
```

### 3.7 `paypal_calculate_split_preview` (Commit C37 Milestone 3)
Calculates and previews proportional partial escrow split math:
- Itemized feature allocations according to `price_weight`.
- Deterministic Remainder Rule: Dynamically assigns the rounding delta ($\pm \$0.01$) to the last feature so that $\sum_{i=1}^N \text{allocated}_i == \text{total\_amount}$ exactly to the cent.
- Invariant guarantee: `round(passed_amount + refund_amount, 2) == round(total_amount, 2)` with zero lost pennies under any combination of weights and prices.

```json
{
  "name": "paypal_calculate_split_preview",
  "description": "Computes exact itemized milestone feature split math and remainder cents reconciliation for an escrow contract.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "contract_id": {
        "type": "string",
        "description": "Unique UUID of the contract in PactPal core repository."
      },
      "feature_results": {
        "type": "object",
        "description": "Optional map of feature IDs to PASSED or FAILED verdicts."
      }
    },
    "required": ["contract_id"]
  }
}
```

---

## 4. Autonomous Agent Workflow Patterns

### Pattern A: AI Referee Pre-flight Policy Verification Gate
Before triggering any financial settlement, the AI Referee agent executes a strict pre-flight check:

```
[Agent] ---> Call paypal_check_approval_policy(contract_id, "SETTLE_ESCROW", ...)
   |
   +---> If approved == False:
   |        Log reasons (e.g. "Checklist not locked" or "Unresolved high-severity cheat finding")
   |        Notify parties via chat message; HALT payment execution.
   |
   +---> If approved == True:
            Proceed to execute Capture and Payout.
```

### Pattern B: Milestone Partial Settlement & Disbursal
When verification concludes with 80% passed features and 20% failed features:
1. `paypal_capture_authorization`: Captures 80% with `is_final_capture=False`.
2. `paypal_create_payout`: Immediately routes the 80% captured funds to seller's PayPal address.
3. `paypal_void_authorization`: Voids the remaining 20% hold, releasing it back to buyer.
4. Generates SHA-256 tamper-proof proof-of-work receipt.

### Pattern C: Escrow Hold Expiry Watcher
A scheduled background agent periodically checks hold status:
- If `seconds_remaining <= 259,200` (3 days), flags `EXPIRING_SOON` and triggers proactive notification to buyer/seller.
- If deadline reached, triggers automated partial payout evaluation.

---

## 5. Fintech Security, Zero-Trust Guardrails & Sandbox Isolation

1. **Strict Idempotency Enforcement**:
   - Every mutating MCP tool (`paypal_capture_authorization`, `paypal_create_payout`, `paypal_void_authorization`) enforces an explicit `idempotency_key`.
   - Propagated as `PayPal-Request-Id` to PayPal REST rails.
   - Caching layer prevents double-capture or duplicate payout on network retry.
2. **Zero Credential Exposure**:
   - `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET` are never exposed in agent prompts, system context, or tool schemas.
   - Stored in encrypted server-side environment variables and handled exclusively by the server process.
3. **Role Gating & Tiered Authorization**:
   - Funding tools (`CREATE_HOLD`, `AUTHORIZE_HOLD`) require authenticated BUYER persona.
   - Settlement and payout tools require AI_REFEREE or platform ADMIN persona.
   - High-severity loophole overrides strictly require `ADMIN` role.
4. **Mathematical Invariant Enforcement**:
   - The MCP server mathematically asserts:
     $$\text{round}(\text{passed\_amount} + \text{refund\_amount}, 2) == \text{round}(\text{total\_amount}, 2)$$
   - Both amounts must be non-negative.
5. **Audit Ledger Immutability**:
   - Every tool execution verdict, parameter set, and response payload is recorded in the relational `messages` table with cryptographic timestamping.

