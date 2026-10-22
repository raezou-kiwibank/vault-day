# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, call, patch, sentinel
from zoneinfo import ZoneInfo

import pytest

import feature_library.common.denomination as denomination_module
import feature_library.common.tuples as common_tuples
import feature_library.deposit.addresses as deposit_addresses

# third party
from feature_library.deposit.interest import interest_accrual

# contracts api
from contracts_api import (
    Balance,
    ParametersObservation,
    ScheduledEvent,
    ScheduleExpression,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

from tests.common.test_denomination import DEFAULT_DENOMINATION

# feature_library
from tests.utils import initialise_mock_state

DEFAULT_DATETIME = datetime(2025, 1, 1, tzinfo=ZoneInfo("UTC"))

FETCHER_ID = "fetcher_id"
PARAMETER_NAME = "parameter_name"


class InterestAccrualTest(FeatureTest):
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

        result = interest_accrual.get_parameters(
            vault=mock_vault,
            param_fetcher_id=FETCHER_ID,
        )

        self.assertEqual(
            result,
            {PARAMETER_NAME: "parameter_value"},
        )

    @patch.object(interest_accrual, "get_parameters")
    @patch.object(interest_accrual.state_utils, "append_to_state")
    @pytest.mark.unit
    def test_append_to_state(
        self,
        mock_append_to_state: MagicMock,
        mock_get_parameters: MagicMock,
    ):
        mock_vault = self.create_mock()
        initial_parameters = {"INITIAL_PARAM": "INITIAL_VALUE"}
        new_parameters = {"NEW_PARAM": "NEW_VALUE"}

        mock_state = initialise_mock_state(vault=mock_vault, parameters=initial_parameters)
        mock_get_parameters.return_value = new_parameters

        mock_append_to_state.return_value = initialise_mock_state(
            vault=mock_vault,
            parameters=initial_parameters | new_parameters,
            effective_datetime=mock_state.effective_datetime,
        )

        result = interest_accrual._append_to_state(
            state=mock_state, param_fetcher_id=sentinel.param_fetcher_id
        )

        mock_get_parameters.assert_called_once_with(mock_vault, sentinel.param_fetcher_id)
        mock_append_to_state.assert_called_once_with(
            state=mock_state,
            parameters=new_parameters,
        )

        # Check that parameters were merged correctly
        for key, value in initial_parameters.items():
            self.assertEqual(result.parameters[key], value)
        for key, value in new_parameters.items():
            self.assertEqual(result.parameters[key], value)

        self.assertEqual(result.vault, mock_vault)
        self.assertEqual(result.effective_datetime, mock_state.effective_datetime)

    @patch.object(interest_accrual, "_append_to_state")
    @pytest.mark.unit
    def test_get_scheduled_events(self, mock_append_to_state: MagicMock):
        accrual_time = "12:34:56"
        mock_state = initialise_mock_state(
            effective_datetime=DEFAULT_DATETIME,
            balances=sentinel.balances,
            parameters={interest_accrual.INTEREST_ACCRUAL_TIME_PARAM_ID: accrual_time},
        )
        mock_append_to_state.return_value = mock_state

        result = interest_accrual.get_scheduled_events(state=mock_state)

        mock_append_to_state.assert_called_once_with(
            state=mock_state,
            param_fetcher_id=interest_accrual.DEFAULT_INTEREST_ACCRUAL_FETCHERS_CONFIG.param_fetcher_id,
        )

        expected_event = {
            interest_accrual.INTEREST_ACCRUAL_EVENT_TYPE: ScheduledEvent(
                start_datetime=DEFAULT_DATETIME,
                expression=ScheduleExpression(
                    hour=12,
                    minute=34,
                    second=56,
                ),
            )
        }
        self.assertEqual(result, expected_event)

    @patch.object(interest_accrual.state_utils, "check_parameters_exist")
    @patch.object(interest_accrual, "_append_to_state")
    @pytest.mark.unit
    def test_get_scheduled_events_returns_rejection_if_parameter_missing(
        self, mock_append_to_state: MagicMock, mock_check_parameters_exist: MagicMock
    ):
        mock_state = initialise_mock_state()
        mock_append_to_state.return_value = mock_state
        mock_check_parameters_exist.return_value = sentinel.rejection

        with self.assertRaises(AssertionError) as ex:
            interest_accrual.get_scheduled_events(state=mock_state)

        self.assertEqual(ex.exception.args[0], sentinel.rejection)
        mock_check_parameters_exist.assert_called_once_with(
            state=mock_state,
            param_ids={
                interest_accrual.DEFAULT_INTEREST_ACCRUAL_FETCHERS_CONFIG.interest_accrual_time_param_id
            },
        )

    @patch.object(interest_accrual.state_utils, "check_parameters_exist")
    @patch.object(interest_accrual, "_append_to_state")
    @pytest.mark.unit
    def test_schedule_logic_raises_assertion_error_if_parameter_missing(
        self, mock_append_to_state: MagicMock, mock_check_parameters_exist: MagicMock
    ):
        mock_state = initialise_mock_state()
        mock_append_to_state.return_value = mock_state
        mock_check_parameters_exist.return_value = sentinel.rejection

        with self.assertRaises(AssertionError) as ex:
            interest_accrual.schedule_logic(state=mock_state, interest_types=[])

        self.assertEqual(ex.exception.args[0], sentinel.rejection)
        mock_check_parameters_exist.assert_called_once_with(
            state=mock_state,
            param_ids={
                interest_accrual.DEFAULT_INTEREST_ACCRUAL_FETCHERS_CONFIG.denomination_param_id,
                interest_accrual.DEFAULT_INTEREST_ACCRUAL_FETCHERS_CONFIG.days_in_year_param_id,
                interest_accrual.DEFAULT_INTEREST_ACCRUAL_FETCHERS_CONFIG.rounding_precision_param_id,
                interest_accrual.DEFAULT_INTEREST_ACCRUAL_FETCHERS_CONFIG.accrued_payable_account_param_id,
                interest_accrual.DEFAULT_INTEREST_ACCRUAL_FETCHERS_CONFIG.accrued_receivable_account_param_id,
            },
        )

    @patch.object(interest_accrual.accrual_utils, "create_payable_accrual_custom_instruction")
    @patch.object(interest_accrual.deposit_interest_accrual_utils, "get_accrual_capital")
    @patch.object(interest_accrual, "_append_to_state")
    @pytest.mark.unit
    def test_schedule_logic(
        self,
        mock_append_to_state: MagicMock,
        mock_get_accrual_capital: MagicMock,
        mock_accrual_ci: MagicMock,
    ):
        mock_state = initialise_mock_state(
            effective_datetime=DEFAULT_DATETIME,
            balances=sentinel.balances,
            parameters={
                denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
                interest_accrual.DAYS_IN_YEAR_PARAM_ID: "365",
                interest_accrual.ACCRUAL_PRECISION_PARAM_ID: Decimal("5"),
                interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID: "payable_acc",
                interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID: "receivable_acc",
            },
        )
        mock_append_to_state.return_value = mock_state
        mock_get_accrual_capital.return_value = Balance(
            credit=Decimal(1000), debit=Decimal(0), net=Decimal(1000)
        )

        mock_interest_type = MagicMock()
        mock_interest_type.get_interest_rate.return_value = common_tuples.InterestRateTuple(
            interest_rate_param_value='{"0": "0.01"}',
            interest_type=common_tuples.INTEREST_TYPE_TIERED,
        )
        mock_interest_type.get_accrual_amount.return_value = common_tuples.AccrualDetail(
            accrual_amount=Decimal("1.5"),
            description="test description",
        )
        mock_interest_type.get_accrual_payable_customer_address.return_value = (
            deposit_addresses.ACCRUED_INTEREST_PAYABLE
        )
        mock_interest_type.get_accrual_payable_internal_account.return_value = "payable_acc"

        mock_accrual_ci.return_value = [sentinel.instruction]

        result = interest_accrual.schedule_logic(
            state=mock_state,
            interest_types=[
                interest_accrual.InterestTypeConfig(
                    interest_type=mock_interest_type, fetchers_config=None
                )
            ],
        )

        mock_append_to_state.assert_called_once_with(
            state=mock_state,
            param_fetcher_id=interest_accrual.DEFAULT_INTEREST_ACCRUAL_FETCHERS_CONFIG.param_fetcher_id,
        )
        mock_get_accrual_capital.assert_called_once_with(
            state=mock_state, balances=sentinel.balances
        )
        mock_interest_type.get_interest_rate.assert_called_once_with(
            state=mock_state, fetchers_config=None
        )
        mock_interest_type.get_accrual_amount.assert_called_once_with(
            effective_balance=Balance(
                credit=Decimal("1000"), debit=Decimal("0"), net=Decimal("1000")
            ),
            effective_datetime=DEFAULT_DATETIME,
            interest_rates='{"0": "0.01"}',
            days_in_year="365",
            precision=5,
            state=mock_state,
            fetchers_config=None,
        )
        mock_interest_type.get_accrual_payable_customer_address.assert_called_once_with()
        mock_interest_type.get_accrual_payable_internal_account.assert_called_once_with(
            state=mock_state,
        )
        mock_accrual_ci.assert_called_once_with(
            customer_account=mock_state.vault.account_id,
            customer_address=deposit_addresses.ACCRUED_INTEREST_PAYABLE,
            denomination=DEFAULT_DENOMINATION,
            amount=Decimal("1.5"),
            internal_account="payable_acc",
            instruction_details={
                "description": "test description",
                "event": interest_accrual.INTEREST_ACCRUAL_EVENT_TYPE,
                "gl_impacted": "True",
                "account_type": "",
            },
        )
        self.assertEqual(result, [sentinel.instruction])

    @patch.object(interest_accrual.deposit_interest_accrual_utils, "get_accrual_capital")
    @patch.object(interest_accrual, "_append_to_state")
    @pytest.mark.unit
    def test_schedule_logic_skips_if_rate_is_none(
        self,
        mock_append_to_state: MagicMock,
        mock_get_accrual_capital: MagicMock,
    ):
        mock_state = initialise_mock_state(
            parameters={
                denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
                interest_accrual.DAYS_IN_YEAR_PARAM_ID: "365",
                interest_accrual.ACCRUAL_PRECISION_PARAM_ID: Decimal("5"),
                interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID: "payable_acc",
                interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID: "receivable_acc",
            },
        )
        mock_append_to_state.return_value = mock_state
        mock_get_accrual_capital.return_value = Balance(
            credit=Decimal(1000), debit=Decimal(0), net=Decimal(1000)
        )

        mock_interest_type = MagicMock()
        mock_interest_type.get_interest_rate.return_value = common_tuples.InterestRateTuple(
            interest_rate_param_value=None, interest_type=common_tuples.INTEREST_TYPE_FLAT
        )

        result = interest_accrual.schedule_logic(
            state=mock_state,
            interest_types=[
                interest_accrual.InterestTypeConfig(
                    interest_type=mock_interest_type, fetchers_config=None
                )
            ],
        )

        self.assertEqual(result, [])

    @patch.object(interest_accrual.deposit_interest_accrual_utils, "get_accrual_capital")
    @patch.object(interest_accrual, "_append_to_state")
    @pytest.mark.unit
    def test_schedule_logic_filters_interest_by_balance_direction(
        self,
        mock_append_to_state: MagicMock,
        mock_get_accrual_capital: MagicMock,
    ):
        mock_state = initialise_mock_state(
            parameters={
                denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
                interest_accrual.DAYS_IN_YEAR_PARAM_ID: "365",
                interest_accrual.ACCRUAL_PRECISION_PARAM_ID: Decimal("5"),
                interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID: "payable_acc",
                interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID: "receivable_acc",
            },
        )
        mock_append_to_state.return_value = mock_state

        # Case 1: Overdraft interest on positive balance -> Skip
        mock_get_accrual_capital.return_value = Balance(
            credit=Decimal(100), debit=Decimal(0), net=Decimal(100)
        )

        overdraft_type = MagicMock()
        overdraft_type.get_interest_rate.return_value = common_tuples.InterestRateTuple(
            interest_rate_param_value=Decimal("0.1"),
            interest_type=common_tuples.INTEREST_TYPE_OVERDRAFT,
        )
        overdraft_type.get_accrual_amount.return_value = common_tuples.AccrualDetail(
            accrual_amount=Decimal("0"),
            description="",
        )

        # Case 2: Standard interest on negative balance -> Skip
        mock_get_accrual_capital.return_value = Balance(
            credit=Decimal(0), debit=Decimal(100), net=Decimal(-100)
        )
        standard_type = MagicMock()
        standard_type.get_interest_rate.return_value = common_tuples.InterestRateTuple(
            interest_rate_param_value=Decimal("0.05"),
            interest_type=common_tuples.INTEREST_TYPE_FLAT,
        )
        standard_type.get_accrual_amount.return_value = common_tuples.AccrualDetail(
            accrual_amount=Decimal("0"), description=""
        )

        result_1 = interest_accrual.schedule_logic(
            state=mock_state,
            interest_types=[
                interest_accrual.InterestTypeConfig(
                    interest_type=overdraft_type, fetchers_config=None
                )
            ],
        )
        result_2 = interest_accrual.schedule_logic(
            state=mock_state,
            interest_types=[
                interest_accrual.InterestTypeConfig(
                    interest_type=standard_type, fetchers_config=None
                )
            ],
        )

        self.assertEqual(result_1, [])
        self.assertEqual(result_2, [])

    @patch.object(interest_accrual.accrual_utils, "create_receivable_accrual_custom_instruction")
    @patch.object(interest_accrual.deposit_interest_accrual_utils, "get_accrual_capital")
    @patch.object(interest_accrual, "_append_to_state")
    @pytest.mark.unit
    def test_schedule_logic_handles_negative_accrual(
        self,
        mock_append_to_state: MagicMock,
        mock_get_accrual_capital: MagicMock,
        mock_accrual_ci: MagicMock,
    ):
        mock_state = initialise_mock_state(
            parameters={
                denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
                interest_accrual.DAYS_IN_YEAR_PARAM_ID: "365",
                interest_accrual.ACCRUAL_PRECISION_PARAM_ID: Decimal("5"),
                interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID: "payable_acc",
                interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID: "receivable_acc",
            },
        )
        mock_append_to_state.return_value = mock_state
        mock_get_accrual_capital.return_value = Balance(
            credit=Decimal(1000), debit=Decimal(0), net=Decimal(1000)
        )

        mock_interest_type = MagicMock()
        mock_interest_type.get_interest_rate.return_value = common_tuples.InterestRateTuple(
            interest_rate_param_value=Decimal("-0.01"),
            interest_type=common_tuples.INTEREST_TYPE_FLAT,
        )
        # Return a negative accrual amount (e.g., negative interest rate)
        mock_interest_type.get_accrual_amount.return_value = common_tuples.AccrualDetail(
            accrual_amount=Decimal("-1.5"),
            description="negative accrual description",
        )
        mock_interest_type.get_accrual_receivable_customer_address.return_value = (
            deposit_addresses.ACCRUED_INTEREST_RECEIVABLE
        )
        mock_interest_type.get_accrual_receivable_internal_account.return_value = "receivable_acc"

        interest_accrual.schedule_logic(
            state=mock_state,
            interest_types=[
                interest_accrual.InterestTypeConfig(
                    interest_type=mock_interest_type, fetchers_config=None
                )
            ],
        )

        # Verify it uses the RECEIVABLE address and account
        mock_interest_type.get_accrual_amount.assert_called_once_with(
            effective_balance=Balance(credit=Decimal(1000), debit=Decimal(0), net=Decimal(1000)),
            effective_datetime=mock_state.effective_datetime,
            interest_rates=Decimal("-0.01"),
            days_in_year="365",
            precision=5,
            state=mock_state,
            fetchers_config=None,
        )
        mock_interest_type.get_accrual_receivable_customer_address.assert_called_once_with()
        mock_interest_type.get_accrual_receivable_internal_account.assert_called_once_with(
            state=mock_state,
        )
        mock_accrual_ci.assert_called_once_with(
            customer_account=mock_state.vault.account_id,
            customer_address=deposit_addresses.ACCRUED_INTEREST_RECEIVABLE,
            denomination=DEFAULT_DENOMINATION,
            amount=Decimal("1.5"),
            internal_account="receivable_acc",
            instruction_details={
                "description": "negative accrual description",
                "event": interest_accrual.INTEREST_ACCRUAL_EVENT_TYPE,
                "gl_impacted": "True",
                "account_type": "",
            },
        )

    @patch.object(interest_accrual.accrual_utils, "create_payable_accrual_custom_instruction")
    @patch.object(interest_accrual.deposit_interest_accrual_utils, "get_accrual_capital")
    @patch.object(interest_accrual, "_append_to_state")
    @pytest.mark.unit
    def test_schedule_logic_with_decimal_rate(
        self,
        mock_append_to_state: MagicMock,
        mock_get_accrual_capital: MagicMock,
        mock_accrual_ci: MagicMock,
    ):
        # Setup
        mock_state = initialise_mock_state(
            effective_datetime=DEFAULT_DATETIME,
            balances=sentinel.balances,
            parameters={
                denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
                interest_accrual.DAYS_IN_YEAR_PARAM_ID: "365",
                interest_accrual.ACCRUAL_PRECISION_PARAM_ID: Decimal("5"),
                interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID: "payable_acc",
                interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID: "receivable_acc",
            },
        )
        mock_append_to_state.return_value = mock_state
        mock_get_accrual_capital.return_value = Balance(
            credit=Decimal(1000), debit=Decimal(0), net=Decimal(1000)
        )

        mock_interest_type = MagicMock()
        mock_interest_type.get_interest_rate.return_value = common_tuples.InterestRateTuple(
            interest_rate_param_value=Decimal("0.01"),
            interest_type=common_tuples.INTEREST_TYPE_FLAT,
        )
        mock_interest_type.get_accrual_amount.return_value = common_tuples.AccrualDetail(
            accrual_amount=Decimal("1.5"),
            description="decimal rate description",
        )
        mock_interest_type.get_accrual_payable_customer_address.return_value = (
            deposit_addresses.ACCRUED_INTEREST_PAYABLE
        )
        mock_interest_type.get_accrual_payable_internal_account.return_value = "payable_acc"

        mock_accrual_ci.return_value = [sentinel.instruction]

        # Run
        result = interest_accrual.schedule_logic(
            state=mock_state,
            interest_types=[
                interest_accrual.InterestTypeConfig(
                    interest_type=mock_interest_type, fetchers_config=None
                )
            ],
        )

        # Verify
        mock_interest_type.get_accrual_amount.assert_called_once_with(
            effective_balance=Balance(
                credit=Decimal("1000"), debit=Decimal("0"), net=Decimal("1000")
            ),
            effective_datetime=DEFAULT_DATETIME,
            interest_rates=Decimal("0.01"),
            days_in_year="365",
            precision=5,
            state=mock_state,
            fetchers_config=None,
        )
        mock_interest_type.get_accrual_payable_customer_address.assert_called_once_with()
        mock_interest_type.get_accrual_payable_internal_account.assert_called_once_with(
            state=mock_state,
        )
        self.assertEqual(result, [sentinel.instruction])

    @patch.object(interest_accrual.accrual_utils, "create_payable_accrual_custom_instruction")
    @patch.object(interest_accrual.deposit_interest_accrual_utils, "get_accrual_capital")
    @patch.object(interest_accrual, "_append_to_state")
    @pytest.mark.unit
    def test_schedule_logic_with_multiple_interest_types(
        self,
        mock_append_to_state: MagicMock,
        mock_get_accrual_capital: MagicMock,
        mock_accrual_ci: MagicMock,
    ):
        mock_state = initialise_mock_state(
            parameters={
                denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
                interest_accrual.DAYS_IN_YEAR_PARAM_ID: "365",
                interest_accrual.ACCRUAL_PRECISION_PARAM_ID: Decimal("5"),
                interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID: "payable_acc",
                interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID: "receivable_acc",
            },
        )
        mock_append_to_state.return_value = mock_state
        mock_get_accrual_capital.return_value = Balance(
            credit=Decimal(1000), debit=Decimal(0), net=Decimal(1000)
        )

        type_1 = MagicMock()
        type_1.get_interest_rate.return_value = common_tuples.InterestRateTuple(
            interest_rate_param_value=Decimal("0.01"),
            interest_type=common_tuples.INTEREST_TYPE_FLAT,
        )
        type_1.get_accrual_amount.return_value = common_tuples.AccrualDetail(
            accrual_amount=Decimal("1.0"), description="feature 1 description"
        )
        type_1.get_accrual_payable_customer_address.return_value = (
            deposit_addresses.ACCRUED_INTEREST_PAYABLE
        )
        type_1.get_accrual_payable_internal_account.return_value = "payable_acc"

        type_2 = MagicMock()
        type_2.get_interest_rate.return_value = common_tuples.InterestRateTuple(
            interest_rate_param_value=Decimal("0.02"),
            interest_type=common_tuples.INTEREST_TYPE_FLAT,
        )
        type_2.get_accrual_amount.return_value = common_tuples.AccrualDetail(
            accrual_amount=Decimal("2.0"), description="feature 2 description"
        )
        type_2.get_accrual_payable_customer_address.return_value = (
            deposit_addresses.ACCRUED_INTEREST_PAYABLE
        )
        type_2.get_accrual_payable_internal_account.return_value = "payable_acc"

        mock_accrual_ci.side_effect = [[sentinel.ci_1], [sentinel.ci_2]]

        result = interest_accrual.schedule_logic(
            state=mock_state,
            interest_types=[
                interest_accrual.InterestTypeConfig(interest_type=type_1, fetchers_config=None),
                interest_accrual.InterestTypeConfig(interest_type=type_2, fetchers_config=None),
            ],
        )

        self.assertEqual(result, [sentinel.ci_1, sentinel.ci_2])
        mock_accrual_ci.assert_has_calls(
            [
                call(
                    customer_account=mock_state.vault.account_id,
                    customer_address=deposit_addresses.ACCRUED_INTEREST_PAYABLE,
                    denomination=DEFAULT_DENOMINATION,
                    amount=Decimal("1.0"),
                    internal_account="payable_acc",
                    instruction_details={
                        "description": "feature 1 description",
                        "event": interest_accrual.INTEREST_ACCRUAL_EVENT_TYPE,
                        "gl_impacted": "True",
                        "account_type": "",
                    },
                ),
                call(
                    customer_account=mock_state.vault.account_id,
                    customer_address=deposit_addresses.ACCRUED_INTEREST_PAYABLE,
                    denomination=DEFAULT_DENOMINATION,
                    amount=Decimal("2.0"),
                    internal_account="payable_acc",
                    instruction_details={
                        "description": "feature 2 description",
                        "event": interest_accrual.INTEREST_ACCRUAL_EVENT_TYPE,
                        "gl_impacted": "True",
                        "account_type": "",
                    },
                ),
            ]
        )
