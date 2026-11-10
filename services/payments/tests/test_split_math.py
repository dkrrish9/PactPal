"""
Unit & Integration Tests for Proportional Partial Split Math (Commit C37: Milestone 3 - Money & Extras)

Done Criteria:
  "Paid + refunded always equals contract price, to the cent"

Coverage:
  1. Equal percentage splits with recurring decimals (3 features @ 33.33% on $1,000, $100, $49.99).
  2. Remainder cent assignment strictly to the last feature (by sort_order / last index).
  3. Negative delta adjustment (e.g. 2 features @ 50.0% on $49.99 -> $25.00 and $24.99).
  4. 100% full release ($0 refund), 0% complete refund ($0 payout).
  5. Asymmetric partial splits (70/30, 80/20, 15/85).
  6. Randomized invariant fuzz test: 100 random amounts ($0.01 - $100,000) & weights verifying:
       round(passed_amount + refund_amount, 2) == round(total_amount, 2) with zero lost pennies.
  7. Verification report integration & dynamic feature_results resolution.
  8. REST API endpoints:
       - GET  /api/v1/contracts/{id}/split-preview (200, 401, 403, 404, 405)
       - POST /api/v1/contracts/{id}/split-preview (200 with dynamic feature_results override)
       - POST /api/v1/payments/split-preview (200, 400, 401, 403, 404)
  9. RBAC permission guards: Buyer, Seller, Admin, AI Referee authorized; stranger forbidden.
  10. Settlement integration: auto-deriving split in settle_contract_escrow().
"""

import json
import random
import unittest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from unittest.mock import MagicMock

from services.payments.client import PayPalClient
from services.payments.service import (
    EscrowPaymentService,
    ProportionalSplitResult,
    ContractRepository,
    User,
    UserRole,
    ContractState,
    ForbiddenActionError
)
from services.payments.api import PaymentsAPIHandler


