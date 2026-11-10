"""
Authentication & Role-Based Access Control (RBAC) Module
Linked Tasks: C09 / A2
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any

class UserRole(str, Enum):
    BUYER = "BUYER"
    SELLER = "SELLER"
    ADMIN = "ADMIN"

@dataclass
class User:
    id: str
    name: str
    email: str
    role: UserRole
    paypal_email: Optional[str] = None

# Custom Domain Exceptions
class AuthError(Exception):
    """Base exception for authentication and authorization errors."""
    pass

class UnauthorizedRoleError(AuthError):
    """Raised when an actor's role does not permit the requested operation."""
    pass

class ForbiddenActionError(AuthError):
    """Raised when an actor attempts an action on a resource they do not own."""
    pass

# Permission Guards
def assert_can_create_contract(actor: User) -> None:
    """Only a BUYER can create contracts."""
    if actor.role != UserRole.BUYER:
        raise UnauthorizedRoleError(
            f"User '{actor.id}' with role '{actor.role.value}' cannot create contracts. Only BUYER can create contracts."
        )

def assert_can_submit_for_review(actor: User, contract: Dict[str, Any]) -> None:
    """Only the assigned BUYER can submit a contract for review."""
    if actor.role != UserRole.BUYER:
        raise UnauthorizedRoleError(f"Only BUYER can submit a contract for review (actor role: {actor.role.value}).")
    if contract.get("buyer_id") != actor.id:
        raise ForbiddenActionError(
            f"User '{actor.id}' is not the buyer for contract '{contract.get('id')}'. Assigned buyer is '{contract.get('buyer_id')}'."
        )

def assert_can_sign_contract(actor: User, contract: Dict[str, Any]) -> None:
    """Only the assigned SELLER can sign/accept a contract in review."""
    if actor.role != UserRole.SELLER:
        raise UnauthorizedRoleError(f"Only SELLER can sign a contract (actor role: {actor.role.value}).")
    if contract.get("seller_id") != actor.id:
        raise ForbiddenActionError(
            f"User '{actor.id}' is not the seller for contract '{contract.get('id')}'. Assigned seller is '{contract.get('seller_id')}'."
        )

def assert_can_request_revision(actor: User, contract: Dict[str, Any]) -> None:
    """Only the assigned SELLER can request revisions on a contract in review."""
    if actor.role != UserRole.SELLER:
        raise UnauthorizedRoleError(f"Only SELLER can request revisions (actor role: {actor.role.value}).")
    if contract.get("seller_id") != actor.id:
        raise ForbiddenActionError(f"User '{actor.id}' is not the seller for contract '{contract.get('id')}'.")

def assert_can_fund_contract(actor: User, contract: Dict[str, Any]) -> None:
    """Only the assigned BUYER can authorize and fund the escrow contract."""
    if actor.role != UserRole.BUYER:
        raise UnauthorizedRoleError(
            f"User '{actor.id}' with role '{actor.role.value}' cannot fund contracts. Only the assigned BUYER can fund escrow."
        )
    if contract.get("buyer_id") != actor.id:
        raise ForbiddenActionError(
            f"User '{actor.id}' is not the buyer for contract '{contract.get('id')}'. Assigned buyer is '{contract.get('buyer_id')}'."
        )

def assert_can_view_receipt(actor: User, contract: Dict[str, Any]) -> None:
    """Only participant BUYER, SELLER, platform ADMIN, or AI Referee can inspect contract receipt (Commit C44)."""
    if actor.role == UserRole.ADMIN:
        return
    if getattr(actor, "id", None) == "AI_REFEREE" or getattr(actor, "name", None) == "AI Referee" or getattr(actor, "role", None) == "AI_REFEREE":
        return
    if actor.id != contract.get("buyer_id") and actor.id != contract.get("seller_id"):
        raise ForbiddenActionError(
            f"User '{actor.id}' with role '{actor.role.value}' is not authorized to view receipt for contract '{contract.get('id')}'. "
            f"Access restricted to contract buyer, seller, admin, or AI referee."
        )


