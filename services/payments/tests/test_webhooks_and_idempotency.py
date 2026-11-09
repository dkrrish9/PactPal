"""
Unit and Integration Tests for Idempotency Keys and PayPal Webhook Verification (Commit C28)
Tests:
  - Idempotency key prevents duplicate PayPal order creation
  - Idempotency key prevents duplicate authorization execution
  - Idempotency key prevents duplicate settlement and double charges/payouts
  - Service and DB idempotency cache returns exact prior response on duplicate request
  - PayPal-Request-Id header propagation in PayPalClient
  - PayPal webhook signature verification (SUCCESS vs FAILURE)
  - Rejection of webhooks with missing cryptographic transmission headers
  - REST endpoint POST /api/v1/payments/webhooks dispatching and status codes (200, 400, 401, 405)
"""

import json
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from services.payments.client import PayPalClient, PayPalAPIError
from services.payments.service import (
    EscrowPaymentService,
    ContractRepository,
    User,
    UserRole,
    ContractState,
    WebhookVerificationError
)
from services.payments.api import PaymentsAPIHandler, create_payments_app


class TestIdempotencyAndWebhooks(unittest.TestCase):

    def setUp(self):
        self.repo = ContractRepository(db_path=":memory:")
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
        self.admin = self.repo.create_user(
            name="Platform Admin",
            email="admin@pactpal.test",
            role=UserRole.ADMIN
        )

        self.mock_paypal = MagicMock(spec=PayPalClient)
        self.service = EscrowPaymentService(repository=self.repo, paypal_client=self.mock_paypal)
        self.api_handler = PaymentsAPIHandler(service=self.service)

    def tearDown(self):
        self.repo.close()

    def _create_signed_contract(self, amount: float = 1000.0) -> Dict[str, Any]:
        contract = self.repo.create_contract(
            buyer=self.buyer,
            seller_id=self.seller.id,
            title="Idempotency Test Contract",
            description="Escrow build milestone",
            total_amount=amount,
            deadline=(datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        )
        cid = contract["id"]
        self.repo.transition_contract(cid, self.buyer, ContractState.REVIEW)
        return self.repo.transition_contract(cid, self.seller, ContractState.SIGNED, metadata={"acceptance_confirmed": True})

    def _create_funded_contract(self, amount: float = 1500.0, auth_id: str = "AUTH_PP_IDEM") -> Dict[str, Any]:
        signed = self._create_signed_contract(amount=amount)
        return self.repo.transition_contract(
            signed["id"],
            self.buyer,
            ContractState.FUNDED,
            metadata={"paypal_order_id": "ORDER_PP_IDEM", "paypal_auth_id": auth_id}
        )

    # -------------------------------------------------------------------------
    # Idempotency Tests: Settlement & Double Charge Prevention
    # -------------------------------------------------------------------------
    def test_idempotency_prevents_duplicate_settlement_and_double_charge(self):
        """
        Critical fintech invariant: Calling settlement twice with the same idempotency key
        MUST NOT double-charge or execute duplicate payouts to the seller.
        """
        contract = self._create_funded_contract(amount=1500.0, auth_id="AUTH_PP_SETTLE_IDEM")
        cid = contract["id"]

        self.mock_paypal.capture_authorization.return_value = {
            "capture_id": "CAP_IDEM_100",
            "status": "COMPLETED",
            "amount": "1200.00",
            "currency": "USD"
        }
        self.mock_paypal.create_payout.return_value = {
            "payout_batch_id": "BATCH_IDEM_100",
            "batch_status": "SUCCESS"
        }
        self.mock_paypal.void_authorization.return_value = {
            "authorization_id": "AUTH_PP_SETTLE_IDEM",
            "status": "VOIDED"
        }

        idem_key = "IDEM_SETTLE_REQ_9999"

        # 1. First execution - executes rails and persists state
        res1 = self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=1200.00,
            refund_amount=300.00,
            seller_paypal_email=self.seller.paypal_email,
            actor=self.admin,
            idempotency_key=idem_key
        )
        self.assertEqual(res1["status"], "SETTLED")
        self.assertEqual(res1["capture_id"], "CAP_IDEM_100")
        self.assertEqual(res1["payout_batch_id"], "BATCH_IDEM_100")
        self.assertEqual(res1["refund_id"], "AUTH_PP_SETTLE_IDEM")

        self.mock_paypal.capture_authorization.assert_called_once()
        self.mock_paypal.create_payout.assert_called_once()
        self.mock_paypal.void_authorization.assert_called_once()

        # Check payments table has exactly 3 records
        payments = self.repo.get_payments(cid)
        self.assertEqual(len(payments), 3)

        # 2. Duplicate retry with same idempotency key
        res2 = self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=1200.00,
            refund_amount=300.00,
            seller_paypal_email=self.seller.paypal_email,
            actor=self.admin,
            idempotency_key=idem_key
        )

        # Responses must be identical
        self.assertEqual(res1, res2)

        # PayPal rails must NOT have been invoked a second time!
        self.mock_paypal.capture_authorization.assert_called_once()
        self.mock_paypal.create_payout.assert_called_once()
        self.mock_paypal.void_authorization.assert_called_once()

        # Ledger records must remain 3 (no duplicate payments)
        self.assertEqual(len(self.repo.get_payments(cid)), 3)

    def test_idempotency_prevents_duplicate_order_creation(self):
        """Duplicate initiate_contract_hold calls return cached order without creating a 2nd PayPal order."""
        contract = self._create_signed_contract(amount=1000.0)
        cid = contract["id"]

        self.mock_paypal.create_authorize_order.return_value = {
            "order_id": "ORDER_FIRST_123",
            "approve_url": "https://sandbox.paypal.com/approve?token=123",
            "status": "CREATED"
        }

        idem_key = "IDEM_ORDER_CREATE_111"
        res1 = self.service.initiate_contract_hold(cid, self.buyer, idempotency_key=idem_key)
        self.assertEqual(res1["paypal_order_id"], "ORDER_FIRST_123")

        # Second call with same idempotency key
        res2 = self.service.initiate_contract_hold(cid, self.buyer, idempotency_key=idem_key)
        self.assertEqual(res1, res2)

        # Ensure PayPal client was called only once
        self.mock_paypal.create_authorize_order.assert_called_once()

    def test_idempotency_prevents_duplicate_authorization(self):
        """Duplicate confirm_and_store_authorization returns cached contract without duplicate state transition."""
        contract = self._create_signed_contract(amount=1000.0)
        cid = contract["id"]

        self.mock_paypal.execute_authorization.return_value = {
            "authorization_id": "AUTH_EXEC_555",
            "status": "CREATED"
        }

        idem_key = "IDEM_AUTH_CONFIRM_222"
        res1 = self.service.confirm_and_store_authorization(
            cid, "ORDER_ID_555", self.buyer, idempotency_key=idem_key
        )
        self.assertEqual(res1["status"], ContractState.FUNDED.value)

        # Second call with same key
        res2 = self.service.confirm_and_store_authorization(
            cid, "ORDER_ID_555", self.buyer, idempotency_key=idem_key
        )
        self.assertEqual(res1["id"], res2["id"])
        self.assertEqual(res2["status"], ContractState.FUNDED.value)

        # PayPal execution was called only once
        self.mock_paypal.execute_authorization.assert_called_once()

    def test_api_settle_idempotency_header_integration(self):
        """API: Idempotency-Key header is respected by REST dispatcher for settle requests."""
        contract = self._create_funded_contract(amount=1000.0, auth_id="AUTH_API_IDEM")
        cid = contract["id"]

        self.mock_paypal.capture_authorization.return_value = {"capture_id": "CAP_API_IDEM", "status": "COMPLETED"}
        self.mock_paypal.create_payout.return_value = {"payout_batch_id": "BATCH_API_IDEM", "batch_status": "SUCCESS"}

        payload = {
            "contract_id": cid,
            "passed_amount": 1000.00,
            "refund_amount": 0.00,
            "seller_paypal_email": self.seller.paypal_email
        }
        headers = {
            "X-Actor-Id": self.admin.id,
            "Content-Type": "application/json",
            "Idempotency-Key": "IDEM_REST_HEADER_777"
        }

        status1, _, body1 = self.api_handler.dispatch("POST", "/api/v1/payments/settle", headers=headers, body=json.dumps(payload).encode("utf-8"))
        self.assertEqual(status1, 200)

        # Second request with identical Idempotency-Key
        status2, _, body2 = self.api_handler.dispatch("POST", "/api/v1/payments/settle", headers=headers, body=json.dumps(payload).encode("utf-8"))
        self.assertEqual(status2, 200)
        self.assertEqual(body1, body2)

        # Upstream PayPal capture and payout called only once
        self.mock_paypal.capture_authorization.assert_called_once()
        self.mock_paypal.create_payout.assert_called_once()

    # -------------------------------------------------------------------------
    # PayPal Webhook Verification Tests
    # -------------------------------------------------------------------------
    def test_process_paypal_webhook_verified_success(self):
        """Webhook with valid cryptographic signature is verified and processed."""
        self.mock_paypal.verify_webhook_signature.return_value = True

        contract = self._create_funded_contract(amount=1000.0)
        cid = contract["id"]

        headers = {
            "paypal-auth-algo": "SHA256withRSA",
            "paypal-cert-url": "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-1234",
            "paypal-transmission-id": "TRANS-UUID-1234",
            "paypal-transmission-sig": "SIGNATURE_BASE_64_STRING",
            "paypal-transmission-time": "2026-11-10T04:00:00Z"
        }
        event_body = {
            "id": "WH-EVT-998877",
            "event_type": "PAYMENT.CAPTURE.COMPLETED",
            "resource": {
                "id": "CAP-8877",
                "custom_id": cid,
                "status": "COMPLETED"
            }
        }

        res = self.service.process_paypal_webhook(
            headers=headers,
            raw_body=json.dumps(event_body).encode("utf-8")
        )

        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["verified"])
        self.assertEqual(res["event_id"], "WH-EVT-998877")
        self.assertEqual(res["event_type"], "PAYMENT.CAPTURE.COMPLETED")
        self.assertEqual(res["action_taken"], "PROCESSED_PAYMENT.CAPTURE.COMPLETED")

        self.mock_paypal.verify_webhook_signature.assert_called_once()

    def test_process_paypal_webhook_invalid_signature_raises(self):
        """Webhook failing verification raises WebhookVerificationError."""
        self.mock_paypal.verify_webhook_signature.return_value = False

        headers = {
            "paypal-auth-algo": "SHA256withRSA",
            "paypal-cert-url": "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-FAKE",
            "paypal-transmission-id": "TRANS-FAKE",
            "paypal-transmission-sig": "INVALID_SIGNATURE",
            "paypal-transmission-time": "2026-11-10T04:00:00Z"
        }
        event_body = {"id": "WH-BAD-1", "event_type": "PAYMENT.CAPTURE.COMPLETED"}

        with self.assertRaises(WebhookVerificationError) as ctx:
            self.service.process_paypal_webhook(
                headers=headers,
                raw_body=json.dumps(event_body).encode("utf-8")
            )
        self.assertIn("signature verification failed", str(ctx.exception))

    def test_process_paypal_webhook_missing_transmission_headers_rejected(self):
        """Webhook missing required PayPal headers raises WebhookVerificationError."""
        headers = {
            # Missing paypal-transmission-sig and paypal-cert-url!
            "paypal-auth-algo": "SHA256withRSA",
            "paypal-transmission-id": "TRANS-INCOMPLETE"
        }
        with self.assertRaises(WebhookVerificationError) as ctx:
            self.service.process_paypal_webhook(headers=headers, raw_body=b'{"id": "1"}')
        self.assertIn("Missing required PayPal transmission signature headers", str(ctx.exception))

    def test_process_paypal_webhook_malformed_json_rejected(self):
        """Webhook with invalid non-JSON payload raises ValueError."""
        headers = {
            "paypal-auth-algo": "SHA256withRSA",
            "paypal-cert-url": "https://cert.test",
            "paypal-transmission-id": "ID",
            "paypal-transmission-sig": "SIG",
            "paypal-transmission-time": "TIME"
        }
        with self.assertRaises(ValueError):
            self.service.process_paypal_webhook(headers=headers, raw_body=b"not-valid-json{{{")

    # -------------------------------------------------------------------------
    # REST API Webhook Endpoint Tests (POST /api/v1/payments/webhooks)
    # -------------------------------------------------------------------------
    def test_api_webhook_endpoint_success_200(self):
        """API: POST /api/v1/payments/webhooks returns 200 on verified webhook."""
        self.mock_paypal.verify_webhook_signature.return_value = True

        headers = {
            "Content-Type": "application/json",
            "Paypal-Auth-Algo": "SHA256withRSA",
            "Paypal-Cert-Url": "https://cert.paypal.com/cert",
            "Paypal-Transmission-Id": "TX-1234",
            "Paypal-Transmission-Sig": "VALID_SIG",
            "Paypal-Transmission-Time": "2026-11-10T04:00:00Z"
        }
        payload = {
            "id": "WH-API-SUCCESS",
            "event_type": "PAYMENT.PAYOUTSBATCH.SUCCESS",
            "resource": {"batch_header": {"payout_batch_id": "BATCH_OK"}}
        }

        status, _, body = self.api_handler.dispatch(
            "POST",
            "/api/v1/payments/webhooks",
            headers=headers,
            body=json.dumps(payload).encode("utf-8")
        )
        self.assertEqual(status, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["status"], "SUCCESS")
        self.assertTrue(data["verified"])
        self.assertEqual(data["event_type"], "PAYMENT.PAYOUTSBATCH.SUCCESS")

    def test_api_webhook_endpoint_invalid_signature_returns_401(self):
        """API: POST /api/v1/payments/webhooks returns 401 when signature verification fails."""
        self.mock_paypal.verify_webhook_signature.return_value = False

        headers = {
            "Content-Type": "application/json",
            "Paypal-Auth-Algo": "SHA256withRSA",
            "Paypal-Cert-Url": "https://cert.paypal.com/cert",
            "Paypal-Transmission-Id": "TX-BAD",
            "Paypal-Transmission-Sig": "BAD_SIG",
            "Paypal-Transmission-Time": "2026-11-10T04:00:00Z"
        }
        status, _, body = self.api_handler.dispatch(
            "POST",
            "/api/v1/payments/webhooks/paypal",
            headers=headers,
            body=json.dumps({"id": "WH-BAD"}).encode("utf-8")
        )
        self.assertEqual(status, 401)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["error"], "INVALID_WEBHOOK_SIGNATURE")

    def test_api_webhook_method_not_allowed_405(self):
        """API: GET on webhook endpoint returns 405 Method Not Allowed."""
        status, _, body = self.api_handler.dispatch("GET", "/api/v1/payments/webhooks")
        self.assertEqual(status, 405)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["error"], "METHOD_NOT_ALLOWED")

    # -------------------------------------------------------------------------
    # PayPalClient Concrete Unit Tests for Headers & Verification
    # -------------------------------------------------------------------------
    def test_paypal_client_sends_idempotency_header(self):
        """PayPalClient sends PayPal-Request-Id header when idempotency_key is provided."""
        client = PayPalClient(client_id="cid", client_secret="sec")
        with patch.object(client, "_send_authorized_request") as mock_req:
            mock_req.return_value = {"id": "CAP_1", "status": "COMPLETED"}
            client.capture_authorization(
                authorization_id="AUTH_1",
                amount=100.0,
                idempotency_key="REQ_ID_IDEM_123"
            )
            mock_req.assert_called_once()
            _, kwargs = mock_req.call_args
            self.assertEqual(kwargs.get("idempotency_key"), "REQ_ID_IDEM_123")

    def test_paypal_client_verify_webhook_signature_schema(self):
        """PayPalClient.verify_webhook_signature sends proper verify payload to PayPal."""
        client = PayPalClient(client_id="cid", client_secret="sec")
        with patch.object(client, "_send_authorized_request") as mock_req:
            mock_req.return_value = {"verification_status": "SUCCESS"}
            is_valid = client.verify_webhook_signature(
                auth_algo="SHA256withRSA",
                cert_url="https://cert.url",
                transmission_id="T_ID",
                transmission_sig="T_SIG",
                transmission_time="T_TIME",
                webhook_event={"id": "EVENT_1"},
                webhook_id="WH_CUSTOM_123"
            )
            self.assertTrue(is_valid)
            mock_req.assert_called_once()
            url, kwargs = mock_req.call_args[0][0], mock_req.call_args[1]
            self.assertIn("/v1/notifications/verify-webhook-signature", url)
            payload = json.loads(kwargs["data"].decode("utf-8"))
            self.assertEqual(payload["webhook_id"], "WH_CUSTOM_123")
            self.assertEqual(payload["auth_algo"], "SHA256withRSA")
            self.assertEqual(payload["transmission_id"], "T_ID")


if __name__ == "__main__":
    unittest.main()

