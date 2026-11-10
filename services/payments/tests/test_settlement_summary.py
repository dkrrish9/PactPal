"""
Unit & Integration Tests for Settlement Summary (Commit C41: Milestone 3 - Money & Extras)

Done Criteria:
  "Summary appears after every settlement"

Specifications:
  1. Dual Settlement Summary Generation:
     - Buyer Summary: Total funded amount, amount returned/refunded, amount released,
       breakdown of which features passed vs failed, and clear, human-readable rationale ("why") for the refund.
     - Seller Summary: Total contract price, amount paid out (with payout batch reference),
       unreleased/deducted amount, itemized feature payouts with remainder adjustments,
       and detailed explanation ("why") for any failed or deducted features.
  2. Audit Trail & Message Ledger Persistence:
     - Immutably logs summary into relational messages table for both buyer and seller view.
     - Includes cryptographic receipt fingerprint (receipt_hash) linking to proof-of-work receipt.
  3. Service & API Exposure:
     - EscrowPaymentService.get_settlement_summary(contract_id, actor=None)
     - REST API Endpoint: GET /api/v1/contracts/{id}/settlement-summary (200, 401, 403, 404, 400, 405)
     - POST /api/v1/payments/settle returns settlement summary in its response payload.
  4. Scenarios Tested:
     - Full release (100% payout / $0 returned with celebratory summary)
     - Full refund (0% payout / 100% returned with failure explanation)
     - Partial split summaries with itemized remainder adjustments and specific passed/failed explanations
     - Invariant enforcement: round(passed_amount + refund_amount, 2) == round(total_amount, 2)
     - Idempotency replay returns cached settlement summary
     - RBAC enforcement: Buyer, Seller, Platform Admin, AI Referee allowed; Unauthorized actor forbidden.
"""

import json
import unittest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch

from services.payments.client import PayPalClient
from services.payments.service import (
    EscrowPaymentService,
    SettlementSummary,
    ProportionalSplitResult,
    ContractRepository,
    User,
    UserRole,
    ContractState,
    ForbiddenActionError,
    StateValidationError
)
from services.payments.api import PaymentsAPIHandler


