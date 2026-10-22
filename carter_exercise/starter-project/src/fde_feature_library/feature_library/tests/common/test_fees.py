# standard libs
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel

import pytest

# third party
from parameterized import parameterized

# features
from feature_library.common import fees

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    CustomInstruction,
    Phase,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest
from inception_sdk.test_framework.contracts.unit.contracts_api_sentinels import SentinelPosting

from tests.common.test_denomination import DEFAULT_DENOMINATION


class FeesTest(FeatureTest):
    @parameterized.expand(
        input=[
            ("Positive amount", Decimal("10.00"), False, 2),
            ("Zero amount", Decimal("0.00"), False, 0),
            ("Negative amount", Decimal("-10.00"), False, 0),
            ("Positive amount reversal", Decimal("10.00"), True, 2),
        ]
    )
    @pytest.mark.unit
    def test_fee_postings(self, name, amount, reversal, expected_len):
        customer_account_id = "CUSTOMER_ACC"
        internal_account_id = "INTERNAL_ACC"
        denomination = DEFAULT_DENOMINATION
        customer_address = "FEES"

        result = fees.fee_postings(
            customer_account_id=customer_account_id,
            customer_account_address=customer_address,
            denomination=denomination,
            amount=amount,
            internal_account=internal_account_id,
            reversal=reversal,
        )

        self.assertEqual(len(result), expected_len)

        if expected_len == 2:
            # First posting
            self.assertEqual(result[0].amount, amount)
            self.assertEqual(result[0].denomination, denomination)
            self.assertEqual(result[0].asset, DEFAULT_ASSET)
            self.assertEqual(result[0].phase, Phase.COMMITTED)

            # Second posting
            self.assertEqual(result[1].amount, amount)
            self.assertEqual(result[1].denomination, denomination)
            self.assertEqual(result[1].asset, DEFAULT_ASSET)
            self.assertEqual(result[1].phase, Phase.COMMITTED)

            if not reversal:
                # Normal fee: Debit Customer, Credit Internal
                self.assertFalse(result[0].credit)
                self.assertEqual(result[0].account_id, customer_account_id)
                self.assertEqual(result[0].account_address, customer_address)

                self.assertTrue(result[1].credit)
                self.assertEqual(result[1].account_id, internal_account_id)
                self.assertEqual(result[1].account_address, DEFAULT_ADDRESS)
            else:
                # Reversal: Credit Customer, Debit Internal
                self.assertTrue(result[0].credit)
                self.assertEqual(result[0].account_id, customer_account_id)
                self.assertEqual(result[0].account_address, customer_address)

                self.assertFalse(result[1].credit)
                self.assertEqual(result[1].account_id, internal_account_id)
                self.assertEqual(result[1].account_address, DEFAULT_ADDRESS)

    @patch.object(fees, "fee_postings")
    @pytest.mark.unit
    def test_fee_custom_instruction(self, mock_fee_postings: MagicMock):
        customer_account_id = sentinel.customer_account_id
        internal_account_id = sentinel.internal_account_id
        denomination = sentinel.denomination
        amount = Decimal("15.50")
        instruction_details = {"description": "Monthly fee"}
        fee_postings = [SentinelPosting("fee_1"), SentinelPosting("fee_2")]
        mock_fee_postings.return_value = fee_postings

        result = fees.fee_custom_instruction(
            customer_account_id=customer_account_id,
            denomination=denomination,
            amount=amount,
            internal_account=internal_account_id,
            instruction_details=instruction_details,
        )

        self.assertListEqual(
            result,
            [
                CustomInstruction(
                    postings=fee_postings,  # type: ignore
                    instruction_details=instruction_details,
                    override_all_restrictions=True,
                )
            ],
        )
        mock_fee_postings.assert_called_once_with(
            customer_account_id=customer_account_id,
            customer_account_address=DEFAULT_ADDRESS,
            denomination=denomination,
            amount=amount,
            internal_account=internal_account_id,
            reversal=False,
        )

    @patch.object(fees, "fee_postings")
    @pytest.mark.unit
    def test_fee_custom_instruction_custom_address(self, mock_fee_postings: MagicMock):
        fee_postings = [SentinelPosting("fee_1")]
        mock_fee_postings.return_value = fee_postings
        result = fees.fee_custom_instruction(
            customer_account_id=sentinel.customer_account_id,
            denomination=sentinel.denomination,
            amount=Decimal("1"),
            internal_account=sentinel.internal_account,
            customer_account_address=sentinel.customer_address,
            instruction_details={"test": "details"},
        )
        self.assertEqual(len(result), 1)
        mock_fee_postings.assert_called_once_with(
            customer_account_id=sentinel.customer_account_id,
            customer_account_address=sentinel.customer_address,
            denomination=sentinel.denomination,
            amount=Decimal("1"),
            internal_account=sentinel.internal_account,
            reversal=False,
        )

    @patch.object(fees, "fee_postings")
    @pytest.mark.unit
    def test_fee_custom_instruction_reversal(self, mock_fee_postings: MagicMock):
        fee_postings = [SentinelPosting("fee_1")]
        mock_fee_postings.return_value = fee_postings
        result = fees.fee_custom_instruction(
            customer_account_id=sentinel.customer_account_id,
            denomination=sentinel.denomination,
            amount=Decimal("1"),
            internal_account=sentinel.internal_account,
            reversal=True,
        )
        self.assertEqual(len(result), 1)
        mock_fee_postings.assert_called_once_with(
            customer_account_id=sentinel.customer_account_id,
            customer_account_address=DEFAULT_ADDRESS,
            denomination=sentinel.denomination,
            amount=Decimal("1"),
            internal_account=sentinel.internal_account,
            reversal=True,
        )

    @patch.object(fees, "fee_postings")
    @pytest.mark.unit
    def test_fee_custom_instruction_no_postings(self, mock_fee_postings: MagicMock):
        mock_fee_postings.return_value = []
        result = fees.fee_custom_instruction(
            customer_account_id=sentinel.customer_account_id,
            denomination=sentinel.denomination,
            amount=Decimal("1"),
            internal_account=sentinel.internal_account,
        )
        self.assertListEqual(result, [])

    @pytest.mark.unit
    def test_fee_custom_instruction_zero_amount(self):
        result = fees.fee_custom_instruction(
            customer_account_id="ACC",
            denomination=DEFAULT_DENOMINATION,
            amount=Decimal("0"),
            internal_account="INTERNAL",
        )
        self.assertEqual(len(result), 0)

    @pytest.mark.unit
    def test_fee_custom_instruction_negative_amount(self):
        result = fees.fee_custom_instruction(
            customer_account_id="ACC",
            denomination=DEFAULT_DENOMINATION,
            amount=Decimal("-1"),
            internal_account="INTERNAL",
        )
        self.assertListEqual(result, [])
