# standard libs
from unittest import TestCase
from unittest.mock import sentinel

# contracts api
from contracts_api import CustomInstruction

# inception sdk
from inception_sdk.test_framework.contracts.unit.contracts_api_sentinels import SentinelPosting


class SentinelTest(TestCase):
    def test_sentinel_attributes_all_set(self):
        sentinel_posting = SentinelPosting("id_1")
        self.assertDictEqual(
            sentinel_posting.__dict__,
            {
                "credit": sentinel.credit_id_1,
                "account_id": sentinel.account_id_id_1,
                "account_address": sentinel.account_address_id_1,
                "denomination": sentinel.denomination_id_1,
                "amount": sentinel.amount_id_1,
                "asset": sentinel.asset_id_1,
                "phase": sentinel.phase_id_1,
                "sub_account_id": sentinel.sub_account_id_id_1,
                # Multiple Processing Groups is currently not supported, see IDEA-777
                "internal_account_processing_label": None,
            },
        )

    def test_sentinel_with_same_ids_are_equal(self):
        self.assertEqual(SentinelPosting("id_1"), SentinelPosting("id_1"))

    def test_sentinels_with_different_ids_are_not_equal(self):
        self.assertNotEqual(SentinelPosting("id_1"), SentinelPosting("id_2"))

    def test_sentinel_matches_parent_type(self):
        # This would raise an exception if we passed in a regular sentinel as postings
        # are checked against Posting type
        ci = CustomInstruction(
            postings=[SentinelPosting("id_1")],
        )
        self.assertEqual(ci.postings[0], SentinelPosting("id_1"))
