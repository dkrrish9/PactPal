#!/usr/bin/env python3
"""
PactPal Milestone 0 Foundation: Schema Verification Test (Task C06)
Verifies that the 9 core entities connect cleanly:
- users
- contracts
- features
- change_requests (changes)
- submissions
- verification_reports (reports)
- payments
- receipts
- messages
"""

import sqlite3
import uuid
import json
from datetime import datetime, timezone

def generate_uuid():
    return str(uuid.uuid4())

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def test_schema_connectivity():
    print("=" * 70)
    print("PactPal Relational Schema Connectivity Test (Task C06)")
    print("=" * 70)

    # Use in-memory SQLite with foreign keys enabled
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    # 1. Create tables
    print("\n--- 1. Creating 9 Core Tables ---")
    tables = [
        """
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            role TEXT NOT NULL CHECK(role IN ('BUYER', 'SELLER', 'ADMIN')),
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            paypal_email TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """,
        """
        CREATE TABLE contracts (
            id TEXT PRIMARY KEY,
            buyer_id TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            seller_id TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('DRAFT','REVIEW','SIGNED','FUNDED','IN_PROGRESS','SUBMITTED','VERIFYING','DECISION','SETTLED','DISPUTE')),
            total_amount REAL NOT NULL CHECK(total_amount >= 0),
            currency TEXT NOT NULL DEFAULT 'USD',
            deadline TEXT NOT NULL,
            paypal_order_id TEXT UNIQUE,
            paypal_auth_id TEXT UNIQUE,
            auth_expires_at TEXT,
            figma_url TEXT,
            repo_url TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """,
        """
        CREATE TABLE features (
            id TEXT PRIMARY KEY,
            contract_id TEXT NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            acceptance_test TEXT NOT NULL,
            price_weight REAL NOT NULL CHECK(price_weight >= 0 AND price_weight <= 100),
            allocated_amount REAL NOT NULL CHECK(allocated_amount >= 0),
            status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'PASSED', 'FAILED', 'DISPUTED')),
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """,
        """
        CREATE TABLE change_requests (
            id TEXT PRIMARY KEY,
            contract_id TEXT NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
            proposed_by_id TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            description TEXT NOT NULL,
            proposed_price REAL NOT NULL,
            proposed_extra_time_hours INTEGER NOT NULL DEFAULT 0,
            ai_reasoning TEXT,
            status TEXT NOT NULL DEFAULT 'PROPOSED' CHECK(status IN ('PROPOSED', 'ACCEPTED', 'REJECTED', 'COUNTERED')),
            additional_auth_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """,
        """
        CREATE TABLE submissions (
            id TEXT PRIMARY KEY,
            contract_id TEXT NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
            seller_id TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            repo_url TEXT NOT NULL,
            commit_sha TEXT NOT NULL,
            build_notes TEXT,
            submission_number INTEGER NOT NULL DEFAULT 1 CHECK(submission_number BETWEEN 1 AND 3),
            is_late INTEGER NOT NULL DEFAULT 0,
            submitted_at TEXT NOT NULL
        );
        """,
        """
        CREATE TABLE verification_reports (
            id TEXT PRIMARY KEY,
            submission_id TEXT UNIQUE NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
            contract_id TEXT NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
            render_job_id TEXT,
            build_succeeded INTEGER NOT NULL DEFAULT 0,
            build_logs TEXT,
            test_suite_results TEXT NOT NULL,
            cheat_scan_findings TEXT NOT NULL,
            visual_diff_summary TEXT NOT NULL,
            per_feature_results TEXT NOT NULL,
            overall_score REAL,
            completed_at TEXT NOT NULL
        );
        """,
        """
        CREATE TABLE payments (
            id TEXT PRIMARY KEY,
            contract_id TEXT NOT NULL REFERENCES contracts(id) ON DELETE RESTRICT,
            payment_type TEXT NOT NULL CHECK(payment_type IN ('AUTHORIZATION','CAPTURE','PAYOUT','REFUND','VOID')),
            paypal_reference_id TEXT NOT NULL,
            amount REAL NOT NULL CHECK(amount > 0),
            currency TEXT NOT NULL DEFAULT 'USD',
            status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING','COMPLETED','FAILED')),
            metadata TEXT,
            processed_at TEXT NOT NULL
        );
        """,
        """
        CREATE TABLE receipts (
            id TEXT PRIMARY KEY,
            contract_id TEXT NOT NULL REFERENCES contracts(id) ON DELETE RESTRICT,
            report_id TEXT UNIQUE NOT NULL REFERENCES verification_reports(id) ON DELETE RESTRICT,
            payment_id TEXT REFERENCES payments(id) ON DELETE RESTRICT,
            receipt_hash TEXT NOT NULL CHECK(length(receipt_hash) = 64),
            summary_text TEXT NOT NULL,
            passed_features_count INTEGER NOT NULL DEFAULT 0,
            total_features_count INTEGER NOT NULL DEFAULT 0,
            seller_payout_amount REAL NOT NULL CHECK(seller_payout_amount >= 0),
            buyer_refund_amount REAL NOT NULL CHECK(buyer_refund_amount >= 0),
            verification_fingerprint_payload TEXT NOT NULL,
            issued_at TEXT NOT NULL
        );
        """,
        """
        CREATE TABLE messages (
            id TEXT PRIMARY KEY,
            contract_id TEXT NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
            sender_id TEXT REFERENCES users(id) ON DELETE SET NULL,
            sender_type TEXT NOT NULL CHECK(sender_type IN ('BUYER','SELLER','AI_REFEREE','ADMIN')),
            content TEXT NOT NULL,
            metadata TEXT,
            sent_at TEXT NOT NULL
        );
        """
    ]

    for ddl in tables:
        cursor.execute(ddl)
    print("  [✓] All 9 tables created successfully.")

    # 2. Insert Sample Connected Data
    print("\n--- 2. Populating Sample End-to-End Entities ---")

    # 2.1 Users (Buyer, Seller)
    buyer_id = generate_uuid()
    seller_id = generate_uuid()
    cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (buyer_id, "BUYER", "Alice Buyer", "alice@example.com", "alice_buyer@paypal.example.com", now_iso(), now_iso()))
    cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (seller_id, "SELLER", "Bob Freelancer", "bob@example.com", "bob_seller@paypal.example.com", now_iso(), now_iso()))
    print("  [✓] 1. Users created: Buyer and Seller")

    # 2.2 Contract
    contract_id = generate_uuid()
    cursor.execute("""
        INSERT INTO contracts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        contract_id, buyer_id, seller_id, "Website Redesign Project",
        "Build 4 features matching Figma design specifications.",
        "FUNDED", 1000.00, "USD", "2026-11-30T00:00:00Z",
        "ORDER_PP_12345", "AUTH_PP_67890", "2026-12-04T00:00:00Z",
        "https://figma.com/file/sample", "https://github.com/seller/repo",
        now_iso(), now_iso()
    ))
    print("  [✓] 2. Contract created: $1000.00 Escrow Funded")

    # 2.3 Features (Checklist: weights must sum to 100%)
    feature_1_id = generate_uuid()
    feature_2_id = generate_uuid()
    cursor.execute("INSERT INTO features VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (feature_1_id, contract_id, "Header Navigation", "Renders logo and 4 working links", 40.00, 400.00, "PASSED", 1, now_iso(), now_iso()))
    cursor.execute("INSERT INTO features VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (feature_2_id, contract_id, "Contact Form Submission", "Validates input and submits to API", 60.00, 600.00, "PASSED", 2, now_iso(), now_iso()))
    print("  [✓] 3. Features created: 2 items summing to 100% weight")

    # 2.4 Change Request
    change_id = generate_uuid()
    cursor.execute("INSERT INTO change_requests VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (change_id, contract_id, buyer_id, "Add dark mode toggle", 150.00, 24,
                    "AI estimated 3 hours work at $50/hr based on codebase complexity.", "ACCEPTED", "AUTH_PP_CHANGE_01", now_iso(), now_iso()))
    print("  [✓] 4. Change Request created: Negotiated scope addition ($150.00)")

    # 2.5 Submission
    submission_id = generate_uuid()
    cursor.execute("INSERT INTO submissions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (submission_id, contract_id, seller_id, "https://github.com/seller/repo", "4a7c8e9b01", "Build with npm run build", 1, 0, now_iso()))
    print("  [✓] 5. Submission created: Commit 4a7c8e9b01 by Seller")

    # 2.6 Verification Report (1:1 with Submission)
    report_id = generate_uuid()
    cursor.execute("INSERT INTO verification_reports VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (report_id, submission_id, contract_id, "srv-job-render-99", 1, "Build completed in 14.2s",
                    json.dumps({"total": 6, "passed": 6, "failed": 0}),
                    json.dumps([]),
                    json.dumps({"similarity_score": 0.94, "mismatches": 0}),
                    json.dumps({feature_1_id: "PASSED", feature_2_id: "PASSED"}),
                    0.97, now_iso()))
    print("  [✓] 6. Verification Report created: Render Workflow build + test succeeded (Score 0.97)")

    # 2.7 Payment (Authorization and Capture)
    payment_id = generate_uuid()
    cursor.execute("INSERT INTO payments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (payment_id, contract_id, "CAPTURE", "CAP_PP_99999", 1000.00, "USD", "COMPLETED", json.dumps({"payout_status": "SUCCESS"}), now_iso()))
    print("  [✓] 7. Payment created: PayPal Capture CAP_PP_99999 ($1000.00)")

    # 2.8 Receipt (Tamper-evident SHA-256)
    receipt_id = generate_uuid()
    mock_hash = "a" * 64
    cursor.execute("INSERT INTO receipts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                   (receipt_id, contract_id, report_id, payment_id, mock_hash,
                    "Full milestone verified and released by AI Referee. All 2 features passed acceptance tests with 0 security findings.",
                    2, 2, 1000.00, 0.00, json.dumps({"features_passed": 2}), now_iso()))
    print("  [✓] 8. Receipt created: SHA-256 Proof-of-Work Receipt ($1000 payout / $0 refund)")

    # 2.9 Message (Audit trail)
    msg_id = generate_uuid()
    cursor.execute("INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (msg_id, contract_id, None, "AI_REFEREE",
                    "AI Escrow Referee: Verification passed with 97% confidence. $1,000.00 released to seller.",
                    json.dumps({"card": "SETTLEMENT_COMPLETE"}), now_iso()))
    print("  [✓] 9. Message created: AI Referee settlement dispatch")

    # 3. Test Unified Relational Query
    print("\n--- 3. Verifying Clean Relational Joins Across All 9 Entities ---")
    query = """
    SELECT
        c.title AS contract_title,
        c.status AS contract_status,
        b.name AS buyer_name,
        s.name AS seller_name,
        COUNT(DISTINCT f.id) AS feature_count,
        SUM(f.price_weight) AS total_weight,
        cr.proposed_price AS change_request_amount,
        sub.commit_sha AS submission_commit,
        vr.overall_score AS verification_score,
        p.amount AS payment_captured,
        r.receipt_hash AS proof_of_work_hash,
        m.content AS latest_referee_message
    FROM contracts c
    JOIN users b ON c.buyer_id = b.id
    JOIN users s ON c.seller_id = s.id
    JOIN features f ON f.contract_id = c.id
    JOIN change_requests cr ON cr.contract_id = c.id
    JOIN submissions sub ON sub.contract_id = c.id
    JOIN verification_reports vr ON vr.submission_id = sub.id
    JOIN payments p ON p.contract_id = c.id
    JOIN receipts r ON r.contract_id = c.id
    JOIN messages m ON m.contract_id = c.id
    WHERE c.id = ?
    GROUP BY c.id;
    """

    cursor.execute(query, (contract_id,))
    row = cursor.fetchone()

    print(f"Contract:           {row[0]} ({row[1]})")
    print(f"Parties:            Buyer: {row[2]} | Seller: {row[3]}")
    print(f"Checklist Features: {row[4]} items, Total Weight: {row[5]}%")
    print(f"Change Request:     +${row[6]:.2f}")
    print(f"Verified Commit:    {row[7]} (Score: {row[8]})")
    print(f"Captured Payment:   ${row[9]:.2f}")
    print(f"Tamper-Proof Hash:  {row[10][:16]}... ({len(row[10])} chars)")
    print(f"Referee Dispatch:   {row[11]}")

    assert row[5] == 100.0, "Feature price weights must sum to 100%"
    assert row[9] == 1000.0, "Captured payment must match contract total"
    assert len(row[10]) == 64, "Receipt hash must be 64-character SHA-256"

    print("\n" + "=" * 70)
    print("ALL 9 CORE ENTITIES CONNECT CLEANLY WITH ZERO INTEGRITY ERRORS!")
    print("=" * 70)
    conn.close()

if __name__ == "__main__":
    test_schema_connectivity()

