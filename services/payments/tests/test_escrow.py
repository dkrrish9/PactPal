"""
Unit & Integration Tests for PactPal Escrow Payment Service (Task C10)
Tests order creation with AUTHORIZE intent, buyer approval handling,
and storing the authorization reference against the contract.
"""

import os
import unittest
from unittest.mock import MagicMock
from datetime import datetime, timezone, timedelta

from services.payments.client import PayPalClient
from services.payments.service import (
    EscrowPaymentService,
    ContractRepository,
    User,
    UserRole,
    ContractState,
    StateValidationError
)

class TestEscrowPaymentService(unittest.TestCase):

    def setUp(self):
        # In-memory clean repository for each test
        self.repo = ContractRepository(db_path=":memory:")

        # Setup Buyer and Seller users
        self.buyer = self.repo.create_user(
            name="Alice Buyer",
            email="buyer@pactpal.test",
            role=UserRole.BUYER,
            paypal_email="sb-buyer@example.com"
        )
        self.seller = self.repo.create_user(
            name="Bob Freelancer",
            email="seller@pactpal.test",
            role=UserRole.SELLER,
            paypal_email="sb-seller@example.com"
        )

        # Mock PayPal Client
        self.mock_paypal = MagicMock(spec=PayPalClient)
        self.service = EscrowPaymentService(repository=self.repo, paypal_client=self.mock_paypal)

    def tearDown(self):
        self.repo.close()

    def _create_signed_contract(self, amount: float = 1500.0) -> str:
        """Helper to create a contract and advance it cleanly to SIGNED state."""
        contract = self.repo.create_contract(
            buyer=self.buyer,
            seller_id=self.seller.id,
            title="Fullstack Web App Milestone",
            description="4 features matching design spec",
            total_amount=amount,
            deadline=(datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        )
        contract_id = contract["id"]

        # Advance DRAFT -> REVIEW (by buyer)
        self.repo.transition_contract(contract_id, self.buyer, ContractState.REVIEW)

        # Advance REVIEW -> SIGNED (by seller)
        self.repo.transition_contract(contract_id, self.seller, ContractState.SIGNED, metadata={"acceptance_confirmed": True})

        return contract_id

    def test_initiate_contract_hold_success(self):
        """Verify order creation with AUTHORIZE intent for a SIGNED contract."""
        contract_id = self._create_signed_contract(amount=1500.0)

        # Configure mock PayPal response
        self.mock_paypal.create_authorize_order.return_value = {
            "order_id": "ORDER_PP_998877",
            "approve_url": "https://www.sandbox.paypal.com/checkoutnow?token=ORDER_PP_998877",
            "status": "CREATED",
            "intent": "AUTHORIZE"
        }

        res = self.service.initiate_contract_hold(contract_id, self.buyer)

        self.assertEqual(res["contract_id"], contract_id)
        self.assertEqual(res["paypal_order_id"], "ORDER_PP_998877")
        self.assertIn("https://www.sandbox.paypal.com/checkoutnow", res["approve_url"])
        self.assertEqual(res["amount"], 1500.0)
        self.assertEqual(res["currency"], "USD")

        # Verify PayPal API was called with exact contract amount and intent
        self.mock_paypal.create_authorize_order.assert_called_once()
        args, kwargs = self.mock_paypal.create_authorize_order.call_args
        self.assertEqual(kwargs.get("amount") or args[1], 1500.0)
        self.assertEqual(kwargs.get("reference_id") or args[0], contract_id)

    def test_confirm_and_store_authorization_success(self):
        """Verify buyer authorization is executed, stored, and contract moves to FUNDED."""
        contract_id = self._create_signed_contract(amount=1500.0)
        order_id = "ORDER_PP_998877"
        mock_auth_id = "AUTH_PP_445566"

        self.mock_paypal.execute_authorization.return_value = {
            "order_id": order_id,
            "authorization_id": mock_auth_id,
            "status": "CREATED",
            "expiration_time": (datetime.now(timezone.utc) + timedelta(days=29)).isoformat(),
            "amount": "1500.00",
            "currency": "USD"
        }

        funded_contract = self.service.confirm_and_store_authorization(
            contract_id=contract_id,
            paypal_order_id=order_id,
            actor=self.buyer
        )

        # Assert contract state moved to FUNDED
        self.assertEqual(funded_contract["status"], ContractState.FUNDED.value)
        self.assertEqual(funded_contract["paypal_order_id"], order_id)
        self.assertEqual(funded_contract["paypal_auth_id"], mock_auth_id)
        self.assertIsNotNone(funded_contract["auth_expires_at"])
        self.assertIsNotNone(funded_contract["funded_at"])

        # Fetch contract fresh from database to ensure persistence
        db_contract = self.repo.get_contract(contract_id)
        self.assertEqual(db_contract["status"], "FUNDED")
        self.assertEqual(db_contract["paypal_auth_id"], mock_auth_id)
        self.assertEqual(db_contract["paypal_order_id"], order_id)

    def test_seller_cannot_fund_contract(self):
        """Ensure RBAC permissions guard blocks seller from funding escrow."""
        contract_id = self._create_signed_contract()

        with self.assertRaises(Exception):
            self.service.initiate_contract_hold(contract_id, self.seller)

        with self.assertRaises(Exception):
            self.service.confirm_and_store_authorization(contract_id, "ORDER_123", self.seller)

    def test_cannot_fund_draft_contract(self):
        """Ensure contract must be SIGNED before escrow hold can be initiated."""
        draft_contract = self.repo.create_contract(
            buyer=self.buyer,
            seller_id=self.seller.id,
            title="Draft Contract",
            description="Not yet signed",
            total_amount=500.0,
            deadline=(datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        )

        with self.assertRaises(StateValidationError):
            self.service.initiate_contract_hold(draft_contract["id"], self.buyer)

    def test_paypal_client_token_caching(self):
        """Ensure OAuth tokens are properly cached and reused."""
        client = PayPalClient(client_id="dummy_id", client_secret="dummy_secret")
        client._cached_token = "cached_test_token_abc"
        client._token_expires_at = datetime.now(timezone.utc).timestamp() + 3600

        # Should return cached token without making HTTP call
        token = client.get_access_token(force_refresh=False)
        self.assertEqual(token, "cached_test_token_abc")

if __name__ == "__main__":
    unittest.main()

