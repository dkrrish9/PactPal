"""
PactPal Database Repository Layer
Supports local SQLite and PostgreSQL (Supabase).
Linked Tasks: C09 / C19 / A2 / A5
"""

import sqlite3
import uuid
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from ..auth.roles import User, UserRole, assert_can_create_contract
from ..state_machine.engine import ContractState, ContractStateMachine

class ChecklistLockError(Exception):
    """Raised when an unauthorized modification is attempted on a locked checklist."""
    pass

def generate_uuid() -> str:
    return str(uuid.uuid4())

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class ContractRepository:
    def __init__(self, db_path: str = ":memory:"):
        """Initializes connection to SQLite database (default in-memory for testing)."""
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.notification_service = None
        self._init_tables()

    def _init_tables(self) -> None:
        """Initializes baseline tables compatible with schema.sql."""
        cursor = self.conn.cursor()
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            role TEXT NOT NULL CHECK(role IN ('BUYER', 'SELLER', 'ADMIN')),
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            paypal_email TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS contracts (
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
            is_locked INTEGER NOT NULL DEFAULT 0,
            buyer_confirmed_at TEXT,
            seller_confirmed_at TEXT,
            locked_at TEXT,
            signed_at TEXT,
            funded_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS features (
            id TEXT PRIMARY KEY,
            contract_id TEXT NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            acceptance_test TEXT NOT NULL,
            price_weight REAL NOT NULL CHECK(price_weight >= 0 AND price_weight <= 100),
            allocated_amount REAL NOT NULL CHECK(allocated_amount >= 0),
            status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'PASSED', 'FAILED', 'DISPUTED')),
            sort_order INTEGER NOT NULL DEFAULT 0,
            change_request_id TEXT,
            amended INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            contract_id TEXT NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
            sender_id TEXT REFERENCES users(id) ON DELETE SET NULL,
            sender_type TEXT NOT NULL CHECK(sender_type IN ('BUYER','SELLER','AI_REFEREE','ADMIN')),
            content TEXT NOT NULL,
            metadata TEXT,
            sent_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS payments (
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

        CREATE TABLE IF NOT EXISTS receipts (
            id TEXT PRIMARY KEY,
            contract_id TEXT NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
            submission_id TEXT,
            verification_report_id TEXT,
            receipt_hash TEXT UNIQUE NOT NULL,
            evidence_payload TEXT NOT NULL,
            generated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS idempotency_keys (
            key TEXT NOT NULL,
            scope TEXT NOT NULL,
            response_data TEXT NOT NULL,
            status_code INTEGER NOT NULL DEFAULT 200,
            created_at TEXT NOT NULL,
            PRIMARY KEY (key, scope)
        );

        CREATE TABLE IF NOT EXISTS change_requests (
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

        CREATE TABLE IF NOT EXISTS submissions (
            id TEXT PRIMARY KEY,
            contract_id TEXT NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
            seller_id TEXT REFERENCES users(id) ON DELETE RESTRICT,
            repo_url TEXT NOT NULL DEFAULT '',
            commit_sha TEXT NOT NULL DEFAULT '',
            build_notes TEXT,
            submission_number INTEGER NOT NULL DEFAULT 1 CHECK(submission_number BETWEEN 1 AND 3),
            is_late INTEGER NOT NULL DEFAULT 0,
            submitted_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS verification_reports (
            id TEXT PRIMARY KEY,
            submission_id TEXT UNIQUE REFERENCES submissions(id) ON DELETE CASCADE,
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
        """)
        self.conn.commit()

    # --- User Management ---
    def create_user(self, name: str, email: str, role: UserRole, paypal_email: Optional[str] = None) -> User:
        user_id = generate_uuid()
        timestamp = now_iso()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO users (id, role, name, email, paypal_email, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, role.value, name, email, paypal_email, timestamp, timestamp)
        )
        self.conn.commit()
        return User(id=user_id, name=name, email=email, role=role, paypal_email=paypal_email)

    def get_user(self, user_id: str) -> Optional[User]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return User(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            role=UserRole(row["role"]),
            paypal_email=row["paypal_email"]
        )

    # --- Contract Management ---
    def create_contract(
        self,
        buyer: User,
        seller_id: str,
        title: str,
        description: str,
        total_amount: float,
        deadline: str,
        figma_url: Optional[str] = None,
        repo_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a contract in initial DRAFT state. Asserts actor is a BUYER."""
        assert_can_create_contract(buyer)

        contract_id = generate_uuid()
        timestamp = now_iso()
        status = ContractState.DRAFT.value

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO contracts (
                id, buyer_id, seller_id, title, description, status,
                total_amount, currency, deadline, figma_url, repo_url,
                is_locked, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'USD', ?, ?, ?, 0, ?, ?)
        """, (
            contract_id, buyer.id, seller_id, title, description, status,
            total_amount, deadline, figma_url, repo_url, timestamp, timestamp
        ))

        # Record creation event in messages table
        cursor.execute("""
            INSERT INTO messages (id, contract_id, sender_id, sender_type, content, metadata, sent_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            generate_uuid(), contract_id, buyer.id, "BUYER",
            f"Contract '{title}' drafted by buyer.", json.dumps({"action": "CONTRACT_CREATED", "status": "DRAFT"}), timestamp
        ))

        self.conn.commit()
        return self.get_contract(contract_id)

    def get_contract(self, contract_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM contracts WHERE id = ?", (contract_id,))
        row = cursor.fetchone()
        if not row:
            return None
        contract = dict(row)
        contract["is_locked"] = bool(contract.get("is_locked", 0))
        contract["features"] = self.get_features(contract_id)
        return contract

    # --- Dual Confirmation & Checklist Locking (Task C19) ---
    def confirm_checklist(self, contract_id: str, actor: User) -> Dict[str, Any]:
        """
        Registers timestamped confirmation from Buyer or Seller.
        When BOTH parties confirm, the checklist transitions to LOCKED status.
        """
        contract = self.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract '{contract_id}' not found.")

        timestamp = now_iso()
        cursor = self.conn.cursor()

        if actor.role == UserRole.BUYER:
            if contract.get("buyer_id") != actor.id:
                raise ChecklistLockError("Actor is not the designated buyer for this contract.")
            cursor.execute("UPDATE contracts SET buyer_confirmed_at = ?, updated_at = ? WHERE id = ?", (timestamp, timestamp, contract_id))
        elif actor.role == UserRole.SELLER:
            if contract.get("seller_id") != actor.id:
                raise ChecklistLockError("Actor is not the designated seller for this contract.")
            cursor.execute("UPDATE contracts SET seller_confirmed_at = ?, updated_at = ? WHERE id = ?", (timestamp, timestamp, contract_id))
        else:
            raise ChecklistLockError(f"Role '{actor.role.value}' cannot confirm checklist. Only BUYER and SELLER can confirm.")

        # Check if both confirmations are now recorded
        updated = self.get_contract(contract_id)
        if updated.get("buyer_confirmed_at") and updated.get("seller_confirmed_at"):
            cursor.execute("UPDATE contracts SET is_locked = 1, locked_at = ?, updated_at = ? WHERE id = ?", (timestamp, timestamp, contract_id))
            cursor.execute("""
                INSERT INTO messages (id, contract_id, sender_id, sender_type, content, metadata, sent_at)
                VALUES (?, ?, NULL, 'AI_REFEREE', ?, ?, ?)
            """, (
                generate_uuid(), contract_id,
                "Checklist LOCKED by timestamped dual confirmation. Features cannot change except via the Price Negotiator.",
                json.dumps({"event": "CHECKLIST_LOCKED", "buyer_confirmed_at": updated["buyer_confirmed_at"], "seller_confirmed_at": updated["seller_confirmed_at"]}),
                timestamp
            ))

        self.conn.commit()
        return self.get_contract(contract_id)

    # --- Feature Checklist Items with Lock Guard ---
    def add_feature(
        self,
        contract_id: str,
        title: str,
        acceptance_test: str,
        price_weight: float,
        allocated_amount: float,
        sort_order: int = 0,
        source: str = "DIRECT",
        change_request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Adds a checklist feature.
        Invariant (C19): Once locked, checklist cannot change except via the Price Negotiator.
        """
        contract = self.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract '{contract_id}' not found.")

        # Lock Guard: Block direct edits if locked
        if contract.get("is_locked"):
            if source != "PRICE_NEGOTIATOR" or not change_request_id:
                raise ChecklistLockError(
                    f"Checklist for contract '{contract_id}' is LOCKED by dual confirmation. "
                    "Checklist cannot change except via the Price Negotiator with an approved change request."
                )

        feature_id = generate_uuid()
        timestamp = now_iso()
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO features (
                id, contract_id, title, acceptance_test, price_weight,
                allocated_amount, status, sort_order, change_request_id, amended,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?, ?)
        """, (
            feature_id, contract_id, title, acceptance_test,
            price_weight, allocated_amount, sort_order,
            change_request_id, 1 if change_request_id else 0,
            timestamp, timestamp
        ))
        self.conn.commit()
        return {
            "id": feature_id,
            "contract_id": contract_id,
            "title": title,
            "acceptance_test": acceptance_test,
            "price_weight": price_weight,
            "allocated_amount": allocated_amount,
            "status": "PENDING",
            "sort_order": sort_order,
            "change_request_id": change_request_id,
            "amended": bool(change_request_id)
        }

    def get_features(self, contract_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM features WHERE contract_id = ? ORDER BY sort_order ASC", (contract_id,))
        return [dict(r) for r in cursor.fetchall()]

    # --- State Machine Transition ---
    def transition_contract(
        self,
        contract_id: str,
        actor: User,
        target_state: ContractState,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes state machine validation and persists updated status in the database.
        """
        contract = self.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract with ID '{contract_id}' not found.")

        # 1. State Machine Engine Validation (checks graph, roles, and data guards)
        updates = ContractStateMachine.validate_transition(
            contract=contract,
            actor=actor,
            target_state=target_state,
            metadata=metadata
        )

        # 2. Persist State Changes
        cursor = self.conn.cursor()
        set_clauses = [f"{k} = ?" for k in updates.keys()]
        values = list(updates.values())
        values.append(contract_id)

        sql = f"UPDATE contracts SET {', '.join(set_clauses)} WHERE id = ?"
        cursor.execute(sql, values)

        # 3. Log Audit Message
        sender_type = actor.role.value
        sender_id = actor.id if self.get_user(actor.id) else None
        cursor.execute("""
            INSERT INTO messages (id, contract_id, sender_id, sender_type, content, metadata, sent_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            generate_uuid(),
            contract_id,
            sender_id,
            sender_type,
            f"State transitioned from {contract['status']} to {target_state.value} by {actor.name}.",
            json.dumps({"transition": f"{contract['status']} -> {target_state.value}", "metadata": metadata or {}}),
            now_iso()
        ))

        self.conn.commit()

        # 4. Trigger Automated Email Notifications (Commit C51)
        if getattr(self, "notification_service", None) is not None:
            try:
                state_val = target_state.value if hasattr(target_state, "value") else str(target_state)
                self.notification_service.notify_state_change(
                    contract_id=contract_id,
                    new_state=state_val,
                    metadata=metadata,
                    actor=actor
                )
            except Exception:
                pass

        return self.get_contract(contract_id)

    def set_notification_service(self, notification_service: Any) -> None:
        """Attaches automated notification service for state transitions (Commit C51)."""
        self.notification_service = notification_service

    def get_contract_notifications(self, contract_id: str) -> List[Dict[str, Any]]:
        """Retrieves all email notification audit events for a contract from messages table (Commit C51)."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM messages
            WHERE contract_id = ? AND metadata LIKE '%EMAIL_NOTIFICATION_SENT%'
            ORDER BY sent_at ASC
        """, (contract_id,))
        records = []
        for row in cursor.fetchall():
            rec = dict(row)
            if isinstance(rec.get("metadata"), str):
                try:
                    rec["metadata"] = json.loads(rec["metadata"])
                except Exception:
                    pass
            meta = rec.get("metadata", {})
            records.append({
                "id": rec["id"],
                "contract_id": contract_id,
                "recipient_email": meta.get("recipient_email"),
                "recipient_name": meta.get("recipient_name"),
                "role": meta.get("role"),
                "state_transition": meta.get("state_transition"),
                "subject": meta.get("subject"),
                "delivery_status": meta.get("delivery_status"),
                "message_id": meta.get("message_id"),
                "provider": meta.get("provider"),
                "sent_at": meta.get("sent_at") or rec["sent_at"]
            })
        return records

    # --- Payment Ledger Management (C24) ---
    def record_payment(
        self,
        contract_id: str,
        payment_type: str,
        paypal_reference_id: str,
        amount: float,
        currency: str = "USD",
        status: str = "COMPLETED",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Inserts a payment ledger entry into the relational payments table.
        Valid payment types: AUTHORIZATION, CAPTURE, PAYOUT, REFUND, VOID.
        """
        payment_id = generate_uuid()
        timestamp = now_iso()
        meta_str = json.dumps(metadata or {})
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO payments (
                id, contract_id, payment_type, paypal_reference_id,
                amount, currency, status, metadata, processed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payment_id, contract_id, payment_type, paypal_reference_id,
            float(amount), currency, status, meta_str, timestamp
        ))
        self.conn.commit()
        return {
            "id": payment_id,
            "contract_id": contract_id,
            "payment_type": payment_type,
            "paypal_reference_id": paypal_reference_id,
            "amount": float(amount),
            "currency": currency,
            "status": status,
            "metadata": metadata or {},
            "processed_at": timestamp
        }

    def get_payments(self, contract_id: str) -> List[Dict[str, Any]]:
        """Retrieves all payment records for a contract in chronological order."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM payments WHERE contract_id = ? ORDER BY processed_at ASC", (contract_id,))
        records = []
        for row in cursor.fetchall():
            rec = dict(row)
            if isinstance(rec.get("metadata"), str):
                try:
                    rec["metadata"] = json.loads(rec["metadata"])
                except Exception:
                    pass
            records.append(rec)
        return records

    # --- Message Ledger & Settlement Summary Audit (C41) ---
    def record_message(
        self,
        contract_id: str,
        content: str,
        sender_type: str,
        sender_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Inserts an immutable message / audit record into the relational messages table.
        """
        msg_id = generate_uuid()
        timestamp = now_iso()
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO messages (id, contract_id, sender_id, sender_type, content, metadata, sent_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            msg_id,
            contract_id,
            sender_id if (sender_id and self.get_user(sender_id)) else None,
            sender_type,
            content,
            json.dumps(metadata or {}),
            timestamp
        ))
        self.conn.commit()
        return {
            "id": msg_id,
            "contract_id": contract_id,
            "sender_id": sender_id,
            "sender_type": sender_type,
            "content": content,
            "metadata": metadata or {},
            "sent_at": timestamp
        }

    def get_messages(self, contract_id: str) -> List[Dict[str, Any]]:
        """Retrieves all messages/audit logs for a contract in chronological order."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE contract_id = ? ORDER BY sent_at ASC", (contract_id,))
        records = []
        for row in cursor.fetchall():
            rec = dict(row)
            if isinstance(rec.get("metadata"), str):
                try:
                    rec["metadata"] = json.loads(rec["metadata"])
                except Exception:
                    pass
            records.append(rec)
        return records

    # --- Receipt Ledger Management (C41 / C44) ---
    def record_receipt(
        self,
        contract_id: str,
        receipt_hash: str,
        evidence_payload: Dict[str, Any],
        submission_id: Optional[str] = None,
        verification_report_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Records a cryptographic receipt fingerprint linking to proof-of-work evidence."""
        receipt_id = generate_uuid()
        timestamp = now_iso()
        cursor = self.conn.cursor()
        payload_str = json.dumps(evidence_payload) if not isinstance(evidence_payload, str) else evidence_payload
        cursor.execute("""
            INSERT OR REPLACE INTO receipts (id, contract_id, submission_id, verification_report_id, receipt_hash, evidence_payload, generated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            receipt_id, contract_id, submission_id, verification_report_id, receipt_hash, payload_str, timestamp
        ))
        self.conn.commit()
        return {
            "id": receipt_id,
            "contract_id": contract_id,
            "receipt_hash": receipt_hash,
            "submission_id": submission_id,
            "verification_report_id": verification_report_id,
            "evidence_payload": evidence_payload,
            "generated_at": timestamp
        }

    def get_receipt(self, contract_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the latest receipt record for a given contract."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM receipts WHERE contract_id = ? ORDER BY generated_at DESC LIMIT 1", (contract_id,))
        row = cursor.fetchone()
        if not row:
            return None
        rec = dict(row)
        if isinstance(rec.get("evidence_payload"), str):
            try:
                rec["evidence_payload"] = json.loads(rec["evidence_payload"])
            except Exception:
                pass
        return rec

    def get_receipt_by_hash(self, receipt_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieves a receipt record by its unique cryptographic receipt hash."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM receipts WHERE receipt_hash = ? LIMIT 1", (receipt_hash,))
        row = cursor.fetchone()
        if not row:
            return None
        rec = dict(row)
        if isinstance(rec.get("evidence_payload"), str):
            try:
                rec["evidence_payload"] = json.loads(rec["evidence_payload"])
            except Exception:
                pass
        return rec

    # --- Idempotency Key Storage (C28) ---
    def get_idempotency_key(self, key: str, scope: str = "default") -> Optional[Dict[str, Any]]:
        """Retrieves a previously cached response by idempotency key and scope."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM idempotency_keys WHERE key = ? AND scope = ?", (key, scope))
        row = cursor.fetchone()
        if not row:
            return None
        res_data = row["response_data"]
        try:
            parsed = json.loads(res_data)
        except Exception:
            parsed = res_data
        return {
            "key": row["key"],
            "scope": row["scope"],
            "response_data": parsed,
            "status_code": row["status_code"],
            "created_at": row["created_at"]
        }

    def save_idempotency_key(self, key: str, scope: str, response_data: Any, status_code: int = 200) -> None:
        """Stores a response against an idempotency key and scope to prevent duplicate actions."""
        cursor = self.conn.cursor()
        meta_str = json.dumps(response_data) if not isinstance(response_data, str) else response_data
        timestamp = now_iso()
        cursor.execute("""
            INSERT OR REPLACE INTO idempotency_keys (key, scope, response_data, status_code, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (key, scope, meta_str, status_code, timestamp))
        self.conn.commit()

    # --- Verification Reports & Deliverable Evidence (C31) ---
    def save_verification_report(
        self,
        contract_id: str,
        submission_id: Optional[str] = None,
        report_id: Optional[str] = None,
        render_job_id: Optional[str] = None,
        build_succeeded: bool = True,
        build_logs: str = "",
        test_suite_results: Optional[Any] = None,
        cheat_scan_findings: Optional[Any] = None,
        visual_diff_summary: Optional[Any] = None,
        per_feature_results: Optional[Any] = None,
        overall_score: Optional[float] = 1.0,
        completed_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Persists a multi-modal verification report matching core schema.
        Ensures foreign key relations with submissions and contracts.
        """
        contract = self.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract '{contract_id}' not found.")

        cursor = self.conn.cursor()
        sub_id = submission_id
        timestamp = completed_at or now_iso()

        # Ensure submission parent record exists
        if not sub_id:
            sub_id = generate_uuid()
            cursor.execute("""
                INSERT INTO submissions (id, contract_id, seller_id, repo_url, commit_sha, build_notes, submitted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (sub_id, contract_id, contract.get("seller_id"), contract.get("repo_url") or "", "head", "Automated intake", timestamp))

        rep_id = report_id or generate_uuid()
        tests_json = json.dumps(test_suite_results or {}) if not isinstance(test_suite_results, str) else test_suite_results
        cheat_json = json.dumps(cheat_scan_findings or []) if not isinstance(cheat_scan_findings, str) else cheat_scan_findings
        vision_json = json.dumps(visual_diff_summary or {}) if not isinstance(visual_diff_summary, str) else visual_diff_summary
        features_json = json.dumps(per_feature_results or {}) if not isinstance(per_feature_results, str) else per_feature_results

        cursor.execute("""
            INSERT OR REPLACE INTO verification_reports (
                id, submission_id, contract_id, render_job_id, build_succeeded,
                build_logs, test_suite_results, cheat_scan_findings, visual_diff_summary,
                per_feature_results, overall_score, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rep_id, sub_id, contract_id, render_job_id or f"job_{rep_id[:8]}",
            1 if build_succeeded else 0, build_logs, tests_json, cheat_json,
            vision_json, features_json, overall_score, timestamp
        ))
        self.conn.commit()

        return self.get_latest_verification_report(contract_id) or {
            "id": rep_id,
            "contract_id": contract_id,
            "submission_id": sub_id,
            "build_succeeded": bool(build_succeeded),
            "completed_at": timestamp
        }

    def get_latest_verification_report(self, contract_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the latest completed verification report for a contract."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM verification_reports WHERE contract_id = ? ORDER BY completed_at DESC LIMIT 1",
            (contract_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        rec = dict(row)
        rec["build_succeeded"] = bool(rec.get("build_succeeded", 0))

        # Parse JSON fields
        for field_name in ("test_suite_results", "cheat_scan_findings", "visual_diff_summary", "per_feature_results"):
            raw_val = rec.get(field_name)
            if isinstance(raw_val, str):
                try:
                    rec[field_name] = json.loads(raw_val)
                except Exception:
                    rec[field_name] = {} if field_name != "cheat_scan_findings" else []

        return rec

    def get_submission(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a deliverable submission by primary ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM submissions WHERE id = ? LIMIT 1", (submission_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_latest_submission(self, contract_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the latest deliverable submission for a contract."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM submissions WHERE contract_id = ? ORDER BY submitted_at DESC LIMIT 1",
            (contract_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def create_submission(
        self,
        contract_id: str,
        seller_id: str,
        repo_url: str = "https://github.com/pactpal/deliverable",
        commit_sha: str = "c049dead11",
        build_notes: str = "Deliverable submission for milestone verification",
        submission_number: int = 1,
        is_late: bool = False,
        submitted_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a submission record in the submissions table."""
        sub_id = generate_uuid()
        timestamp = submitted_at or now_iso()
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO submissions (id, contract_id, seller_id, repo_url, commit_sha, build_notes, submission_number, is_late, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (sub_id, contract_id, seller_id, repo_url, commit_sha, build_notes, submission_number, 1 if is_late else 0, timestamp))
        self.conn.commit()
        return self.get_submission(sub_id)

    def create_change_request(
        self,
        contract_id: str,
        proposed_by_id: str,
        description: str,
        proposed_price: float,
        proposed_extra_time_hours: int = 0,
        ai_reasoning: Optional[str] = None,
        status: str = "PROPOSED",
        additional_auth_id: Optional[str] = None,
        change_request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a change request record in the change_requests table (Commit C46)."""
        cr_id = change_request_id or generate_uuid()
        timestamp = now_iso()
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO change_requests (
                id, contract_id, proposed_by_id, description, proposed_price,
                proposed_extra_time_hours, ai_reasoning, status, additional_auth_id,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cr_id, contract_id, proposed_by_id, description, float(proposed_price),
            int(proposed_extra_time_hours), ai_reasoning, status, additional_auth_id,
            timestamp, timestamp
        ))
        self.conn.commit()
        return self.get_change_request(cr_id) or {
            "id": cr_id,
            "contract_id": contract_id,
            "proposed_by_id": proposed_by_id,
            "description": description,
            "proposed_price": float(proposed_price),
            "proposed_extra_time_hours": int(proposed_extra_time_hours),
            "ai_reasoning": ai_reasoning,
            "status": status,
            "additional_auth_id": additional_auth_id,
            "created_at": timestamp,
            "updated_at": timestamp
        }

    def get_change_request(self, change_request_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a change request by primary ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM change_requests WHERE id = ? LIMIT 1", (change_request_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_change_requests(self, contract_id: str) -> List[Dict[str, Any]]:
        """Retrieves all change requests associated with a contract."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM change_requests WHERE contract_id = ? ORDER BY created_at ASC", (contract_id,))
        return [dict(row) for row in cursor.fetchall()]

    def update_change_request(
        self,
        change_request_id: str,
        status: Optional[str] = None,
        additional_auth_id: Optional[str] = None,
        ai_reasoning: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Updates status, additional_auth_id, and/or reasoning on a change request."""
        updates = []
        params = []
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if additional_auth_id is not None:
            updates.append("additional_auth_id = ?")
            params.append(additional_auth_id)
        if ai_reasoning is not None:
            updates.append("ai_reasoning = ?")
            params.append(ai_reasoning)

        if not updates:
            return self.get_change_request(change_request_id)

        updates.append("updated_at = ?")
        params.append(now_iso())
        params.append(change_request_id)

        sql = f"UPDATE change_requests SET {', '.join(updates)} WHERE id = ?"
        cursor = self.conn.cursor()
        cursor.execute(sql, tuple(params))
        self.conn.commit()
        return self.get_change_request(change_request_id)

    def update_contract_hold(
        self,
        contract_id: str,
        total_amount: float,
        paypal_auth_id: Optional[str] = None,
        auth_expires_at: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Updates total_amount, paypal_auth_id, and auth_expires_at for a contract (Commit C46)."""
        updates = ["total_amount = ?", "updated_at = ?"]
        params = [float(total_amount), now_iso()]

        if paypal_auth_id is not None:
            updates.append("paypal_auth_id = ?")
            params.append(paypal_auth_id)
        if auth_expires_at is not None:
            updates.append("auth_expires_at = ?")
            params.append(auth_expires_at)

        params.append(contract_id)
        sql = f"UPDATE contracts SET {', '.join(updates)} WHERE id = ?"
        cursor = self.conn.cursor()
        cursor.execute(sql, tuple(params))
        self.conn.commit()
        return self.get_contract(contract_id)

    # --- Active Contracts & Status Queries (Commit C49) ---
    def get_contracts_by_status(self, statuses: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Retrieves contracts matching a given list of statuses (or all contracts if None),
        ordered by deadline ASC, created_at DESC.
        """
        cursor = self.conn.cursor()
        if not statuses:
            cursor.execute("SELECT * FROM contracts ORDER BY deadline ASC, created_at DESC")
        else:
            placeholders = ",".join("?" for _ in statuses)
            sql = f"SELECT * FROM contracts WHERE status IN ({placeholders}) ORDER BY deadline ASC, created_at DESC"
            cursor.execute(sql, tuple(statuses))
        rows = cursor.fetchall()
        contracts: List[Dict[str, Any]] = []
        for row in rows:
            contract = dict(row)
            contract["is_locked"] = bool(contract.get("is_locked", 0))
            contract["features"] = self.get_features(contract["id"])
            contracts.append(contract)
        return contracts

    def get_active_contracts(self, statuses: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Retrieves active contracts subject to automated deadline monitoring.
        Defaults to ('IN_PROGRESS', 'SUBMITTED', 'VERIFYING').
        """
        target_statuses = statuses or ["IN_PROGRESS", "SUBMITTED", "VERIFYING"]
        return self.get_contracts_by_status(target_statuses)

    def close(self):
        self.conn.close()
