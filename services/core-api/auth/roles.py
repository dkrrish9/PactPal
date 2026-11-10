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

def assert_can_apply_incremental_hold(actor: User, contract: Dict[str, Any]) -> None:
    """
    Enforces authorization to apply an incremental hold for an accepted change request (Commit C46).
    Allowed actors:
    - Contract BUYER (the buyer funding the additional scope)
    - Platform ADMIN
    - AI Referee / Price Negotiator agent acting on behalf of the automated platform
    """
    # Platform Admin is always authorized
    if actor.role == UserRole.ADMIN:
        return
    # AI Referee or automated negotiation agent
    if getattr(actor, "id", None) in ("AI_REFEREE", "PRICE_NEGOTIATOR") or getattr(actor, "role", None) in ("AI_REFEREE", "PRICE_NEGOTIATOR"):
        return
    # Buyer
    if actor.role == UserRole.BUYER:
        if contract.get("buyer_id") != actor.id:
            raise ForbiddenActionError(
                f"User '{actor.id}' is not the buyer for contract '{contract.get('id')}'. Assigned buyer is '{contract.get('buyer_id')}'."
            )
        return

    raise UnauthorizedRoleError(
        f"User '{actor.id}' with role '{actor.role.value}' cannot apply incremental holds. Only the contract BUYER, ADMIN, or AI Negotiator can authorize additional funds."
    )

def assert_can_trigger_deadline_watcher(actor: User) -> None:
    """
    Enforces authorization to trigger or simulate deadline watcher sweeps or force triggers (Commit C49).
    Allowed actors:
    - Platform ADMIN
    - AI Referee agent
    """
    if actor.role == UserRole.ADMIN:
        return
    if getattr(actor, "id", None) in ("AI_REFEREE", "ADMIN") or getattr(actor, "name", None) in ("AI Referee", "Platform Admin"):
        return
    raise ForbiddenActionError(
        f"User '{actor.id}' with role '{actor.role.value}' is not authorized to trigger deadline actions. "
        f"Only platform ADMIN or AI Referee can execute deadline sweeps or simulations."
    )


def assert_can_view_notifications(actor: User, contract: Dict[str, Any]) -> None:
    """
    Only participant BUYER, SELLER, platform ADMIN, or AI Referee can inspect contract notifications (Commit C51).
    """
    if actor.role == UserRole.ADMIN:
        return
    if getattr(actor, "id", None) in ("AI_REFEREE", "ADMIN") or getattr(actor, "name", None) in ("AI Referee", "Platform Admin") or getattr(actor, "role", None) == "AI_REFEREE":
        return
    if actor.id != contract.get("buyer_id") and actor.id != contract.get("seller_id"):
        raise ForbiddenActionError(
            f"User '{actor.id}' with role '{actor.role.value}' is not authorized to view notifications for contract '{contract.get('id')}'. "
            f"Access restricted to contract buyer, seller, admin, or AI referee."
        )


def assert_can_dispatch_notification(actor: User, contract: Dict[str, Any]) -> None:
    """
    Enforces permission to manually dispatch contract email notifications (Commit C51).
    Allowed actors:
    - Contract BUYER
    - Contract SELLER
    - Platform ADMIN
    - AI Referee agent
    """
    if actor.role == UserRole.ADMIN:
        return
    if getattr(actor, "id", None) in ("AI_REFEREE", "ADMIN") or getattr(actor, "name", None) in ("AI Referee", "Platform Admin") or getattr(actor, "role", None) == "AI_REFEREE":
        return
    if actor.id == contract.get("buyer_id") or actor.id == contract.get("seller_id"):
        return
    raise ForbiddenActionError(
        f"User '{actor.id}' with role '{actor.role.value}' is not authorized to dispatch notifications for contract '{contract.get('id')}'. "
        f"Access restricted to contract buyer, seller, admin, or AI referee."
    )




