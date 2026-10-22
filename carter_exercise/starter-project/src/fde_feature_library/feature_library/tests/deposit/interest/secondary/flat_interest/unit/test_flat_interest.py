# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

# features
import feature_library.common.tuples as common_tuples
import feature_library.deposit.interest.secondary.flat_interest as flat_interest

# contracts api
from contracts_api import Balance

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

# feature_library
from tests.utils import initialise_mock_state

DEFAULT_DATETIME = datetime(2025, 1, 1, tzinfo=ZoneInfo("UTC"))


class TestGetInterestRate(FeatureTest):
    def setUp(self) -> None:
        self.mock_vault = self.create_mock()
        self.mock_state = initialise_mock_state(
            vault=self.mock_vault,
            effective_datetime=DEFAULT_DATETIME,
        )
        return super().setUp()

    @patch.object(flat_interest, "_append_to_state")
    @pytest.mark.unit
    def test_get_interest_rate_success(self, mock_append_to_state: MagicMock):
        fixed_rate = Decimal("0.01")
        self.mock_state.parameters[flat_interest.FIXED_INTEREST_RATE_PARAM_ID] = fixed_rate
        mock_append_to_state.return_value = self.mock_state

        result = flat_interest.get_interest_rate(state=self.mock_state)

        self.assertEqual(result.interest_rate_param_value, fixed_rate)
        self.assertEqual(result.interest_type, common_tuples.INTEREST_TYPE_FLAT)

    @patch.object(flat_interest.state_utils, "check_parameters_exist")
    @patch.object(flat_interest, "_append_to_state")
    @pytest.mark.unit
    def test_get_interest_rate_missing_param(
        self, mock_append_to_state: MagicMock, mock_check_parameters_exist: MagicMock
    ):
        mock_append_to_state.return_value = self.mock_state
        mock_check_parameters_exist.return_value = "Missing Param Rejection"

        with self.assertRaises(AssertionError) as ex:
            flat_interest.get_interest_rate(state=self.mock_state)

        self.assertEqual(ex.exception.args[0], "Missing Param Rejection")
        mock_check_parameters_exist.assert_called_once_with(
            state=self.mock_state, param_ids={flat_interest.FIXED_INTEREST_RATE_PARAM_ID}
        )


class TestFixedInterestAccrualAmount(FeatureTest):
    @patch.object(flat_interest.parameter_utils, "yearly_to_daily_rate")
    @pytest.mark.unit
    def test_get_fixed_interest_accrual_amount(self, mock_yearly_to_daily_rate: MagicMock):
        # Mocking daily rate: 0.01 / 365
        mock_yearly_to_daily_rate.return_value = Decimal("0.000027397")

        accrual_result = flat_interest.get_fixed_interest_accrual_amount(
            effective_balance=Balance(
                credit=Decimal("1000"), debit=Decimal("0"), net=Decimal("1000")
            ),
            effective_datetime=DEFAULT_DATETIME,
            interest_rates=Decimal("0.01"),
            days_in_year="365",
            precision=5,
        )

        # 1000 * 0.000027397 = 0.027397. Rounded to 5 decimal places: 0.02740
        self.assertEqual(accrual_result.accrual_amount, Decimal("0.02740"))
        self.assertEqual(
            accrual_result.description,
            "Daily interest accrued at 0.00274% on balance of 1000.00",
        )

    @pytest.mark.unit
    def test_get_fixed_interest_accrual_amount_zero_balance(self):
        accrual_result = flat_interest.get_fixed_interest_accrual_amount(
            effective_balance=Balance(credit=Decimal("0"), debit=Decimal("0"), net=Decimal("0")),
            effective_datetime=DEFAULT_DATETIME,
            interest_rates=Decimal("0.01"),
            days_in_year="365",
            precision=5,
        )

        self.assertEqual(accrual_result.accrual_amount, Decimal("0"))
        self.assertEqual(accrual_result.description, "")
