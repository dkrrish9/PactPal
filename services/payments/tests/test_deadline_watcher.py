"""
PactPal Unit & Integration Test Suite for Scheduled Deadline Watcher
Commit C49 (Milestone 3: Money & Extras)
Done When: Watcher fires on a test contract without manual help.
"""

import json
import unittest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from typing import Dict, Any, Optional, List

from services.payments.client import PayPalClient, PayPalAPIError
from services.payments.service import (
    EscrowPaymentService,
    PaymentApprovalService,
    PaymentApprovalError,
    ContractRepository,
    User,
    UserRole,
    ContractState,
    ForbiddenActionError,
    UnauthorizedRoleError,
    StateValidationError,
    assert_can_trigger_deadline_watcher
)
from services.payments.deadline_watcher import (
    DeadlineWatcherService,
    SweepResult,
    parse_datetime
)
from services.payments.api import PaymentsAPIHandler, create_payments_app


class TestDeadlineWatcher(unittest.TestCase):

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
            paypal_email="sb-seller@business.example.com"
        )
        self.admin = self.repo.create_user(
            name="Platform Admin",
            email="admin@pactpal.test",
            role=UserRole.ADMIN
        )
        self.ai_referee = User(
            id="AI_REFEREE",
            name="AI Referee",
            email="referee@pactpal.internal",
            role=UserRole.ADMIN
        )
        self.stranger = self.repo.create_user(
            name="Charlie Stranger",
            email="stranger@pactpal.test",
            role=UserRole.BUYER
        )

        self.mock_paypal = MagicMock(spec=PayPalClient)
        # Default mock responses
        self.mock_paypal.capture_authorization.return_value = {
            "capture_id": "CAP_MOCK_12345",
            "status": "COMPLETED",
            "amount": "600.00",
            "currency": "USD"
        }
        self.mock_paypal.create_payout.return_value = {
            "payout_batch_id": "BATCH_MOCK_67890",
            "batch_status": "SUCCESS",
            "amount": "600.00",
            "currency": "USD"
        }
        self.mock_paypal.void_authorization.return_value = {
            "authorization_id": "AUTH_MOCK_445566",
            "status": "VOIDED"
        }

        self.payment_service = EscrowPaymentService(
            repository=self.repo,
            paypal_client=self.mock_paypal
        )
        self.watcher = DeadlineWatcherService(
            repository=self.repo,
            payment_service=self.payment_service
        )
        self.api_handler = PaymentsAPIHandler(
            service=self.payment_service,
            deadline_watcher=self.watcher
        )

    def tearDown(self):
        if self.watcher.is_daemon_running():
            self.watcher.stop_background_daemon()
        self.repo.close()

    def _create_active_contract(
        self,
        total_amount: float = 1000.0,
        deadline: Optional[str] = None,
        status: ContractState = ContractState.IN_PROGRESS,
        auth_id: str = "AUTH_PP_DEADLINE_TEST",
        features: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Creates a locked, funded contract advanced to active state (IN_PROGRESS/SUBMITTED/VERIFYING)."""
        dl_str = deadline or (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        contract = self.repo.create_contract(
            buyer=self.buyer,
            seller_id=self.seller.id,
            title="SaaS Mobile App MVP",
            description="Milestone deliverable under deadline watch",
            total_amount=total_amount,
            deadline=dl_str
        )
        cid = contract["id"]

        # Add features BEFORE locking checklist
        if features:
            for f in features:
                self.repo.add_feature(
                    contract_id=cid,
                    title=f.get("title", "Feature"),
                    acceptance_test=f.get("acceptance_test", "Test"),
                    price_weight=float(f.get("price_weight", 100.0)),
                    allocated_amount=float(f.get("allocated_amount", total_amount)),
                    sort_order=int(f.get("sort_order", 1))
                )
        else:
            self.repo.add_feature(
                contract_id=cid,
                title="MVP Deliverable",
                acceptance_test="Core feature acceptance tests",
                price_weight=100.0,
                allocated_amount=total_amount,
                sort_order=1
            )

        # Dual confirm to lock checklist (Gate 1 invariant)
        self.repo.confirm_checklist(cid, self.buyer)
        self.repo.confirm_checklist(cid, self.seller)

        # Advance DRAFT -> REVIEW -> SIGNED -> FUNDED
        self.repo.transition_contract(cid, self.buyer, ContractState.REVIEW)
        self.repo.transition_contract(cid, self.seller, ContractState.SIGNED, metadata={"acceptance_confirmed": True})
        self.repo.transition_contract(
            cid,
            self.buyer,
            ContractState.FUNDED,
            metadata={"paypal_order_id": f"ORD_{cid[:8]}", "paypal_auth_id": auth_id}
        )

        # Advance FUNDED -> IN_PROGRESS
        if status in (ContractState.IN_PROGRESS, ContractState.SUBMITTED, ContractState.VERIFYING):
            self.repo.transition_contract(cid, self.seller, ContractState.IN_PROGRESS)

        if status in (ContractState.SUBMITTED, ContractState.VERIFYING):
            self.repo.transition_contract(cid, self.seller, ContractState.SUBMITTED)

        if status == ContractState.VERIFYING:
            self.repo.transition_contract(cid, self.ai_referee, ContractState.VERIFYING)

        return self.repo.get_contract(cid)

    # -------------------------------------------------------------------------
    # 1. Detection of Expired vs Future Deadlines
    # -------------------------------------------------------------------------
    def test_watcher_detects_expired_deadline(self):
        """Watcher accurately identifies when contract deadline is in the past."""
        past_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        contract = self._create_active_contract(deadline=past_time)

        self.assertTrue(self.watcher.is_deadline_expired(contract))

    def test_watcher_ignores_future_deadline(self):
        """Watcher accurately identifies that a future deadline has not expired."""
        future_time = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        contract = self._create_active_contract(deadline=future_time)

        self.assertFalse(self.watcher.is_deadline_expired(contract))

        # Check and process contract should skip processing
        res = self.watcher.check_and_process_contract(contract["id"], force=False)
        self.assertFalse(res["processed"])
        self.assertEqual(res["status"], "SKIPPED")
        self.assertIn("has not expired", res["reason"])

        # Contract state remains unchanged
        unchanged = self.repo.get_contract(contract["id"])
        self.assertEqual(unchanged["status"], ContractState.IN_PROGRESS.value)

    # -------------------------------------------------------------------------
    # 2. Zero-Submission Abandonment Handling (100% Refund to Buyer)
    # -------------------------------------------------------------------------
    def test_zero_submission_abandonment_full_refund(self):
        """
        When deadline expires and seller submitted NO code:
        Treat as complete abandonment: 0% passed to seller, 100% refunded to buyer.
        Void authorization on PayPal rails, transition contract to SETTLED.
        """
        past_deadline = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        contract = self._create_active_contract(total_amount=1500.0, deadline=past_deadline)
        cid = contract["id"]

        # Ensure no submission exists
        self.assertIsNone(self.repo.get_latest_submission(cid))

        res = self.watcher.check_and_process_contract(cid)

        # Assertions on watcher response
        self.assertTrue(res["processed"])
        self.assertEqual(res["status"], "SETTLED")
        self.assertEqual(res["passed_amount"], 0.0)
        self.assertEqual(res["refund_amount"], 1500.0)
        self.assertEqual(res["rule_applied"], "FULL_REFUND_ABANDONMENT_NO_SUBMISSION")

        # PayPal Rails assertions
        self.mock_paypal.capture_authorization.assert_not_called()
        self.mock_paypal.create_payout.assert_not_called()
        self.mock_paypal.void_authorization.assert_called_once()

        # Database state assertions
        updated = self.repo.get_contract(cid)
        self.assertEqual(updated["status"], ContractState.SETTLED.value)

        # Audit message recorded in messages table
        messages = self.repo.get_messages(cid)
        trigger_events = [
            m for m in messages
            if (isinstance(m.get("metadata"), dict) and m["metadata"].get("event") == "DEADLINE_EXPIRED_SETTLEMENT_TRIGGERED")
            or "DEADLINE_EXPIRED_SETTLEMENT_TRIGGERED" in str(m.get("metadata", ""))
        ]
        self.assertGreaterEqual(len(trigger_events), 1)
        meta = trigger_events[0]["metadata"]
        event_meta = meta if isinstance(meta, dict) else json.loads(meta)
        self.assertEqual(event_meta["event"], "DEADLINE_EXPIRED_SETTLEMENT_TRIGGERED")
        self.assertEqual(event_meta["passed_amount"], 0.0)
        self.assertEqual(event_meta["refund_amount"], 1500.0)
        self.assertFalse(event_meta["has_submission"])

    # -------------------------------------------------------------------------
    # 3. Partial-Pass Submission Handling (Proportional Split Math Integration)
    # -------------------------------------------------------------------------
    def test_partial_pass_submission_settlement(self):
        """
        When deadline expires and seller submitted deliverable with partial pass results:
        Proportional split engine evaluates passed features ($600 passed, $400 refund).
        Executes capture ($600), seller payout ($600), and voids remainder ($400).
        """
        past_deadline = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
        feats = [
            {"title": "API Gateway", "acceptance_test": "Passes auth tests", "price_weight": 60.0, "allocated_amount": 600.0, "sort_order": 1},
            {"title": "Dashboard UI", "acceptance_test": "Renders chart widgets", "price_weight": 40.0, "allocated_amount": 400.0, "sort_order": 2}
        ]
        contract = self._create_active_contract(total_amount=1000.0, deadline=past_deadline, features=feats)
        cid = contract["id"]

        contract_features = self.repo.get_features(cid)
        f1_id = contract_features[0]["id"]
        f2_id = contract_features[1]["id"]

        # Seller submits deliverable
        sub = self.repo.create_submission(
            contract_id=cid,
            seller_id=self.seller.id,
            repo_url="https://github.com/pactpal/saas-repo",
            commit_sha="c49partial11"
        )

        # Verification report: Feature 1 PASSED, Feature 2 FAILED
        per_feature_results = {
            f1_id: {
                "id": f1_id,
                "status": "PASSED",
                "price_weight": 60.0,
                "allocated_amount": 600.0
            },
            f2_id: {
                "id": f2_id,
                "status": "FAILED",
                "price_weight": 40.0,
                "allocated_amount": 400.0
            }
        }
        self.repo.save_verification_report(
            contract_id=cid,
            submission_id=sub["id"],
            build_succeeded=True,
            test_suite_results={"passed": 1, "failed": 1, "total": 2},
            cheat_scan_findings=[],
            per_feature_results=per_feature_results,
            overall_score=0.6
        )

        # Configure mock PayPal capture and payout
        self.mock_paypal.capture_authorization.return_value = {
            "capture_id": "CAP_PARTIAL_600",
            "status": "COMPLETED",
            "amount": "600.00",
            "currency": "USD"
        }
        self.mock_paypal.create_payout.return_value = {
            "payout_batch_id": "BATCH_PARTIAL_600",
            "batch_status": "SUCCESS",
            "amount": "600.00",
            "currency": "USD"
        }

        # Watcher processes expired contract
        res = self.watcher.check_and_process_contract(cid)

        # Assertions on watcher result
        self.assertTrue(res["processed"])
        self.assertEqual(res["status"], "SETTLED")
        self.assertEqual(res["passed_amount"], 600.0)
        self.assertEqual(res["refund_amount"], 400.0)
        self.assertEqual(res["rule_applied"], "PROPORTIONAL_PARTIAL_SPLIT")
        self.assertTrue(res["has_submission"])
        self.assertIsNotNone(res["receipt_hash"])

        # PayPal Rails assertions
        self.mock_paypal.capture_authorization.assert_called_once()
        capture_kwargs = self.mock_paypal.capture_authorization.call_args[1]
        self.assertEqual(capture_kwargs["amount"], 600.0)
        self.assertFalse(capture_kwargs["is_final_capture"])

        self.mock_paypal.create_payout.assert_called_once()
        payout_kwargs = self.mock_paypal.create_payout.call_args[1]
        self.assertEqual(payout_kwargs["amount"], 600.0)
        self.assertEqual(payout_kwargs["receiver_email"], self.seller.paypal_email)

        self.mock_paypal.void_authorization.assert_called_once()

        # Contract moved to SETTLED
        updated = self.repo.get_contract(cid)
        self.assertEqual(updated["status"], ContractState.SETTLED.value)

        # Proof of work receipt recorded in receipts table
        receipt = self.repo.get_receipt(cid)
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt["receipt_hash"], res["receipt_hash"])

    # -------------------------------------------------------------------------
    # 4. Full-Pass Submission Settlement (100% Payout to Seller)
    # -------------------------------------------------------------------------
    def test_full_pass_submission_settlement(self):
        """When seller passes 100% of features by deadline, full capture & payout executed."""
        past_deadline = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        feats = [{"title": "Full Feature", "acceptance_test": "Passes", "price_weight": 100.0, "allocated_amount": 1200.0, "sort_order": 1}]
        contract = self._create_active_contract(total_amount=1200.0, deadline=past_deadline, features=feats)
        cid = contract["id"]

        contract_features = self.repo.get_features(cid)
        f1_id = contract_features[0]["id"]

        sub = self.repo.create_submission(contract_id=cid, seller_id=self.seller.id)
        self.repo.save_verification_report(
            contract_id=cid,
            submission_id=sub["id"],
            build_succeeded=True,
            test_suite_results={"passed": 1, "failed": 0, "total": 1},
            cheat_scan_findings=[],
            per_feature_results={f1_id: {"status": "PASSED", "allocated_amount": 1200.0, "price_weight": 100.0}},
            overall_score=1.0
        )

        res = self.watcher.check_and_process_contract(cid)

        self.assertEqual(res["passed_amount"], 1200.0)
        self.assertEqual(res["refund_amount"], 0.0)
        self.assertEqual(res["rule_applied"], "FULL_RELEASE_100_PERCENT")

        self.mock_paypal.capture_authorization.assert_called_once()
        self.mock_paypal.create_payout.assert_called_once()
        self.mock_paypal.void_authorization.assert_not_called()

        updated = self.repo.get_contract(cid)
        self.assertEqual(updated["status"], ContractState.SETTLED.value)

    # -------------------------------------------------------------------------
    # 5. Scheduled Batch Sweep Execution (sweep_expired_deadlines)
    # -------------------------------------------------------------------------
    def test_sweep_expired_deadlines_batch(self):
        """
        Batch sweep tests:
          - Contract A: Expired, no submission -> full refund.
          - Contract B: Future deadline -> skipped.
          - Contract C: Expired, verified submission -> partial payout.
          - Contract D: Already settled -> skipped.
        SweepResult behaves both as a list and as a dict with metrics.
        """
        past_dl = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        future_dl = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()

        # Contract A (Expired, Abandoned)
        cA = self._create_active_contract(total_amount=500.0, deadline=past_dl, auth_id="AUTH_SWEEP_A")

        # Contract B (Future deadline)
        cB = self._create_active_contract(total_amount=800.0, deadline=future_dl, auth_id="AUTH_SWEEP_B")

        # Contract C (Expired, Verified)
        feats_C = [{"title": "Feature C", "acceptance_test": "Test C", "price_weight": 100.0, "allocated_amount": 1000.0, "sort_order": 1}]
        cC = self._create_active_contract(total_amount=1000.0, deadline=past_dl, auth_id="AUTH_SWEEP_C", features=feats_C)
        fC_id = self.repo.get_features(cC["id"])[0]["id"]

        subC = self.repo.create_submission(contract_id=cC["id"], seller_id=self.seller.id)
        self.repo.save_verification_report(
            contract_id=cC["id"],
            submission_id=subC["id"],
            build_succeeded=True,
            test_suite_results={"passed": 1},
            cheat_scan_findings=[],
            per_feature_results={fC_id: {"status": "PASSED", "allocated_amount": 1000.0, "price_weight": 100.0}},
            overall_score=1.0
        )

        # Execute sweep
        sweep_result = self.watcher.sweep_expired_deadlines()

        # Verify dual list/dict behavior
        self.assertIsInstance(sweep_result, list)
        self.assertEqual(len(sweep_result), 2)  # cA and cC processed
        self.assertEqual(sweep_result["contracts_settled"], 2)
        self.assertGreaterEqual(sweep_result["contracts_inspected"], 3)

        # Check outcomes
        processed_ids = [r["contract_id"] for r in sweep_result]
        self.assertIn(cA["id"], processed_ids)
        self.assertIn(cC["id"], processed_ids)
        self.assertNotIn(cB["id"], processed_ids)

        # Contract states updated
        self.assertEqual(self.repo.get_contract(cA["id"])["status"], ContractState.SETTLED.value)
        self.assertEqual(self.repo.get_contract(cB["id"])["status"], ContractState.IN_PROGRESS.value)
        self.assertEqual(self.repo.get_contract(cC["id"])["status"], ContractState.SETTLED.value)

    # -------------------------------------------------------------------------
    # 6. Admin Simulate Deadline Endpoint (POST /api/v1/contracts/{id}/simulate-deadline)
    # -------------------------------------------------------------------------
    def test_admin_simulate_deadline_endpoint_success(self):
        """Admin can force simulate deadline expiry on a future-dated contract for testing."""
        future_dl = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        contract = self._create_active_contract(total_amount=750.0, deadline=future_dl)
        cid = contract["id"]

        headers = {
            "Content-Type": "application/json",
            "X-Actor-Id": self.admin.id
        }
        body = json.dumps({"force": True}).encode("utf-8")

        status, resp_headers, resp_bytes = self.api_handler.dispatch(
            method="POST",
            path=f"/api/v1/contracts/{cid}/simulate-deadline",
            headers=headers,
            body=body
        )

        self.assertEqual(status, 200)
        data = json.loads(resp_bytes.decode("utf-8"))
        self.assertEqual(data["contract_id"], cid)
        self.assertEqual(data["status"], "SETTLED")
        self.assertTrue(data["processed"])
        self.assertEqual(data["refund_amount"], 750.0)

        # Contract moved to SETTLED
        self.assertEqual(self.repo.get_contract(cid)["status"], ContractState.SETTLED.value)

    def test_simulate_deadline_rbac_rejections(self):
        """Non-admin actors (Buyer, Seller, Stranger) are blocked from simulating deadline (403 Forbidden)."""
        future_dl = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        contract = self._create_active_contract(total_amount=500.0, deadline=future_dl)
        cid = contract["id"]

        # Buyer attempts simulation -> 403
        status, _, resp_bytes = self.api_handler.dispatch(
            method="POST",
            path=f"/api/v1/contracts/{cid}/simulate-deadline",
            headers={"X-Actor-Id": self.buyer.id}
        )
        self.assertEqual(status, 403)
        self.assertIn("FORBIDDEN", resp_bytes.decode("utf-8"))

        # Seller attempts simulation -> 403
        status, _, resp_bytes = self.api_handler.dispatch(
            method="POST",
            path=f"/api/v1/contracts/{cid}/simulate-deadline",
            headers={"X-Actor-Id": self.seller.id}
        )
        self.assertEqual(status, 403)

        # Stranger attempts simulation -> 403
        status, _, resp_bytes = self.api_handler.dispatch(
            method="POST",
            path=f"/api/v1/contracts/{cid}/simulate-deadline",
            headers={"X-Actor-Id": self.stranger.id}
        )
        self.assertEqual(status, 403)

        # Missing actor -> 401 Unauthorized
        status, _, resp_bytes = self.api_handler.dispatch(
            method="POST",
            path=f"/api/v1/contracts/{cid}/simulate-deadline",
            headers={}
        )
        self.assertEqual(status, 401)

        # Non-existent contract -> 404 Not Found
        status, _, _ = self.api_handler.dispatch(
            method="POST",
            path="/api/v1/contracts/non-existent-contract-uuid/simulate-deadline",
            headers={"X-Actor-Id": self.admin.id}
        )
        self.assertEqual(status, 404)

        # Invalid method -> 405 Method Not Allowed
        status, _, _ = self.api_handler.dispatch(
            method="GET",
            path=f"/api/v1/contracts/{cid}/simulate-deadline",
            headers={"X-Actor-Id": self.admin.id}
        )
        self.assertEqual(status, 405)

    # -------------------------------------------------------------------------
    # 7. Sweep REST Endpoint (POST /api/v1/payments/deadline-watcher/sweep)
    # -------------------------------------------------------------------------
    def test_sweep_rest_endpoint_dispatch_and_rbac(self):
        """Tests REST API dispatch and role enforcement on the deadline sweep endpoint."""
        # 1. Admin trigger -> 200 OK
        status, _, resp_bytes = self.api_handler.dispatch(
            method="POST",
            path="/api/v1/payments/deadline-watcher/sweep",
            headers={"X-Actor-Id": self.admin.id}
        )
        self.assertEqual(status, 200)
        data = json.loads(resp_bytes.decode("utf-8"))
        self.assertIn("contracts_inspected", data)

        # 2. AI Referee trigger -> 200 OK
        status, _, resp_bytes = self.api_handler.dispatch(
            method="POST",
            path="/api/v1/payments/deadline-watcher/sweep",
            headers={"X-Actor-Id": "AI_REFEREE"}
        )
        self.assertEqual(status, 200)

        # 3. Buyer trigger -> 403 Forbidden
        status, _, _ = self.api_handler.dispatch(
            method="POST",
            path="/api/v1/payments/deadline-watcher/sweep",
            headers={"X-Actor-Id": self.buyer.id}
        )
        self.assertEqual(status, 403)

        # 4. Anonymous trigger -> 401 Unauthorized
        status, _, _ = self.api_handler.dispatch(
            method="POST",
            path="/api/v1/payments/deadline-watcher/sweep",
            headers={}
        )
        self.assertEqual(status, 401)

        # 5. Method not allowed (GET) -> 405
        status, _, _ = self.api_handler.dispatch(
            method="GET",
            path="/api/v1/payments/deadline-watcher/sweep",
            headers={"X-Actor-Id": self.admin.id}
        )
        self.assertEqual(status, 405)

    # -------------------------------------------------------------------------
    # 8. Background Daemon Thread Lifecycle
    # -------------------------------------------------------------------------
    def test_background_daemon_lifecycle(self):
        """Watcher daemon thread can be started and gracefully stopped."""
        self.assertFalse(self.watcher.is_daemon_running())

        daemon = self.watcher.start_background_daemon(interval_seconds=0.1)
        self.assertTrue(self.watcher.is_daemon_running())
        self.assertTrue(daemon.is_alive())

        time.sleep(0.15)

        self.watcher.stop_background_daemon()
        self.assertFalse(self.watcher.is_daemon_running())

    # -------------------------------------------------------------------------
    # 9. Done When Checklist: Watcher fires on a test contract without manual help
    # -------------------------------------------------------------------------
    def test_done_when_watcher_fires_without_manual_help(self):
        """
        Verifies the authoritative Done When criteria:
        'Watcher fires on a test contract without manual help'
        Contract with expired deadline is swept automatically and settled without any manual intervention.
        """
        past_deadline = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        contract = self._create_active_contract(total_amount=2000.0, deadline=past_deadline)
        cid = contract["id"]

        # Run sweep without any manual parameters or manual help
        sweep_result = self.watcher.sweep_expired_deadlines()

        # Contract was settled automatically
        self.assertGreaterEqual(len(sweep_result), 1)
        processed_cid = [r["contract_id"] for r in sweep_result]
        self.assertIn(cid, processed_cid)

        # Database contract status is now SETTLED
        updated_contract = self.repo.get_contract(cid)
        self.assertEqual(updated_contract["status"], ContractState.SETTLED.value)

        # PayPal Void was executed automatically without manual help
        self.mock_paypal.void_authorization.assert_called()


if __name__ == "__main__":
    unittest.main()
