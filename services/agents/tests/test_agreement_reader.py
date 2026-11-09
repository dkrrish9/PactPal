#!/usr/bin/env python3
"""
PactPal Milestone 1: Agreement Reader Acceptance Test (Task C12)
Validates that:
1. Form fields are converted into a priced checklist.
2. Each feature has an acceptance test, price weight, allocated amount, and deadline.
3. Auto-validation enforces 100% weight sum, valid future deadlines, and non-empty tests.
4. Generates actionable clarification prompts on failure.
5. Locks checklist upon dual confirmation.
"""

import unittest
from datetime import datetime, timezone, timedelta

from ..agreement_reader.models import PricedChecklist, ChecklistFeature
from ..agreement_reader.reader import parse_contract_form, AgreementValidationError
from ..agreement_reader.validator import validate_contract_form
from ..agreement_reader.lock import lock_checklist, assert_checklist_is_unlocked, ChecklistLockError

class TestAgreementReader(unittest.TestCase):

    def setUp(self):
        # Reference future date for test stability
        self.future_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        self.valid_form = {
            "title": "PactPal Freelance Milestone",
            "description": "Develop 4 core features matching Figma mockups.",
            "total_amount": 1000.00,
            "currency": "USD",
            "deadline": self.future_date,
            "features": [
                {
                    "name": "Landing page",
                    "weight": 25.0,
                    "test": "All sections render, CTA links work, responsive mobile view verified."
                },
                {
                    "name": "Login system",
                    "weight": 20.0,
                    "test": "Login/logout with JWT authentication; persistent session storage verified."
                },
                {
                    "name": "Dashboard",
                    "weight": 30.0,
                    "test": "Bryntum Gantt chart loads contract data with zero console errors."
                },
                {
                    "name": "Payment flow",
                    "weight": 25.0,
                    "test": "PayPal checkout triggers authorize intent; receipt hash is recorded."
                }
            ]
        }

    def test_turns_form_into_priced_checklist(self):
        """
        Checklist Acceptance Test (C12 Done When):
        Each feature has acceptance test, price weight and deadline.
        """
        checklist: PricedChecklist = parse_contract_form(self.valid_form)

        # Assert top-level attributes
        self.assertEqual(checklist.title, "PactPal Freelance Milestone")
        self.assertEqual(checklist.total_amount, 1000.00)
        self.assertEqual(checklist.currency, "USD")
        self.assertEqual(checklist.deadline, self.future_date)
        self.assertFalse(checklist.is_locked)
        self.assertEqual(len(checklist.features), 4)

        # Assert every feature satisfies C12 acceptance criteria
        total_weight = 0.0
        total_allocated = 0.0

        for idx, feat in enumerate(checklist.features):
            # 1. Has non-empty acceptance test
            self.assertTrue(len(feat.acceptance_test.strip()) > 10, f"Feature {feat.title} missing test")
            # 2. Has price weight > 0
            self.assertTrue(feat.price_weight > 0, f"Feature {feat.title} missing weight")
            # 3. Has allocated dollar amount
            self.assertTrue(feat.allocated_amount > 0, f"Feature {feat.title} missing allocated amount")
            # 4. Has future deadline
            self.assertEqual(feat.deadline, self.future_date)
            # 5. Status initialized to PENDING
            self.assertEqual(feat.status, "PENDING")

            total_weight += feat.price_weight
            total_allocated += feat.allocated_amount

        # Assert mathematical invariants
        self.assertAlmostEqual(total_weight, 100.0, places=2)
        self.assertAlmostEqual(total_allocated, 1000.0, places=2)

    def test_penny_rounding_conservation(self):
        """Ensures penny rounding assigns remainders to guarantee exact sum = total_amount."""
        odd_form = {
            "title": "Split Milestone",
            "total_amount": 100.00,
            "currency": "USD",
            "deadline": self.future_date,
            "features": [
                {"name": "Item 1", "weight": 33.33, "test": "Test condition 1"},
                {"name": "Item 2", "weight": 33.33, "test": "Test condition 2"},
                {"name": "Item 3", "weight": 33.34, "test": "Test condition 3"}
            ]
        }
        checklist = parse_contract_form(odd_form)
        allocated_sum = sum(f.allocated_amount for f in checklist.features)
        self.assertEqual(allocated_sum, 100.00)

    def test_auto_validation_fails_when_weights_not_100(self):
        """Weights sum != 100% must raise AgreementValidationError with actionable clarification."""
        invalid_form = dict(self.valid_form)
        invalid_form["features"] = [
            {"name": "Item 1", "weight": 40.0, "test": "Test 1"},
            {"name": "Item 2", "weight": 50.0, "test": "Test 2"}  # Sums to 90%!
        ]

        with self.assertRaises(AgreementValidationError) as ctx:
            parse_contract_form(invalid_form)

        error = ctx.exception
        self.assertTrue(any("must sum to exactly 100.0%" in e for e in error.errors))
        self.assertTrue(any("+10.0%" in c.suggested_action for c in error.clarifications))

    def test_auto_validation_fails_on_missing_acceptance_test(self):
        """Missing acceptance test must fail with clarification naming the specific feature."""
        invalid_form = dict(self.valid_form)
        invalid_form["features"] = [
            {"name": "Landing page", "weight": 50.0, "test": "Valid test"},
            {"name": "Vague feature", "weight": 50.0, "test": "   "}  # Empty test!
        ]

        with self.assertRaises(AgreementValidationError) as ctx:
            parse_contract_form(invalid_form)

        error = ctx.exception
        self.assertTrue(any("Vague feature" in e and "missing a measurable acceptance test" in e for e in error.errors))

    def test_auto_validation_fails_on_past_deadline(self):
        """Past deadline must be rejected with future date guidance."""
        past_form = dict(self.valid_form)
        past_form["deadline"] = "2020-01-01T00:00:00Z"

        with self.assertRaises(AgreementValidationError) as ctx:
            parse_contract_form(past_form)

        error = ctx.exception
        self.assertTrue(any("is in the past" in e for e in error.errors))

    def test_dual_confirmation_checklist_lock(self):
        """Locked checklist requires dual confirmation and blocks mutations."""
        checklist = parse_contract_form(self.valid_form)
        self.assertFalse(checklist.is_locked)

        # Dual confirmation
        now_str = datetime.now(timezone.utc).isoformat()
        locked = lock_checklist(
            checklist,
            buyer_confirmed_at=now_str,
            seller_confirmed_at=now_str
        )

        self.assertTrue(locked.is_locked)
        self.assertIsNotNone(locked.locked_at)
        self.assertEqual(locked.buyer_confirmed_at, now_str)
        self.assertEqual(locked.seller_confirmed_at, now_str)

        # Attempting modification on locked checklist must raise ChecklistLockError
        with self.assertRaises(ChecklistLockError):
            assert_checklist_is_unlocked(locked)

    def test_dual_confirmation_requires_both_parties(self):
        """Locking without seller confirmation timestamp must fail."""
        checklist = parse_contract_form(self.valid_form)
        with self.assertRaises(ChecklistLockError):
            lock_checklist(checklist, buyer_confirmed_at="2026-11-10T00:00:00Z", seller_confirmed_at="")

if __name__ == "__main__":
    unittest.main()

