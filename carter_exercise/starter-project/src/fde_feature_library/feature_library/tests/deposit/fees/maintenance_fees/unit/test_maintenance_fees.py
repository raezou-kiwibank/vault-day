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
import feature_library.deposit.common as common
import feature_library.deposit.fees.maintenance_fees as maintenance_fees_module

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
MONTHLY_INCOME_ACCOUNT = "MONTHLY_MAINTENANCE_FEE_INCOME"
ANNUAL_INCOME_ACCOUNT = "ANNUAL_MAINTENANCE_FEE_INCOME"
ACCOUNT_TYPE = "account_type"
FETCHER_ID = "fetcher_id"
PARAMETER_NAME = "parameter_name"


class MaintenanceFeesTest(FeatureTest):
    def setup_mock_data(
        self,
        account_activation_datetime: datetime = DEFAULT_DATETIME,
        effective_datetime: datetime = DEFAULT_DATETIME,
        monthly_maintenance_fee_by_tier: str | None = '{"UPPER_TIER": "5", "LOWER_TIER": "10"}',
        monthly_maintenance_fee_income_account: str | None = MONTHLY_INCOME_ACCOUNT,
        partial_maintenance_fee_enabled: str | None = "False",
        annual_maintenance_fee_by_tier: str | None = '{"UPPER_TIER": "50", "LOWER_TIER": "100"}',
        annual_maintenance_fee_income_account: str | None = ANNUAL_INCOME_ACCOUNT,
        maintenance_fee_application_day: str | None = "1",
        maintenance_fee_application_time: str | None = "00:00:00",
        account_tier: str | None = "UPPER_TIER",
        default_bal: Decimal | None = None,
        denomination: str | None = DEFAULT_DENOMINATION,
    ):
        self.effective_datetime = effective_datetime

        denom_params = {}
        if denomination is not None:
            denom_params[denomination_module.DENOMINATION_PARAM.id] = denomination

        maintenance_fees_params = {}
        if monthly_maintenance_fee_by_tier is not None:
            maintenance_fees_params[
                maintenance_fees_module.MONTHLY_MAINTENANCE_FEE_BY_TIER_PARAM.id
            ] = monthly_maintenance_fee_by_tier
        if monthly_maintenance_fee_income_account is not None:
            maintenance_fees_params[
                maintenance_fees_module.MONTHLY_MAINTENANCE_FEE_INCOME_ACCOUNT_PARAM.id
            ] = monthly_maintenance_fee_income_account
        if partial_maintenance_fee_enabled is not None:
            maintenance_fees_params[
                maintenance_fees_module.MONTHLY_MAINTENANCE_FEE_PARTIAL_FEE_ENABLED_PARAM.id
            ] = partial_maintenance_fee_enabled
        if annual_maintenance_fee_by_tier is not None:
            maintenance_fees_params[
                maintenance_fees_module.ANNUAL_MAINTENANCE_FEE_BY_TIER_PARAM.id
            ] = annual_maintenance_fee_by_tier
        if annual_maintenance_fee_income_account is not None:
            maintenance_fees_params[
                maintenance_fees_module.ANNUAL_MAINTENANCE_FEE_INCOME_ACCOUNT_PARAM.id
            ] = annual_maintenance_fee_income_account
        if maintenance_fee_application_day is not None:
            maintenance_fees_params[
                maintenance_fees_module.MAINTENANCE_FEE_APPLICATION_DAY_PARAM.id
            ] = maintenance_fee_application_day
        if maintenance_fee_application_time is not None:
            maintenance_fees_params[
                maintenance_fees_module.MAINTENANCE_FEE_APPLICATION_TIME_PARAM.id
            ] = maintenance_fee_application_time
        if account_tier is not None:
            maintenance_fees_params[common.ACCOUNT_TIER_PARAM.id] = account_tier

        params_obs: dict[str, ParametersObservation] = {
            denomination_module.DENOMINATION_ET_POF.fetcher_id: ParametersObservation(
                parameters=denom_params, value_datetime=effective_datetime
            ),
            maintenance_fees_module.MAINTENANCE_FEES_POF.fetcher_id: ParametersObservation(
                parameters=maintenance_fees_params,
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
        self.mock_vault.events_timezone = UTC_ZONE
        self.state = MagicMock(
            vault=self.mock_vault,
            effective_datetime=effective_datetime,
            parameters=maintenance_fees_params | denom_params,
            balances=default_bals,
        )

    @pytest.mark.unit
    def test_apply_monthly_fee_raises_assertion_error_if_parameter_missing(self):
        params_to_test = [
            ("denomination", {"denomination": None}),
            ("account_tier", {"account_tier": None}),
            ("monthly_maintenance_fee_by_tier", {"monthly_maintenance_fee_by_tier": None}),
            (
                "monthly_maintenance_fee_income_account",
                {"monthly_maintenance_fee_income_account": None},
            ),
        ]

        for param_name, setup_kwargs in params_to_test:
            with self.subTest(missing_param=param_name):
                self.setup_mock_data(**setup_kwargs)  # type: ignore
                with self.assertRaises(AssertionError) as cm:
                    maintenance_fees_module.apply_monthly_fee(
                        state=self.state,
                        account_type=ACCOUNT_TYPE,
                    )
                self.assertIn("parameters are missing: ", str(cm.exception))

    @pytest.mark.unit
    def test_apply_monthly_fee_fee_applied(self):
        self.setup_mock_data(
            monthly_maintenance_fee_by_tier='{"UPPER_TIER": "5.00"}',
            account_tier="UPPER_TIER",
            monthly_maintenance_fee_income_account=MONTHLY_INCOME_ACCOUNT,
            partial_maintenance_fee_enabled="False",
        )
        result = maintenance_fees_module.apply_monthly_fee(
            state=self.state,
            account_type=ACCOUNT_TYPE,
        )
        expected = [
            CustomInstruction(
                postings=[
                    Posting(
                        credit=False,
                        amount=Decimal("5.00"),
                        denomination=DENOMINATION,
                        account_id=ACCOUNT_ID,
                        account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                    Posting(
                        credit=True,
                        amount=Decimal("5.00"),
                        denomination=DENOMINATION,
                        account_id=MONTHLY_INCOME_ACCOUNT,
                        account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                ],
                instruction_details={
                    "description": "Monthly maintenance fee",
                    "event": "APPLY_MONTHLY_FEE",
                    "gl_impacted": str(True),
                    "account_type": ACCOUNT_TYPE,
                },
                value_datetime=self.effective_datetime,
                override_all_restrictions=True,
            )
        ]
        self.assertListEqual(result, expected)

    @pytest.mark.unit
    def test_apply_monthly_fee_not_applied_when_fee_is_zero(self):
        self.setup_mock_data(
            monthly_maintenance_fee_by_tier='{"UPPER_TIER": "0.00"}', account_tier="UPPER_TIER"
        )

        result = maintenance_fees_module.apply_monthly_fee(
            state=self.state,
            account_type=ACCOUNT_TYPE,
        )
        self.assertListEqual(result, [])

    @pytest.mark.unit
    def test_apply_monthly_fee_waived(self):
        self.setup_mock_data()
        mock_waive_condition = MagicMock()
        mock_waive_condition.waive_fees.return_value = True

        result = maintenance_fees_module.apply_monthly_fee(
            state=self.state,
            account_type=ACCOUNT_TYPE,
            monthly_fee_waive_conditions=[mock_waive_condition],
        )
        self.assertListEqual(result, [])

    @patch.object(maintenance_fees_module.partial_fee, "charge_partial_fee")
    @pytest.mark.unit
    def test_apply_monthly_fee_partially_applied(
        self,
        mock_charge_partial_fee: MagicMock,
    ):
        self.setup_mock_data(
            monthly_maintenance_fee_by_tier='{"UPPER_TIER": "5.00"}',
            account_tier="UPPER_TIER",
            monthly_maintenance_fee_income_account=MONTHLY_INCOME_ACCOUNT,
            partial_maintenance_fee_enabled="True",
        )
        mock_charge_partial_fee.return_value = [sentinel.partial_fee_instruction]

        result = maintenance_fees_module.apply_monthly_fee(
            state=self.state,
            account_type=ACCOUNT_TYPE,
            available_balance_feature=sentinel.available_balance_feature,
        )

        self.assertListEqual(result, [sentinel.partial_fee_instruction])

    @pytest.mark.unit
    def test_apply_annual_fee_raises_assertion_error_if_parameter_missing(self):
        params_to_test = [
            ("denomination", {"denomination": None}),
            ("account_tier", {"account_tier": None}),
            ("annual_maintenance_fee_by_tier", {"annual_maintenance_fee_by_tier": None}),
            (
                "annual_maintenance_fee_income_account",
                {"annual_maintenance_fee_income_account": None},
            ),
        ]

        for param_name, setup_kwargs in params_to_test:
            with self.subTest(missing_param=param_name):
                self.setup_mock_data(**setup_kwargs)  # type: ignore
                with self.assertRaises(AssertionError) as cm:
                    maintenance_fees_module.apply_annual_fee(
                        state=self.state,
                        account_type=ACCOUNT_TYPE,
                    )
                self.assertIn("parameters are missing: ", str(cm.exception))

    @pytest.mark.unit
    def test_apply_annual_fee_fee_applied(self):
        self.setup_mock_data(
            annual_maintenance_fee_by_tier='{"UPPER_TIER": "50.00"}',
            account_tier="UPPER_TIER",
            annual_maintenance_fee_income_account=ANNUAL_INCOME_ACCOUNT,
        )
        result = maintenance_fees_module.apply_annual_fee(
            state=self.state,
            account_type=ACCOUNT_TYPE,
        )
        expected = [
            CustomInstruction(
                postings=[
                    Posting(
                        credit=False,
                        amount=Decimal("50.00"),
                        denomination=DENOMINATION,
                        account_id=ACCOUNT_ID,
                        account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                    Posting(
                        credit=True,
                        amount=Decimal("50.00"),
                        denomination=DENOMINATION,
                        account_id=ANNUAL_INCOME_ACCOUNT,
                        account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                ],
                instruction_details={
                    "description": "Annual maintenance fee",
                    "event": "APPLY_ANNUAL_FEE",
                    "gl_impacted": str(True),
                    "account_type": ACCOUNT_TYPE,
                },
                value_datetime=self.effective_datetime,
                override_all_restrictions=True,
            )
        ]
        self.assertListEqual(result, expected)

    @pytest.mark.unit
    def test_apply_annual_fee_not_applied_when_fee_is_zero(self):
        self.setup_mock_data(
            annual_maintenance_fee_by_tier='{"UPPER_TIER": "0.00"}', account_tier="UPPER_TIER"
        )

        result = maintenance_fees_module.apply_annual_fee(
            state=self.state,
            account_type=ACCOUNT_TYPE,
        )
        self.assertListEqual(result, [])


class MaintenanceFeesHelpersTest(FeatureTest):
    @pytest.mark.unit
    def test_get_parameters(self):
        mock_vault = self.create_mock(
            parameters_observation_fetchers_mapping={
                FETCHER_ID: ParametersObservation(
                    parameters={PARAMETER_NAME: "parameter_value"},
                    value_datetime=DEFAULT_DATETIME,
                )
            }
        )

        result = maintenance_fees_module.get_parameters(
            vault=mock_vault,
            param_fetcher_id=FETCHER_ID,
        )

        self.assertEqual(
            result,
            {PARAMETER_NAME: "parameter_value"},
        )

    @patch.object(maintenance_fees_module, "get_parameters")
    @patch.object(maintenance_fees_module.state_utils, "append_to_state")
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
        initial_parameters: dict[str, str | Decimal | datetime | None] = {
            "INITIAL_PARAM": "INITIAL_VALUE"
        }
        new_parameters: dict[str, str | Decimal | datetime | None] = {"NEW_PARAM": "NEW_VALUE"}

        mock_state = initialise_mock_state(vault=mock_vault, parameters=initial_parameters)
        mock_get_parameters.return_value = new_parameters

        mock_append_to_state.return_value = initialise_mock_state(
            vault=mock_vault,
            parameters=initial_parameters | new_parameters,
            effective_datetime=mock_state.effective_datetime,
        )

        _ = maintenance_fees_module._append_to_state(
            state=mock_state,
            fetchers_config=maintenance_fees_module.DEFAULT_MAINTENANCE_FEES_FETCHERS_CONFIG,
        )

        mock_get_parameters.assert_called_once_with(
            mock_vault,
            maintenance_fees_module.DEFAULT_MAINTENANCE_FEES_FETCHERS_CONFIG.param_fetcher_id,
        )
        mock_append_to_state.assert_called_once_with(
            state=mock_state,
            parameters=new_parameters,
            balances=mock_vault.get_balances_observation(
                fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID
            ).balances,
        )

    @patch.object(maintenance_fees_module, "_append_to_state")
    @patch.object(maintenance_fees_module.state_utils, "append_to_state")
    @pytest.mark.unit
    def test_get_scheduled_events_monthly(
        self, mock_state_utils_append_to_state: MagicMock, mock_append_to_state: MagicMock
    ):
        application_time = "12:34:56"
        day = "1"
        mock_state = initialise_mock_state(
            effective_datetime=DEFAULT_DATETIME,
            parameters={
                maintenance_fees_module.MAINTENANCE_FEE_APPLICATION_TIME_PARAM.id: application_time,
                maintenance_fees_module.MAINTENANCE_FEE_APPLICATION_DAY_PARAM.id: day,
            },
        )
        mock_state.vault.events_timezone = UTC_ZONE
        mock_state_utils_append_to_state.return_value = mock_state

        result = maintenance_fees_module.get_scheduled_events(
            state=mock_state, frequency=maintenance_fees_module.MONTHLY
        )

        expected_event = {
            maintenance_fees_module.APPLY_MONTHLY_FEE_EVENT: ScheduledEvent(
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

    @patch.object(maintenance_fees_module, "_append_to_state")
    @patch.object(maintenance_fees_module.state_utils, "append_to_state")
    @pytest.mark.unit
    def test_get_scheduled_events_annually(
        self, mock_state_utils_append_to_state: MagicMock, mock_append_to_state: MagicMock
    ):
        application_time = "12:34:56"
        day = "1"
        mock_state = initialise_mock_state(
            effective_datetime=DEFAULT_DATETIME,
            parameters={
                maintenance_fees_module.MAINTENANCE_FEE_APPLICATION_TIME_PARAM.id: application_time,
                maintenance_fees_module.MAINTENANCE_FEE_APPLICATION_DAY_PARAM.id: day,
            },
        )
        mock_state.vault.events_timezone = UTC_ZONE
        mock_state_utils_append_to_state.return_value = mock_state

        result = maintenance_fees_module.get_scheduled_events(
            state=mock_state, frequency=maintenance_fees_module.ANNUALLY
        )

        expected_event = {
            maintenance_fees_module.APPLY_ANNUAL_FEE_EVENT: ScheduledEvent(
                start_datetime=DEFAULT_DATETIME + relativedelta(years=1),
                expression=ScheduleExpression(
                    day=1,
                    hour=12,
                    minute=34,
                    second=56,
                ),
            )
        }
        self.assertEqual(result, expected_event)

    @patch.object(maintenance_fees_module.state_utils, "check_parameters_exist")
    @patch.object(maintenance_fees_module.state_utils, "append_to_state")
    @pytest.mark.unit
    def test_get_scheduled_events_returns_rejection_if_parameter_missing(
        self, mock_state_utils_append_to_state: MagicMock, mock_check_parameters_exist: MagicMock
    ):
        mock_state = initialise_mock_state()
        mock_state_utils_append_to_state.return_value = mock_state
        mock_check_parameters_exist.return_value = sentinel.rejection

        with self.assertRaises(AssertionError) as ex:
            maintenance_fees_module.get_scheduled_events(
                state=mock_state, frequency=maintenance_fees_module.MONTHLY
            )

        self.assertEqual(ex.exception.args[0], sentinel.rejection)

    @patch.object(maintenance_fees_module.state_utils, "append_to_state")
    @pytest.mark.unit
    def test_update_next_annual_schedule_execution_no_update_needed(self, mock_append_to_state):
        # Effective date is January
        mock_state = initialise_mock_state(
            effective_datetime=datetime(2026, 1, 15, tzinfo=UTC_ZONE),
            parameters={maintenance_fees_module.MAINTENANCE_FEE_APPLICATION_DAY_PARAM.id: "15"},
        )
        mock_append_to_state.return_value = mock_state

        result = maintenance_fees_module.update_next_annual_schedule_execution(mock_state)
        self.assertIsNone(result)

        # Effective date is February but day < 29
        mock_state = initialise_mock_state(
            effective_datetime=datetime(2026, 2, 28, tzinfo=UTC_ZONE),
            parameters={maintenance_fees_module.MAINTENANCE_FEE_APPLICATION_DAY_PARAM.id: "28"},
        )
        mock_append_to_state.return_value = mock_state

        result = maintenance_fees_module.update_next_annual_schedule_execution(mock_state)
        self.assertIsNone(result)

    @patch.object(maintenance_fees_module, "get_scheduled_events")
    @patch.object(maintenance_fees_module.state_utils, "append_to_state")
    @pytest.mark.unit
    def test_update_next_annual_schedule_execution_update_needed(
        self, mock_append_to_state: MagicMock, mock_get_scheduled_events: MagicMock
    ):
        mock_state = initialise_mock_state(
            effective_datetime=datetime(2024, 2, 29, tzinfo=UTC_ZONE),
            parameters={
                maintenance_fees_module.MAINTENANCE_FEE_APPLICATION_DAY_PARAM.id: "29",
                maintenance_fees_module.MAINTENANCE_FEE_APPLICATION_TIME_PARAM.id: "00:00:00",
            },
        )
        mock_append_to_state.return_value = mock_state

        mock_scheduled_event = ScheduledEvent(
            start_datetime=DEFAULT_DATETIME,
            expression=ScheduleExpression(day=29, hour=0, minute=0, second=0),
        )
        mock_get_scheduled_events.return_value = {
            maintenance_fees_module.APPLY_ANNUAL_FEE_EVENT: mock_scheduled_event
        }

        result = maintenance_fees_module.update_next_annual_schedule_execution(mock_state)

        self.assertIsNotNone(result)
        self.assertEqual(result.event_type, maintenance_fees_module.APPLY_ANNUAL_FEE_EVENT)
        self.assertEqual(result.expression, mock_scheduled_event.expression)

    @pytest.mark.unit
    def test_are_monthly_partial_payments_enabled(self):
        mock_state = initialise_mock_state(
            parameters={
                maintenance_fees_module.MONTHLY_MAINTENANCE_FEE_PARTIAL_FEE_ENABLED_PARAM.id: "True"
            }
        )
        self.assertTrue(maintenance_fees_module._are_monthly_partial_payments_enabled(mock_state))

        mock_state = initialise_mock_state(
            parameters={
                maintenance_fees_module.MONTHLY_MAINTENANCE_FEE_PARTIAL_FEE_ENABLED_PARAM.id: (
                    "False"
                )
            }
        )
        self.assertFalse(maintenance_fees_module._are_monthly_partial_payments_enabled(mock_state))
