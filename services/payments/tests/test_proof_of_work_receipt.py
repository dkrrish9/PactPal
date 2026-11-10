"""
Unit & Integration Tests for Proof-of-Work Quality Summary & Cryptographic Receipt (Commit C44)

Done Criteria:
  "Changing one character of the summary changes the hash"

Specifications:
  1. Canonical Proof-of-Work Quality Summary Assembly:
     - Deliverable metadata (repo URL, commit SHA, submission number).
     - Verification metrics (test suite passed/failed, coverage %, cheat scan findings, visual diff score).
     - Per-feature checklist verdict (passed vs failed, price weights, allocated amounts, remainder adjustments).
     - Settlement financial dispatch (passed capture/payout, refund amount, currency, payout batch reference).
     - Deterministic serialization (sorted keys, stripped whitespace, fixed JSON formatting).
  2. Cryptographic SHA-256 Tamper-Evident Hashing:
     - receipt_hash = hashlib.sha256(canonical_summary_bytes).hexdigest()
     - Avalanche effect: Mutating 1 character, 1 digit, or 1 feature status changes the hash completely.
  3. Attachment to PayPal Transaction Rails:
     - In capture_authorization: attach receipt reference in note_to_payer and custom_id.
     - In create_payout: attach receipt reference in payout item note [Receipt: <receipt_hash[:16]>].
  4. Persistence & Verification Storage:
     - Relational receipts table (contract_id, receipt_hash, evidence_payload, submission_id, verification_report_id, generated_at).
     - Relational messages audit ledger (PROOF_OF_WORK_RECEIPT event).
  5. Service & API Exposure:
     - EscrowPaymentService.get_contract_receipt(contract_id, actor=None) -> Dict[str, Any]
     - EscrowPaymentService.verify_receipt_hash(receipt_payload, receipt_hash) -> bool
     - REST API Endpoint: GET /api/v1/contracts/{id}/receipt (200, 401, 403, 404, 405)
     - Dedicated verification endpoint: POST /api/v1/payments/receipts/verify
"""

import json
import copy
import hashlib
import unittest
from datetime import datetime, timezone
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch

from services.payments.client import PayPalClient
from services.payments.service import (
    EscrowPaymentService,
    ProofOfWorkReceipt,
    SettlementSummary,
    canonicalize_proof_of_work_summary,
    generate_proof_of_work_hash,
    verify_receipt_hash,
    ContractRepository,
    User,
    UserRole,
    ContractState,
    ForbiddenActionError,
    StateValidationError
)
from services.payments.api import PaymentsAPIHandler


