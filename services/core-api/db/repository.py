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
        cursor.execute("""
            INSERT INTO messages (id, contract_id, sender_id, sender_type, content, metadata, sent_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            generate_uuid(),
            contract_id,
            actor.id,
            sender_type,
            f"State transitioned from {contract['status']} to {target_state.value} by {actor.name}.",
            json.dumps({"transition": f"{contract['status']} -> {target_state.value}", "metadata": metadata or {}}),
            now_iso()
        ))

        self.conn.commit()
        return self.get_contract(contract_id)

    def close(self):
        self.conn.close()
