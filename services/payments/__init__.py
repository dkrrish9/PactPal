"""
PactPal Payments Subsystem
Escrow Rails, PayPal Orders AUTHORIZE intent, Capture, and Payouts.
"""

from .client import PayPalClient, PayPalAPIError
from .service import (
    EscrowPaymentService,
    PaymentApprovalService,
    PaymentApprovalError,
    ApprovalVerdict,
    ProofOfWorkReceipt,
    canonicalize_proof_of_work_summary,
    generate_proof_of_work_hash,
    verify_receipt_hash,
    assert_can_view_receipt,
    assert_can_apply_incremental_hold
)
from .api import PaymentsAPIHandler, create_payments_app

__all__ = [
    "PayPalClient",
    "PayPalAPIError",
    "EscrowPaymentService",
    "PaymentApprovalService",
    "PaymentApprovalError",
    "ApprovalVerdict",
    "ProofOfWorkReceipt",
    "canonicalize_proof_of_work_summary",
    "generate_proof_of_work_hash",
    "verify_receipt_hash",
    "assert_can_view_receipt",
    "assert_can_apply_incremental_hold",
    "PaymentsAPIHandler",
    "create_payments_app"
]


