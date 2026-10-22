# standard libs
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Callable
from unittest.mock import MagicMock, call, patch, sentinel
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

# features
import feature_library.common.addresses as common_addresses
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.repayments.overpayment_allowance as overpayment_allowance

# contracts api
from contracts_api import (
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    CustomInstruction,
    ParameterTimeseries,
    Phase,
    ScheduledEvent,
    ScheduleSkip,
    SmartContractEventType,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest
from inception_sdk.test_framework.contracts.unit.contracts_api_sentinels import (
    SentinelBalance,
    SentinelBalancesObservation,
    SentinelPosting,
)

from tests.utils import initialise_mock_state

# We define these here as they are used in the feature but missing from the addresses module
if not hasattr(lending_addresses, "ALL_OUTSTANDING"):
    lending_addresses.ALL_OUTSTANDING = sentinel.ALL_OUTSTANDING  # type: ignore
if not hasattr(lending_addresses, "REPAYMENT_HIERARCHY"):
    lending_addresses.REPAYMENT_HIERARCHY = sentinel.REPAYMENT_HIERARCHY  # type: ignore


DEFAULT_DATE = datetime(2020, 1, 2, 3, 4, 5, 6, tzinfo=ZoneInfo("UTC"))

OVERPAYMENT_COORDINATE = BalanceCoordinate(
    account_address=overpayment_allowance.overpayment.OVERPAYMENT_ADDRESS,
    asset=DEFAULT_ASSET,
    denomination=sentinel.denomination,
    phase=Phase.COMMITTED,
)

PRINCIPAL_COORDINATE = BalanceCoordinate(
    account_address=lending_addresses.PRINCIPAL,
    asset=DEFAULT_ASSET,
    denomination=sentinel.denomination,
    phase=Phase.COMMITTED,
)


@pytest.mark.unit
class OverpaymentTest(FeatureTest):
    maxDiff = None


@pytest.mark.unit
class EventTypesTest(FeatureTest):
    def test_event_types(self):
        self.assertListEqual(
            overpayment_allowance.event_types(account_type="some_account"),
            [
                SmartContractEventType(
                    name=overpayment_allowance.CHECK_OVERPAYMENT_ALLOWANCE_EVENT,
                    scheduler_tag_ids=[
                        f"SOME_ACCOUNT_{overpayment_allowance.CHECK_OVERPAYMENT_ALLOWANCE_EVENT}"
                        "_AST"
                    ],
                )
            ],
        )


@pytest.mark.unit
@patch.object(overpayment_allowance.date_and_time, "parse_time_str")
class ScheduledEventsTest(FeatureTest):
    def test_scheduled_event_runs_on_yearly_basis(self, mock_parse_time_str: MagicMock):
        mock_parse_time_str.return_value = MagicMock(hour=0, minute=0, second=0)

        parameters = {
            overpayment_allowance.CHECK_OVERPAYMENT_ALLOWANCE_TIME_PARAM_ID: "00:00:00",
        }
        mock_vault = self.create_mock(
            parameters_observation_fetchers_mapping={
                overpayment_allowance.OVERPAYMENT_ALLOWANCE_PARAM_POF_ID: MagicMock(
                    parameters=parameters
                )
            }
        )

        mock_state = initialise_mock_state(
            parameters=parameters,
            vault=mock_vault,
        )

        scheduled_events = overpayment_allowance.scheduled_events(
            state=mock_state, allowance_period_start_datetime=DEFAULT_DATE
        )

        self.assertDictEqual(
            scheduled_events,
            {
                overpayment_allowance.CHECK_OVERPAYMENT_ALLOWANCE_EVENT: ScheduledEvent(
                    start_datetime=datetime(2021, 1, 1, 23, 59, 59, tzinfo=ZoneInfo("UTC")),
                    expression=overpayment_allowance.ScheduleExpression(
                        year=None,
                        month="1",
                        day="2",
                        hour="0",
                        minute="0",
                        second="0",
                    ),
                )
            },
        )

        mock_parse_time_str.assert_called_once_with(time_str="00:00:00")


@pytest.mark.unit
class HandleAllowanceHelpersTest(FeatureTest):
    @patch.object(overpayment_allowance.utils, "round_decimal")
    @patch.object(overpayment_allowance.balance_utils, "balance_at_coordinates")
    def test_get_allowance_for_period(
        self, mock_balance_at_coordinates: MagicMock, mock_round_decimal: MagicMock
    ):
        mock_balance_at_coordinates.return_value = Decimal("1000")
        mock_round_decimal.return_value = sentinel.rounded_allowance

        self.assertEqual(
            overpayment_allowance.get_allowance_for_period(
                start_of_period_balances=BalanceDefaultDict(lambda: Balance()),
                allowance_percentage=Decimal("0.05"),
                denomination=sentinel.denomination,
            ),
            sentinel.rounded_allowance,
        )

        mock_balance_at_coordinates.assert_called_once_with(
            balances=BalanceDefaultDict(lambda: Balance()),
            address=lending_addresses.PRINCIPAL,
            denomination=sentinel.denomination,
        )
        mock_round_decimal.assert_called_once_with(amount=Decimal("50"), decimal_places=2)

    @patch.object(overpayment_allowance.utils, "round_decimal")
    @patch.object(overpayment_allowance.balance_utils, "balance_at_coordinates")
    def test_get_allowance_for_period_custom_address(
        self, mock_balance_at_coordinates: MagicMock, mock_round_decimal: MagicMock
    ):
        mock_balance_at_coordinates.return_value = Decimal("1000")
        mock_round_decimal.return_value = sentinel.rounded_allowance

        self.assertEqual(
            overpayment_allowance.get_allowance_for_period(
                start_of_period_balances=BalanceDefaultDict(lambda: Balance()),
                allowance_percentage=Decimal("0.05"),
                denomination=sentinel.denomination,
                principal_address="CUSTOM_PRINCIPAL",
            ),
            sentinel.rounded_allowance,
        )

        mock_balance_at_coordinates.assert_called_once_with(
            balances=BalanceDefaultDict(lambda: Balance()),
            address="CUSTOM_PRINCIPAL",
            denomination=sentinel.denomination,
        )
        mock_round_decimal.assert_called_once_with(amount=Decimal("50"), decimal_places=2)

    @patch.object(overpayment_allowance.balance_utils, "net_debit")
    @patch.object(overpayment_allowance.balance_utils, "get_current_net_balance")
    def test_get_allowance_usage(
        self, mock_get_current_net_balance: MagicMock, mock_net_debit: MagicMock
    ):
        mock_get_current_net_balance.side_effect = lambda balances, address, denomination, phase: (
            SentinelBalance("start")
            if balances == sentinel.start_of_period_balances
            else SentinelBalance("end")
        )
        mock_net_debit.side_effect = lambda bal: (
            Decimal("100") if bal == SentinelBalance("start") else Decimal("200")
        )

        self.assertEqual(
            overpayment_allowance.get_allowance_usage(
                start_of_period_balances=sentinel.start_of_period_balances,
                end_of_period_balances=sentinel.end_of_period_balances,
                denomination=sentinel.denomination,
            ),
            Decimal("100"),
        )

        mock_get_current_net_balance.assert_has_calls(
            [
                call(
                    balances=sentinel.end_of_period_balances,
                    address=overpayment_allowance.overpayment.OVERPAYMENT_ADDRESS,
                    denomination=sentinel.denomination,
                    phase=Phase.COMMITTED,
                ),
                call(
                    balances=sentinel.start_of_period_balances,
                    address=overpayment_allowance.overpayment.OVERPAYMENT_ADDRESS,
                    denomination=sentinel.denomination,
                    phase=Phase.COMMITTED,
                ),
            ]
        )
        mock_net_debit.assert_has_calls(
            [
                call(bal=SentinelBalance("end")),
                call(bal=SentinelBalance("start")),
            ]
        )

    @patch.object(overpayment_allowance.balance_utils, "net_debit")
    @patch.object(overpayment_allowance.balance_utils, "get_current_net_balance")
    def test_get_allowance_usage_custom_address(
        self, mock_get_current_net_balance: MagicMock, mock_net_debit: MagicMock
    ):
        mock_get_current_net_balance.side_effect = lambda balances, address, denomination, phase: (
            SentinelBalance("start")
            if balances == sentinel.start_of_period_balances
            else SentinelBalance("end")
        )
        mock_net_debit.side_effect = lambda bal: (
            Decimal("100") if bal == SentinelBalance("start") else Decimal("200")
        )

        self.assertEqual(
            overpayment_allowance.get_allowance_usage(
                start_of_period_balances=sentinel.start_of_period_balances,
                end_of_period_balances=sentinel.end_of_period_balances,
                denomination=sentinel.denomination,
                overpayment_address="CUSTOM_OVERPAYMENT",
            ),
            Decimal("100"),
        )

    @patch.object(overpayment_allowance.balance_utils, "net_debit")
    @patch.object(overpayment_allowance.balance_utils, "get_current_net_balance")
    def test_get_allowance_usage_at_least_0(
        self, mock_get_current_net_balance: MagicMock, mock_net_debit: MagicMock
    ):
        mock_get_current_net_balance.side_effect = lambda balances, address, denomination, phase: (
            SentinelBalance("start")
            if balances == sentinel.start_of_period_balances
            else SentinelBalance("end")
        )
        mock_net_debit.side_effect = lambda bal: (
            Decimal("100") if bal == SentinelBalance("start") else Decimal("0")
        )

        self.assertEqual(
            overpayment_allowance.get_allowance_usage(
                start_of_period_balances=sentinel.start_of_period_balances,
                end_of_period_balances=sentinel.end_of_period_balances,
                denomination=sentinel.denomination,
            ),
            Decimal("0"),
        )

    @patch.object(overpayment_allowance.utils, "round_decimal")
    def test_get_allowance_fee(self, mock_round_decimal: MagicMock):
        mock_round_decimal.return_value = sentinel.rounded_fee

        self.assertEqual(
            overpayment_allowance.get_allowance_usage_fee(
                allowance=Decimal("0"),
                used_allowance=Decimal("1"),
                overpayment_allowance_fee_percentage=Decimal("0.01"),
            ),
            sentinel.rounded_fee,
        )

        mock_round_decimal.assert_called_once_with(Decimal("0.01"), decimal_places=2)

    @patch.object(overpayment_allowance.utils, "round_decimal")
    def test_get_allowance_fee_zero_if_allowance_not_exceeded(self, mock_round_decimal: MagicMock):
        self.assertEqual(
            overpayment_allowance.get_allowance_usage_fee(
                allowance=Decimal("1"),
                used_allowance=Decimal("0"),
                overpayment_allowance_fee_percentage=Decimal("0.01"),
            ),
            Decimal("0"),
        )

        mock_round_decimal.assert_not_called()


@patch.object(overpayment_allowance.posting_utils, "standard_instruction_details")
@patch.object(overpayment_allowance.fees, "fee_custom_instruction")
@patch.object(overpayment_allowance, "get_allowance_usage_fee")
@patch.object(overpayment_allowance, "get_allowance_usage")
@patch.object(overpayment_allowance, "get_allowance_for_period")
@patch.object(overpayment_allowance, "set_overpayment_allowance_for_period")
@pytest.mark.unit
class HandleAllowanceUsageTest(FeatureTest):
    standard_params = {
        overpayment_allowance.denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination,
        overpayment_allowance.OVERPAYMENT_ALLOWANCE_PERCENTAGE_PARAM_ID: (
            sentinel.overpayment_percentage
        ),
        overpayment_allowance.OVERPAYMENT_ALLOWANCE_FEE_PERCENTAGE_PARAM_ID: (
            sentinel.allowance_fee_percentage
        ),
        overpayment_allowance.OVERPAYMENT_ALLOWANCE_FEE_INCOME_ACCOUNT_PARAM_ID: (
            sentinel.allowance_fee_income_account
        ),
    }

    @patch.object(overpayment_allowance.balance_utils, "balance_at_coordinates")
    def test_allowance_fee_charged(
        self,
        mock_balance_at_coordinates: MagicMock,
        mock_set_overpayment_allowance_for_period: MagicMock,
        mock_get_allowance_for_period: MagicMock,
        mock_get_allowance_usage: MagicMock,
        mock_get_allowance_usage_fee: MagicMock,
        mock_fee_custom_instruction: MagicMock,
        mock_standard_instruction_details: MagicMock,
    ):
        mock_get_allowance_for_period.return_value = sentinel.allowance
        mock_get_allowance_usage.return_value = sentinel.used_allowance
        mock_get_allowance_usage_fee.return_value = Decimal("10")
        mock_fee_custom_instruction.return_value = [sentinel.fee_custom_instruction]
        mock_balance_at_coordinates.return_value = (
            sentinel.remaining_overpayment_allowance_tracker_balance
        )
        mock_set_overpayment_allowance_for_period.return_value = [
            sentinel.set_overpayment_allowance
        ]
        mock_standard_instruction_details.return_value = {"sentinel": "details"}

        eod_observation = SentinelBalancesObservation("eod")
        one_year_observation = SentinelBalancesObservation("one_year")
        mock_vault = self.create_mock(
            balances_observation_fetchers_mapping={
                overpayment_allowance.EOD_OVERPAYMENT_ALLOWANCE_BOF_ID: (  # type: ignore
                    eod_observation
                ),
                overpayment_allowance.ONE_YEAR_OVERPAYMENT_ALLOWANCE_BOF_ID: (  # type: ignore
                    one_year_observation
                ),
            },
            parameters_observation_fetchers_mapping={
                overpayment_allowance.OVERPAYMENT_ALLOWANCE_PARAM_POF_ID: MagicMock(
                    parameters=HandleAllowanceUsageTest.standard_params
                )
            },
        )

        mock_state = initialise_mock_state(
            parameters=HandleAllowanceUsageTest.standard_params,
            vault=mock_vault,
            effective_datetime=DEFAULT_DATE,
        )

        result = overpayment_allowance.handle_allowance_usage(mock_state, sentinel.account_type)

        self.assertListEqual(
            result, [sentinel.set_overpayment_allowance, sentinel.fee_custom_instruction]
        )

        mock_get_allowance_for_period.assert_has_calls(
            [
                call(
                    start_of_period_balances=sentinel.balances_eod,
                    allowance_percentage=sentinel.overpayment_percentage,
                    denomination=sentinel.denomination,
                ),
                call(
                    start_of_period_balances=sentinel.balances_one_year,
                    allowance_percentage=sentinel.overpayment_percentage,
                    denomination=sentinel.denomination,
                ),
            ]
        )
        mock_get_allowance_usage.assert_called_once_with(
            start_of_period_balances=sentinel.balances_one_year,
            end_of_period_balances=sentinel.balances_eod,
            denomination=sentinel.denomination,
        )
        mock_get_allowance_usage_fee.assert_called_once_with(
            used_allowance=sentinel.used_allowance,
            allowance=sentinel.allowance,
            overpayment_allowance_fee_percentage=sentinel.allowance_fee_percentage,
        )
        mock_fee_custom_instruction.assert_called_once_with(
            customer_account_id=mock_vault.account_id,
            denomination=sentinel.denomination,
            amount=Decimal("10"),
            internal_account=sentinel.allowance_fee_income_account,
            customer_account_address=common_addresses.PENALTIES,
            instruction_details={"sentinel": "details"},
        )
        mock_balance_at_coordinates.assert_called_once_with(
            balances=sentinel.balances_eod,
            address=overpayment_allowance.REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER,
            denomination=sentinel.denomination,
        )
        mock_set_overpayment_allowance_for_period.assert_called_once_with(
            current_overpayment_allowance=sentinel.remaining_overpayment_allowance_tracker_balance,
            updated_overpayment_allowance=sentinel.allowance,
            denomination=sentinel.denomination,
            account_id=mock_vault.account_id,
        )

    @patch.object(overpayment_allowance, "get_start_of_current_allowance_period")
    def test_allowance_fee_charged_adhoc(
        self,
        mock_get_start_of_current_allowance_period: MagicMock,
        mock_set_overpayment_allowance_for_period: MagicMock,
        mock_get_allowance_for_period: MagicMock,
        mock_get_allowance_usage: MagicMock,
        mock_get_allowance_usage_fee: MagicMock,
        mock_fee_custom_instruction: MagicMock,
        mock_standard_instruction_details: MagicMock,
    ):
        start_of_period = datetime(2020, 1, 2, 3, 4, 5, 6, tzinfo=ZoneInfo("UTC"))
        effective_datetime = datetime(2020, 4, 5, 6, 7, 8, 9, tzinfo=ZoneInfo("UTC"))

        mock_get_allowance_for_period.return_value = sentinel.allowance
        mock_get_allowance_usage.return_value = sentinel.used_allowance
        mock_get_allowance_usage_fee.return_value = Decimal("10")
        mock_fee_custom_instruction.return_value = [sentinel.fee_custom_instruction]
        mock_set_overpayment_allowance_for_period.return_value = []
        mock_standard_instruction_details.return_value = {"sentinel": "details"}
        mock_get_start_of_current_allowance_period.return_value = start_of_period
        overpayment_balance_ts = MagicMock()
        overpayment_balance_ts.at.side_effect = lambda at_datetime: (
            SentinelBalance("start_of_period_overpayment")
            if at_datetime == start_of_period
            else SentinelBalance("effective_datetime_overpayment")
        )

        principal_balance_ts = MagicMock()
        principal_balance_ts.at.side_effect = lambda at_datetime: (
            SentinelBalance("start_of_period_principal")
            if at_datetime == start_of_period
            else SentinelBalance("effective_datetime_principal")
        )

        expected_start_of_period_balances = BalanceDefaultDict(
            mapping={
                OVERPAYMENT_COORDINATE: SentinelBalance("start_of_period_overpayment"),
                PRINCIPAL_COORDINATE: SentinelBalance("start_of_period_principal"),
            }
        )
        expected_end_of_period_balances = BalanceDefaultDict(
            mapping={
                OVERPAYMENT_COORDINATE: SentinelBalance("effective_datetime_overpayment"),
                PRINCIPAL_COORDINATE: SentinelBalance("effective_datetime_principal"),
            }
        )

        balances_interval_fetchers_mapping = {
            overpayment_allowance.ONE_YEAR_OVERPAYMENT_ALLOWANCE_BIF_ID: defaultdict(  # noqa: E501
                None,
                {
                    OVERPAYMENT_COORDINATE: overpayment_balance_ts,
                    PRINCIPAL_COORDINATE: principal_balance_ts,
                },
            )
        }

        mock_vault = self.create_mock(
            balances_interval_fetchers_mapping=balances_interval_fetchers_mapping,
            last_scheduled_event_datetimes_observation_mapping={
                overpayment_allowance.OVERPAYMENT_ALLOWANCE_LAST_EXECUTION_SOF_ID: MagicMock(  # noqa: E501
                    last_scheduled_event_datetimes={
                        overpayment_allowance.CHECK_OVERPAYMENT_ALLOWANCE_EVENT: sentinel.last_exec_time  # noqa: E501
                    }
                )
            },
            parameters_observation_fetchers_mapping={
                overpayment_allowance.OVERPAYMENT_ALLOWANCE_PARAM_POF_ID: MagicMock(
                    parameters=HandleAllowanceUsageTest.standard_params
                )
            },
        )

        mock_state = initialise_mock_state(
            parameters=HandleAllowanceUsageTest.standard_params,
            vault=mock_vault,
            effective_datetime=effective_datetime,
        )

        result = overpayment_allowance.handle_allowance_usage_adhoc(
            state=mock_state,
            account_type=sentinel.account_type,
            effective_datetime=effective_datetime,
        )

        self.assertListEqual(result, [sentinel.fee_custom_instruction])

        mock_get_start_of_current_allowance_period.assert_called_once_with(
            state=mock_state,
            check_overpayment_allowance_last_execution_datetime=sentinel.last_exec_time,
        )
        mock_get_allowance_for_period.assert_called_once_with(
            start_of_period_balances=expected_start_of_period_balances,
            allowance_percentage=sentinel.overpayment_percentage,
            denomination=sentinel.denomination,
        )
        mock_get_allowance_usage.assert_called_once_with(
            start_of_period_balances=expected_start_of_period_balances,
            end_of_period_balances=expected_end_of_period_balances,
            denomination=sentinel.denomination,
        )
        mock_get_allowance_usage_fee.assert_called_once_with(
            used_allowance=sentinel.used_allowance,
            allowance=sentinel.allowance,
            overpayment_allowance_fee_percentage=sentinel.allowance_fee_percentage,
        )
        mock_fee_custom_instruction.assert_called_once_with(
            customer_account_id=mock_vault.account_id,
            denomination=sentinel.denomination,
            amount=Decimal("10"),
            internal_account=sentinel.allowance_fee_income_account,
            customer_account_address=common_addresses.PENALTIES,
            instruction_details={"sentinel": "details"},
        )


@pytest.mark.unit
class StartOfAllowancePeriodTest(FeatureTest):
    def test_start_of_allowance_period_when_handle_allowance_schedule_has_run(self):
        last_execution_datetime = datetime(2023, 1, 2, 3, 4, 5, 6, tzinfo=ZoneInfo("UTC"))
        expected = datetime(2023, 1, 2, tzinfo=ZoneInfo("UTC"))
        mock_vault = MagicMock(events_timezone=ZoneInfo("UTC"))
        activation_dt = sentinel.account_activation_datetime
        mock_vault.get_account_activation_datetime.return_value = activation_dt
        mock_state = MagicMock(vault=mock_vault, effective_datetime=sentinel.effective_datetime)

        self.assertEqual(
            overpayment_allowance.get_start_of_current_allowance_period(
                state=mock_state,
                check_overpayment_allowance_last_execution_datetime=last_execution_datetime,
            ),
            expected,
        )

    def test_start_of_allowance_period_when_effective_date_gt_1_year_after_account_creation(self):
        effective_datetime = datetime(2023, 1, 2, 3, 4, 5, 6, tzinfo=ZoneInfo("UTC"))
        account_activation_datetime = effective_datetime - relativedelta(years=2)
        expected = datetime(2022, 1, 2, tzinfo=ZoneInfo("UTC"))
        mock_vault = MagicMock(events_timezone=ZoneInfo("UTC"))
        mock_vault.get_account_activation_datetime.return_value = account_activation_datetime
        mock_state = MagicMock(vault=mock_vault, effective_datetime=effective_datetime)

        self.assertEqual(
            overpayment_allowance.get_start_of_current_allowance_period(
                state=mock_state,
                check_overpayment_allowance_last_execution_datetime=None,
            ),
            expected,
        )

    def test_start_of_allowance_period_when_effective_date_eq_1_year_after_account_creation(
        self,
    ):
        effective_datetime = datetime(2023, 1, 2, 3, 4, 5, 6, tzinfo=ZoneInfo("UTC"))
        account_activation_datetime = effective_datetime - relativedelta(years=1)
        expected = account_activation_datetime
        mock_vault = MagicMock(events_timezone=ZoneInfo("UTC"))
        mock_vault.get_account_activation_datetime.return_value = account_activation_datetime
        mock_state = MagicMock(vault=mock_vault, effective_datetime=effective_datetime)

        self.assertEqual(
            overpayment_allowance.get_start_of_current_allowance_period(
                state=mock_state,
                check_overpayment_allowance_last_execution_datetime=None,
            ),
            expected,
        )

    def test_start_of_allowance_period_when_effective_date_lt_1_year_after_account_creation(self):
        effective_datetime = datetime(2023, 1, 2, 3, 4, 5, 6, tzinfo=ZoneInfo("UTC"))
        account_activation_datetime = effective_datetime - relativedelta(months=2)
        expected = account_activation_datetime
        mock_vault = MagicMock(events_timezone=ZoneInfo("UTC"))
        mock_vault.get_account_activation_datetime.return_value = account_activation_datetime
        mock_state = MagicMock(vault=mock_vault, effective_datetime=effective_datetime)

        self.assertEqual(
            overpayment_allowance.get_start_of_current_allowance_period(
                state=mock_state,
                check_overpayment_allowance_last_execution_datetime=None,
            ),
            expected,
        )


@pytest.mark.unit
class OverpaymentAllowanceStatusTest(FeatureTest):
    @patch.object(overpayment_allowance, "get_start_of_current_allowance_period")
    @patch.object(overpayment_allowance, "get_allowance")
    def test_overpayment_allowance_status(
        self,
        mock_get_allowance: MagicMock,
        mock_get_start_of_current_allowance_period: MagicMock,
    ):
        start_of_period = datetime(2020, 1, 2, 3, 4, 5, 6, tzinfo=ZoneInfo("UTC"))
        effective_datetime = datetime(2020, 4, 5, 6, 7, 8, 9, tzinfo=ZoneInfo("UTC"))

        mock_get_start_of_current_allowance_period.return_value = start_of_period
        mock_get_allowance.return_value = sentinel.allowance
        overpayment_balance_ts = MagicMock()
        overpayment_balance_ts.at.side_effect = lambda at_datetime: (
            Balance(debit=Decimal("100"), credit=Decimal("0"), net=Decimal("100"))
            if at_datetime == start_of_period
            else Balance(debit=Decimal("300"), credit=Decimal("0"), net=Decimal("300"))
        )

        principal_balance_ts = MagicMock()
        principal_balance_ts.at.side_effect = lambda at_datetime: (
            SentinelBalance("start_of_period_principal")
            if at_datetime == start_of_period
            else SentinelBalance("effective_datetime_principal")
        )

        # this is the difference between the overpayment balance timeseries items
        expected_allowance_used = Decimal("200")
        expected_allowance = sentinel.allowance

        balances_interval_fetchers_mapping = {
            overpayment_allowance.ONE_YEAR_OVERPAYMENT_ALLOWANCE_BIF_ID: defaultdict(  # noqa: E501
                None,
                {
                    OVERPAYMENT_COORDINATE: overpayment_balance_ts,
                    PRINCIPAL_COORDINATE: principal_balance_ts,
                },
            )
        }

        params = {
            overpayment_allowance.denomination_module.DENOMINATION_PARAM_ID: (
                sentinel.denomination
            ),
            overpayment_allowance.OVERPAYMENT_ALLOWANCE_PERCENTAGE_PARAM_ID: (
                sentinel.overpayment_percentage
            ),
        }

        mock_vault = self.create_mock(
            balances_interval_fetchers_mapping=balances_interval_fetchers_mapping,
            last_scheduled_event_datetimes_observation_mapping={
                overpayment_allowance.OVERPAYMENT_ALLOWANCE_LAST_EXECUTION_SOF_ID: MagicMock(  # noqa: E501
                    last_scheduled_event_datetimes={
                        overpayment_allowance.CHECK_OVERPAYMENT_ALLOWANCE_EVENT: sentinel.last_exec_time  # noqa: E501
                    }
                )
            },
            parameters_observation_fetchers_mapping={
                overpayment_allowance.OVERPAYMENT_ALLOWANCE_PARAM_POF_ID: MagicMock(
                    parameters=params
                )
            },
            parameters_interval_fetchers_mapping={
                overpayment_allowance.ONE_YEAR_ALLOWANCE_PARAM_PIF_ID: {
                    overpayment_allowance.OVERPAYMENT_ALLOWANCE_PERCENTAGE_PARAM_ID: ParameterTimeseries(
                        [(start_of_period, sentinel.overpayment_percentage)]
                    )
                }
            },
        )

        mock_state = initialise_mock_state(
            parameters=params,
            vault=mock_vault,
            effective_datetime=effective_datetime,
        )

        self.assertEqual(
            overpayment_allowance.get_overpayment_allowance_status(
                state=mock_state, effective_datetime=effective_datetime
            ),
            overpayment_allowance.OverpaymentAllowanceStatus(
                overpayment_allowance=expected_allowance,
                overpayment_allowance_used=expected_allowance_used,
            ),
        )

        mock_get_start_of_current_allowance_period.assert_called_once_with(
            state=mock_state,
            check_overpayment_allowance_last_execution_datetime=sentinel.last_exec_time,
        )
        mock_get_allowance.assert_called_once_with(
            principal=sentinel.net_start_of_period_principal,
            allowance_percentage=sentinel.overpayment_percentage,
        )


@patch.object(overpayment_allowance.posting_utils, "create_postings")
@pytest.mark.unit
class SetOverpaymentAllowanceForPeriodTest(FeatureTest):
    def test_no_postings_to_return_if_overpayment_delta_is_the_same(
        self,
        mock_create_postings: MagicMock,
    ):
        self.assertListEqual(
            overpayment_allowance.set_overpayment_allowance_for_period(
                current_overpayment_allowance=Decimal("100"),
                updated_overpayment_allowance=Decimal("100"),
                denomination=sentinel.denomination,
                account_id=sentinel.account_id,
            ),
            [],
        )

        mock_create_postings.assert_not_called()

    def test_positive_overpayment_allowance_delta_returns_correct_ci(
        self,
        mock_create_postings: MagicMock,
    ):
        mock_create_postings.return_value = [SentinelPosting("overpayment_allowance")]

        self.assertListEqual(
            overpayment_allowance.set_overpayment_allowance_for_period(
                current_overpayment_allowance=Decimal("150"),
                updated_overpayment_allowance=Decimal("100"),
                denomination=sentinel.denomination,
                account_id=sentinel.account_id,
            ),
            [
                CustomInstruction(
                    postings=[SentinelPosting("overpayment_allowance")],
                    instruction_details={
                        "description": "Resetting the overpayment allowance tracker balance",
                        "event": "RESET_REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER",
                    },
                )
            ],
        )

        mock_create_postings.assert_called_once_with(
            amount=Decimal("50"),
            debit_account=sentinel.account_id,
            credit_account=sentinel.account_id,
            debit_address=common_addresses.INTERNAL_CONTRA,
            credit_address=overpayment_allowance.REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER,
            denomination=sentinel.denomination,
        )

    def test_negative_overpayment_allowance_delta_returns_correct_ci(
        self,
        mock_create_postings: MagicMock,
    ):
        mock_create_postings.return_value = [SentinelPosting("overpayment_allowance")]

        self.assertListEqual(
            overpayment_allowance.set_overpayment_allowance_for_period(
                current_overpayment_allowance=Decimal("100"),
                updated_overpayment_allowance=Decimal("150"),
                denomination=sentinel.denomination,
                account_id=sentinel.account_id,
            ),
            [
                CustomInstruction(
                    postings=[SentinelPosting("overpayment_allowance")],
                    instruction_details={
                        "description": "Resetting the overpayment allowance tracker balance",
                        "event": "RESET_REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER",
                    },
                )
            ],
        )

        mock_create_postings.assert_called_once_with(
            amount=Decimal("50"),
            debit_account=sentinel.account_id,
            credit_account=sentinel.account_id,
            debit_address=overpayment_allowance.REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER,
            credit_address=common_addresses.INTERNAL_CONTRA,
            denomination=sentinel.denomination,
        )


@patch.object(overpayment_allowance.balance_utils, "balance_at_coordinates")
@patch.object(overpayment_allowance.posting_utils, "create_postings")
@pytest.mark.unit
class ReduceOverpaymentAllowanceTest(FeatureTest):
    def test_no_postings_when_overpayment_amount_is_negative(
        self,
        mock_create_postings: MagicMock,
        mock_balance_at_coordinates: MagicMock,
    ):
        # outstanding principal on loan
        mock_balance_at_coordinates.return_value = Decimal("100000")

        parameters = {
            overpayment_allowance.denomination_module.DENOMINATION_PARAM_ID: (sentinel.denomination)
        }
        mock_vault = self.create_mock(
            parameters_observation_fetchers_mapping={
                overpayment_allowance.OVERPAYMENT_ALLOWANCE_PARAM_POF_ID: MagicMock(
                    parameters=parameters
                )
            }
        )

        mock_state = initialise_mock_state(
            parameters=parameters,
            vault=mock_vault,
            effective_datetime=DEFAULT_DATE,
        )

        self.assertListEqual(
            overpayment_allowance.reduce_overpayment_allowance(
                state=mock_state,
                overpayment_amount=Decimal("-10"),
                balances=BalanceDefaultDict(lambda: Balance()),
            ),
            [],
        )

        mock_balance_at_coordinates.assert_called_once_with(
            balances=BalanceDefaultDict(lambda: Balance()),
            address=lending_addresses.PRINCIPAL,
            denomination=sentinel.denomination,
        )
        mock_create_postings.assert_not_called()

    def test_no_postings_when_overpayment_amount_is_0(
        self,
        mock_create_postings: MagicMock,
        mock_balance_at_coordinates: MagicMock,
    ):
        # outstanding principal on loan
        mock_balance_at_coordinates.return_value = Decimal("100000")

        parameters = {
            overpayment_allowance.denomination_module.DENOMINATION_PARAM_ID: (sentinel.denomination)
        }
        mock_vault = self.create_mock(
            parameters_observation_fetchers_mapping={
                overpayment_allowance.OVERPAYMENT_ALLOWANCE_PARAM_POF_ID: MagicMock(
                    parameters=parameters
                )
            }
        )

        mock_state = initialise_mock_state(
            parameters=parameters,
            vault=mock_vault,
            effective_datetime=DEFAULT_DATE,
        )

        self.assertListEqual(
            overpayment_allowance.reduce_overpayment_allowance(
                state=mock_state,
                overpayment_amount=Decimal("0"),
                balances=BalanceDefaultDict(lambda: Balance()),
            ),
            [],
        )

        mock_balance_at_coordinates.assert_called_once_with(
            balances=BalanceDefaultDict(lambda: Balance()),
            address=lending_addresses.PRINCIPAL,
            denomination=sentinel.denomination,
        )
        mock_create_postings.assert_not_called()

    def test_no_postings_when_total_outstanding_principal_is_0(
        self,
        mock_create_postings: MagicMock,
        mock_balance_at_coordinates: MagicMock,
    ):
        # outstanding principal on loan
        mock_balance_at_coordinates.return_value = Decimal("0")

        parameters = {
            overpayment_allowance.denomination_module.DENOMINATION_PARAM_ID: (sentinel.denomination)
        }
        mock_vault = self.create_mock(
            parameters_observation_fetchers_mapping={
                overpayment_allowance.OVERPAYMENT_ALLOWANCE_PARAM_POF_ID: MagicMock(
                    parameters=parameters
                )
            }
        )

        mock_state = initialise_mock_state(
            parameters=parameters,
            vault=mock_vault,
            effective_datetime=DEFAULT_DATE,
        )

        self.assertListEqual(
            overpayment_allowance.reduce_overpayment_allowance(
                state=mock_state,
                overpayment_amount=Decimal("10"),
                balances=BalanceDefaultDict(lambda: Balance()),
            ),
            [],
        )

        mock_balance_at_coordinates.assert_called_once_with(
            balances=BalanceDefaultDict(lambda: Balance()),
            address=lending_addresses.PRINCIPAL,
            denomination=sentinel.denomination,
        )
        mock_create_postings.assert_not_called()

    def test_return_postings_to_decrease_overpayment_allowance(
        self,
        mock_create_postings: MagicMock,
        mock_balance_at_coordinates: MagicMock,
    ):
        # outstanding principal on loan
        mock_balance_at_coordinates.return_value = Decimal("100000")
        mock_create_postings.return_value = [sentinel.postings]
        parameters = {
            overpayment_allowance.denomination_module.DENOMINATION_PARAM_ID: (sentinel.denomination)
        }
        mock_vault = self.create_mock(
            parameters_observation_fetchers_mapping={
                overpayment_allowance.OVERPAYMENT_ALLOWANCE_PARAM_POF_ID: MagicMock(
                    parameters=parameters
                )
            }
        )

        mock_state = initialise_mock_state(
            parameters=parameters,
            vault=mock_vault,
            effective_datetime=DEFAULT_DATE,
        )

        self.assertListEqual(
            overpayment_allowance.reduce_overpayment_allowance(
                state=mock_state,
                overpayment_amount=Decimal("10"),
                balances=BalanceDefaultDict(lambda: Balance()),
            ),
            [sentinel.postings],
        )

        mock_balance_at_coordinates.assert_called_once_with(
            balances=BalanceDefaultDict(lambda: Balance()),
            address=lending_addresses.PRINCIPAL,
            denomination=sentinel.denomination,
        )
        mock_create_postings.assert_called_once_with(
            amount=Decimal("10"),
            debit_account=mock_vault.account_id,
            debit_address=common_addresses.INTERNAL_CONTRA,
            credit_account=mock_vault.account_id,
            credit_address=overpayment_allowance.REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER,
            denomination=sentinel.denomination,
        )


@patch.object(overpayment_allowance.balance_utils, "sum_balances")
@patch.object(overpayment_allowance.balance_utils, "net_debit")
@patch.object(overpayment_allowance.balance_utils, "balance_at_coordinates")
@patch.object(overpayment_allowance.utils, "round_decimal")
@pytest.mark.unit
class GetOverpaymentAllowanceFeeForEarlyRepaymentTest(FeatureTest):
    def mock_sum_balances(
        self, mock_net_debit: MagicMock, address_name_to_amount_mapping: dict[str, Decimal]
    ) -> Callable:
        outstanding_addresses = lending_addresses.ALL_OUTSTANDING
        repayment_addresses = lending_addresses.REPAYMENT_HIERARCHY

        def net_debit(balance):
            if balance == "ALL_OUTSTANDING":
                return address_name_to_amount_mapping["ALL_OUTSTANDING"]
            elif balance == "REPAYMENT_HIERARCHY":
                return address_name_to_amount_mapping["REPAYMENT_HIERARCHY"]
            return Decimal("0")

        mock_net_debit.side_effect = net_debit

        def sum_balances(balances: BalanceDefaultDict, addresses: list[str], denomination: str):
            if addresses == outstanding_addresses:
                return "ALL_OUTSTANDING"
            elif addresses == repayment_addresses:
                return "REPAYMENT_HIERARCHY"

        return sum_balances

    def test_overpayment_allowance_covers_early_repayment_amount_exactly(
        self,
        mock_round_decimal: MagicMock,
        mock_balance_at_coordinates: MagicMock,
        mock_net_debit: MagicMock,
        mock_sum_balances: MagicMock,
    ):
        parameters = {
            overpayment_allowance.denomination_module.DENOMINATION_PARAM_ID: (
                sentinel.denomination
            ),
            overpayment_allowance.OVERPAYMENT_ALLOWANCE_FEE_PERCENTAGE_PARAM_ID: Decimal("0.01"),
        }
        mock_vault = self.create_mock(
            parameters_observation_fetchers_mapping={
                overpayment_allowance.OVERPAYMENT_ALLOWANCE_PARAM_POF_ID: MagicMock(
                    parameters=parameters
                )
            }
        )
        mock_state = initialise_mock_state(
            parameters=parameters,
            vault=mock_vault,
            balances=BalanceDefaultDict(lambda: Balance()),
            effective_datetime=DEFAULT_DATE,
        )

        mock_sum_balances.side_effect = self.mock_sum_balances(
            mock_net_debit,
            {"ALL_OUTSTANDING": Decimal("5000"), "REPAYMENT_HIERARCHY": Decimal("2000")},
        )
        # the balance of the overpayment allowance tracker
        mock_balance_at_coordinates.return_value = Decimal("3000")
        mock_round_decimal.return_value = Decimal("0")

        self.assertEqual(
            overpayment_allowance.get_overpayment_allowance_fee_for_early_repayment(
                state=mock_state,
            ),
            Decimal("0"),
        )
        mock_balance_at_coordinates.assert_called_once_with(
            balances=BalanceDefaultDict(lambda: Balance()),
            address=overpayment_allowance.REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER,
            denomination=sentinel.denomination,
        )
        mock_round_decimal.assert_called_once_with(
            amount=Decimal("0"),
            decimal_places=2,
        )

    def test_overpayment_allowance_exceeds_early_repayment_amount(
        self,
        mock_round_decimal: MagicMock,
        mock_balance_at_coordinates: MagicMock,
        mock_net_debit: MagicMock,
        mock_sum_balances: MagicMock,
    ):
        parameters = {
            overpayment_allowance.denomination_module.DENOMINATION_PARAM_ID: (
                sentinel.denomination
            ),
            overpayment_allowance.OVERPAYMENT_ALLOWANCE_FEE_PERCENTAGE_PARAM_ID: Decimal("0.01"),
        }
        mock_vault = self.create_mock(
            parameters_observation_fetchers_mapping={
                overpayment_allowance.OVERPAYMENT_ALLOWANCE_PARAM_POF_ID: MagicMock(
                    parameters=parameters
                )
            }
        )
        mock_state = initialise_mock_state(
            parameters=parameters,
            vault=mock_vault,
            balances=BalanceDefaultDict(lambda: Balance()),
            effective_datetime=DEFAULT_DATE,
        )

        mock_sum_balances.side_effect = self.mock_sum_balances(
            mock_net_debit,
            {"ALL_OUTSTANDING": Decimal("5000"), "REPAYMENT_HIERARCHY": Decimal("2000")},
        )
        # the balance of the overpayment allowance tracker
        mock_balance_at_coordinates.return_value = Decimal("4000")
        mock_round_decimal.return_value = Decimal("0")

        self.assertEqual(
            overpayment_allowance.get_overpayment_allowance_fee_for_early_repayment(
                state=mock_state,
            ),
            Decimal("0"),
        )
        mock_balance_at_coordinates.assert_called_once_with(
            balances=BalanceDefaultDict(lambda: Balance()),
            address=overpayment_allowance.REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER,
            denomination=sentinel.denomination,
        )
        mock_round_decimal.assert_called_once_with(
            amount=Decimal("0"),
            decimal_places=2,
        )

    def test_overpayment_allowance_is_less_than_early_repayment_amount(
        self,
        mock_round_decimal: MagicMock,
        mock_balance_at_coordinates: MagicMock,
        mock_net_debit: MagicMock,
        mock_sum_balances: MagicMock,
    ):
        parameters = {
            overpayment_allowance.denomination_module.DENOMINATION_PARAM_ID: (
                sentinel.denomination
            ),
            overpayment_allowance.OVERPAYMENT_ALLOWANCE_FEE_PERCENTAGE_PARAM_ID: Decimal("0.01"),
        }
        mock_vault = self.create_mock(
            parameters_observation_fetchers_mapping={
                overpayment_allowance.OVERPAYMENT_ALLOWANCE_PARAM_POF_ID: MagicMock(
                    parameters=parameters
                )
            }
        )
        mock_state = initialise_mock_state(
            parameters=parameters,
            vault=mock_vault,
            balances=BalanceDefaultDict(lambda: Balance()),
            effective_datetime=DEFAULT_DATE,
        )

        mock_sum_balances.side_effect = self.mock_sum_balances(
            mock_net_debit,
            {"ALL_OUTSTANDING": Decimal("5000"), "REPAYMENT_HIERARCHY": Decimal("2000")},
        )
        # the balance of the overpayment allowance tracker
        mock_balance_at_coordinates.return_value = Decimal("2000")
        mock_round_decimal.return_value = Decimal("10")

        self.assertEqual(
            overpayment_allowance.get_overpayment_allowance_fee_for_early_repayment(
                state=mock_state,
            ),
            Decimal("10"),
        )
        mock_balance_at_coordinates.assert_called_once_with(
            balances=BalanceDefaultDict(lambda: Balance()),
            address=overpayment_allowance.REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER,
            denomination=sentinel.denomination,
        )
        mock_round_decimal.assert_called_once_with(
            # 0.01 * 1000
            amount=Decimal("10"),
            decimal_places=2,
        )

    def test_optional_parameters_are_defaulted_correctly(
        self,
        mock_round_decimal: MagicMock,
        mock_balance_at_coordinates: MagicMock,
        mock_net_debit: MagicMock,
        mock_sum_balances: MagicMock,
    ):
        parameters = {
            overpayment_allowance.denomination_module.DENOMINATION_PARAM_ID: (
                sentinel.denomination
            ),
            overpayment_allowance.OVERPAYMENT_ALLOWANCE_FEE_PERCENTAGE_PARAM_ID: Decimal("0.01"),
        }
        mock_vault = self.create_mock(
            balances_observation_fetchers_mapping={
                "live_balances_bof": SentinelBalancesObservation("dummy_balances")
            },
            parameters_observation_fetchers_mapping={
                overpayment_allowance.OVERPAYMENT_ALLOWANCE_PARAM_POF_ID: MagicMock(
                    parameters=parameters
                )
            },
        )

        mock_state = initialise_mock_state(
            parameters=parameters,
            vault=mock_vault,
            effective_datetime=DEFAULT_DATE,
        )

        mock_sum_balances.side_effect = self.mock_sum_balances(
            mock_net_debit,
            {"ALL_OUTSTANDING": Decimal("5000"), "REPAYMENT_HIERARCHY": Decimal("2000")},
        )
        # the balance of the overpayment allowance tracker
        mock_balance_at_coordinates.return_value = Decimal("2000")
        mock_round_decimal.return_value = Decimal("10")

        self.assertEqual(
            overpayment_allowance.get_overpayment_allowance_fee_for_early_repayment(
                state=mock_state,
            ),
            Decimal("10"),
        )
        mock_balance_at_coordinates.assert_called_once_with(
            balances=mock_state.balances,
            address=overpayment_allowance.REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER,
            denomination=sentinel.denomination,
        )
        mock_round_decimal.assert_called_once_with(
            # 0.01 * 1000
            amount=Decimal("10"),
            decimal_places=2,
        )


@patch.object(overpayment_allowance.date_and_time, "parse_time_str")
@pytest.mark.unit
class UpdateScheduleEventTest(FeatureTest):
    def test_update_schedule_event(self, mock_parse_time_str: MagicMock):
        mock_parse_time_str.return_value = MagicMock(hour=0, minute=0, second=0)

        mock_state = MagicMock(
            parameters={
                overpayment_allowance.CHECK_OVERPAYMENT_ALLOWANCE_TIME_PARAM_ID: "00:00:00",
            },
            vault=MagicMock(events_timezone=ZoneInfo("UTC")),
        )

        expected_skip = DEFAULT_DATE.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + relativedelta(years=1, seconds=-1)

        expected_result = {
            overpayment_allowance.CHECK_OVERPAYMENT_ALLOWANCE_EVENT: ScheduledEvent(
                expression=overpayment_allowance.ScheduleExpression(
                    year=None,
                    month="1",
                    day="2",
                    hour="0",
                    minute="0",
                    second="0",
                ),
                skip=ScheduleSkip(end=expected_skip),
            )
        }
        result = overpayment_allowance.update_scheduled_event(
            state=mock_state, effective_datetime=DEFAULT_DATE
        )
        self.assertEqual(expected_result, result)


@patch.object(overpayment_allowance, "set_overpayment_allowance_for_period")
@pytest.mark.unit
class InitialiseOverpaymentAllowanceFromPrincipalAmountTest(FeatureTest):
    def test_sets_allowance_with_denomination(
        self, mock_set_overpayment_allowance_for_period: MagicMock
    ):
        parameters = {
            overpayment_allowance.denomination_module.DENOMINATION_PARAM_ID: (
                sentinel.denomination
            ),
            overpayment_allowance.OVERPAYMENT_ALLOWANCE_PERCENTAGE_PARAM_ID: Decimal("0.01"),
        }
        mock_vault = self.create_mock(
            parameters_observation_fetchers_mapping={
                overpayment_allowance.OVERPAYMENT_ALLOWANCE_PARAM_POF_ID: MagicMock(
                    parameters=parameters
                )
            },
        )

        mock_state = initialise_mock_state(
            parameters=parameters,
            vault=mock_vault,
            effective_datetime=DEFAULT_DATE,
        )
        mock_set_overpayment_allowance_for_period.return_value = [sentinel.custom_instruction]

        self.assertEqual(
            overpayment_allowance.initialise_overpayment_allowance_from_principal_amount(
                state=mock_state, principal=Decimal("100")
            ),
            [sentinel.custom_instruction],
        )

        mock_set_overpayment_allowance_for_period.assert_called_once_with(
            current_overpayment_allowance=Decimal("0"),
            updated_overpayment_allowance=Decimal("1"),
            denomination=sentinel.denomination,
            account_id=mock_state.vault.account_id,
        )


@patch.object(overpayment_allowance.balance_utils, "net_debit")
@patch.object(overpayment_allowance.balance_utils, "get_current_net_balance")
@patch.object(overpayment_allowance.posting_utils, "create_postings")
@pytest.mark.unit
class GetResidualCleanupPostingsTest(FeatureTest):
    def test_negative_overpayment_allowance_amount_returns_correct_postings(
        self,
        mock_create_postings: MagicMock,
        mock_get_current_net_balance: MagicMock,
        mock_net_debit: MagicMock,
    ):
        # overpayment allowance amount
        mock_net_debit.return_value = Decimal("-10")
        mock_create_postings.return_value = [sentinel.postings]

        self.assertEqual(
            overpayment_allowance.get_residual_cleanup_postings(
                balances=BalanceDefaultDict(lambda: Balance()),
                account_id=sentinel.account_id,
                denomination=sentinel.denomination,
            ),
            [sentinel.postings],
        )
        mock_get_current_net_balance.assert_called_once_with(
            balances=BalanceDefaultDict(lambda: Balance()),
            address=overpayment_allowance.REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER,
            denomination=sentinel.denomination,
        )
        mock_create_postings.assert_called_once_with(
            amount=Decimal("-10"),
            debit_account=sentinel.account_id,
            credit_account=sentinel.account_id,
            debit_address=common_addresses.INTERNAL_CONTRA,
            credit_address=overpayment_allowance.REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER,
            denomination=sentinel.denomination,
        )

    def test_positive_overpayment_allowance_amount_returns_correct_postings(
        self,
        mock_create_postings: MagicMock,
        mock_get_current_net_balance: MagicMock,
        mock_net_debit: MagicMock,
    ):
        # overpayment allowance amount
        mock_net_debit.return_value = Decimal("10")
        mock_create_postings.return_value = [sentinel.postings]

        self.assertEqual(
            overpayment_allowance.get_residual_cleanup_postings(
                balances=BalanceDefaultDict(lambda: Balance()),
                account_id=sentinel.account_id,
                denomination=sentinel.denomination,
            ),
            [sentinel.postings],
        )
        mock_get_current_net_balance.assert_called_once_with(
            balances=BalanceDefaultDict(lambda: Balance()),
            address=overpayment_allowance.REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER,
            denomination=sentinel.denomination,
        )
        mock_create_postings.assert_called_once_with(
            amount=Decimal("10"),
            debit_account=sentinel.account_id,
            credit_account=sentinel.account_id,
            debit_address=common_addresses.INTERNAL_CONTRA,
            credit_address=overpayment_allowance.REMAINING_OVERPAYMENT_ALLOWANCE_TRACKER,
            denomination=sentinel.denomination,
        )