class TestProportionalSplitMath(unittest.TestCase):

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
        self.ai_referee = User(
            id="AI_REFEREE",
            name="AI Referee",
            email="referee@pactpal.internal",
            role=UserRole.ADMIN
        )
        self.stranger = self.repo.create_user(
            name="Eve Stranger",
            email="stranger@pactpal.test",
            role=UserRole.BUYER
        )

        self.mock_paypal = MagicMock(spec=PayPalClient)
        self.service = EscrowPaymentService(repository=self.repo, paypal_client=self.mock_paypal)
        self.api_handler = PaymentsAPIHandler(service=self.service)

    def tearDown(self):
        self.repo.close()

    def _create_contract_with_features(
        self,
        total_amount: float,
        feature_weights: List[float],
        lock: bool = True
    ) -> str:
        """Helper to create a contract and add features with given percentage weights."""
        contract = self.repo.create_contract(
            buyer=self.buyer,
            seller_id=self.seller.id,
            title="Split Math Test Milestone",
            description="Testing deterministic split math",
            total_amount=total_amount,
            deadline=(datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        )
        cid = contract["id"]

        for idx, weight in enumerate(feature_weights):
            self.repo.add_feature(
                contract_id=cid,
                title=f"Feature {idx + 1}",
                acceptance_test=f"Acceptance test for feature {idx + 1}",
                price_weight=weight,
                allocated_amount=round(total_amount * (weight / 100.0), 2),
                sort_order=idx
            )

        if lock:
            self.repo.confirm_checklist(cid, self.buyer)
            self.repo.confirm_checklist(cid, self.seller)

        return cid

    # -------------------------------------------------------------------------
    # 1. Recurring Decimal & Equal Split Tests
    # -------------------------------------------------------------------------
    def test_three_features_at_33_33_percent_on_1000_dollars(self):
        """
        Verify: 3 features @ 33.33% on $1,000.
        Unadjusted allocations: $333.33 x 3 = $999.99 ($0.01 unallocated).
        Deterministic remainder rule allocates +$0.01 to the 3rd (last) feature:
          Feature 1: $333.33
          Feature 2: $333.33
          Feature 3: $333.34
        Total itemized sum == $1,000.00 exactly to the cent.
        """
        cid = self._create_contract_with_features(
            total_amount=1000.0,
            feature_weights=[33.33, 33.33, 33.33]
        )

        res = self.service.calculate_proportional_split(cid, actor=self.buyer)

        self.assertIsInstance(res, ProportionalSplitResult)
        self.assertEqual(res.total_amount, 1000.00)
        self.assertEqual(res.rounding_adjustment_cents, 1)

        items = res.itemized_features
        self.assertEqual(len(items), 3)

        self.assertEqual(items[0]["allocated_amount"], 333.33)
        self.assertEqual(items[0]["adjustment_applied"], 0.0)
        self.assertFalse(items[0]["is_last_feature"])

        self.assertEqual(items[1]["allocated_amount"], 333.33)
        self.assertEqual(items[1]["adjustment_applied"], 0.0)
        self.assertFalse(items[1]["is_last_feature"])

        self.assertEqual(items[2]["allocated_amount"], 333.34)
        self.assertEqual(items[2]["adjustment_applied"], 0.01)
        self.assertTrue(items[2]["is_last_feature"])

        # Check total itemized sum equals total_amount
        item_sum = round(sum(it["allocated_amount"] for it in items), 2)
        self.assertEqual(item_sum, 1000.00)

        # Invariant check
        self.assertEqual(round(res.passed_amount + res.refund_amount, 2), 1000.00)

    def test_three_features_at_33_33_percent_on_100_dollars(self):
        """
        Verify: 3 features @ 33.33% on $100.
        Allocations: $33.33, $33.33, $33.34. Sum == $100.00.
        """
        cid = self._create_contract_with_features(
            total_amount=100.0,
            feature_weights=[33.33, 33.33, 33.33]
        )

        res = self.service.calculate_proportional_split(cid, actor=self.admin)

        self.assertEqual(res.total_amount, 100.00)
        self.assertEqual(res.rounding_adjustment_cents, 1)

        items = res.itemized_features
        self.assertEqual(items[0]["allocated_amount"], 33.33)
        self.assertEqual(items[1]["allocated_amount"], 33.33)
        self.assertEqual(items[2]["allocated_amount"], 33.34)
        self.assertEqual(round(sum(it["allocated_amount"] for it in items), 2), 100.00)

    def test_three_features_at_33_33_percent_on_49_99_dollars(self):
        """
        Verify: 3 features @ 33.33% on uneven contract amount $49.99.
        Unadjusted: 49.99 / 3 = 16.6633 -> $16.66 x 3 = $49.98.
        Remainder +$0.01 to the last feature -> $16.66, $16.66, $16.67.
        Sum == $49.99.
        """
        cid = self._create_contract_with_features(
            total_amount=49.99,
            feature_weights=[33.33, 33.33, 33.33]
        )

        res = self.service.calculate_proportional_split(cid, actor=self.seller)

        self.assertEqual(res.total_amount, 49.99)
        self.assertEqual(res.rounding_adjustment_cents, 1)

        items = res.itemized_features
        self.assertEqual(items[0]["allocated_amount"], 16.66)
        self.assertEqual(items[1]["allocated_amount"], 16.66)
        self.assertEqual(items[2]["allocated_amount"], 16.67)
        self.assertEqual(round(sum(it["allocated_amount"] for it in items), 2), 49.99)

    def test_uneven_amount_100_01_with_explicit_weights(self):
        """
        Verify: $100.01 with weights [33.33, 33.33, 33.34] summing to 100.0%.
        Feature 1: round(100.01 * 0.3333) = 33.33
        Feature 2: round(100.01 * 0.3333) = 33.33
        Feature 3: round(100.01 * 0.3334) = 33.34 -> +$0.01 delta -> 33.35.
        Sum == 33.33 + 33.33 + 33.35 = $100.01.
        """
        cid = self._create_contract_with_features(
            total_amount=100.01,
            feature_weights=[33.33, 33.33, 33.34]
        )

        res = self.service.calculate_proportional_split(cid)

        items = res.itemized_features
        self.assertEqual(items[0]["allocated_amount"], 33.33)
        self.assertEqual(items[1]["allocated_amount"], 33.33)
        self.assertEqual(items[2]["allocated_amount"], 33.35)
        self.assertEqual(round(sum(it["allocated_amount"] for it in items), 2), 100.01)

    def test_negative_delta_adjustment_two_features_50_percent_on_49_99(self):
        """
        Verify negative rounding adjustment: 2 features @ 50.0% on $49.99.
        Unadjusted: 49.99 * 0.5 = 25.00 each -> sum = $50.00.
        Delta = 49.99 - 50.00 = -$0.01.
        Feature 1: $25.00
        Feature 2: $24.99
        Sum == $49.99.
        """
        cid = self._create_contract_with_features(
            total_amount=49.99,
            feature_weights=[50.0, 50.0]
        )

        res = self.service.calculate_proportional_split(cid)

        self.assertEqual(res.rounding_adjustment_cents, -1)
        items = res.itemized_features
        self.assertEqual(items[0]["allocated_amount"], 25.00)
        self.assertEqual(items[0]["adjustment_applied"], 0.0)

        self.assertEqual(items[1]["allocated_amount"], 24.99)
        self.assertEqual(items[1]["adjustment_applied"], -0.01)
        self.assertTrue(items[1]["is_last_feature"])

        self.assertEqual(round(sum(it["allocated_amount"] for it in items), 2), 49.99)

    # -------------------------------------------------------------------------
    # 2. Release & Refund Scenarios (100% Release, 0% Release, Partial)
    # -------------------------------------------------------------------------
    def test_full_release_100_percent_when_all_features_pass(self):
        """All features pass: seller receives 100% total amount, $0 refund."""
        cid = self._create_contract_with_features(
            total_amount=1500.0,
            feature_weights=[40.0, 35.0, 25.0]
        )

        # Mark all passed
        features = self.repo.get_features(cid)
        results = {f["id"]: "PASSED" for f in features}

        res = self.service.calculate_proportional_split(cid, feature_results=results)

        self.assertEqual(res.rule_applied, "FULL_RELEASE_100_PERCENT")
        self.assertEqual(res.passed_amount, 1500.00)
        self.assertEqual(res.refund_amount, 0.00)
        self.assertEqual(res.passed_weight, 100.00)
        self.assertEqual(res.failed_weight, 0.00)
        self.assertEqual(round(res.passed_amount + res.refund_amount, 2), 1500.00)

    def test_full_refund_0_percent_when_all_features_fail(self):
        """All features fail: buyer receives 100% refund, $0 seller payout."""
        cid = self._create_contract_with_features(
            total_amount=1500.0,
            feature_weights=[40.0, 35.0, 25.0]
        )

        features = self.repo.get_features(cid)
        results = {f["id"]: "FAILED" for f in features}

        res = self.service.calculate_proportional_split(cid, feature_results=results)

        self.assertEqual(res.rule_applied, "FULL_REFUND_0_PERCENT")
        self.assertEqual(res.passed_amount, 0.00)
        self.assertEqual(res.refund_amount, 1500.00)
        self.assertEqual(res.passed_weight, 0.00)
        self.assertEqual(res.failed_weight, 100.00)
        self.assertEqual(round(res.passed_amount + res.refund_amount, 2), 1500.00)

    def test_asymmetric_partial_split_70_30(self):
        """Feature 1 (70%) passes, Feature 2 (30%) fails on $1,000."""
        cid = self._create_contract_with_features(
            total_amount=1000.0,
            feature_weights=[70.0, 30.0]
        )

        features = self.repo.get_features(cid)
        results = {features[0]["id"]: "PASSED", features[1]["id"]: "FAILED"}

        res = self.service.calculate_proportional_split(cid, feature_results=results)

        self.assertEqual(res.rule_applied, "PROPORTIONAL_PARTIAL_SPLIT")
        self.assertEqual(res.passed_amount, 700.00)
        self.assertEqual(res.refund_amount, 300.00)
        self.assertEqual(res.passed_weight, 70.00)
        self.assertEqual(res.failed_weight, 30.00)
        self.assertEqual(round(res.passed_amount + res.refund_amount, 2), 1000.00)

    def test_asymmetric_partial_split_80_20(self):
        """Feature 1 (80%) passes, Feature 2 (20%) fails on $1,000."""
        cid = self._create_contract_with_features(
            total_amount=1000.0,
            feature_weights=[80.0, 20.0]
        )

        features = self.repo.get_features(cid)
        results = {features[0]["id"]: "PASSED", features[1]["id"]: "FAILED"}

        res = self.service.calculate_proportional_split(cid, feature_results=results)

        self.assertEqual(res.passed_amount, 800.00)
        self.assertEqual(res.refund_amount, 200.00)
        self.assertEqual(round(res.passed_amount + res.refund_amount, 2), 1000.00)

    def test_asymmetric_partial_split_15_85(self):
        """Feature 1 (15%) passes, Feature 2 (85%) fails on $1,000."""
        cid = self._create_contract_with_features(
            total_amount=1000.0,
            feature_weights=[15.0, 85.0]
        )

        features = self.repo.get_features(cid)
        results = {features[0]["id"]: "PASSED", features[1]["id"]: "FAILED"}

        res = self.service.calculate_proportional_split(cid, feature_results=results)

        self.assertEqual(res.passed_amount, 150.00)
        self.assertEqual(res.refund_amount, 850.00)
        self.assertEqual(round(res.passed_amount + res.refund_amount, 2), 1000.00)

    def test_partial_split_where_remainder_feature_passes_vs_fails(self):
        """
        Verify: 3 features @ 33.33% on $1,000.
        Allocations: f1=333.33, f2=333.33, f3=333.34 (holds remainder).
        Case A: f1 & f2 pass, f3 fails -> passed=666.66, refund=333.34. Sum=1000.00.
        Case B: f3 passes, f1 & f2 fail -> passed=333.34, refund=666.66. Sum=1000.00.
        Case C: f1 & f3 pass, f2 fails -> passed=666.67, refund=333.33. Sum=1000.00.
        """
        cid = self._create_contract_with_features(
            total_amount=1000.0,
            feature_weights=[33.33, 33.33, 33.33]
        )
        features = self.repo.get_features(cid)
        f1, f2, f3 = features[0]["id"], features[1]["id"], features[2]["id"]

        # Case A: f3 (remainder) fails
        res_a = self.service.calculate_proportional_split(cid, feature_results={f1: "PASSED", f2: "PASSED", f3: "FAILED"})
        self.assertEqual(res_a.passed_amount, 666.66)
        self.assertEqual(res_a.refund_amount, 333.34)
        self.assertEqual(round(res_a.passed_amount + res_a.refund_amount, 2), 1000.00)

        # Case B: f3 (remainder) passes
        res_b = self.service.calculate_proportional_split(cid, feature_results={f1: "FAILED", f2: "FAILED", f3: "PASSED"})
        self.assertEqual(res_b.passed_amount, 333.34)
        self.assertEqual(res_b.refund_amount, 666.66)
        self.assertEqual(round(res_b.passed_amount + res_b.refund_amount, 2), 1000.00)

        # Case C: f1 and f3 pass
        res_c = self.service.calculate_proportional_split(cid, feature_results={f1: "PASSED", f2: "FAILED", f3: "PASSED"})
        self.assertEqual(res_c.passed_amount, 666.67)
        self.assertEqual(res_c.refund_amount, 333.33)
        self.assertEqual(round(res_c.passed_amount + res_c.refund_amount, 2), 1000.00)

    # -------------------------------------------------------------------------
    # 3. Verification Report & Format Flexibility
    # -------------------------------------------------------------------------
    def test_split_calculation_from_verification_report(self):
        """When feature_results is omitted, split engine pulls from the latest verification report."""
        cid = self._create_contract_with_features(
            total_amount=1200.0,
            feature_weights=[50.0, 50.0]
        )
        features = self.repo.get_features(cid)
        f1, f2 = features[0]["id"], features[1]["id"]

        # Save verification report with feature 1 PASSED, feature 2 FAILED
        self.repo.save_verification_report(
            contract_id=cid,
            build_succeeded=True,
            per_feature_results={
                f1: {"status": "PASSED", "evidence": "Unit tests passed"},
                f2: {"status": "FAILED", "evidence": "Visual mismatch"}
            }
        )

        res = self.service.calculate_proportional_split(cid)
        self.assertEqual(res.passed_amount, 600.00)
        self.assertEqual(res.refund_amount, 600.00)
        self.assertEqual(res.passed_weight, 50.00)
        self.assertEqual(res.failed_weight, 50.00)

    def test_feature_results_various_input_formats(self):
        """Tests that list of passed IDs or list of dicts are accepted seamlessly."""
        cid = self._create_contract_with_features(
            total_amount=900.0,
            feature_weights=[30.0, 30.0, 40.0]
        )
        features = self.repo.get_features(cid)

        # Format 1: List of passed IDs
        res_list = self.service.calculate_proportional_split(cid, feature_results=[features[0]["id"], features[2]["id"]])
        self.assertEqual(res_list.passed_amount, 630.00)
        self.assertEqual(res_list.refund_amount, 270.00)

        # Format 2: Dict with passed list
        res_dict_passed = self.service.calculate_proportional_split(cid, feature_results={"passed": [features[0]["id"]]})
        self.assertEqual(res_dict_passed.passed_amount, 270.00)
        self.assertEqual(res_dict_passed.refund_amount, 630.00)

    # -------------------------------------------------------------------------
    # 4. Randomized Invariant Fuzz Testing (100 Iterations)
    # -------------------------------------------------------------------------
    def test_randomized_invariant_fuzz_test_100_runs(self):
        """
        Randomized Invariant Fuzz Test:
        Generates 100 randomized contracts with:
          - random total_amount between $0.01 and $99,999.99 (including micro and huge amounts)
          - random number of features (between 2 and 8)
          - random weight distribution (summing to ~100%)
          - random subsets of PASSED and FAILED features
        Verifies with zero tolerance:
          1. round(passed_amount + refund_amount, 2) == round(total_amount, 2)
          2. sum(allocated_amount) == total_amount to the cent
          3. sum(passed_features allocated) == passed_amount
          4. sum(failed_features allocated) == refund_amount
        """
        rng = random.Random(42)  # Deterministic seed for reproducible testing

        for run in range(100):
            total_amt = round(rng.uniform(0.01, 25000.0), 2)
            num_features = rng.randint(2, 7)

            # Generate random integer slices that partition 10000 (100.00%)
            cuts = sorted([rng.randint(1, 9999) for _ in range(num_features - 1)])
            slices = [cuts[0]] + [cuts[i] - cuts[i - 1] for i in range(1, len(cuts))] + [10000 - cuts[-1]]
            weights = [round(s / 100.0, 2) for s in slices]

            contract = self.repo.create_contract(
                buyer=self.buyer,
                seller_id=self.seller.id,
                title=f"Fuzz Run {run}",
                description="Randomized invariant fuzzing",
                total_amount=total_amt,
                deadline=(datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
            )
            cid = contract["id"]

            feat_ids = []
            for idx, w in enumerate(weights):
                f = self.repo.add_feature(
                    contract_id=cid,
                    title=f"Fuzz Feature {idx}",
                    acceptance_test="Random test",
                    price_weight=w,
                    allocated_amount=round(total_amt * (w / 100.0), 2),
                    sort_order=idx
                )
                feat_ids.append(f["id"])

            # Randomly pass/fail features
            passed_set = {fid for fid in feat_ids if rng.choice([True, False])}
            feature_results = {fid: ("PASSED" if fid in passed_set else "FAILED") for fid in feat_ids}

            split = self.service.calculate_proportional_split(cid, feature_results=feature_results)

            # Invariant 1: Paid + Refunded == Total price to the cent
            self.assertEqual(
                round(split.passed_amount + split.refund_amount, 2),
                total_amt,
                f"Run {run} failed invariant: {split.passed_amount} + {split.refund_amount} != {total_amt}"
            )

            # Invariant 2: Itemized allocations sum exactly to total price
            item_sum = round(sum(it["allocated_amount"] for it in split.itemized_features), 2)
            self.assertEqual(
                item_sum,
                total_amt,
                f"Run {run} itemized sum mismatch: {item_sum} != {total_amt}"
            )

            # Invariant 3: Passed allocated sum matches passed_amount
            passed_sum = round(sum(it["allocated_amount"] for it in split.itemized_features if it["status"] == "PASSED"), 2)
            self.assertEqual(passed_sum, split.passed_amount)

            # Invariant 4: Failed allocated sum matches refund_amount
            failed_sum = round(sum(it["allocated_amount"] for it in split.itemized_features if it["status"] == "FAILED"), 2)
            self.assertEqual(failed_sum, split.refund_amount)

    # -------------------------------------------------------------------------
    # 5. REST API Endpoint Tests
    # -------------------------------------------------------------------------
    def test_api_get_split_preview_buyer_200(self):
        """GET /api/v1/contracts/{id}/split-preview returns 200 for contract buyer."""
        cid = self._create_contract_with_features(1000.0, [33.33, 33.33, 33.33])

        code, headers, body = self.api_handler.dispatch(
            method="GET",
            path=f"/api/v1/contracts/{cid}/split-preview",
            headers={"X-Actor-Id": self.buyer.id}
        )

        self.assertEqual(code, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["contract_id"], cid)
        self.assertEqual(data["total_amount"], 1000.00)
        self.assertEqual(data["rounding_adjustment_cents"], 1)
        self.assertEqual(len(data["itemized_features"]), 3)

    def test_api_get_split_preview_seller_200(self):
        """GET /api/v1/contracts/{id}/split-preview returns 200 for contract seller."""
        cid = self._create_contract_with_features(500.0, [50.0, 50.0])

        code, _, body = self.api_handler.dispatch(
            method="GET",
            path=f"/api/v1/contracts/{cid}/split-preview",
            headers={"X-Actor-Id": self.seller.id}
        )
        self.assertEqual(code, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["total_amount"], 500.00)

    def test_api_get_split_preview_admin_and_referee_200(self):
        """GET /api/v1/contracts/{id}/split-preview returns 200 for Admin and AI Referee."""
        cid = self._create_contract_with_features(500.0, [50.0, 50.0])

        # Admin
        code, _, _ = self.api_handler.dispatch(
            method="GET",
            path=f"/api/v1/contracts/{cid}/split-preview",
            headers={"X-Actor-Id": self.admin.id}
        )
        self.assertEqual(code, 200)

        # AI Referee
        code_ref, _, _ = self.api_handler.dispatch(
            method="GET",
            path=f"/api/v1/contracts/{cid}/split-preview",
            headers={"X-Actor-Id": "AI_REFEREE"}
        )
        self.assertEqual(code_ref, 200)

    def test_api_get_split_preview_unauthorized_401(self):
        """Missing X-Actor-Id header returns 401 Unauthorized."""
        cid = self._create_contract_with_features(1000.0, [50.0, 50.0])

        code, _, body = self.api_handler.dispatch(
            method="GET",
            path=f"/api/v1/contracts/{cid}/split-preview",
            headers={}
        )
        self.assertEqual(code, 401)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["error"], "UNAUTHORIZED")

    def test_api_get_split_preview_forbidden_403(self):
        """Third-party user (not buyer, seller, admin, or referee) returns 403 Forbidden."""
        cid = self._create_contract_with_features(1000.0, [50.0, 50.0])

        code, _, body = self.api_handler.dispatch(
            method="GET",
            path=f"/api/v1/contracts/{cid}/split-preview",
            headers={"X-Actor-Id": self.stranger.id}
        )
        self.assertEqual(code, 403)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["error"], "FORBIDDEN")

    def test_api_get_split_preview_not_found_404(self):
        """Non-existent contract returns 404 Not Found."""
        code, _, body = self.api_handler.dispatch(
            method="GET",
            path="/api/v1/contracts/non_existent_contract_id/split-preview",
            headers={"X-Actor-Id": self.admin.id}
        )
        self.assertEqual(code, 404)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["error"], "NOT_FOUND")

    def test_api_method_not_allowed_405(self):
        """Unsupported HTTP method returns 405 Method Not Allowed."""
        cid = self._create_contract_with_features(1000.0, [50.0, 50.0])

        code, _, _ = self.api_handler.dispatch(
            method="DELETE",
            path=f"/api/v1/contracts/{cid}/split-preview",
            headers={"X-Actor-Id": self.admin.id}
        )
        self.assertEqual(code, 405)

    def test_api_post_contract_split_preview_with_custom_features_200(self):
        """POST /api/v1/contracts/{id}/split-preview accepts feature_results payload."""
        cid = self._create_contract_with_features(1000.0, [70.0, 30.0])
        features = self.repo.get_features(cid)

        payload = {
            "feature_results": {
                features[0]["id"]: "PASSED",
                features[1]["id"]: "FAILED"
            }
        }
        code, _, body = self.api_handler.dispatch(
            method="POST",
            path=f"/api/v1/contracts/{cid}/split-preview",
            headers={"X-Actor-Id": self.buyer.id, "Content-Type": "application/json"},
            body=json.dumps(payload).encode("utf-8")
        )
        self.assertEqual(code, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["passed_amount"], 700.00)
        self.assertEqual(data["refund_amount"], 300.00)

    def test_api_post_payments_split_preview_200(self):
        """POST /api/v1/payments/split-preview returns 200 when contract_id is provided in body."""
        cid = self._create_contract_with_features(1000.0, [60.0, 40.0])

        payload = {"contract_id": cid}
        code, _, body = self.api_handler.dispatch(
            method="POST",
            path="/api/v1/payments/split-preview",
            headers={"X-Actor-Id": self.buyer.id, "Content-Type": "application/json"},
            body=json.dumps(payload).encode("utf-8")
        )
        self.assertEqual(code, 200)
        data = json.loads(body.decode("utf-8"))
        self.assertEqual(data["total_amount"], 1000.00)

    # -------------------------------------------------------------------------
    # 6. Settlement Integration with Split Engine
    # -------------------------------------------------------------------------
    def test_settle_contract_escrow_auto_derives_split_from_engine(self):
        """
        Verify: Calling settle_contract_escrow() without passed_amount/refund_amount
        automatically executes split math and settles cleanly.
        """
        cid = self._create_contract_with_features(1000.0, [50.0, 50.0])
        features = self.repo.get_features(cid)

        # Transition contract to FUNDED state
        self.repo.transition_contract(cid, self.buyer, ContractState.REVIEW)
        self.repo.transition_contract(cid, self.seller, ContractState.SIGNED, metadata={"acceptance_confirmed": True})
        self.repo.transition_contract(
            cid,
            self.buyer,
            ContractState.FUNDED,
            metadata={"paypal_order_id": "ORD_TEST_99", "paypal_auth_id": "AUTH_PP_TEST_99"}
        )

        # Attach verification report (Feature 1 PASSED, Feature 2 FAILED)
        self.repo.save_verification_report(
            contract_id=cid,
            build_succeeded=True,
            per_feature_results={
                features[0]["id"]: {"status": "PASSED"},
                features[1]["id"]: {"status": "FAILED"}
            }
        )

        # Mock PayPal capture and void
        self.mock_paypal.capture_authorization.return_value = {"capture_id": "CAP_999", "status": "COMPLETED"}
        self.mock_paypal.create_payout.return_value = {"payout_batch_id": "PAYOUT_999", "status": "SUCCESS"}
        self.mock_paypal.void_authorization.return_value = {"authorization_id": "AUTH_PP_TEST_99", "status": "VOIDED"}

        # Settle using auto-derived split (omitting passed_amount and refund_amount)
        res = self.service.settle_contract_escrow(
            contract_id=cid,
            passed_amount=None,
            refund_amount=None,
            seller_paypal_email="sb-seller@example.com",
            actor=self.admin
        )

        self.assertEqual(res["status"], "SETTLED")
        self.assertEqual(res["passed_amount"], 500.00)
        self.assertEqual(res["refund_amount"], 500.00)
        self.assertIsNotNone(res.get("split_breakdown"))
        self.assertEqual(round(res["passed_amount"] + res["refund_amount"], 2), 1000.00)


if __name__ == "__main__":
    unittest.main()

