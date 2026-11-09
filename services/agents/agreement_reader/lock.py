"""
Dual-Confirmation and Checklist Lock Module
Linked Tasks: C12 / C19 / A5
Enforces timestamped dual confirmation from Buyer and Seller.
Locks the priced checklist as the single source of truth.
Checklist cannot change except via the Price Negotiator.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from .models import PricedChecklist, ChecklistFeature

class ChecklistLockError(Exception):
    """Raised when an unauthorized modification is attempted on a locked checklist."""
    pass

def confirm_party(
    checklist: PricedChecklist,
    actor_id: str,
    actor_role: str,
    timestamp: Optional[str] = None
) -> PricedChecklist:
    """
    Registers an official confirmation from a party (BUYER or SELLER).
    Once BOTH parties confirm, the checklist transitions to LOCKED status.
    """
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    role_upper = actor_role.upper()

    if role_upper == "BUYER":
        checklist.buyer_confirmed_at = ts
    elif role_upper == "SELLER":
        checklist.seller_confirmed_at = ts
    else:
        raise ChecklistLockError(f"Role '{actor_role}' is not authorized to confirm contracts. Only BUYER and SELLER can confirm.")

    # When both confirmations are recorded, lock the checklist
    if checklist.buyer_confirmed_at and checklist.seller_confirmed_at:
        checklist.is_locked = True
        checklist.locked_at = ts
        checklist.locked_by_dual_confirmation = True

    return checklist

def lock_checklist(
    checklist: PricedChecklist,
    buyer_confirmed_at: str,
    seller_confirmed_at: str,
    locked_at: Optional[str] = None
) -> PricedChecklist:
    """
    Applies timestamped dual confirmation directly and locks the checklist.
    """
    if not buyer_confirmed_at or not str(buyer_confirmed_at).strip():
        raise ChecklistLockError("Checklist cannot be locked without buyer confirmation timestamp.")
    if not seller_confirmed_at or not str(seller_confirmed_at).strip():
        raise ChecklistLockError("Checklist cannot be locked without seller confirmation timestamp.")

    now_iso = locked_at or datetime.now(timezone.utc).isoformat()

    checklist.is_locked = True
    checklist.buyer_confirmed_at = buyer_confirmed_at
    checklist.seller_confirmed_at = seller_confirmed_at
    checklist.locked_at = now_iso
    checklist.locked_by_dual_confirmation = True
    return checklist

def assert_can_modify_checklist(
    checklist: PricedChecklist,
    source: str = "DIRECT",
    change_request_id: Optional[str] = None
) -> None:
    """
    Guards against unauthorized modifications to a locked checklist.
    Invariant: Checklist CANNOT change except via the Price Negotiator with a valid change request.
    """
    if not checklist.is_locked:
        return  # Still in draft/review, modifications permitted

    # If locked, only the Price Negotiator with an official change request ID is permitted
    if source == "PRICE_NEGOTIATOR" and change_request_id:
        return  # Authorized negotiated amendment

    raise ChecklistLockError(
        f"Checklist for contract '{checklist.contract_id}' is LOCKED by timestamped dual confirmation. "
        "It cannot be altered directly by buyers or sellers. "
        "Modifications are permitted ONLY via the Price Negotiator with an approved change request."
    )

def assert_checklist_is_unlocked(checklist: PricedChecklist) -> None:
    """Guards against unauthorized mutations to a locked checklist."""
    assert_can_modify_checklist(checklist, source="DIRECT")

def apply_negotiated_amendment(
    checklist: PricedChecklist,
    amendment_feature: ChecklistFeature,
    change_request_id: str,
    source: str = "PRICE_NEGOTIATOR"
) -> PricedChecklist:
    """
    Safely applies a new checklist feature negotiated via a formal change request.
    Preserves all existing features without silent overwrites.
    """
    assert_can_modify_checklist(checklist, source=source, change_request_id=change_request_id)

    amendment_feature.change_request_id = change_request_id
    amendment_feature.amended = True
    amendment_feature.sort_order = len(checklist.features) + 1

    checklist.features.append(amendment_feature)
    return checklist
