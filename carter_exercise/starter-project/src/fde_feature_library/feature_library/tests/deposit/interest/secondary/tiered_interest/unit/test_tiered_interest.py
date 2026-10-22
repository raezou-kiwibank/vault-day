# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

# features
import feature_library.common.tuples as common_tuples
import feature_library.deposit.interest.secondary.tiered_interest as tiered_interest

# contracts api
from contracts_api import Balance

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

# feature_library
from tests.utils import initialise_mock_state

DEFAULT_DATETIME = datetime(2025, 1, 1, tzinfo=ZoneInfo("UTC"))


class TestGetInterestRates(FeatureTest):
    def setUp(self) -> None:
        self.mock_vault = self.create_mock()
        self.mock_state = initialise_mock_state(
            vault=self.mock_vault,
            effective_datetime=DEFAULT_DATETIME,
        )
        return super().setUp()

    @patch.object(tiered_interest, "_append_to_state")
    @pytest.mark.unit
    def test_get_interest_rates_success(self, mock_append_to_state: MagicMock):
        tiered_rates = '{"0": "0.01"}'
        self.mock_state.parameters[tiered_interest.TIERED_INTEREST_RATES_PARAM_ID] = tiered_rates
        mock_append_to_state.return_value = self.mock_state

        result = tiered_interest.get_interest_rates(state=self.mock_state)

        self.assertEqual(result.interest_rate_param_value, tiered_rates)
        self.assertEqual(result.interest_type, common_tuples.INTEREST_TYPE_TIERED)

    @patch.object(tiered_interest.state_utils, "check_parameters_exist")
    @patch.object(tiered_interest, "_append_to_state")
    @pytest.mark.unit
    def test_get_interest_rates_missing_param(
        self, mock_append_to_state: MagicMock, mock_check_parameters_exist: MagicMock
    ):
        mock_append_to_state.return_value = self.mock_state
        mock_check_parameters_exist.return_value = "Missing Param Rejection"

        with self.assertRaises(AssertionError) as ex:
            tiered_interest.get_interest_rates(state=self.mock_state)

        self.assertEqual(ex.exception.args[0], "Missing Param Rejection")
        mock_check_parameters_exist.assert_called_once_with(
            state=self.mock_state, param_ids={tiered_interest.TIERED_INTEREST_RATES_PARAM_ID}
        )


class TestTieredAccrualAmount(FeatureTest):
    @patch.object(tiered_interest.parameter_utils, "yearly_to_daily_rate")
    @pytest.mark.unit
    def test_get_tiered_accrual_amount_with_multiple_tiers(
        self, mock_yearly_to_daily_rate: MagicMock
    ):
        # Mocking daily rates
        mock_yearly_to_daily_rate.side_effect = [Decimal("0.01"), Decimal("0.02"), Decimal("0.03")]

        accrual_result = tiered_interest.get_tiered_accrual_amount(
            effective_balance=Balance(
                credit=Decimal("100"), debit=Decimal("0"), net=Decimal("100")
            ),
            effective_datetime=DEFAULT_DATETIME,
            interest_rates='{"0": "0.01", "4": "0.02", "10": "0.03"}',
            days_in_year="365",
            precision=2,
        )

        # Tier 1 (0-4): 4 * 0.01 = 0.04
        # Tier 2 (4-10): 6 * 0.02 = 0.12
        # Tier 3 (10-100): 90 * 0.03 = 2.70
        # Total: 2.86
        self.assertEqual(accrual_result.accrual_amount, Decimal("2.86"))
        self.assertEqual(
            accrual_result.description,
            "Accrual on 4.00 at annual rate of 1.00%. Accrual on 6.00 at annual rate of 2.00%. "
            "Accrual on 90.00 at annual rate of 3.00%.",
        )

    @pytest.mark.unit
    def test_get_tiered_accrual_amount_below_lowest_tier(self):
        accrual_result = tiered_interest.get_tiered_accrual_amount(
            effective_balance=Balance(credit=Decimal("50"), debit=Decimal("0"), net=Decimal("50")),
            effective_datetime=DEFAULT_DATETIME,
            interest_rates='{"100": "0.01"}',
            days_in_year="365",
        )
        self.assertEqual(accrual_result.accrual_amount, Decimal("0"))

    @patch.object(tiered_interest.parameter_utils, "yearly_to_daily_rate")
    @pytest.mark.unit
    def test_get_tiered_accrual_amount_with_negative_rates(
        self, mock_yearly_to_daily_rate: MagicMock
    ):
        mock_yearly_to_daily_rate.side_effect = [Decimal("-0.01")]

        accrual_result = tiered_interest.get_tiered_accrual_amount(
            effective_balance=Balance(
                credit=Decimal("1000"), debit=Decimal("0"), net=Decimal("1000")
            ),
            effective_datetime=DEFAULT_DATETIME,
            interest_rates='{"0": "-0.01"}',
            days_in_year="365",
            precision=2,
        )
        self.assertEqual(accrual_result.accrual_amount, Decimal("-10"))
        self.assertEqual(
            accrual_result.description,
            "Accrual on 1000.00 at annual rate of -1.00%.",
        )
