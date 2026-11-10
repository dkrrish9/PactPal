"""
PactPal Supabase Authentication & Session Management Module
Linked Tasks:
- C09a / feature/agents: Google OAuth sign-in, session, user created on first login
- C09b / feature/agents: Role selection and role-based route protection
"""

import os
import json
import time
import hmac
import hashlib
import base64
from typing import Dict, Any, Optional, Tuple, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..db.repository import ContractRepository

from .roles import (
    UserRole,
    User,
    AuthError,
    UnauthorizedRoleError,
    ForbiddenActionError,
    assert_can_access_contract,
    assert_contract_participant,
)



class TokenError(AuthError):
    """Base exception for JWT / session token errors."""
    pass


class TokenExpiredError(TokenError):
    """Raised when a Supabase JWT session token has expired."""
    pass


class InvalidTokenError(TokenError):
    """Raised when a token signature is invalid, forged, or claims are corrupted."""
    pass


class MalformedTokenError(TokenError):
    """Raised when a token structure cannot be parsed as a 3-part base64url JWT."""
    pass


# --- Base64URL Encoding & Decoding Helpers ---

def b64url_encode(data: bytes) -> str:
    """Encodes bytes to Base64URL string without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def b64url_decode(s: str) -> bytes:
    """Decodes Base64URL string with optional missing padding."""
    padding = 4 - (len(s) % 4)
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s.encode("utf-8"))


# --- Supabase JWT Signature & Verification Engine (HS256) ---

def create_supabase_jwt(
    payload: Dict[str, Any],
    secret: str,
    header: Optional[Dict[str, Any]] = None
) -> str:
    """
    Creates a signed Supabase HS256 JWT string.
    Useful for generating mock Google OAuth tokens, testing, and service tokens.
    """
    if header is None:
        header = {"alg": "HS256", "typ": "JWT"}

    h_b64 = b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    p_b64 = b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{h_b64}.{p_b64}".encode("utf-8")

    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = b64url_encode(sig)

    return f"{h_b64}.{p_b64}.{sig_b64}"


def verify_supabase_jwt(
    token: str,
    secret: Optional[str] = None,
    allow_unverified: bool = False,
    leeway: int = 0
) -> Dict[str, Any]:
    """
    Decodes and validates a Supabase HS256 JWT token.
    Validates:
    - 3-segment format (header.payload.signature)
    - HMAC-SHA256 signature against the Supabase JWT secret
    - Expiration timestamp ('exp') with optional leeway
    - Not-before timestamp ('nbf') with optional leeway
    """
    if not token or not isinstance(token, str):
        raise MalformedTokenError("JWT token must be a non-empty string.")

    parts = token.strip().split(".")
    if len(parts) != 3:
        raise MalformedTokenError(
            f"Invalid JWT format: expected 3 segments (header.payload.signature), got {len(parts)}."
        )

    h_b64, p_b64, sig_b64 = parts

    # 1. Decode header & payload
    try:
        header_bytes = b64url_decode(h_b64)
        header = json.loads(header_bytes.decode("utf-8"))
    except Exception as e:
        raise MalformedTokenError(f"Malformed JWT header: {e}") from e

    try:
        payload_bytes = b64url_decode(p_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as e:
        raise MalformedTokenError(f"Malformed JWT payload: {e}") from e

    # 2. Verify signature if secret provided and not in unverified mode
    if secret and not allow_unverified:
        signing_input = f"{h_b64}.{p_b64}".encode("utf-8")
        expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        try:
            actual_sig = b64url_decode(sig_b64)
        except Exception as e:
            raise InvalidTokenError(f"Invalid signature encoding: {e}") from e

        if not hmac.compare_digest(expected_sig, actual_sig):
            raise InvalidTokenError("JWT signature verification failed.")

    # 3. Check expiration claim ('exp')
    now = int(time.time())
    if "exp" in payload:
        try:
            exp = int(payload["exp"])
            if now > exp + leeway:
                raise TokenExpiredError(
                    f"Session token expired at {exp} (current time: {now}). Please re-authenticate."
                )
        except (ValueError, TypeError) as e:
            raise InvalidTokenError(f"Invalid 'exp' claim in token: {e}") from e

    # 4. Check not-before claim ('nbf')
    if "nbf" in payload:
        try:
            nbf = int(payload["nbf"])
            if now < nbf - leeway:
                raise InvalidTokenError(f"Token not yet valid before {nbf} (current time: {now}).")
        except (ValueError, TypeError) as e:
            raise InvalidTokenError(f"Invalid 'nbf' claim in token: {e}") from e

    return payload


def generate_mock_supabase_token(
    sub: str,
    email: str,
    name: str,
    role: str = "authenticated",
    expires_in: int = 3600,
    secret: str = "pactpal_dev_jwt_secret_token_12345"
) -> str:
    """
    Generates a realistic Supabase Google OAuth JWT session token for tests and sandbox demos.
    Matches the exact schema issued by Supabase GoTrue Auth when a user signs in with Google.
    """
    now = int(time.time())
    payload = {
        "sub": sub,
        "aud": "authenticated",
        "role": role,
        "email": email,
        "app_metadata": {
            "provider": "google",
            "providers": ["google"]
        },
        "user_metadata": {
            "full_name": name,
            "name": name,
            "email": email,
            "email_verified": True,
            "avatar_url": f"https://lh3.googleusercontent.com/a/{sub[:10]}"
        },
        "iat": now,
        "exp": now + expires_in
    }
    return create_supabase_jwt(payload=payload, secret=secret)


# --- Supabase Auth Service ---

class SupabaseAuthService:
    """
    Manages Supabase Google OAuth session verification, first-login user synchronization,
    role selection, and role-based route protection for PactPal.
    """

    def __init__(
        self,
        repository: ContractRepository,
        jwt_secret: Optional[str] = None,
        default_role: UserRole = UserRole.BUYER
    ):
        self.repo = repository
        self.jwt_secret = (
            jwt_secret
            or os.getenv("SUPABASE_JWT_SECRET")
            or os.getenv("JWT_SECRET")
            or "pactpal_dev_jwt_secret_token_12345"
        )
        self.default_role = default_role

    def extract_token_from_header(self, auth_header: Optional[str]) -> str:
        """Parses 'Authorization: Bearer <token>' header."""
        if not auth_header:
            raise AuthError("Missing 'Authorization' header in request.")
        
        parts = auth_header.strip().split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise MalformedTokenError("Authorization header must follow 'Bearer <token>' format.")
        
        token = parts[1].strip()
        if not token:
            raise MalformedTokenError("Bearer token in Authorization header is empty.")
        
        return token

    def authenticate_bearer(self, auth_header: Optional[str]) -> User:
        """
        Convenience method to authenticate directly from an HTTP Authorization header.
        Validates token, extracts identity, and synchronizes user record.
        """
        token = self.extract_token_from_header(auth_header)
        return self.authenticate_token(token)

    def authenticate_token(self, token: str) -> User:
        """
        Validates a Supabase JWT token and resolves the authenticated User.
        If this is the user's first login, creates their user record in the database (Task C09a).
        """
        claims = verify_supabase_jwt(token, secret=self.jwt_secret)
        user, _ = self.sync_user_from_claims(claims)
        return user

    def sync_user_from_claims(self, claims: Dict[str, Any]) -> Tuple[User, bool]:
        """
        Extracts user metadata from verified Supabase Google OAuth claims.
        Fulfills Task C09a Done criteria:
        'A new Google account signs in and a user record exists'.

        Returns:
            Tuple[User, bool]: (User entity, was_created: bool)
        """
        sub = claims.get("sub")
        if not sub:
            raise InvalidTokenError("Supabase token claims missing subject identifier ('sub').")

        email = claims.get("email") or claims.get("user_metadata", {}).get("email")
        if not email:
            raise InvalidTokenError("Supabase token claims missing required 'email' address.")

        user_meta = claims.get("user_metadata") or {}
        name = user_meta.get("full_name") or user_meta.get("name") or email.split("@")[0]

        # 1. Check if user already exists by Supabase UUID
        existing_user = self.repo.get_user(sub)
        if existing_user:
            return existing_user, False

        # 2. Check if user exists by email (account linking for invited or pre-seeded users)
        existing_by_email = self.repo.get_user_by_email(email)
        if existing_by_email:
            return existing_by_email, False

        # 3. First login: automatically persist user record
        new_user = self.repo.create_user(
            name=name,
            email=email,
            role=self.default_role,
            id=sub
        )
        return new_user, True

    def select_role(self, user_id: str, new_role: UserRole | str) -> User:
        """
        Updates the user's role during onboarding role selection (Task C09b).
        Fulfills Task C09b: 'role selection and role-based route protection'.
        """
        return self.repo.update_user_role(user_id=user_id, role=new_role)

    def get_contracts_for_user(self, user: User) -> List[Dict[str, Any]]:
        """
        Fulfills Task C09b Done criteria:
        'Buyer, seller and admin only see their own contracts'.
        """
        return self.repo.get_contracts_for_user(user)

    def get_contract(self, user: User, contract_id: str) -> Dict[str, Any]:
        """
        Retrieves a single contract enforced with role-based route protection (Task C09b).
        Raises ForbiddenActionError if an unauthorized buyer or seller tries to view another user's contract.
        """
        contract = self.repo.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract '{contract_id}' not found.")

        # Enforce route access protection
        assert_can_access_contract(actor=user, contract=contract)
        return contract

