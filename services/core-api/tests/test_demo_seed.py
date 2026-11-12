#!/usr/bin/env python3
"""
Test demo seed data initialization and repository query capabilities.
"""

import unittest
from ..db.repository import ContractRepository

class TestDemoSeed(unittest.TestCase):
    def setUp(self):
        self.repo = ContractRepository(db_path=":memory:", seed_demo=True)

    def tearDown(self):
        self.repo.close()

    def test_seed_demo_users_and_contracts(self):
        # 1. Users
        buyer = self.repo.get_user("usr_buyer_01")
        self.assertIsNotNone(buyer)
        self.assertEqual(buyer.name, "Alice Buyer")

        seller = self.repo.get_user("usr_seller_01")
        self.assertIsNotNone(seller)
        self.assertEqual(seller.name, "Bob Developer")

        # 2. Main demo contract
        main_contract = self.repo.get_contract("pct_099e77")
        self.assertIsNotNone(main_contract)
        self.assertEqual(main_contract["status"], "FUNDED")
        self.assertEqual(main_contract["total_amount"], 1500.0)
        self.assertEqual(len(main_contract["features"]), 3)
        self.assertEqual(main_contract["features"][0]["id"], "feat_pct_099e77_1")

        # 3. Additional contracts
        draft = self.repo.get_contract("pct_draft_01")
        self.assertIsNotNone(draft)
        self.assertEqual(draft["status"], "DRAFT")

        review = self.repo.get_contract("pct_review_02")
        self.assertIsNotNone(review)
        self.assertEqual(review["status"], "REVIEW")

        settled = self.repo.get_contract("pct_settled_04")
        self.assertIsNotNone(settled)
        self.assertEqual(settled["status"], "SETTLED")

        # 4. Total count of seeded contracts
        all_contracts = self.repo.get_contracts_by_status(None)
        self.assertEqual(len(all_contracts), 4)

    def test_seed_demo_idempotence(self):
        # Calling seed_demo_data again should not raise errors or duplicate primary keys
        self.repo.seed_demo_data()
        all_contracts = self.repo.get_contracts_by_status(None)
        self.assertEqual(len(all_contracts), 4)

if __name__ == "__main__":
    unittest.main()

