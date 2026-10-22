# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

# features
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.deposit.fees.minimum_monthly_balance as minimum_monthly_balance_module

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    BalancesObservation,
    CustomInstruction,
    ParametersObservation,
    Phase,
    Posting,
    ScheduledEvent,
    ScheduleExpression,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import (
    ACCOUNT_ID,
    FeatureTest,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.utils import initialise_mock_state

UTC_ZONE = ZoneInfo("UTC")
DEFAULT_DATETIME = datetime(2026, 1, 1, tzinfo=UTC_ZONE)

DENOMINATION = DEFAULT_DENOMINATION
INCOME_ACCOUNT = "MINIMUM_BALANCE_FEE_INCOME"
ACCOUNT_TYPE = "account_type"
FETCHER_ID = "fetcher_id"
PARAMETER_NAME = "parameter_name"


class MinimumMonthlyBalanceTest(FeatureTest):
    def setup_mock_data(
        self,
        account_activation_datetime: datetime = DEFAULT_DATETIME,
        effective_datetime: datetime = DEFAULT_DATETIME,
        minimum_balance_fee: Decimal | None = Decimal("5.00"),
        minimum_balance_threshold_by_tier: str | None = '{"UPPER_TIER": "25", "LOWER_TIER": "100"}',
        minimum_balance_fee_income_account: str | None = INCOME_ACCOUNT,
        minimum_balance_fee_application_day: str | None = "1",
        minimum_balance_fee_application_time: str | None = "00:00:00",
        partial_minimum_balance_fee_application_enabled: str | None = "False",
        account_tier: str | None = "UPPER_TIER",
        default_bal: Decimal | None = None,
        denomination: str | None = DEFAULT_DENOMINATION,
    ):
        self.effective_datetime = effective_datetime

        denom_params = {}
        if denomination is not None:
            denom_params[denomination_module.DENOMINATION_PARAM.id] = denomination

        minimum_balance_fees_params = {}
        if minimum_balance_fee is not None:
            minimum_balance_fees_params[
                minimum_monthly_balance_module.MINIMUM_BALANCE_FEE_PARAM.id
            ] = minimum_balance_fee
        if minimum_balance_threshold_by_tier is not None:
            minimum_balance_fees_params[
                minimum_monthly_balance_module.MINIMUM_BALANCE_THRESHOLD_BY_TIER_PARAM.id
            ] = minimum_balance_threshold_by_tier
        if minimum_balance_fee_income_account is not None:
            minimum_balance_fees_params[
                minimum_monthly_balance_module.MINIMUM_BALANCE_FEE_INCOME_ACCOUNT_PARAM.id
            ] = minimum_balance_fee_income_account
        if minimum_balance_fee_application_day is not None:
            minimum_balance_fees_params[
                minimum_monthly_balance_module.MINIMUM_BALANCE_FEE_APPLICATION_DAY_PARAM.id
            ] = minimum_balance_fee_application_day
        if minimum_balance_fee_application_time is not None:
            minimum_balance_fees_params[
                minimum_monthly_balance_module.MINIMUM_BALANCE_FEE_APPLICATION_TIME_PARAM.id
            ] = minimum_balance_fee_application_time
        if partial_minimum_balance_fee_application_enabled is not None:
            minimum_balance_fees_params[
                minimum_monthly_balance_module.MINIMUM_BALANCE_PARTIAL_FEE_ENABLED_PARAM.id
            ] = partial_minimum_balance_fee_application_enabled
        if account_tier is not None:
            minimum_balance_fees_params[
                minimum_monthly_balance_module.common.ACCOUNT_TIER_PARAM.id
            ] = account_tier

        params_obs: dict[str, ParametersObservation] = {
            denomination_module.DENOMINATION_ET_POF.fetcher_id: ParametersObservation(
                parameters=denom_params, value_datetime=effective_datetime
            ),
            minimum_monthly_balance_module.MINIMUM_BALANCE_FEE_POF.fetcher_id: ParametersObservation(  # noqa: E501
                parameters=minimum_balance_fees_params,
                value_datetime=effective_datetime,
            ),
        }

        default_bals = BalanceDefaultDict(
            lambda: Balance(),
            {
                BalanceCoordinate(
                    DEFAULT_ADDRESS, DEFAULT_ASSET, DENOMINATION, Phase.COMMITTED
                ): Balance(default_bal or Decimal(0), Decimal(0), default_bal or Decimal(0)),
            },
        )
        self.mock_vault = self.create_mock(
            account_id=ACCOUNT_ID,
            activation_datetime=account_activation_datetime,
            balances_observation_fetchers_mapping={
                fetchers.ALL_BALANCES_ET_BOF.fetcher_id: BalancesObservation(
                    balances=default_bals,
                    value_datetime=effective_datetime,
                    at_datetime=effective_datetime,
                ),
            },
            creation_date=account_activation_datetime,
            parameters_observation_fetchers_mapping=params_obs,
        )
        self.state = MagicMock(
            vault=self.mock_vault,
            effective_datetime=effective_datetime,
            parameters=minimum_balance_fees_params | denom_params,
            balances=default_bals,
        )

    @pytest.mark.unit
    def test_apply_fees_raises_assertion_error_if_parameter_missing(self):
        params_to_test = [
            ("minimum_balance_fee", {"minimum_balance_fee": None}),
            ("minimum_balance_fee_income_account", {"minimum_balance_fee_income_account": None}),
            ("minimum_balance_threshold_by_tier", {"minimum_balance_threshold_by_tier": None}),
            ("account_tier", {"account_tier": None}),
            ("denomination", {"denomination": None}),
        ]

        for param_name, setup_kwargs in params_to_test:
            with self.subTest(missing_param=param_name):
                self.setup_mock_data(**setup_kwargs)  # type: ignore
                with self.assertRaises(AssertionError) as cm:
                    minimum_monthly_balance_module.apply_fees(
                        state=self.state,
                        account_type=ACCOUNT_TYPE,
                    )
                self.assertIn("parameters are missing: ", str(cm.exception))

    @patch.object(minimum_monthly_balance_module, "_is_monthly_mean_balance_above_threshold")
    @pytest.mark.unit
    def test_apply_fees_fee_applied(
        self,
        mock_is_above: MagicMock,
    ):
        mock_is_above.return_value = False
        fee_rate = Decimal("5.00")
        self.setup_mock_data(
            minimum_balance_fee=fee_rate,
            minimum_balance_fee_income_account=INCOME_ACCOUNT,
            partial_minimum_balance_fee_application_enabled="False",
        )
        result = minimum_monthly_balance_module.apply_fees(
            state=self.state,
            account_type=ACCOUNT_TYPE,
        )
        expected = [
            CustomInstruction(
                postings=[
                    Posting(
                        credit=False,
                        amount=fee_rate,
                        denomination=DENOMINATION,
                        account_id=ACCOUNT_ID,
                        account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                    Posting(
                        credit=True,
                        amount=fee_rate,
                        denomination=DENOMINATION,
                        account_id=INCOME_ACCOUNT,
                        account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                ],
                instruction_details={
                    "description": "Minimum balance fee",
                    "event": "APPLY_MINIMUM_BALANCE_FEE",
                    "gl_impacted": str(True),
                    "account_type": ACCOUNT_TYPE,
                },
                value_datetime=self.effective_datetime,
                override_all_restrictions=True,
            )
        ]
        self.assertListEqual(result, expected)

    @patch.object(minimum_monthly_balance_module, "_is_monthly_mean_balance_above_threshold")
    @pytest.mark.unit
    def test_apply_fees_not_applied_when_above_threshold(
        self,
        mock_is_above: MagicMock,
    ):
        mock_is_above.return_value = True
        self.setup_mock_data()

        result = minimum_monthly_balance_module.apply_fees(
            state=self.state,
            account_type=ACCOUNT_TYPE,
        )
        self.assertListEqual(result, [])

    @patch.object(minimum_monthly_balance_module, "_is_monthly_mean_balance_above_threshold")
    @pytest.mark.unit
    def test_apply_fees_not_applied_when_fee_is_zero(
        self,
        mock_is_above: MagicMock,
    ):
        self.setup_mock_data(minimum_balance_fee=Decimal("0.00"))

        result = minimum_monthly_balance_module.apply_fees(
            state=self.state,
            account_type=ACCOUNT_TYPE,
        )
        self.assertListEqual(result, [])
        mock_is_above.assert_not_called()

    @patch.object(minimum_monthly_balance_module, "_is_monthly_mean_balance_above_threshold")
    @patch.object(minimum_monthly_balance_module.partial_fee, "charge_partial_fee")
    @pytest.mark.unit
    def test_apply_fees_partially_applied(
        self,
        mock_charge_partial_fee: MagicMock,
        mock_is_above: MagicMock,
    ):
        mock_is_above.return_value = False
        fee_rate = Decimal("5.00")
        self.setup_mock_data(
            minimum_balance_fee=fee_rate,
            minimum_balance_fee_income_account=INCOME_ACCOUNT,
            partial_minimum_balance_fee_application_enabled="True",
        )
        mock_charge_partial_fee.return_value = [sentinel.partial_fee_instruction]

        result = minimum_monthly_balance_module.apply_fees(
            state=self.state,
            account_type=ACCOUNT_TYPE,
            available_balance_feature=sentinel.available_balance_feature,
        )

        self.assertListEqual(result, [sentinel.partial_fee_instruction])


class MinimumMonthlyBalanceHelpersTest(FeatureTest):
    @pytest.mark.unit
    def test_get_parameters(
        self,
    ):
        mock_vault = self.create_mock(
            parameters_observation_fetchers_mapping={
                FETCHER_ID: ParametersObservation(
                    parameters={PARAMETER_NAME: "parameter_value"},
                    value_datetime=DEFAULT_DATETIME,
                )
            }
        )

        result = minimum_monthly_balance_module.get_parameters(
            vault=mock_vault,
            param_fetcher_id=FETCHER_ID,
        )

        self.assertEqual(
            result,
            {PARAMETER_NAME: "parameter_value"},
        )

    @patch.object(minimum_monthly_balance_module, "get_parameters")
    @patch.object(minimum_monthly_balance_module.state_utils, "append_to_state")
    @pytest.mark.unit
    def test_append_to_state(
        self,
        mock_append_to_state: MagicMock,
        mock_get_parameters: MagicMock,
    ):
        mock_vault = self.create_mock(
            balances_observation_fetchers_mapping={
                fetchers.ALL_BALANCES_ET_BOF.fetcher_id: BalancesObservation(
                    balances=BalanceDefaultDict(lambda: Balance(), {}),
                    value_datetime=DEFAULT_DATETIME,
                )
            }
        )
        initial_parameters = {"INITIAL_PARAM": "INITIAL_VALUE"}
        new_parameters = {"NEW_PARAM": "NEW_VALUE"}

        mock_state = initialise_mock_state(vault=mock_vault, parameters=initial_parameters)
        mock_get_parameters.return_value = new_parameters

        mock_append_to_state.return_value = initialise_mock_state(
            vault=mock_vault,
            parameters=initial_parameters | new_parameters,
            effective_datetime=mock_state.effective_datetime,
        )

        _ = minimum_monthly_balance_module._append_to_state(
            state=mock_state,
            fetchers_config=minimum_monthly_balance_module.DEFAULT_MINIMUM_BALANCE_FETCHERS_CONFIG,
        )

        mock_get_parameters.assert_called_once_with(
            mock_vault,
            minimum_monthly_balance_module.DEFAULT_MINIMUM_BALANCE_FETCHERS_CONFIG.param_fetcher_id,
        )
        mock_append_to_state.assert_called_once_with(
            state=mock_state,
            parameters=new_parameters,
            balances=mock_vault.get_balances_observation(
                fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID
            ).balances,
        )

    @patch.object(minimum_monthly_balance_module, "_append_to_state")
    @patch.object(minimum_monthly_balance_module.state_utils, "append_to_state")
    @pytest.mark.unit
    def test_get_scheduled_events(
        self, mock_state_utils_append_to_state: MagicMock, mock_append_to_state: MagicMock
    ):
        application_time = "12:34:56"
        day = "1"
        mock_state = initialise_mock_state(
            effective_datetime=DEFAULT_DATETIME,
            parameters={
                minimum_monthly_balance_module.MINIMUM_BALANCE_FEE_APPLICATION_TIME_PARAM.id: application_time,  # noqa: E501
                minimum_monthly_balance_module.MINIMUM_BALANCE_FEE_APPLICATION_DAY_PARAM.id: day,
            },
        )
        # the function uses state_utils.append_to_state directly so that balances aren't requested
        mock_state.vault.events_timezone = UTC_ZONE
        mock_state_utils_append_to_state.return_value = mock_state

        result = minimum_monthly_balance_module.get_scheduled_events(state=mock_state)

        expected_event = {
            minimum_monthly_balance_module.APPLY_MINIMUM_MONTHLY_BALANCE_EVENT: ScheduledEvent(
                start_datetime=DEFAULT_DATETIME + relativedelta(months=1),
                expression=ScheduleExpression(
                    day=1,
                    hour=12,
                    minute=34,
                    second=56,
                ),
            )
        }
        self.assertEqual(result, expected_event)

    @patch.object(minimum_monthly_balance_module.state_utils, "check_parameters_exist")
    @patch.object(minimum_monthly_balance_module.state_utils, "append_to_state")
    @pytest.mark.unit
    def test_get_scheduled_events_returns_rejection_if_parameter_missing(
        self, mock_state_utils_append_to_state: MagicMock, mock_check_parameters_exist: MagicMock
    ):
        mock_state = initialise_mock_state()
        mock_state_utils_append_to_state.return_value = mock_state
        mock_check_parameters_exist.return_value = sentinel.rejection

        with self.assertRaises(AssertionError) as ex:
            minimum_monthly_balance_module.get_scheduled_events(state=mock_state)

        self.assertEqual(ex.exception.args[0], sentinel.rejection)