class TestProofOfWorkReceipt(unittest.TestCase):

    def setUp(self):
        self.repo = ContractRepository(db_path=":memory:")
        self.buyer = self.repo.create_user(
            name="Alice Buyer",
            email="buyer@pactpal.test",
            role=UserRole.BUYER,
            paypal_email="sb-buyer@example.com"
        )
        self.seller = self.repo.create_user(
            name="Bob Seller",
            email="seller@pactpal.test",
            role=UserRole.SELLER,
            paypal_email="sb-seller@example.com"
        )
        self.admin = self.repo.create_user(
            name="Platform Admin",
            email="admin@pactpal.test",
            role=UserRole.ADMIN,
            paypal_email="admin@pactpal.com"
        )
        self.third_party = self.repo.create_user(
            name="Eve Intruder",
            email="intruder@pactpal.test",
            role=UserRole.BUYER,
            paypal_email="sb-intruder@example.com"
        )
        self.ai_referee = User(
            id="AI_REFEREE",
            name="AI Referee",
            email="referee@pactpal.internal",
            role=UserRole.ADMIN
        )

        self.mock_paypal = MagicMock(spec=PayPalClient)
        self.service = EscrowPaymentService(
            paypal_client=self.mock_paypal,
            repository=self.repo
        )
        self.api = PaymentsAPIHandler(service=self.service)

    def tearDown(self):
        if hasattr(self, "repo") and self.repo:
            self.repo.close()

    def _setup_contract_with_deliverable_and_report(
        self,
        total_amount: float = 1000.0,
        weights: List[float] = None,
        feature_statuses: List[str] = None,
        repo_url: str = "https://github.com/freelancer/pactpal-milestone",
        commit_sha: str = "c044a1b2c3d4",
        submission_number: int = 1,
        coverage_percentage: float = 88.5,
        cheat_findings: List[Dict[str, Any]] = None,
        visual_similarity: float = 0.995
    ) -> str:
        weights = weights or [50.0, 50.0]
        feature_statuses = feature_statuses or ["PASSED", "PASSED"]

        contract = self.repo.create_contract(
            buyer=self.buyer,
            seller_id=self.seller.id,
            title="E-Commerce Escrow Contract",
            description="Production escrow milestone contract",
            total_amount=total_amount,
            deadline="2026-12-31T23:59:59Z",
            repo_url=repo_url
        )
        cid = contract["id"]

        feat_ids = []
        for i, (w, st) in enumerate(zip(weights, feature_statuses)):
            f = self.repo.add_feature(
                contract_id=cid,
                title=f"Feature {i+1}",
                acceptance_test=f"Tests for feature {i+1} must pass 100%",
                price_weight=w,
                allocated_amount=round(total_amount * (w / 100.0), 2),
                sort_order=i
            )
            feat_ids.append(f["id"])

        cursor = self.repo.conn.cursor()
        for fid, st in zip(feat_ids, feature_statuses):
            cursor.execute("UPDATE features SET status = ? WHERE id = ?", (st, fid))

        self.repo.confirm_checklist(cid, self.buyer)
        self.repo.confirm_checklist(cid, self.seller)

        cursor.execute("""
            UPDATE contracts
            SET status = 'FUNDED', paypal_auth_id = ?, paypal_order_id = ?, is_locked = 1
            WHERE id = ?
        """, (f"AUTH_{cid[:8]}", f"ORDER_{cid[:8]}", cid))
        self.repo.conn.commit()

        # Create submission record
        sub_id = f"sub_{cid[:8]}"
        cursor.execute("""
            INSERT INTO submissions (id, contract_id, seller_id, repo_url, commit_sha, build_notes, submission_number, is_late, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sub_id, cid, self.seller.id, repo_url, commit_sha, "Milestone delivery",
            submission_number, 0, datetime.now(timezone.utc).isoformat()
        ))
        self.repo.conn.commit()

        # Create verification report
        rep_id = f"rep_{cid[:8]}"
        passed_count = sum(1 for s in feature_statuses if s == "PASSED")
        failed_count = sum(1 for s in feature_statuses if s != "PASSED")
        test_suites = [
            {"name": f"test_feat_{i+1}.js", "status": st}
            for i, st in enumerate(feature_statuses)
        ]

        self.repo.save_verification_report(
            contract_id=cid,
            submission_id=sub_id,
            report_id=rep_id,
            build_succeeded=True,
            test_suite_results={
                "test_suites": test_suites,
                "passed_tests": passed_count,
                "failed_tests": failed_count,
                "status": "PASSED" if failed_count == 0 else "FAILED"
            },
            cheat_scan_findings=cheat_findings or [],
            visual_diff_summary={
                "similarity_score": visual_similarity,
                "passed": visual_similarity >= 0.95
            },
            per_feature_results={
                fid: {"status": st, "passed": (st == "PASSED")} for fid, st in zip(feat_ids, feature_statuses)
            },
            overall_score=passed_count / max(1, len(feature_statuses))
        )

        return cid

    # --- 1. Deterministic Canonical Hash Generation ---

    def test_deterministic_hash_generation(self):
        """Verify that identical proof-of-work quality summaries produce the exact same SHA-256 hash."""
        summary1 = {
            "contract_id": "cnt_1001",
            "deliverable": {
                "commit_sha": "a1b2c3d4e5f6",
                "repo_url": "https://github.com/freelancer/pactpal-store",
                "submission_number": 1
            },
            "features": [
                {
                    "allocated_amount": 500.0,
                    "feature_id": "feat_1",
                    "price_weight": 50.0,
                    "remainder_adjustment": 0.0,
                    "status": "PASSED",
                    "title": "Feature 1: User Login"
                },
                {
                    "allocated_amount": 500.0,
                    "feature_id": "feat_2",
                    "price_weight": 50.0,
                    "remainder_adjustment": 0.0,
                    "status": "PASSED",
                    "title": "Feature 2: Shopping Cart"
                }
            ],
            "financial_dispatch": {
                "currency": "USD",
                "passed_amount": 1000.0,
                "payout_batch_reference": "batch_pactpal_1001",
                "refund_amount": 0.0,
                "total_amount": 1000.0
            },
            "verification_metrics": {
                "cheat_scan_findings_by_severity": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
                "coverage_percentage": 92.4,
                "test_suite": {"failed": 0, "passed": 4, "status": "PASSED", "total": 4},
                "visual_diff_similarity_score": 0.998
            }
        }

        # Create duplicate summary with completely scrambled key ordering
        summary2 = {
            "verification_metrics": {
                "visual_diff_similarity_score": 0.998,
                "test_suite": {"total": 4, "status": "PASSED", "passed": 4, "failed": 0},
                "coverage_percentage": 92.4,
                "cheat_scan_findings_by_severity": {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
            },
            "financial_dispatch": {
                "total_amount": 1000.0,
                "refund_amount": 0.0,
                "payout_batch_reference": "batch_pactpal_1001",
                "passed_amount": 1000.0,
                "currency": "USD"
            },
            "deliverable": {
                "submission_number": 1,
                "repo_url": "https://github.com/freelancer/pactpal-store",
                "commit_sha": "a1b2c3d4e5f6"
            },
            "contract_id": "cnt_1001",
            "features": [
                {
                    "allocated_amount": 500.0,
                    "feature_id": "feat_1",
                    "price_weight": 50.0,
                    "remainder_adjustment": 0.0,
                    "status": "PASSED",
                    "title": "Feature 1: User Login"
                },
                {
                    "allocated_amount": 500.0,
                    "feature_id": "feat_2",
                    "price_weight": 50.0,
                    "remainder_adjustment": 0.0,
                    "status": "PASSED",
                    "title": "Feature 2: Shopping Cart"
                }
            ]
        }

        hash1 = generate_proof_of_work_hash(summary1)
        hash2 = generate_proof_of_work_hash(summary2)

        self.assertEqual(len(hash1), 64)
        self.assertEqual(hash1, hash2, "Scrambled dictionary keys must produce identical canonical hash.")

    # --- 2. Tamper-Evidence: Avalanche Effect (Done Criteria) ---

    def test_tamper_evidence_changing_one_character_changes_hash(self):
        """
        Checklist / Done When: Changing one character of the summary changes the hash.
        Fuzzes mutations across all deliverable, verification, feature, and financial fields.
        """
        base_summary = {
            "contract_id": "cnt_test_avalanche",
            "deliverable": {
                "commit_sha": "commit_sha_123456",
                "repo_url": "https://github.com/alice/project",
                "submission_number": 1
            },
            "features": [
                {
                    "allocated_amount": 250.0,
                    "feature_id": "feat_1",
                    "price_weight": 25.0,
                    "remainder_adjustment": 0.0,
                    "status": "PASSED",
                    "title": "Feature 1: Authentication"
                },
                {
                    "allocated_amount": 250.0,
                    "feature_id": "feat_2",
                    "price_weight": 25.0,
                    "remainder_adjustment": 0.0,
                    "status": "PASSED",
                    "title": "Feature 2: Dashboard"
                }
            ],
            "financial_dispatch": {
                "currency": "USD",
                "passed_amount": 500.0,
                "payout_batch_reference": "batch_ref_alpha",
                "refund_amount": 0.0,
                "total_amount": 500.0
            },
            "verification_metrics": {
                "cheat_scan_findings_by_severity": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
                "coverage_percentage": 85.0,
                "test_suite": {"failed": 0, "passed": 10, "status": "PASSED", "total": 10},
                "visual_diff_similarity_score": 0.99
            }
        }

        base_hash = generate_proof_of_work_hash(base_summary)

        # 1. Mutate 1 character in repo_url
        mut_repo = copy.deepcopy(base_summary)
        mut_repo["deliverable"]["repo_url"] = "https://github.com/alice/project2"
        self.assertNotEqual(generate_proof_of_work_hash(mut_repo), base_hash)

        # 2. Mutate 1 character in commit_sha
        mut_sha = copy.deepcopy(base_summary)
        mut_sha["deliverable"]["commit_sha"] = "commit_sha_123457"
        self.assertNotEqual(generate_proof_of_work_hash(mut_sha), base_hash)

        # 3. Mutate submission_number (1 -> 2)
        mut_sub = copy.deepcopy(base_summary)
        mut_sub["deliverable"]["submission_number"] = 2
        self.assertNotEqual(generate_proof_of_work_hash(mut_sub), base_hash)

        # 4. Mutate test_suite passed count (10 -> 9)
        mut_test = copy.deepcopy(base_summary)
        mut_test["verification_metrics"]["test_suite"]["passed"] = 9
        self.assertNotEqual(generate_proof_of_work_hash(mut_test), base_hash)

        # 5. Mutate test_suite status ('PASSED' -> 'FAILED')
        mut_test_st = copy.deepcopy(base_summary)
        mut_test_st["verification_metrics"]["test_suite"]["status"] = "FAILED"
        self.assertNotEqual(generate_proof_of_work_hash(mut_test_st), base_hash)

        # 6. Mutate coverage by 0.1% (85.0 -> 85.1)
        mut_cov = copy.deepcopy(base_summary)
        mut_cov["verification_metrics"]["coverage_percentage"] = 85.1
        self.assertNotEqual(generate_proof_of_work_hash(mut_cov), base_hash)

        # 7. Mutate cheat scan critical findings (0 -> 1)
        mut_cheat = copy.deepcopy(base_summary)
        mut_cheat["verification_metrics"]["cheat_scan_findings_by_severity"]["CRITICAL"] = 1
        self.assertNotEqual(generate_proof_of_work_hash(mut_cheat), base_hash)

        # 8. Mutate visual diff similarity score by 0.001 (0.99 -> 0.991)
        mut_vis = copy.deepcopy(base_summary)
        mut_vis["verification_metrics"]["visual_diff_similarity_score"] = 0.991
        self.assertNotEqual(generate_proof_of_work_hash(mut_vis), base_hash)

        # 9. Mutate 1 feature status from PASSED to FAILED
        mut_feat_st = copy.deepcopy(base_summary)
        mut_feat_st["features"][0]["status"] = "FAILED"
        self.assertNotEqual(generate_proof_of_work_hash(mut_feat_st), base_hash)

        # 10. Mutate 1 cent in feature allocated_amount (250.0 -> 250.01)
        mut_feat_amt = copy.deepcopy(base_summary)
        mut_feat_amt["features"][0]["allocated_amount"] = 250.01
        self.assertNotEqual(generate_proof_of_work_hash(mut_feat_amt), base_hash)

        # 11. Mutate 1 cent in feature remainder_adjustment (0.0 -> 0.01)
        mut_rem = copy.deepcopy(base_summary)
        mut_rem["features"][1]["remainder_adjustment"] = 0.01
        self.assertNotEqual(generate_proof_of_work_hash(mut_rem), base_hash)

        # 12. Mutate 1 cent in passed_amount (500.0 -> 499.99)
        mut_pass = copy.deepcopy(base_summary)
        mut_pass["financial_dispatch"]["passed_amount"] = 499.99
        self.assertNotEqual(generate_proof_of_work_hash(mut_pass), base_hash)

        # 13. Mutate 1 cent in refund_amount (0.0 -> 0.01)
        mut_ref = copy.deepcopy(base_summary)
        mut_ref["financial_dispatch"]["refund_amount"] = 0.01
        self.assertNotEqual(generate_proof_of_work_hash(mut_ref), base_hash)

        # 14. Mutate 1 character in payout_batch_reference ('alpha' -> 'alphb')
        mut_batch = copy.deepcopy(base_summary)
        mut_batch["financial_dispatch"]["payout_batch_reference"] = "batch_ref_alphb"
        self.assertNotEqual(generate_proof_of_work_hash(mut_batch), base_hash)

    # --- 3. Cryptographic Verification Helper ---

    def test_verify_receipt_hash(self):
        """Verify verify_receipt_hash handles valid, mutated, and malformed receipt payloads."""
        summary = {
            "contract_id": "cnt_verify_test",
            "deliverable": {"commit_sha": "abc", "repo_url": "https://github.com/repo", "submission_number": 1},
            "features": [{"allocated_amount": 100.0, "feature_id": "feat_1", "price_weight": 100.0, "remainder_adjustment": 0.0, "status": "PASSED", "title": "F1"}],
            "financial_dispatch": {"currency": "USD", "passed_amount": 100.0, "payout_batch_reference": "batch_1", "refund_amount": 0.0, "total_amount": 100.0},
            "verification_metrics": {"cheat_scan_findings_by_severity": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}, "coverage_percentage": 90.0, "test_suite": {"failed": 0, "passed": 1, "status": "PASSED", "total": 1}, "visual_diff_similarity_score": 1.0}
        }
        correct_hash = generate_proof_of_work_hash(summary)

        # Valid payload returns True
        self.assertTrue(verify_receipt_hash(summary, correct_hash))

        # Tampered payload returns False
        tampered = copy.deepcopy(summary)
        tampered["deliverable"]["commit_sha"] = "tampered_commit"
        self.assertFalse(verify_receipt_hash(tampered, correct_hash))

        # Wrapped in evidence_payload returns True
        wrapped = {"evidence_payload": {"summary": summary}}
        self.assertTrue(verify_receipt_hash(wrapped, correct_hash))

        # JSON string returns True
        json_str = json.dumps(summary)
        self.assertTrue(verify_receipt_hash(json_str, correct_hash))

        # Empty/None/Invalid returns False
        self.assertFalse(verify_receipt_hash(None, correct_hash))
        self.assertFalse(verify_receipt_hash({}, ""))
        self.assertFalse(verify_receipt_hash(summary, "bad_hash_hex"))

    # --- 4. Attachment to PayPal Rails ---

    def test_paypal_client_rail_attachment(self):
        """Verify PayPalClient capture_authorization and create_payout attach receipt references in payloads."""
        client = PayPalClient(client_id="test_id", client_secret="test_secret")

        # Mock _send_authorized_request to intercept outgoing payload
        captured_requests = []

        def mock_send(url, data=None, method="GET", idempotency_key=None):
            captured_requests.append({
                "url": url,
                "data": json.loads(data.decode()) if data else None,
                "method": method
            })
            if "capture" in url:
                return {"id": "CAP_123", "status": "COMPLETED", "amount": {"value": "100.00", "currency_code": "USD"}}
            elif "payouts" in url:
                return {"batch_header": {"payout_batch_id": "BATCH_123", "batch_status": "PENDING"}}
            return {}

        client._send_authorized_request = mock_send

        test_hash = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"

        # 1. Capture Authorization with receipt reference
        client.capture_authorization(
            authorization_id="AUTH_999",
            amount=100.00,
            currency="USD",
            receipt_hash=test_hash
        )
        self.assertEqual(len(captured_requests), 1)
        cap_req = captured_requests[0]
        self.assertIn("v2/payments/authorizations/AUTH_999/capture", cap_req["url"])
        self.assertEqual(cap_req["data"]["note_to_payer"], f"PactPal Release [Receipt: {test_hash[:16]}]")
        self.assertEqual(cap_req["data"]["custom_id"], test_hash)

        # 2. Payout to Seller with receipt reference
        client.create_payout(
            receiver_email="sb-seller@example.com",
            amount=100.00,
            currency="USD",
            receipt_hash=test_hash
        )
        self.assertEqual(len(captured_requests), 2)
        payout_req = captured_requests[1]
        self.assertIn("v1/payments/payouts", payout_req["url"])
        items = payout_req["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertIn(f"[Receipt: {test_hash[:16]}]", items[0]["note"])

    def test_escrow_settlement_passes_receipt_to_paypal_rails(self):
        """Verify settle_contract_escrow attaches receipt reference when interacting with PayPal rails."""
        cid = self._setup_contract_with_deliverable_and_report(
            total_amount=500.0,
            weights=[100.0],
            feature_statuses=["PASSED"]
        )

        self.mock_paypal.capture_authorization.return_value = {"capture_id": "CAP_ATTACH_TEST"}
        self.mock_paypal.create_payout.return_value = {"payout_batch_id": "BATCH_ATTACH_TEST"}

        res = self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=500.0,
            refund_amount=0.0,
            seller_paypal_email=self.seller.paypal_email,
            actor=self.admin,
            metadata={"attach_receipt_to_rails": True}
        )

        receipt_hash = res["receipt_hash"]
        self.assertEqual(len(receipt_hash), 64)

        # Verify capture_authorization received receipt_hash and note_to_payer
        self.mock_paypal.capture_authorization.assert_called_once()
        cap_call_kwargs = self.mock_paypal.capture_authorization.call_args.kwargs
        self.assertEqual(cap_call_kwargs["receipt_hash"], receipt_hash)
        self.assertEqual(cap_call_kwargs["note_to_payer"], f"PactPal Release [Receipt: {receipt_hash[:16]}]")
        self.assertEqual(cap_call_kwargs["custom_id"], receipt_hash[:127])

        # Verify create_payout received payout note with receipt hash
        self.mock_paypal.create_payout.assert_called_once()
        payout_call_kwargs = self.mock_paypal.create_payout.call_args.kwargs
        self.assertEqual(payout_call_kwargs["receipt_hash"], receipt_hash)
        self.assertIn(f"[Receipt: {receipt_hash[:16]}]", payout_call_kwargs["note"])

    # --- 5. Database Persistence & Audit Messages ---

    def test_database_persistence_and_audit_messages(self):
        """Verify receipts and messages tables record proof-of-work receipt and cryptographic hash."""
        cid = self._setup_contract_with_deliverable_and_report(
            total_amount=600.0,
            weights=[50.0, 50.0],
            feature_statuses=["PASSED", "PASSED"],
            commit_sha="c44sha0099"
        )

        self.mock_paypal.capture_authorization.return_value = {"capture_id": "CAP_DB_TEST"}
        self.mock_paypal.create_payout.return_value = {"payout_batch_id": "BATCH_DB_TEST"}

        res = self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=600.0,
            refund_amount=0.0,
            seller_paypal_email=self.seller.paypal_email,
            actor=self.admin
        )
        receipt_hash = res["receipt_hash"]

        # 1. Receipts table check
        receipt_record = self.repo.get_receipt(cid)
        self.assertIsNotNone(receipt_record)
        self.assertEqual(receipt_record["receipt_hash"], receipt_hash)
        self.assertIsNotNone(receipt_record["submission_id"])
        self.assertIsNotNone(receipt_record["verification_report_id"])

        ev = receipt_record["evidence_payload"]
        self.assertIn("summary", ev)
        self.assertEqual(ev["summary"]["deliverable"]["commit_sha"], "c44sha0099")

        # 2. Messages table check
        msgs = self.repo.get_messages(cid)
        pow_msg = next((m for m in msgs if m.get("metadata", {}).get("event") == "PROOF_OF_WORK_RECEIPT"), None)
        self.assertIsNotNone(pow_msg, "Audit message with event PROOF_OF_WORK_RECEIPT must be recorded.")
        self.assertEqual(pow_msg["metadata"]["receipt_hash"], receipt_hash)
        self.assertIn(receipt_hash, pow_msg["content"])

    # --- 6. Service get_contract_receipt & Tamper Detection ---

    def test_get_contract_receipt_and_tamper_detection(self):
        """Verify get_contract_receipt returns verified status and detects tampering in stored evidence."""
        cid = self._setup_contract_with_deliverable_and_report(
            total_amount=400.0,
            weights=[100.0],
            feature_statuses=["PASSED"]
        )

        self.mock_paypal.capture_authorization.return_value = {"capture_id": "CAP_1"}
        self.mock_paypal.create_payout.return_value = {"payout_batch_id": "BATCH_1"}

        settle_res = self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=400.0,
            refund_amount=0.0,
            seller_paypal_email=self.seller.paypal_email,
            actor=self.admin
        )
        receipt_hash = settle_res["receipt_hash"]

        # 1. Normal verified receipt retrieval
        receipt_data = self.service.get_contract_receipt(contract_id=cid, actor=self.buyer)
        self.assertEqual(receipt_data["receipt_hash"], receipt_hash)
        self.assertTrue(receipt_data["is_valid"])
        self.assertEqual(receipt_data["status"], "VERIFIED")

        # 2. Tamper with the database evidence payload
        cursor = self.repo.conn.cursor()
        cursor.execute("SELECT evidence_payload FROM receipts WHERE contract_id = ?", (cid,))
        row = cursor.fetchone()
        evidence_dict = json.loads(row["evidence_payload"])
        # Mutate 1 character in deliverable repo URL
        evidence_dict["summary"]["deliverable"]["repo_url"] = "https://github.com/tampered/repo"
        cursor.execute(
            "UPDATE receipts SET evidence_payload = ? WHERE contract_id = ?",
            (json.dumps(evidence_dict), cid)
        )
        self.repo.conn.commit()

        # 3. Retrieve receipt again: must detect tampering!
        tampered_receipt = self.service.get_contract_receipt(contract_id=cid, actor=self.buyer)
        self.assertFalse(tampered_receipt["is_valid"], "Tampered evidence payload must fail verification.")
        self.assertEqual(tampered_receipt["status"], "TAMPERED")

    # --- 7. RBAC on get_contract_receipt ---

    def test_rbac_on_get_contract_receipt(self):
        """Verify RBAC permissions on get_contract_receipt."""
        cid = self._setup_contract_with_deliverable_and_report(
            total_amount=500.0,
            weights=[100.0],
            feature_statuses=["PASSED"]
        )
        self.mock_paypal.capture_authorization.return_value = {"capture_id": "CAP_RBAC"}
        self.mock_paypal.create_payout.return_value = {"payout_batch_id": "BATCH_RBAC"}
        self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=500.0,
            refund_amount=0.0,
            seller_paypal_email=self.seller.paypal_email,
            actor=self.admin
        )

        # Buyer can view
        self.assertTrue(self.service.get_contract_receipt(cid, actor=self.buyer)["is_valid"])

        # Seller can view
        self.assertTrue(self.service.get_contract_receipt(cid, actor=self.seller)["is_valid"])

        # Admin can view
        self.assertTrue(self.service.get_contract_receipt(cid, actor=self.admin)["is_valid"])

        # AI Referee can view
        self.assertTrue(self.service.get_contract_receipt(cid, actor=self.ai_referee)["is_valid"])

        # Third-party unauthorized actor is forbidden
        with self.assertRaises(ForbiddenActionError):
            self.service.get_contract_receipt(cid, actor=self.third_party)

        # Non-existent contract raises ValueError
        with self.assertRaises(ValueError):
            self.service.get_contract_receipt("non_existent_cnt", actor=self.buyer)

    # --- 8. REST API GET /api/v1/contracts/{id}/receipt ---

    def test_rest_api_get_receipt_endpoints(self):
        """Verify REST API GET /api/v1/contracts/{id}/receipt dispatch and response codes."""
        cid = self._setup_contract_with_deliverable_and_report(
            total_amount=800.0,
            weights=[50.0, 50.0],
            feature_statuses=["PASSED", "PASSED"]
        )
        self.mock_paypal.capture_authorization.return_value = {"capture_id": "CAP_API"}
        self.mock_paypal.create_payout.return_value = {"payout_batch_id": "BATCH_API"}
        settle_res = self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=800.0,
            refund_amount=0.0,
            seller_paypal_email=self.seller.paypal_email,
            actor=self.admin
        )
        receipt_hash = settle_res["receipt_hash"]

        # 200 OK for Buyer
        code, headers, body = self.api.dispatch("GET", f"/api/v1/contracts/{cid}/receipt", headers={"X-Actor-Id": self.buyer.id})
        self.assertEqual(code, 200)
        data = json.loads(body.decode())
        self.assertEqual(data["receipt_hash"], receipt_hash)
        self.assertTrue(data["is_valid"])
        self.assertEqual(data["status"], "VERIFIED")

        # 200 OK for Seller
        code, _, _ = self.api.dispatch("GET", f"/api/v1/contracts/{cid}/receipt", headers={"X-Actor-Id": self.seller.id})
        self.assertEqual(code, 200)

        # 401 Unauthorized when missing actor
        code, _, _ = self.api.dispatch("GET", f"/api/v1/contracts/{cid}/receipt", headers={})
        self.assertEqual(code, 401)

        # 403 Forbidden for unauthorized intruder
        code, _, _ = self.api.dispatch("GET", f"/api/v1/contracts/{cid}/receipt", headers={"X-Actor-Id": self.third_party.id})
        self.assertEqual(code, 403)

        # 404 Not Found for non-existent contract
        code, _, _ = self.api.dispatch("GET", "/api/v1/contracts/non_existent/receipt", headers={"X-Actor-Id": self.buyer.id})
        self.assertEqual(code, 404)

        # 405 Method Not Allowed on POST
        code, _, _ = self.api.dispatch("POST", f"/api/v1/contracts/{cid}/receipt", headers={"X-Actor-Id": self.buyer.id})
        self.assertEqual(code, 405)

    # --- 9. REST API POST /api/v1/payments/receipts/verify ---

    def test_rest_api_verify_receipt_endpoint(self):
        """Verify REST API POST /api/v1/payments/receipts/verify verifies hashes accurately."""
        summary = {
            "contract_id": "cnt_rest_verify",
            "deliverable": {"commit_sha": "abc1234", "repo_url": "https://github.com/test", "submission_number": 1},
            "features": [{"allocated_amount": 100.0, "feature_id": "f1", "price_weight": 100.0, "remainder_adjustment": 0.0, "status": "PASSED", "title": "F1"}],
            "financial_dispatch": {"currency": "USD", "passed_amount": 100.0, "payout_batch_reference": "ref1", "refund_amount": 0.0, "total_amount": 100.0},
            "verification_metrics": {"cheat_scan_findings_by_severity": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}, "coverage_percentage": 95.0, "test_suite": {"failed": 0, "passed": 2, "status": "PASSED", "total": 2}, "visual_diff_similarity_score": 1.0}
        }
        valid_hash = generate_proof_of_work_hash(summary)

        # 1. Valid receipt payload -> 200 is_valid: True
        req_body = json.dumps({"receipt_payload": summary, "receipt_hash": valid_hash}).encode()
        code, _, resp_bytes = self.api.dispatch("POST", "/api/v1/payments/receipts/verify", body=req_body)
        self.assertEqual(code, 200)
        resp_data = json.loads(resp_bytes.decode())
        self.assertTrue(resp_data["is_valid"])
        self.assertEqual(resp_data["status"], "VERIFIED")

        # 2. Tampered receipt payload -> 200 is_valid: False
        tampered_summary = copy.deepcopy(summary)
        tampered_summary["deliverable"]["commit_sha"] = "mutated_sha"
        bad_req_body = json.dumps({"receipt_payload": tampered_summary, "receipt_hash": valid_hash}).encode()
        code, _, resp_bytes = self.api.dispatch("POST", "/api/v1/payments/receipts/verify", body=bad_req_body)
        self.assertEqual(code, 200)
        resp_data = json.loads(resp_bytes.decode())
        self.assertFalse(resp_data["is_valid"])
        self.assertEqual(resp_data["status"], "TAMPERED")

        # 3. Missing fields -> 400 Bad Request
        code, _, _ = self.api.dispatch("POST", "/api/v1/payments/receipts/verify", body=json.dumps({"receipt_hash": valid_hash}).encode())
        self.assertEqual(code, 400)

        # 4. GET method -> 405 Method Not Allowed
        code, _, _ = self.api.dispatch("GET", "/api/v1/payments/receipts/verify")
        self.assertEqual(code, 405)

    # --- 10. Idempotency Key Preserves Proof-of-Work Receipt ---

    def test_idempotency_preserves_proof_of_work_receipt(self):
        """Verify duplicate settle calls with identical idempotency key return the same receipt_hash and cached proof-of-work receipt."""
        cid = self._setup_contract_with_deliverable_and_report(
            total_amount=350.0,
            weights=[100.0],
            feature_statuses=["PASSED"]
        )

        self.mock_paypal.capture_authorization.return_value = {"capture_id": "CAP_IDEM_POW"}
        self.mock_paypal.create_payout.return_value = {"payout_batch_id": "BATCH_IDEM_POW"}

        key = "idem_key_c44_receipt"
        res1 = self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=350.0,
            refund_amount=0.0,
            seller_paypal_email=self.seller.paypal_email,
            actor=self.admin,
            idempotency_key=key
        )

        res2 = self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=350.0,
            refund_amount=0.0,
            seller_paypal_email=self.seller.paypal_email,
            actor=self.admin,
            idempotency_key=key
        )

        self.assertEqual(res1["receipt_hash"], res2["receipt_hash"])
        self.assertEqual(res1["proof_of_work_summary"], res2["proof_of_work_summary"])
        self.assertEqual(self.mock_paypal.capture_authorization.call_count, 1)


if __name__ == "__main__":
    unittest.main()
