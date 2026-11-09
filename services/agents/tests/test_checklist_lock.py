#!/usr/bin/env python3
"""
PactPal Milestone 1: Checklist Lock Acceptance Test (Task C19)
Validates that:
1. Both Buyer and Seller must submit timestamped confirmations.
2. Dual confirmation locks the checklist as the single source of truth.
3. Once locked, the checklist CANNOT change directly by buyers or sellers.
4. The ONLY entity permitted to amend a locked checklist is the AI Price Negotiator via a formal change request.
"""

import unittest
from datetime import datetime, timezone, timedelta

from ..agreement_reader.models import PricedChecklist, ChecklistFeature
from ..agreement_reader.reader import parse_contract_form
from ..agreement_reader.lock import (
    confirm_party,
    lock_checklist,
    assert_can_modify_checklist,
    apply_negotiated_amendment,
    ChecklistLockError
)

class TestChecklistLock(unittest.TestCase):

    def setUp(self):
        self.future_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        self.form_data = {
            "title": "Zero-Trust Freelance Escrow Milestone",
            "total_amount": 1000.00,
            "currency": "USD",
            "deadline": self.future_date,
            "features": [
                {"name": "Frontend UI", "weight": 40.0, "test": "Renders responsive dashboard"},
                {"name": "Backend API", "weight": 60.0, "test": "Passes all pytest assertions"}
            ]
        }
        self.checklist: PricedChecklist = parse_contract_form(self.form_data)

    def test_dual_confirmation_lifecycle(self):
        """
        Step 1: Buyer confirms -> Still unlocked (waiting for seller).
        Step 2: Seller confirms -> Locked with dual timestamps!
        """
        self.assertFalse(self.checklist.is_locked)
        now_ts = datetime.now(timezone.utc).isoformat()

        # Buyer confirms
        confirm_party(self.checklist, actor_id="buyer_001", actor_role="BUYER", timestamp=now_ts)
        self.assertEqual(self.checklist.buyer_confirmed_at, now_ts)
        self.assertIsNone(self.checklist.seller_confirmed_at)
        self.assertFalse(self.checklist.is_locked, "Checklist must remain unlocked until seller confirms")

        # Seller confirms
        confirm_party(self.checklist, actor_id="seller_001", actor_role="SELLER", timestamp=now_ts)
        self.assertEqual(self.checklist.seller_confirmed_at, now_ts)
        self.assertTrue(self.checklist.is_locked, "Checklist must be locked once both parties confirm")
        self.assertIsNotNone(self.checklist.locked_at)

    def test_direct_modification_blocked_when_locked(self):
        """
        Checklist Acceptance Test (C19 Done When):
        Once locked, direct modification by buyer, seller, or direct API is BLOCKED.
        """
        now_ts = datetime.now(timezone.utc).isoformat()
        confirm_party(self.checklist, actor_id="buyer_001", actor_role="BUYER", timestamp=now_ts)
        confirm_party(self.checklist, actor_id="seller_001", actor_role="SELLER", timestamp=now_ts)
        self.assertTrue(self.checklist.is_locked)

        # Buyer tries to directly alter features
        with self.assertRaises(ChecklistLockError) as ctx:
            assert_can_modify_checklist(self.checklist, source="DIRECT")
        self.assertIn("LOCKED by timestamped dual confirmation", str(ctx.exception))
        self.assertIn("ONLY via the Price Negotiator", str(ctx.exception))

        # Direct amendment attempt without negotiator authorization fails
        amendment_item = ChecklistFeature(
            id="feat_extra",
            title="Extra Feature",
            acceptance_test="Extra test",
            price_weight=10.0,
            allocated_amount=100.0,
            deadline=self.future_date
        )
        with self.assertRaises(ChecklistLockError):
            apply_negotiated_amendment(self.checklist, amendment_item, change_request_id="", source="DIRECT")

    def test_price_negotiator_can_amend_locked_checklist(self):
        """
        The ONLY permitted exception:
        The Price Negotiator with a valid change_request_id can add new checklist features.
        """
        now_ts = datetime.now(timezone.utc).isoformat()
        confirm_party(self.checklist, actor_id="buyer_001", actor_role="BUYER", timestamp=now_ts)
        confirm_party(self.checklist, actor_id="seller_001", actor_role="SELLER", timestamp=now_ts)
        self.assertTrue(self.checklist.is_locked)

        initial_count = len(self.checklist.features)
        amended_feature = ChecklistFeature(
            id="feat_cr_101",
            title="Negotiated Dark Mode",
            acceptance_test="Dark mode toggle persists in localStorage",
            price_weight=15.0,
            allocated_amount=150.0,
            deadline=self.future_date
        )

        # Apply through official Price Negotiator channel
        apply_negotiated_amendment(
            checklist=self.checklist,
            amendment_feature=amended_feature,
            change_request_id="CR-9001",
            source="PRICE_NEGOTIATOR"
        )

        self.assertEqual(len(self.checklist.features), initial_count + 1)
        added = self.checklist.features[-1]
        self.assertEqual(added.title, "Negotiated Dark Mode")
        self.assertEqual(added.change_request_id, "CR-9001")
        self.assertTrue(added.amended)

    def test_dual_confirmation_fails_on_invalid_role(self):
        """Attempting confirmation with a non-party role raises ChecklistLockError."""
        with self.assertRaises(ChecklistLockError):
            confirm_party(self.checklist, actor_id="guest_001", actor_role="AUDITOR")

if __name__ == "__main__":
    unittest.main()
