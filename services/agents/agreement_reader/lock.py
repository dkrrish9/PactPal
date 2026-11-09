"""
Dual-Confirmation and Checklist Lock Module
Linked Tasks: C12 / A5
Enforces timestamped dual confirmation from Buyer and Seller.
Locks the priced checklist as the single source of truth.
Only the AI Price Negotiator can alter a locked checklist via formal change requests.
"""

from datetime import datetime, timezone
from typing import Optional
from .models import PricedChecklist

class ChecklistLockError(Exception):
    """Raised when an unauthorized modification is attempted on a locked checklist."""
    pass

def lock_checklist(
    checklist: PricedChecklist,
    buyer_confirmed_at: str,
    seller_confirmed_at: str,
    locked_at: Optional[str] = None
) -> PricedChecklist:
    """
    Applies timestamped dual confirmation and locks the checklist.
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
    return checklist

def assert_checklist_is_unlocked(checklist: PricedChecklist) -> None:
    """Guards against unauthorized mutations to a locked checklist."""
    if checklist.is_locked:
        raise ChecklistLockError(
            f"Checklist for contract '{checklist.contract_id}' is LOCKED. "
            "It cannot be altered except through an approved Price Negotiator Change Request."
        )

