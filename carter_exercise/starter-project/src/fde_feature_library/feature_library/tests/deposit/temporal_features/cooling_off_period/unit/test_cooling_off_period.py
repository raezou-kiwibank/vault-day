# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel
from zoneinfo import ZoneInfo

import pytest

# features
import feature_library.deposit.temporal_features.cooling_off_period as cooling_off_period
from feature_library.common import balance_utils, posting_utils

# contracts api
from contracts_api import AttributeHookArguments

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import DEFAULT_DATETIME, FeatureTest

from tests.utils import initialise_mock_state

UTC = ZoneInfo("UTC")


@pytest.mark.unit
class AttributeTest(FeatureTest):
    def test_cooling_off_period_end_datetime(self):
        mock_params_observation = MagicMock()
        mock_params_observation.parameters = {
            cooling_off_period.COOLING_OFF_PERIOD_PARAM_ID: Decimal(5),
        }
        mock_vault = self.create_mock(
            activation_datetime=DEFAULT_DATETIME,
            parameters_observation_fetchers_mapping={
                cooling_off_period.COOLING_OFF_PERIOD_PARAMS_ET_POF_ID: mock_params_observation
            },
        )
        mock_vault.events_timezone = UTC
        mock_state = initialise_mock_state(
            vault=mock_vault,
            parameters={
                cooling_off_period.COOLING_OFF_PERIOD_PARAM_ID: Decimal(5),
            },
        )
        expected_result = datetime(2019, 1, 6, 0, 0, 0, tzinfo=UTC)
        result = cooling_off_period.get_cooling_off_period_end_datetime(state=mock_state)

        self.assertEqual(result, expected_result)

    def test_cooling_off_period_end_date_attribute_handler(self):
        mock_vault = sentinel.vault
        mock_hook_args = MagicMock(spec=AttributeHookArguments)
        mock_hook_args.effective_datetime = DEFAULT_DATETIME

        with (
            patch.object(cooling_off_period, "state_utils") as mock_state_utils,
            patch.object(
                cooling_off_period, "get_cooling_off_period_end_datetime"
            ) as mock_get_end_dt,
        ):
            mock_state_utils.initialise_state.return_value = sentinel.state
            mock_get_end_dt.return_value = DEFAULT_DATETIME

            result = cooling_off_period.cooling_off_period_end_date_attribute_handler(
                vault=mock_vault, hook_arguments=mock_hook_args
            )

            self.assertEqual(result.attribute_value, DEFAULT_DATETIME)
            mock_state_utils.initialise_state.assert_called_once_with(
                vault=mock_vault, effective_datetime=DEFAULT_DATETIME
            )
            mock_get_end_dt.assert_called_once_with(
                state=sentinel.state, fetchers_config=cooling_off_period.DEFAULT_FETCHERS_CONFIG
            )


@pytest.mark.unit
class ValidateCoolOffPeriodTest(FeatureTest):
    def setUp(self) -> None:
        self.mock_params_observation = MagicMock()
        self.mock_params_observation.parameters = {
            cooling_off_period.COOLING_OFF_PERIOD_PARAM_ID: Decimal(5),
        }
        self.mock_vault = self.create_mock(
            activation_datetime=DEFAULT_DATETIME,
            parameters_observation_fetchers_mapping={
                cooling_off_period.COOLING_OFF_PERIOD_PARAMS_ET_POF_ID: self.mock_params_observation
            },
        )
        self.mock_vault.events_timezone = UTC
        self.mock_state = initialise_mock_state(
            vault=self.mock_vault,
            parameters={
                cooling_off_period.COOLING_OFF_PERIOD_PARAM_ID: Decimal(5),
            },
        )
        return super().setUp()

    def test_within_cooling_off_period_returns_true(self):
        self.mock_state = initialise_mock_state(
            vault=self.mock_vault,
            effective_datetime=datetime(2019, 1, 5, 23, 59, 59, tzinfo=UTC),
            parameters=self.mock_state.parameters,
        )
        result = cooling_off_period.is_within_cooling_off_period(state=self.mock_state)

        self.assertTrue(result)

    def test_at_cooling_off_period_end_time_returns_true(self):
        self.mock_state = initialise_mock_state(
            vault=self.mock_vault,
            effective_datetime=datetime(2019, 1, 6, 0, 0, 0, tzinfo=UTC),
            parameters=self.mock_state.parameters,
        )
        result = cooling_off_period.is_within_cooling_off_period(state=self.mock_state)

        self.assertTrue(result)

    def test_outside_cooling_off_period_returns_false(self):
        self.mock_state = initialise_mock_state(
            vault=self.mock_vault,
            effective_datetime=datetime(2019, 1, 6, 0, 0, 1, tzinfo=UTC),
            parameters=self.mock_state.parameters,
        )
        result = cooling_off_period.is_within_cooling_off_period(state=self.mock_state)

        self.assertFalse(result)


