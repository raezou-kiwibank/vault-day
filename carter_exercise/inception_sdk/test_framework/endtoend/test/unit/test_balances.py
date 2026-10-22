# standard libs
from datetime import datetime
from decimal import Decimal
from unittest import TestCase
from unittest.mock import Mock, patch

# inception sdk
import inception_sdk.test_framework.endtoend.balances as balances
from inception_sdk.test_framework import endtoend
from inception_sdk.test_framework.common.balance_helpers import (
    Balance,
    BalanceDimensions,
    NetBalance,
    NetBalanceMismatches,
    NetBalances,
)
from inception_sdk.vault.core_api import PostingPhase

BALANCES = [
    {
        "id": "1",
        "account_id": "1",
        "account_address": "DEFAULT",
        "phase": "POSTING_PHASE_COMMITTED",
        "asset": "COMMERCIAL_BANK_MONEY",
        "denomination": "GBP",
        "value_time": "2021-01-01T00:00:00Z",
        "amount": "60",
        "total_debit": "0",
        "total_credit": "60",
    },
    {
        "id": "2",
        "account_id": "1",
        "account_address": "OTHER",
        "phase": "POSTING_PHASE_COMMITTED",
        "asset": "COMMERCIAL_BANK_MONEY",
        "denomination": "GBP",
        "value_time": "",
        "amount": "20",
        "total_debit": "0",
        "total_credit": "20",
    },
]


