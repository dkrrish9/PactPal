#!/usr/bin/env python3
"""
PactPal Milestone 1: Supabase Authentication & Role-Based Access Tests
Linked Tasks:
- C09a / feature/agents: Google OAuth sign-in, session, user created on first login
- C09b / feature/agents: Role selection and role-based route protection

Acceptance Criteria:
- C09a: A new Google account signs in and a user record exists
- C09b: Buyer, seller and admin only see their own contracts
"""

import time
import unittest

from ..auth.roles import (
    UserRole,
    User,
    AuthError,
    ForbiddenActionError,
    assert_can_access_contract,
)
from ..auth.supabase_auth import (
    SupabaseAuthService,
    TokenExpiredError,
    InvalidTokenError,
    MalformedTokenError,
    generate_mock_supabase_token,
    create_supabase_jwt,
    verify_supabase_jwt,
)
from ..db.repository import ContractRepository


class TestSupabaseAuth(unittest.TestCase):

    def setUp(self):
        """Set up in-memory repository and Supabase auth service for testing."""
        self.repo = ContractRepository(db_path=":memory:")
        self.jwt_secret = "test_supabase_jwt_secret_998877"
        self.auth_service = SupabaseAuthService(
            repository=self.repo,
            jwt_secret=self.jwt_secret,
            default_role=UserRole.BUYER
        )

    def tearDown(self):
        self.repo.close()

    # =========================================================================
    # Task C09a: Google OAuth Sign-in & Session Token Verification
    # =========================================================================

    def test_token_verification_valid_signature_and_claims(self):
        """Verifies that a valid HS256 Supabase token parses correctly."""
        sub = "google-oauth2-1001"
        email = "alice@example.com"
        name = "Alice Test"

        token = generate_mock_supabase_token(
            sub=sub,
            email=email,
            name=name,
            secret=self.jwt_secret
        )

        claims = verify_supabase_jwt(token, secret=self.jwt_secret)
        self.assertEqual(claims["sub"], sub)
        self.assertEqual(claims["email"], email)
        self.assertEqual(claims["user_metadata"]["full_name"], name)
        self.assertEqual(claims["role"], "authenticated")

    def test_token_verification_expired_raises_error(self):
        """Verifies that an expired session token raises TokenExpiredError."""
        token = generate_mock_supabase_token(
            sub="user-expired-1",
            email="expired@example.com",
            name="Expired User",
            expires_in=-30,  # Expired 30 seconds ago
            secret=self.jwt_secret
        )

        with self.assertRaises(TokenExpiredError) as ctx:
            verify_supabase_jwt(token, secret=self.jwt_secret)
        self.assertIn("expired", str(ctx.exception).lower())

    def test_token_verification_invalid_signature_raises_error(self):
        """Verifies that tampered or wrongly signed tokens are rejected."""
        token = generate_mock_supabase_token(
            sub="user-tampered",
            email="tampered@example.com",
            name="Tampered User",
            secret="different_wrong_secret"
        )

        with self.assertRaises(InvalidTokenError) as ctx:
            verify_supabase_jwt(token, secret=self.jwt_secret)
        self.assertIn("signature verification failed", str(ctx.exception).lower())

    def test_token_verification_malformed_token_raises_error(self):
        """Verifies that malformed or non-JWT strings raise MalformedTokenError."""
        with self.assertRaises(MalformedTokenError):
            verify_supabase_jwt("not.a.valid.four.part.jwt", secret=self.jwt_secret)

        with self.assertRaises(MalformedTokenError):
            verify_supabase_jwt("single_token_string", secret=self.jwt_secret)

        with self.assertRaises(MalformedTokenError):
            verify_supabase_jwt("", secret=self.jwt_secret)

    def test_c09a_first_login_creates_user_record(self):
        """
        Task C09a Acceptance Criteria:
        'A new Google account signs in and a user record exists'
        """
        google_sub = "google-oauth2-9876543210"
        google_email = "newbuyer@google.example.com"
        google_name = "New Buyer Google"

        # 1. Verify user does not exist in the database initially
        self.assertIsNone(self.repo.get_user(google_sub))
        self.assertIsNone(self.repo.get_user_by_email(google_email))

        # 2. Simulate Google OAuth sign-in via Supabase token
        token = generate_mock_supabase_token(
            sub=google_sub,
            email=google_email,
            name=google_name,
            secret=self.jwt_secret
        )

        # 3. Authenticate session
        user = self.auth_service.authenticate_token(token)

        # 4. Verify user record is returned with correct profile
        self.assertIsNotNone(user)
        self.assertEqual(user.id, google_sub)
        self.assertEqual(user.email, google_email)
        self.assertEqual(user.name, google_name)
        self.assertEqual(user.role, UserRole.BUYER)

        # 5. Verify user record was actually persisted to the relational database
        persisted_user = self.repo.get_user(google_sub)
        self.assertIsNotNone(persisted_user)
        self.assertEqual(persisted_user.id, google_sub)
        self.assertEqual(persisted_user.email, google_email)
        self.assertEqual(persisted_user.name, google_name)
        self.assertEqual(persisted_user.role, UserRole.BUYER)

    def test_c09a_subsequent_login_returns_existing_user_without_duplication(self):
        """Verifies that subsequent logins retrieve existing user without duplicating."""
        google_sub = "google-oauth2-existing-user"
        google_email = "existing@google.example.com"
        google_name = "Existing User"

        token = generate_mock_supabase_token(
            sub=google_sub,
            email=google_email,
            name=google_name,
            secret=self.jwt_secret
        )

        # First login: creates user
        user1 = self.auth_service.authenticate_token(token)
        self.assertIsNotNone(user1)

        # Subsequent login: retrieves same user
        user2 = self.auth_service.authenticate_token(token)
        self.assertEqual(user1.id, user2.id)
        self.assertEqual(user1.email, user2.email)

    def test_c09a_bearer_header_authentication(self):
        """Verifies extraction and authentication via 'Authorization: Bearer <token>' header."""
        google_sub = "google-oauth2-bearer-test"
        google_email = "bearer@example.com"
        google_name = "Bearer User"

        token = generate_mock_supabase_token(
            sub=google_sub,
            email=google_email,
            name=google_name,
            secret=self.jwt_secret
        )

        auth_header = f"Bearer {token}"
        user = self.auth_service.authenticate_bearer(auth_header)
        self.assertEqual(user.id, google_sub)
        self.assertEqual(user.email, google_email)

        # Missing or invalid Bearer header errors
        with self.assertRaises(AuthError):
            self.auth_service.authenticate_bearer("")

        with self.assertRaises(MalformedTokenError):
            self.auth_service.authenticate_bearer("Basic dXNlcjpwYXNz")

        with self.assertRaises(MalformedTokenError):
            self.auth_service.authenticate_bearer("Bearer ")

    # =========================================================================
    # Task C09b: Role Selection & Role-Based Route Protection
    # =========================================================================

    def test_c09b_role_selection(self):
        """
        Task C09b Acceptance Criteria:
        Role selection updates user role from default BUYER to SELLER or ADMIN.
        """
        user = self.repo.create_user(
            name="Freelancer Bob",
            email="bob@freelance.example.com",
            role=UserRole.BUYER
        )
        self.assertEqual(user.role, UserRole.BUYER)

        # Bob selects SELLER role during onboarding
        updated_user = self.auth_service.select_role(user.id, UserRole.SELLER)
        self.assertEqual(updated_user.role, UserRole.SELLER)

        # Verify DB reflects new role
        db_user = self.repo.get_user(user.id)
        self.assertEqual(db_user.role, UserRole.SELLER)

        # Attempt to set invalid role raises ValueError
        with self.assertRaises(ValueError):
            self.auth_service.select_role(user.id, "NOT_A_ROLE")

    def test_c09b_role_based_contract_isolation(self):
        """
        Task C09b Acceptance Criteria:
        'Buyer, seller and admin only see their own contracts'
        """
        # Create users
        buyer_1 = self.repo.create_user(name="Buyer One", email="buyer1@test.com", role=UserRole.BUYER)
        buyer_2 = self.repo.create_user(name="Buyer Two", email="buyer2@test.com", role=UserRole.BUYER)
        seller = self.repo.create_user(name="Seller Bob", email="seller@test.com", role=UserRole.SELLER)
        admin = self.repo.create_user(name="Platform Admin", email="admin@test.com", role=UserRole.ADMIN)

        # Contract 1: Buyer 1 + Seller
        contract_1 = self.repo.create_contract(
            buyer=buyer_1,
            seller_id=seller.id,
            title="Contract 1 - Buyer One Project",
            description="Project 1 description",
            total_amount=1000.00,
            deadline="2026-12-01T00:00:00Z"
        )

        # Contract 2: Buyer 2 + Seller
        contract_2 = self.repo.create_contract(
            buyer=buyer_2,
            seller_id=seller.id,
            title="Contract 2 - Buyer Two Project",
            description="Project 2 description",
            total_amount=2000.00,
            deadline="2026-12-15T00:00:00Z"
        )

        # 1. Buyer 1 queries contracts: sees ONLY Contract 1
        buyer_1_contracts = self.auth_service.get_contracts_for_user(buyer_1)
        self.assertEqual(len(buyer_1_contracts), 1)
        self.assertEqual(buyer_1_contracts[0]["id"], contract_1["id"])
        self.assertEqual(buyer_1_contracts[0]["title"], "Contract 1 - Buyer One Project")

        # 2. Buyer 2 queries contracts: sees ONLY Contract 2
        buyer_2_contracts = self.auth_service.get_contracts_for_user(buyer_2)
        self.assertEqual(len(buyer_2_contracts), 1)
        self.assertEqual(buyer_2_contracts[0]["id"], contract_2["id"])
        self.assertEqual(buyer_2_contracts[0]["title"], "Contract 2 - Buyer Two Project")

        # 3. Seller queries contracts: sees BOTH Contract 1 and Contract 2
        seller_contracts = self.auth_service.get_contracts_for_user(seller)
        self.assertEqual(len(seller_contracts), 2)
        seller_contract_ids = {c["id"] for c in seller_contracts}
        self.assertIn(contract_1["id"], seller_contract_ids)
        self.assertIn(contract_2["id"], seller_contract_ids)

        # 4. Admin queries contracts: sees ALL contracts
        admin_contracts = self.auth_service.get_contracts_for_user(admin)
        self.assertEqual(len(admin_contracts), 2)
        admin_contract_ids = {c["id"] for c in admin_contracts}
        self.assertIn(contract_1["id"], admin_contract_ids)
        self.assertIn(contract_2["id"], admin_contract_ids)

    def test_c09b_route_protection_prevents_unauthorized_contract_access(self):
        """
        Task C09b Acceptance Criteria:
        Route protection ensures an unauthorized buyer cannot access another buyer's contract.
        """
        buyer_alice = self.repo.create_user(name="Alice", email="alice@test.com", role=UserRole.BUYER)
        buyer_charlie = self.repo.create_user(name="Charlie", email="charlie@test.com", role=UserRole.BUYER)
        seller_bob = self.repo.create_user(name="Bob", email="bob@test.com", role=UserRole.SELLER)
        platform_admin = self.repo.create_user(name="Admin", email="admin@pactpal.com", role=UserRole.ADMIN)

        # Contract owned by Alice and Bob
        contract_alice = self.repo.create_contract(
            buyer=buyer_alice,
            seller_id=seller_bob.id,
            title="Alice's Contract",
            description="Alice project description",
            total_amount=500.00,
            deadline="2026-12-01T00:00:00Z"
        )

        # 1. Alice can access her contract
        fetched_by_alice = self.auth_service.get_contract(user=buyer_alice, contract_id=contract_alice["id"])
        self.assertEqual(fetched_by_alice["id"], contract_alice["id"])

        # 2. Bob (assigned seller) can access Alice's contract
        fetched_by_bob = self.auth_service.get_contract(user=seller_bob, contract_id=contract_alice["id"])
        self.assertEqual(fetched_by_bob["id"], contract_alice["id"])

        # 3. Platform Admin can access Alice's contract
        fetched_by_admin = self.auth_service.get_contract(user=platform_admin, contract_id=contract_alice["id"])
        self.assertEqual(fetched_by_admin["id"], contract_alice["id"])

        # 4. Charlie (unauthorized buyer) is FORBIDDEN from accessing Alice's contract
        with self.assertRaises(ForbiddenActionError) as ctx:
            self.auth_service.get_contract(user=buyer_charlie, contract_id=contract_alice["id"])
        self.assertIn("not authorized to access contract", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

