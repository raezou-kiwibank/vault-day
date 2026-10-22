# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

# features
import feature_library.common.tuples as common_tuples
from feature_library.deposit.interest.secondary import overdraft_interest

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

    @pytest.mark.unit
    def test_get_interest_rate_success(self):
        fixed_rate = Decimal("0.05")
        self.mock_state.parameters[overdraft_interest.OVERDRAFT_INTEREST_RATE_PARAM.id] = fixed_rate

        # Use the standard FeatureTest pattern for parameter observations
        self.mock_vault.get_parameters_observation.side_effect = None
        self.mock_vault.get_parameters_observation.return_value = MagicMock(
            parameters={overdraft_interest.OVERDRAFT_INTEREST_RATE_PARAM.id: fixed_rate}
        )

        # Also mock balance observation
        self.mock_vault.get_balances_observation.side_effect = None
        self.mock_vault.get_balances_observation.return_value = MagicMock(balances={})

        result = overdraft_interest.get_interest_rate(state=self.mock_state)

        self.assertEqual(result.interest_rate_param_value, fixed_rate)
        self.assertEqual(result.interest_type, common_tuples.INTEREST_TYPE_OVERDRAFT)


class TestCalculateAccrualBalance(FeatureTest):
    def setUp(self) -> None:
        self.mock_vault = self.create_mock()
        self.mock_state = initialise_mock_state(
            vault=self.mock_vault,
            effective_datetime=DEFAULT_DATETIME,
        )
        return super().setUp()

    @patch.object(overdraft_interest, "_retrieve_eod_observations")
    @pytest.mark.unit
    def test_calculate_accrual_balance_zero_balance(
        self, mock_retrieve_eod_observations: MagicMock
    ):
        # Setup mock parameters
        config = overdraft_interest.DEFAULT_OVERDRAFT_INTEREST_FETCHERS_CONFIG
        self.mock_state.parameters.update(
            {
                config.denomination_param_id: "GBP",
                config.interest_free_buffer_amount_param_id: "0",
                config.interest_free_buffer_days_param_id: "0",
            }
        )
        mock_retrieve_eod_observations.return_value = [
            Balance(net=Decimal("0"), credit=Decimal("0"))
        ]

        result = overdraft_interest.calculate_accrual_balance(
            state=self.mock_state,
            fetchers_config=overdraft_interest.DEFAULT_OVERDRAFT_INTEREST_FETCHERS_CONFIG,
        )

        self.assertEqual(result, Balance())

    @patch.object(overdraft_interest, "_retrieve_eod_observations")
    @pytest.mark.unit
    def test_calculate_accrual_balance_with_overdraft(
        self, mock_retrieve_eod_observations: MagicMock
    ):
        # Setup mock parameters
        config = overdraft_interest.DEFAULT_OVERDRAFT_INTEREST_FETCHERS_CONFIG
        self.mock_state.parameters.update(
            {
                config.denomination_param_id: "GBP",
                config.interest_free_buffer_amount_param_id: "0",
                config.interest_free_buffer_days_param_id: "0",
            }
        )
        balance_in_overdraft = Balance(
            net=Decimal("-100"), debit=Decimal("100"), credit=Decimal("0")
        )
        mock_retrieve_eod_observations.return_value = [balance_in_overdraft]

        result = overdraft_interest.calculate_accrual_balance(
            state=self.mock_state,
            fetchers_config=overdraft_interest.DEFAULT_OVERDRAFT_INTEREST_FETCHERS_CONFIG,
        )

        self.assertEqual(result, balance_in_overdraft)
