# PactPal One-Page Relational Data Map (Schema Specification)

This data map defines the core relational database entities for PactPal, connecting contracts, priced features, verification artifacts, PayPal payments, and cryptographic receipts.

---

## Entity Relationship Overview

```mermaid
erDiagram
    USERS ||--o{ CONTRACTS : "buyer / seller"
    CONTRACTS ||--|{ FEATURES : "contains priced checklist"
    CONTRACTS ||--o{ CHANGE_REQUESTS : "receives mid-project changes"
    CONTRACTS ||--o{ SUBMISSIONS : "receives code deliverables"
    SUBMISSIONS ||--o| VERIFICATION_REPORTS : "evaluates into"
    CONTRACTS ||--o{ PAYMENTS : "tracks holds and payouts"
    CONTRACTS ||--o{ RECEIPTS : "finalizes with"
    CONTRACTS ||--o{ MESSAGES : "includes audit chat"

    USERS {
        uuid id PK
        string role "BUYER | SELLER | ADMIN"
        string email
        string paypal_email
        string name
        timestamp created_at
    }

    CONTRACTS {
        uuid id PK
        uuid buyer_id FK
        uuid seller_id FK
        string title
        text description
        string status "10-state enum"
        decimal total_amount
        string currency
        timestamp deadline
        string paypal_order_id
        string paypal_auth_id
        timestamp auth_expires_at
        timestamp created_at
    }

    FEATURES {
        uuid id PK
        uuid contract_id FK
        string title
        text acceptance_test "Plain-language test"
        decimal price_weight "Percentage weight (0-100)"
        decimal allocated_amount "Calculated amount"
        string status "PENDING | PASSED | FAILED | DISPUTED"
        integer sort_order
    }

    CHANGE_REQUESTS {
        uuid id PK
        uuid contract_id FK
        text proposed_scope
        decimal proposed_price
        integer proposed_extra_days
        string status "PROPOSED | ACCEPTED | REJECTED | COUNTERED"
        string additional_auth_id
    }

    SUBMISSIONS {
        uuid id PK
        uuid contract_id FK
        string repo_url
        string commit_sha
        string build_notes
        timestamp submitted_at
        boolean is_late
        integer attempt_number
    }

    VERIFICATION_REPORTS {
        uuid id PK
        uuid submission_id FK
        boolean build_succeeded
        jsonb test_suite_results
        jsonb cheat_scan_findings "Severity: HIGH | MED | LOW"
        jsonb visual_diff_summary "Similarity score & images"
        jsonb per_feature_results "Feature pass/fail mapping"
        decimal overall_score
        timestamp completed_at
    }

    PAYMENTS {
        uuid id PK
        uuid contract_id FK
        string payment_type "AUTHORIZATION | CAPTURE | PAYOUT | REFUND"
        string paypal_reference_id
        decimal amount
        string currency
        string status "PENDING | COMPLETED | FAILED"
        timestamp processed_at
    }

    RECEIPTS {
        uuid id PK
        uuid contract_id FK
        uuid report_id FK
        string receipt_hash "SHA-256 fingerprint"
        text summary_text
        jsonb passed_features_summary
        decimal seller_payout_amount
        decimal buyer_refund_amount
        timestamp issued_at
    }

    MESSAGES {
        uuid id PK
        uuid contract_id FK
        string sender_type "BUYER | SELLER | AI_REFEREE"
        text content
        jsonb metadata "Negotiation offers or status cards"
        timestamp sent_at
    }
```