class BalancesTest(TestCase):
    def setUp(self) -> None:
        self.sample_balances = BALANCES
        self.maxDiff = None
        return super().setUp()

    def test_standardise_balance_value_time_format(self):
        test_cases = [
            {
                "description": "timestamp without milliseconds",
                "timestamp": "2021-10-11T00:00:00Z",
                "expected_result": datetime(2021, 10, 11, 0, 0, 0),
            },
            {
                "description": "timestamp with milliseconds",
                "timestamp": "2021-10-11T00:00:00.12345Z",
                "expected_result": datetime(2021, 10, 11, 0, 0, 0),
            },
            {
                "description": "No timestamp",
                "timestamp": None,
                "expected_result": datetime(1970, 1, 1, 0, 0, 0),
            },
        ]

        for test_case in test_cases:
            result = balances.standardise_balance_value_time_format(test_case["timestamp"])

            self.assertEqual(result, test_case["expected_result"], test_case["description"])

    def test_create_balance_dict(self):
        expected_balance_dict = {}
        expected_balance_dict[
            BalanceDimensions("DEFAULT", "COMMERCIAL_BANK_MONEY", "GBP", "POSTING_PHASE_COMMITTED")
        ] = Balance(
            net="60",
            credit="60",
            debit="0",
            value_timestamp=datetime(2021, 1, 1, 0, 0, 0),
        )
        expected_balance_dict[
            BalanceDimensions("OTHER", "COMMERCIAL_BANK_MONEY", "GBP", "POSTING_PHASE_COMMITTED")
        ] = Balance(
            net="20",
            credit="20",
            debit="0",
            value_timestamp=datetime(1970, 1, 1, 0, 0, 0),
        )

        result = balances.create_balance_dict(self.sample_balances)
        self.assertDictEqual(expected_balance_dict, result)

        # loop needed because value_time is not considered in the balance __eq__ method
        for dimension, balance_object in expected_balance_dict.items():
            self.assertEqual(balance_object.value_timestamp, result[dimension].value_timestamp)

    @patch.object(endtoend.helper, "send_request")
    def test_get_balances_dict_non_live_duplicate_address_coordinates_returns_only_first_balance(
        self,
        mock_send_request: Mock,
    ):
        balance_1: dict[str, str] = {
            "id": "balance-1",
            "account_id": "account-id-1",
            "account_address": "address-1",
            "phase": "POSTING_PHASE_COMMITTED",
            "asset": "COMMERCIAL_BANK_MONEY",
            "denomination": "GBP",
            "value_time": "",
            "amount": "10",
            "total_debit": "0",
            "total_credit": "10",
        }
        balance_2: dict[str, str] = {
            # Duplicate key as balance-1, so expect this to be discarded.
            "id": "balance-2",
            "account_id": "account-id-1",
            "account_address": "address-1",
            "phase": "POSTING_PHASE_COMMITTED",
            "asset": "COMMERCIAL_BANK_MONEY",
            "denomination": "GBP",
            "value_time": "",
            "amount": "20",
            "total_debit": "0",
            "total_credit": "20",
        }
        balance_3: dict[str, str] = {
            # Separate balance, expect this.
            "id": "balance-3",
            "account_id": "account-id-1",
            "account_address": "address-2",
            "phase": "POSTING_PHASE_COMMITTED",
            "asset": "COMMERCIAL_BANK_MONEY",
            "denomination": "GBP",
            "value_time": "",
            "amount": "30",
            "total_debit": "0",
            "total_credit": "30",
        }
        mock_balances: list[dict[str, str]] = [balance_1, balance_2, balance_3]
        account_id = "account-id-1"
        mock_send_request.return_value = {
            "balances": mock_balances,
            "next_page_token": "",
        }

        # Expect only balance 1 & 3; discard balance 2.
        expected_balances: dict[BalanceDimensions, Balance] = {
            BalanceDimensions(
                balance_1["account_address"],
                balance_1["asset"],
                balance_1["denomination"],
                balance_1["phase"],
            ): Balance(
                balance_1["total_credit"],
                balance_1["total_debit"],
                balance_1["amount"],
                balances.standardise_balance_value_time_format(
                    balances.get_balance_timestamp(balance_1)
                ),
            ),
            BalanceDimensions(
                balance_3["account_address"],
                balance_3["asset"],
                balance_3["denomination"],
                balance_3["phase"],
            ): Balance(
                balance_3["total_credit"],
                balance_3["total_debit"],
                balance_3["amount"],
                balances.standardise_balance_value_time_format(
                    balances.get_balance_timestamp(balance_3)
                ),
            ),
        }

        actual_balances = balances.get_balances_dict(
            account_id=account_id,
            live=False,
        )

        self.assertDictEqual(expected_balances, actual_balances)

        mock_send_request.assert_called_once_with(
            "get",
            "/v1/balances/timerange",
            params={
                "account_ids": account_id,
                "page_size": "50",
                "page_token": "",
            },
        )

    def test_match_net_balances_no_mismatches(self):
        expected_balance = NetBalance(
            account_id="account_1",
            sub_account_id="",
            account_address="DEFAULT",
            phase=PostingPhase.COMMITTED,
            asset="COMMERCIAL_BANK_MONEY",
            denomination="GBP",
            amount=Decimal("100"),
        )
        expected = NetBalances(
            value_net_balances=[expected_balance],
            booking_net_balances=[expected_balance],
        )
        actual = NetBalances(
            value_net_balances=[expected_balance],
            booking_net_balances=[expected_balance],
        )
        result = balances.get_net_balance_mismatches(expected, actual)
        self.assertEqual(result, {})

    def test_match_net_balances_with_mismatches(self):
        expected_balance_val = NetBalance(
            account_id="account_1",
            sub_account_id="",
            account_address="DEFAULT",
            phase=PostingPhase.COMMITTED,
            asset="COMMERCIAL_BANK_MONEY",
            denomination="GBP",
            amount=Decimal("100"),
        )
        expected_balance_book = NetBalance(
            account_id="account_1",
            sub_account_id="",
            account_address="DEFAULT",
            phase=PostingPhase.COMMITTED,
            asset="COMMERCIAL_BANK_MONEY",
            denomination="GBP",
            amount=Decimal("200"),
        )
        expected = NetBalances(
            value_net_balances=[expected_balance_val],
            booking_net_balances=[expected_balance_book],
        )

        actual_balance_val = NetBalance(
            account_id="account_1",
            sub_account_id="",
            account_address="DEFAULT",
            phase=PostingPhase.COMMITTED,
            asset="COMMERCIAL_BANK_MONEY",
            denomination="GBP",
            amount=Decimal("50"),
        )
        actual = NetBalances(
            value_net_balances=[actual_balance_val],
            booking_net_balances=[expected_balance_book],
        )

        result = balances.get_net_balance_mismatches(expected, actual)

        self.assertIn("account_1", result)
        mismatch = result["account_1"]
        self.assertIsInstance(mismatch, NetBalanceMismatches)

        # There was a value mismatch:
        self.assertEqual(mismatch.expected_value_balances, [expected_balance_val])
        self.assertEqual(mismatch.actual_value_balances, [actual_balance_val])

        # There was NO booking mismatch:
        self.assertEqual(mismatch.expected_booking_balances, [])
        self.assertEqual(mismatch.actual_booking_balances, [])
