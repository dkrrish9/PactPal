"""
PactPal Payments Subsystem
Escrow Rails, PayPal Orders AUTHORIZE intent, Capture, and Payouts.
"""

from .client import PayPalClient, PayPalAPIError
from .service import (
    EscrowPaymentService,
    PaymentApprovalService,
    PaymentApprovalError,
    ApprovalVerdict
)
from .api import PaymentsAPIHandler, create_payments_app

__all__ = [
    "PayPalClient",
    "PayPalAPIError",
    "EscrowPaymentService",
    "PaymentApprovalService",
    "PaymentApprovalError",
    "ApprovalVerdict",
    "PaymentsAPIHandler",
    "create_payments_app"
]