class TestSettlementSummary(unittest.TestCase):

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
        self.stranger = self.repo.create_user(
            name="Charlie Stranger",
            email="stranger@pactpal.test",
            role=UserRole.BUYER,
            paypal_email="stranger@example.com"
        )
        self.ai_referee = User(
            id="AI_REFEREE",
            name="AI Referee",
            email="referee@pactpal.internal",
            role=UserRole.ADMIN
        )

        self.mock_paypal = MagicMock(spec=PayPalClient)
        self.service = EscrowPaymentService(paypal_client=self.mock_paypal, repository=self.repo)
        self.api = PaymentsAPIHandler(service=self.service)

    def tearDown(self):
        if hasattr(self, "repo") and self.repo:
            self.repo.close()

    def _setup_contract_with_features(
        self,
        total_amount: float = 1000.0,
        weights: List[float] = None,
        feature_statuses: List[str] = None
    ) -> str:
        """Helper to create a funded and checklist-locked contract with defined features."""
        weights = weights or [33.33, 33.33, 33.34]
        feature_statuses = feature_statuses or ["PASSED", "PASSED", "PASSED"]

        contract = self.repo.create_contract(
            buyer=self.buyer,
            seller_id=self.seller.id,
            title="E-Commerce Storefront MVP",
            description="Build modern headless e-commerce frontend",
            total_amount=total_amount,
            deadline=(datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        )
        cid = contract["id"]

        feat_ids = []
        for i, (w, st) in enumerate(zip(weights, feature_statuses)):
            f = self.repo.add_feature(
                contract_id=cid,
                title=f"Feature {i+1}: Module {chr(65+i)}",
                acceptance_test=f"Tests for module {chr(65+i)} must pass 100%",
                price_weight=w,
                allocated_amount=round(total_amount * (w / 100.0), 2),
                sort_order=i
            )
            feat_ids.append(f["id"])

        # Update status in features table
        cursor = self.repo.conn.cursor()
        for fid, st in zip(feat_ids, feature_statuses):
            cursor.execute("UPDATE features SET status = ? WHERE id = ?", (st, fid))

        # Lock checklist & advance state
        self.repo.confirm_checklist(cid, self.buyer)
        self.repo.confirm_checklist(cid, self.seller)

        cursor.execute("""
            UPDATE contracts
            SET status = 'FUNDED', paypal_auth_id = ?, paypal_order_id = ?, is_locked = 1
            WHERE id = ?
        """, (f"AUTH_{cid[:8]}", f"ORDER_{cid[:8]}", cid))
        self.repo.conn.commit()

        # Seed mock verification report
        per_feat = {
            fid: {"passed": (st == "PASSED"), "status": st, "score": 100.0 if st == "PASSED" else 0.0}
            for fid, st in zip(feat_ids, feature_statuses)
        }
        self.repo.save_verification_report(
            contract_id=cid,
            build_succeeded=True,
            per_feature_results=per_feat
        )

        return cid

    def test_full_release_settlement_summary(self):
        """
        Scenario 1: 100% Full Payout ($1,000 paid to seller, $0 returned to buyer).
        Verifies celebratory summaries for both parties with payout batch references.
        """
        cid = self._setup_contract_with_features(
            total_amount=1000.0,
            weights=[33.33, 33.33, 33.34],
            feature_statuses=["PASSED", "PASSED", "PASSED"]
        )

        self.mock_paypal.capture_authorization.return_value = {
            "capture_id": "CAP_100_FULL",
            "status": "COMPLETED",
            "amount": {"value": "1000.00", "currency_code": "USD"}
        }
        self.mock_paypal.create_payout.return_value = {
            "payout_batch_id": "BATCH_100_FULL",
            "batch_status": "SUCCESS"
        }

        settle_res = self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=1000.0,
            refund_amount=0.0,
            seller_paypal_email="sb-seller@example.com",
            actor=self.admin
        )

        # 1. Verify summary returned in settle payload
        self.assertIn("settlement_summary", settle_res)
        self.assertIn("buyer_summary", settle_res)
        self.assertIn("seller_summary", settle_res)

        summary = settle_res["settlement_summary"]
        self.assertEqual(summary["rule_applied"], "FULL_RELEASE_100_PERCENT")
        self.assertEqual(summary["total_amount"], 1000.0)
        self.assertEqual(summary["passed_amount"], 1000.0)
        self.assertEqual(summary["refund_amount"], 0.0)
        self.assertEqual(summary["payout_batch_id"], "BATCH_100_FULL")

        # 2. Verify Buyer Summary
        buyer_sum = settle_res["buyer_summary"]
        self.assertEqual(buyer_sum["funded_amount"], 1000.0)
        self.assertEqual(buyer_sum["refund_amount"], 0.0)
        self.assertEqual(buyer_sum["amount_released"], 1000.0)
        self.assertEqual(buyer_sum["features_total"], 3)
        self.assertEqual(buyer_sum["features_passed"], 3)
        self.assertEqual(buyer_sum["features_failed"], 0)
        self.assertIn("All 3 checklist features met all verification criteria", buyer_sum["why"])
        self.assertIn("0.00 USD returned", buyer_sum["why"])
        self.assertEqual(len(buyer_sum["features_breakdown"]), 3)
        self.assertTrue(all(f["status"] == "PASSED" for f in buyer_sum["features_breakdown"]))

        # 3. Verify Seller Summary
        seller_sum = settle_res["seller_summary"]
        self.assertEqual(seller_sum["contract_price"], 1000.0)
        self.assertEqual(seller_sum["amount_paid"], 1000.0)
        self.assertEqual(seller_sum["unreleased_amount"], 0.0)
        self.assertEqual(seller_sum["payout_batch_id"], "BATCH_100_FULL")
        self.assertEqual(seller_sum["seller_paypal_email"], "sb-seller@example.com")
        self.assertIn("All 3 checklist features verified successfully", seller_sum["why"])
        self.assertIn("BATCH_100_FULL", seller_sum["why"])
        self.assertEqual(len(seller_sum["itemized_payouts"]), 3)
        self.assertTrue(all(f["paid_out"] is True for f in seller_sum["itemized_payouts"]))

        # 4. Verify perspective retrieval via get_settlement_summary
        buyer_view = self.service.get_settlement_summary(cid, actor=self.buyer)
        self.assertEqual(buyer_view["perspective"], "BUYER")
        self.assertEqual(buyer_view["amount_returned"], 0.0)
        self.assertEqual(buyer_view["amount_released"], 1000.0)
        self.assertIn("All 3 checklist features met", buyer_view["why"])

        seller_view = self.service.get_settlement_summary(cid, actor=self.seller)
        self.assertEqual(seller_view["perspective"], "SELLER")
        self.assertEqual(seller_view["amount_paid"], 1000.0)
        self.assertEqual(seller_view["payout_batch_id"], "BATCH_100_FULL")
        self.assertIn("BATCH_100_FULL", seller_view["why"])

    def test_full_refund_settlement_summary(self):
        """
        Scenario 2: 0% Payout / 100% Refund ($0 paid to seller, $1,000 returned to buyer).
        Verifies failure explanation for both parties.
        """
        cid = self._setup_contract_with_features(
            total_amount=1000.0,
            weights=[50.0, 50.0],
            feature_statuses=["FAILED", "FAILED"]
        )

        self.mock_paypal.void_authorization.return_value = {
            "authorization_id": f"AUTH_{cid[:8]}",
            "status": "VOIDED"
        }

        settle_res = self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=0.0,
            refund_amount=1000.0,
            actor=self.ai_referee
        )

        summary = settle_res["settlement_summary"]
        self.assertEqual(summary["rule_applied"], "FULL_REFUND_0_PERCENT")
        self.assertEqual(summary["passed_amount"], 0.0)
        self.assertEqual(summary["refund_amount"], 1000.0)

        # Buyer View: Failure explanation and 100% refund confirmation
        buyer_sum = settle_res["buyer_summary"]
        self.assertEqual(buyer_sum["refund_amount"], 1000.0)
        self.assertEqual(buyer_sum["amount_released"], 0.0)
        self.assertEqual(buyer_sum["features_passed"], 0)
        self.assertEqual(buyer_sum["features_failed"], 2)
        self.assertIn("No checklist features met acceptance criteria", buyer_sum["why"])
        self.assertIn("1000.00 USD has been refunded", buyer_sum["why"])

        # Seller View: Explanation of why funds were withheld
        seller_sum = settle_res["seller_summary"]
        self.assertEqual(seller_sum["amount_paid"], 0.0)
        self.assertEqual(seller_sum["unreleased_amount"], 1000.0)
        self.assertIn("Deliverable did not meet verification criteria", seller_sum["why"])
        self.assertIn("No funds were disbursed", seller_sum["why"])

    def test_partial_split_settlement_summary_with_remainder_adjustment(self):
        """
        Scenario 3: Proportional partial split with remainder penny adjustment.
        Contract: $1,000.00, 3 features @ 33.33%, 33.33%, 33.33% (sum = 99.99%).
        Unadjusted allocations are $333.33 each ($999.99 total).
        Deterministic remainder rule allocates +$0.01 to Feature 3 ($333.34).
        Feature 1 ($333.33) & Feature 3 ($333.34) PASS ($666.67 passed), Feature 2 FAILS ($333.33 refund).
        Verifies exact cent accounting, remainder note, and itemized breakdowns.
        """
        cid = self._setup_contract_with_features(
            total_amount=1000.0,
            weights=[33.33, 33.33, 33.33],
            feature_statuses=["PASSED", "FAILED", "PASSED"]
        )

        self.mock_paypal.capture_authorization.return_value = {
            "capture_id": "CAP_PARTIAL_C41",
            "status": "COMPLETED"
        }
        self.mock_paypal.create_payout.return_value = {
            "payout_batch_id": "BATCH_PARTIAL_C41",
            "batch_status": "SUCCESS"
        }
        self.mock_paypal.void_authorization.return_value = {
            "authorization_id": f"AUTH_{cid[:8]}",
            "status": "VOIDED"
        }

        # Auto-derive split from features
        settle_res = self.service.settle_contract_escrow(
            contract_id=cid,
            seller_paypal_email="sb-seller@example.com",
            actor=self.admin
        )

        passed = settle_res["passed_amount"]
        refund = settle_res["refund_amount"]
        self.assertEqual(round(passed + refund, 2), 1000.0)
        self.assertEqual(passed, 666.67)
        self.assertEqual(refund, 333.33)

        # Check Buyer Summary
        buyer_sum = settle_res["buyer_summary"]
        self.assertEqual(buyer_sum["amount_released"], 666.67)
        self.assertEqual(buyer_sum["amount_returned"], 333.33)
        self.assertEqual(buyer_sum["features_passed"], 2)
        self.assertEqual(buyer_sum["features_failed"], 1)
        self.assertIn("2 of 3 checklist features passed verification", buyer_sum["why"])
        self.assertIn("666.67 USD was released", buyer_sum["why"])
        self.assertIn("333.33 USD was refunded", buyer_sum["why"])
        self.assertIn("Feature 2: Module B", buyer_sum["why"])

        # Check Seller Summary
        seller_sum = settle_res["seller_summary"]
        self.assertEqual(seller_sum["amount_paid"], 666.67)
        self.assertEqual(seller_sum["unreleased_amount"], 333.33)
        self.assertEqual(seller_sum["payout_batch_id"], "BATCH_PARTIAL_C41")
        self.assertIn("2 of 3 features verified", seller_sum["why"])
        self.assertIn("BATCH_PARTIAL_C41", seller_sum["why"])
        self.assertIn("Feature 2: Module B", seller_sum["why"])
        self.assertIn("Remainder adjustment of +0.01 USD applied", seller_sum["why"])

        # Check itemized payouts and remainder adjustments
        itemized = seller_sum["itemized_payouts"]
        self.assertEqual(len(itemized), 3)
        self.assertTrue(itemized[0]["paid_out"])
        self.assertFalse(itemized[1]["paid_out"])
        self.assertTrue(itemized[2]["paid_out"])
        self.assertTrue(itemized[2]["is_last_feature"])
        self.assertEqual(itemized[2]["adjustment_applied"], 0.01)

    def test_audit_ledger_messages_and_receipt_persistence(self):
        """
        Verify that every settlement automatically logs an immutable audit summary
        to the relational messages table and records the cryptographic receipt fingerprint.
        """
        cid = self._setup_contract_with_features(
            total_amount=500.0,
            weights=[100.0],
            feature_statuses=["PASSED"]
        )

        self.mock_paypal.capture_authorization.return_value = {"capture_id": "CAP_AUDIT"}
        self.mock_paypal.create_payout.return_value = {"payout_batch_id": "BATCH_AUDIT"}

        settle_res = self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=500.0,
            refund_amount=0.0,
            seller_paypal_email="sb-seller@example.com",
            actor=self.admin
        )
        receipt_hash = settle_res["receipt_hash"]

        # Verify record in messages table
        cursor = self.repo.conn.cursor()
        cursor.execute("""
            SELECT * FROM messages
            WHERE contract_id = ? AND metadata LIKE '%SETTLEMENT_SUMMARY%'
            ORDER BY sent_at DESC LIMIT 1
        """, (cid,))
        msg_row = cursor.fetchone()
        self.assertIsNotNone(msg_row)
        self.assertIn("Settlement finalized", msg_row["content"])
        self.assertIn(receipt_hash, msg_row["content"])

        meta = json.loads(msg_row["metadata"])
        self.assertEqual(meta["event"], "SETTLEMENT_SUMMARY")
        self.assertEqual(meta["receipt_hash"], receipt_hash)
        self.assertEqual(meta["passed_amount"], 500.0)
        self.assertEqual(meta["refund_amount"], 0.0)
        self.assertIn("buyer_summary", meta)
        self.assertIn("seller_summary", meta)

        # Verify receipt table storage
        receipt_row = self.repo.get_receipt(cid)
        self.assertIsNotNone(receipt_row)
        self.assertEqual(receipt_row["receipt_hash"], receipt_hash)
        self.assertEqual(receipt_row["evidence_payload"]["passed_amount"], 500.0)

    def test_idempotency_caching_returns_settlement_summary(self):
        """Verify duplicate settle calls with identical idempotency key return cached settlement summary."""
        cid = self._setup_contract_with_features(
            total_amount=300.0,
            weights=[100.0],
            feature_statuses=["PASSED"]
        )

        self.mock_paypal.capture_authorization.return_value = {"capture_id": "CAP_IDEM"}
        self.mock_paypal.create_payout.return_value = {"payout_batch_id": "BATCH_IDEM"}

        key = "idem-c41-summary-test"
        res1 = self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=300.0,
            refund_amount=0.0,
            seller_paypal_email="sb-seller@example.com",
            actor=self.admin,
            idempotency_key=key
        )

        res2 = self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=300.0,
            refund_amount=0.0,
            seller_paypal_email="sb-seller@example.com",
            actor=self.admin,
            idempotency_key=key
        )

        self.assertEqual(res1["receipt_hash"], res2["receipt_hash"])
        self.assertIn("settlement_summary", res2)
        self.assertEqual(res2["settlement_summary"]["total_amount"], 300.0)
        # Verify PayPal client was only called once
        self.assertEqual(self.mock_paypal.capture_authorization.call_count, 1)
        self.assertEqual(self.mock_paypal.create_payout.call_count, 1)

    def test_rest_api_get_settlement_summary_success(self):
        """
        REST API endpoint GET /api/v1/contracts/{id}/settlement-summary:
        Tests 200 OK for Buyer, Seller, and Admin actors.
        """
        cid = self._setup_contract_with_features(
            total_amount=800.0,
            weights=[50.0, 50.0],
            feature_statuses=["PASSED", "FAILED"]
        )

        self.mock_paypal.capture_authorization.return_value = {"capture_id": "CAP_API"}
        self.mock_paypal.create_payout.return_value = {"payout_batch_id": "BATCH_API"}
        self.mock_paypal.void_authorization.return_value = {"authorization_id": f"AUTH_{cid[:8]}"}

        self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=400.0,
            refund_amount=400.0,
            seller_paypal_email="sb-seller@example.com",
            actor=self.admin
        )

        # 1. Buyer Actor Request -> Expect Buyer Perspective
        code, headers, body = self.api.dispatch(
            method="GET",
            path=f"/api/v1/contracts/{cid}/settlement-summary",
            headers={"X-Actor-Id": self.buyer.id}
        )
        self.assertEqual(code, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["perspective"], "BUYER")
        self.assertEqual(data["total_funded_amount"], 800.0)
        self.assertEqual(data["amount_released"], 400.0)
        self.assertEqual(data["amount_returned"], 400.0)
        self.assertIn("why", data)
        self.assertEqual(len(data["features_breakdown"]), 2)

        # 2. Seller Actor Request -> Expect Seller Perspective
        code, headers, body = self.api.dispatch(
            method="GET",
            path=f"/api/v1/contracts/{cid}/settlement-summary",
            headers={"X-Actor-Id": self.seller.id}
        )
        self.assertEqual(code, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["perspective"], "SELLER")
        self.assertEqual(data["contract_price"], 800.0)
        self.assertEqual(data["amount_paid"], 400.0)
        self.assertEqual(data["unreleased_amount"], 400.0)
        self.assertEqual(data["payout_batch_id"], "BATCH_API")
        self.assertIn("why", data)
        self.assertEqual(len(data["itemized_payouts"]), 2)

        # 3. Admin Actor Request -> Expect Comprehensive Dual Perspective
        code, headers, body = self.api.dispatch(
            method="GET",
            path=f"/api/v1/contracts/{cid}/settlement-summary",
            headers={"X-Actor-Id": self.admin.id}
        )
        self.assertEqual(code, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["perspective"], "ADMIN")
        self.assertIn("buyer_summary", data)
        self.assertIn("seller_summary", data)
        self.assertEqual(data["total_amount"], 800.0)
        self.assertEqual(data["passed_amount"], 400.0)
        self.assertEqual(data["refund_amount"], 400.0)

        # 4. AI Referee Request -> Expect Comprehensive Dual Perspective
        code, headers, body = self.api.dispatch(
            method="GET",
            path=f"/api/v1/contracts/{cid}/settlement-summary",
            headers={"X-Actor-Id": "AI_REFEREE"}
        )
        self.assertEqual(code, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["perspective"], "AI_REFEREE")
        self.assertIn("buyer_summary", data)
        self.assertIn("seller_summary", data)

    def test_rest_api_get_settlement_summary_error_cases(self):
        """
        REST API endpoint GET /api/v1/contracts/{id}/settlement-summary:
        Tests 401 Unauthorized, 403 Forbidden, 404 Not Found, 400 Bad Request (unsettled), and 405 Method Not Allowed.
        """
        cid = self._setup_contract_with_features(total_amount=500.0)

        # 1. 401 Unauthorized (No actor headers)
        code, _, body = self.api.dispatch(
            method="GET",
            path=f"/api/v1/contracts/{cid}/settlement-summary",
            headers={}
        )
        self.assertEqual(code, 401)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["error"], "UNAUTHORIZED")

        # 2. 400 Bad Request: Contract exists but is NOT in SETTLED status (currently FUNDED)
        code, _, body = self.api.dispatch(
            method="GET",
            path=f"/api/v1/contracts/{cid}/settlement-summary",
            headers={"X-Actor-Id": self.buyer.id}
        )
        self.assertEqual(code, 400)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["error"], "BAD_REQUEST")
        self.assertIn("not SETTLED", data["message"])

        # Settle the contract
        self.mock_paypal.capture_authorization.return_value = {"capture_id": "CAP_ERR"}
        self.mock_paypal.create_payout.return_value = {"payout_batch_id": "BATCH_ERR"}
        self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=500.0,
            refund_amount=0.0,
            seller_paypal_email="sb-seller@example.com",
            actor=self.admin
        )

        # 3. 403 Forbidden: Stranger actor who is not Buyer, Seller, Admin, or AI Referee
        code, _, body = self.api.dispatch(
            method="GET",
            path=f"/api/v1/contracts/{cid}/settlement-summary",
            headers={"X-Actor-Id": self.stranger.id}
        )
        self.assertEqual(code, 403)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["error"], "FORBIDDEN")

        # 4. 404 Not Found: Non-existent contract ID
        code, _, body = self.api.dispatch(
            method="GET",
            path="/api/v1/contracts/cnt_nonexistent_9999/settlement-summary",
            headers={"X-Actor-Id": self.admin.id}
        )
        self.assertEqual(code, 404)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["error"], "NOT_FOUND")

        # 5. 405 Method Not Allowed: POST to settlement-summary endpoint
        code, _, body = self.api.dispatch(
            method="POST",
            path=f"/api/v1/contracts/{cid}/settlement-summary",
            headers={"X-Actor-Id": self.admin.id}
        )
        self.assertEqual(code, 405)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["error"], "METHOD_NOT_ALLOWED")


if __name__ == "__main__":
    unittest.main()