@pytest.mark.unit
class WithdrawalSubjectToFeesTest(FeatureTest):
    def setUp(self) -> None:
        patch_is_within_cooling_off_period = patch.object(
            cooling_off_period, "is_within_cooling_off_period"
        )
        self.mock_is_within_cooling_off_period = patch_is_within_cooling_off_period.start()
        self.mock_is_within_cooling_off_period.return_value = True

        patch_append_to_state = patch.object(cooling_off_period, "_append_to_state")
        self.mock_append_to_state = patch_append_to_state.start()

        patch_get_posting_instructions_balances = patch.object(
            posting_utils, "get_posting_instructions_balances"
        )
        self.mock_get_posting_instructions_balances = (
            patch_get_posting_instructions_balances.start()
        )
        self.mock_get_posting_instructions_balances.return_value = sentinel.posting_balances

        patch_sum_balances = patch.object(balance_utils, "sum_balances")
        self.mock_sum_balances = patch_sum_balances.start()
        self.mock_sum_balances.return_value = sentinel.summed_posting_balances

        patch_net_debit = patch.object(balance_utils, "net_debit")
        self.mock_net_debit = patch_net_debit.start()

        patch_net_credit = patch.object(balance_utils, "net_credit")
        self.mock_net_credit = patch_net_credit.start()

        patch_get_available_balance = patch.object(balance_utils, "get_available_balance")
        self.mock_get_available_balance = patch_get_available_balance.start()

        self.mock_vault = self.create_mock()
        self.mock_state = initialise_mock_state(
            vault=self.mock_vault,
            parameters={
                cooling_off_period.denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination,
            },
            balances=sentinel.state_balances,
        )
        self.mock_append_to_state.return_value = self.mock_state

        self.addCleanup(patch.stopall)
        return super().setUp()

    def test_partial_withdrawal_within_cooling_off_period(self):
        self.mock_net_debit.return_value = Decimal("1")  # withdrawal amount
        self.mock_net_credit.return_value = Decimal("50")  # current balance
        self.mock_get_available_balance.return_value = sentinel.available_balance

        result = cooling_off_period.is_withdrawal_subject_to_fees(
            state=self.mock_state,
            posting_instructions=sentinel.posting_instructions,
        )

        self.assertTrue(result)
        self.mock_get_posting_instructions_balances.assert_called_once_with(
            posting_instructions=sentinel.posting_instructions
        )
        self.mock_sum_balances.assert_called_once_with(
            balances=sentinel.posting_balances,
            denomination=sentinel.denomination,
        )
        self.mock_net_debit.assert_called_once_with(bal=sentinel.summed_posting_balances)
        self.mock_get_available_balance.assert_called_once_with(
            balances=sentinel.state_balances, denomination=sentinel.denomination
        )
        self.mock_net_credit.assert_called_once_with(bal=sentinel.available_balance)
        self.mock_is_within_cooling_off_period.assert_not_called()

    def test_partial_withdrawal_outside_cooling_off_period(self):
        self.mock_net_debit.return_value = Decimal("1")  # withdrawal amount
        self.mock_net_credit.return_value = Decimal("50")  # current balance
        self.mock_get_available_balance.return_value = sentinel.available_balance
        self.mock_is_within_cooling_off_period.return_value = False

        result = cooling_off_period.is_withdrawal_subject_to_fees(
            state=self.mock_state,
            posting_instructions=sentinel.posting_instructions,
        )

        self.assertTrue(result)
        self.mock_is_within_cooling_off_period.assert_not_called()

    def test_full_withdrawal_within_cooling_off_period(self):
        self.mock_net_debit.return_value = Decimal("1")  # withdrawal amount
        self.mock_net_credit.return_value = Decimal("0")  # current balance
        self.mock_get_available_balance.return_value = sentinel.available_balance

        result = cooling_off_period.is_withdrawal_subject_to_fees(
            state=self.mock_state,
            posting_instructions=sentinel.posting_instructions,
        )

        self.assertFalse(result)
        self.mock_is_within_cooling_off_period.assert_called_once_with(
            state=self.mock_state, fetchers_config=cooling_off_period.DEFAULT_FETCHERS_CONFIG
        )

    def test_full_withdrawal_outside_cooling_off_period(self):
        self.mock_net_debit.return_value = Decimal("1")  # withdrawal amount
        self.mock_net_credit.return_value = Decimal("0")  # current balance
        self.mock_get_available_balance.return_value = sentinel.available_balance
        self.mock_is_within_cooling_off_period.return_value = False

        result = cooling_off_period.is_withdrawal_subject_to_fees(
            state=self.mock_state,
            posting_instructions=sentinel.posting_instructions,
        )

        self.assertTrue(result)
        self.mock_is_within_cooling_off_period.assert_called_once_with(
            state=self.mock_state, fetchers_config=cooling_off_period.DEFAULT_FETCHERS_CONFIG
        )

    def test_deposits_are_not_subject_to_fees(self):
        self.mock_net_debit.return_value = Decimal("0")  # deposit amount (net debit is 0)

        result = cooling_off_period.is_withdrawal_subject_to_fees(
            state=self.mock_state,
            posting_instructions=sentinel.posting_instructions,
        )

        self.assertFalse(result)
        self.mock_get_posting_instructions_balances.assert_called_once_with(
            posting_instructions=sentinel.posting_instructions
        )
        self.mock_sum_balances.assert_called_once_with(
            balances=sentinel.posting_balances,
            denomination=sentinel.denomination,
        )
        self.mock_net_debit.assert_called_once_with(bal=sentinel.summed_posting_balances)
        self.mock_get_available_balance.assert_not_called()
        self.mock_is_within_cooling_off_period.assert_not_called()
