#!/usr/bin/env python3
"""
PactPal Milestone 1: Automated Acceptance Test (Task C09)
Validates that a contract moves DRAFT -> REVIEW -> SIGNED -> FUNDED in the database
with strict role enforcement and state machine rules.
"""

import unittest
from datetime import datetime, timezone, timedelta

from ..auth.roles import (
    UserRole,
    UnauthorizedRoleError,
    ForbiddenActionError
)
from ..state_machine.engine import (
    ContractState,
    InvalidStateTransitionError,
    StateValidationError
)
from ..db.repository import ContractRepository

class TestContractLifecycle(unittest.TestCase):

    def setUp(self):
        """Set up in-memory database and test users for each test."""
        self.repo = ContractRepository(db_path=":memory:")
        self.buyer = self.repo.create_user(
            name="Alice Buyer",
            email="alice@buyer.example.com",
            role=UserRole.BUYER,
            paypal_email="alice.buyer@paypal.example.com"
        )
        self.seller = self.repo.create_user(
            name="Bob Freelancer",
            email="bob@seller.example.com",
            role=UserRole.SELLER,
            paypal_email="bob.seller@paypal.example.com"
        )
        self.charlie_stranger = self.repo.create_user(
            name="Charlie Stranger",
            email="charlie@thirdparty.example.com",
            role=UserRole.BUYER
        )

    def tearDown(self):
        self.repo.close()

    def test_happy_path_draft_to_review_to_signed_to_funded(self):
        """
        Checklist Acceptance Test:
        Contract moves Draft -> Review -> Signed -> Funded in the DB; roles enforced.
        """
        # Step 1: Buyer creates contract in DRAFT
        contract = self.repo.create_contract(
            buyer=self.buyer,
            seller_id=self.seller.id,
            title="SaaS Landing Page & Auth",
            description="Build 2 features matching design.",
            total_amount=1000.00,
            deadline="2026-12-01T00:00:00Z"
        )
        self.assertEqual(contract["status"], ContractState.DRAFT.value)
        self.assertEqual(contract["buyer_id"], self.buyer.id)
        self.assertEqual(contract["seller_id"], self.seller.id)

        # Add features
        self.repo.add_feature(contract["id"], "Hero Section", "Renders CTA", 40.00, 400.00, 1)
        self.repo.add_feature(contract["id"], "Auth Form", "Validates login", 60.00, 600.00, 2)

        # Step 2: Buyer submits contract: DRAFT -> REVIEW
        contract = self.repo.transition_contract(
            contract_id=contract["id"],
            actor=self.buyer,
            target_state=ContractState.REVIEW
        )
        self.assertEqual(contract["status"], ContractState.REVIEW.value)

        # Step 3: Seller signs contract: REVIEW -> SIGNED
        contract = self.repo.transition_contract(
            contract_id=contract["id"],
            actor=self.seller,
            target_state=ContractState.SIGNED
        )
        self.assertEqual(contract["status"], ContractState.SIGNED.value)

        # Step 4: Buyer funds contract: SIGNED -> FUNDED with PayPal Authorization
        funding_meta = {
            "paypal_order_id": "ORDER_PP_9999",
            "paypal_auth_id": "AUTH_PP_8888"
        }
        contract = self.repo.transition_contract(
            contract_id=contract["id"],
            actor=self.buyer,
            target_state=ContractState.FUNDED,
            metadata=funding_meta
        )
        self.assertEqual(contract["status"], ContractState.FUNDED.value)
        self.assertEqual(contract["paypal_order_id"], "ORDER_PP_9999")
        self.assertEqual(contract["paypal_auth_id"], "AUTH_PP_8888")
        self.assertIsNotNone(contract["auth_expires_at"])

        # Verify persisted state directly from DB
        db_contract = self.repo.get_contract(contract["id"])
        self.assertEqual(db_contract["status"], ContractState.FUNDED.value)
        self.assertEqual(len(db_contract["features"]), 2)

    def test_role_enforcement_seller_cannot_fund(self):
        """Seller attempting to fund escrow must be rejected."""
        contract = self.repo.create_contract(
            buyer=self.buyer, seller_id=self.seller.id, title="Test",
            description="Desc", total_amount=500.00, deadline="2026-12-01T00:00:00Z"
        )
        self.repo.transition_contract(contract["id"], self.buyer, ContractState.REVIEW)
        self.repo.transition_contract(contract["id"], self.seller, ContractState.SIGNED)

        with self.assertRaises(UnauthorizedRoleError):
            self.repo.transition_contract(
                contract_id=contract["id"],
                actor=self.seller,  # SELLER tries to fund!
                target_state=ContractState.FUNDED,
                metadata={"paypal_order_id": "O", "paypal_auth_id": "A"}
            )

    def test_role_enforcement_buyer_cannot_sign_as_seller(self):
        """Buyer attempting to sign contract on behalf of seller must be rejected."""
        contract = self.repo.create_contract(
            buyer=self.buyer, seller_id=self.seller.id, title="Test",
            description="Desc", total_amount=500.00, deadline="2026-12-01T00:00:00Z"
        )
        self.repo.transition_contract(contract["id"], self.buyer, ContractState.REVIEW)

        with self.assertRaises(UnauthorizedRoleError):
            self.repo.transition_contract(
                contract_id=contract["id"],
                actor=self.buyer,  # BUYER tries to sign as seller!
                target_state=ContractState.SIGNED
            )

    def test_role_enforcement_unrelated_party_blocked(self):
        """Unrelated user attempting an action must be rejected."""
        contract = self.repo.create_contract(
            buyer=self.buyer, seller_id=self.seller.id, title="Test",
            description="Desc", total_amount=500.00, deadline="2026-12-01T00:00:00Z"
        )
        with self.assertRaises(ForbiddenActionError):
            self.repo.transition_contract(
                contract_id=contract["id"],
                actor=self.charlie_stranger,  # Third party!
                target_state=ContractState.REVIEW
            )

    def test_illegal_state_jump_rejected(self):
        """Attempting to jump directly from DRAFT to FUNDED must be rejected."""
        contract = self.repo.create_contract(
            buyer=self.buyer, seller_id=self.seller.id, title="Test",
            description="Desc", total_amount=500.00, deadline="2026-12-01T00:00:00Z"
        )
        with self.assertRaises(InvalidStateTransitionError):
            self.repo.transition_contract(
                contract_id=contract["id"],
                actor=self.buyer,
                target_state=ContractState.FUNDED,  # Skipping REVIEW and SIGNED!
                metadata={"paypal_order_id": "O", "paypal_auth_id": "A"}
            )

    def test_funding_requires_paypal_references(self):
        """Transition to FUNDED without PayPal auth reference must raise StateValidationError."""
        contract = self.repo.create_contract(
            buyer=self.buyer, seller_id=self.seller.id, title="Test",
            description="Desc", total_amount=500.00, deadline="2026-12-01T00:00:00Z"
        )
        self.repo.transition_contract(contract["id"], self.buyer, ContractState.REVIEW)
        self.repo.transition_contract(contract["id"], self.seller, ContractState.SIGNED)

        with self.assertRaises(StateValidationError):
            self.repo.transition_contract(
                contract_id=contract["id"],
                actor=self.buyer,
                target_state=ContractState.FUNDED,
                metadata={}  # Missing paypal_order_id and paypal_auth_id
            )

    def test_seller_revision_flow(self):
        """Seller can counter and return contract from REVIEW to DRAFT."""
        contract = self.repo.create_contract(
            buyer=self.buyer, seller_id=self.seller.id, title="Test",
            description="Desc", total_amount=500.00, deadline="2026-12-01T00:00:00Z"
        )
        self.repo.transition_contract(contract["id"], self.buyer, ContractState.REVIEW)

        # Seller requests revision
        contract = self.repo.transition_contract(
            contract_id=contract["id"],
            actor=self.seller,
            target_state=ContractState.DRAFT,
            metadata={"notes": "Please increase budget for feature 2"}
        )
        self.assertEqual(contract["status"], ContractState.DRAFT.value)

if __name__ == "__main__":
    unittest.main()
