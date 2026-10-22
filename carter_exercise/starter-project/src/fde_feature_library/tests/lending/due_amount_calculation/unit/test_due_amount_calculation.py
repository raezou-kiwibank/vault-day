# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, sentinel
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

# features
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.due_amount_calculation.due_amount_calculation as due_calc
import feature_library.lending.interfaces as lending_interfaces
from feature_library.common import state_utils
from feature_library.lending.repayments.overpayment import OVERPAYMENT_ADDRESS

# contracts api
from contracts_api import (
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    CustomInstruction,
    Phase,
    Posting,
    ScheduledEvent,
    ScheduleExpression,
    UpdateAccountEventTypeDirective,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

from tests.utils import initialise_mock_state

UTC = ZoneInfo("UTC")
DEFAULT_DATETIME = datetime(2020, 1, 2, 3, tzinfo=UTC)


class DueAmountCalculationTest(FeatureTest):
    maxDiff = None

    def _setup_mock_vault(
        self,
        billing_frequency: str = "monthly",
        due_calculation_time: str = "00:00:00",
        due_calculation_day: int | str = 28,
        first_due_date: datetime | None = None,
        denomination: str = "GBP",
        balances: dict | None = None,
    ) -> MagicMock:
        mock_vault = MagicMock()
        mock_vault.events_timezone = UTC
        mock_vault.account_id = sentinel.account_id
        mock_vault.get_account_activation_datetime.return_value = DEFAULT_DATETIME

        parameters = {
            due_calc.BILLING_FREQUENCY_PARAM_ID: billing_frequency,
            due_calc.DUE_AMOUNT_CALCULATION_TIME_PARAM_ID: due_calculation_time,
            due_calc.DUE_AMOUNT_CALCULATION_DAY_PARAM_ID: due_calculation_day,
            due_calc.FIRST_DUE_DATE_PARAM_ID: first_due_date,
            "&{denomination}": denomination,
        }

        mock_vault.get_parameters_observation.return_value = MagicMock(parameters=parameters)

        mock_vault.get_last_scheduled_event_datetimes_observation.return_value = MagicMock(
            last_scheduled_event_datetimes={}
        )

        bal_dict = balances or {}
        mock_vault.get_balances_observation.return_value = MagicMock(
            balances=BalanceDefaultDict(lambda: Balance(), bal_dict)
        )

        return mock_vault


class ScheduledEventsTest(DueAmountCalculationTest):
    @pytest.mark.unit
    def test_get_scheduled_events_monthly_with_provided_datetime(self):
        mock_vault = self._setup_mock_vault(
            billing_frequency="monthly", due_calculation_time="12:00:00"
        )
        state = initialise_mock_state(vault=mock_vault)

        first_due = datetime(2020, 2, 5, 0, tzinfo=UTC)
        result = due_calc.get_scheduled_events(state, first_due)

        expected = {
            due_calc.DUE_AMOUNT_CALCULATION_EVENT: ScheduledEvent(
                start_datetime=datetime(2020, 2, 5, 0, tzinfo=UTC),
                expression=ScheduleExpression(
                    year="2020",
                    month="2",
                    day="5",
                    hour="12",
                    minute="0",
                    second="0",
                ),
            )
        }
        self.assertEqual(result, expected)

    @pytest.mark.unit
    def test_get_scheduled_events_weekly_with_provided_datetime(self):
        mock_vault = self._setup_mock_vault(
            billing_frequency="weekly", due_calculation_time="09:15:30"
        )
        state = initialise_mock_state(vault=mock_vault)

        # 2020-02-05 is Wednesday (weekday 2)
        first_due = datetime(2020, 2, 5, 0, tzinfo=UTC)
        result = due_calc.get_scheduled_events(state, first_due)

        expected = {
            due_calc.DUE_AMOUNT_CALCULATION_EVENT: ScheduledEvent(
                start_datetime=datetime(2020, 2, 5, 0, tzinfo=UTC),
                expression=ScheduleExpression(
                    day_of_week="2",
                    hour="9",
                    minute="15",
                    second="30",
                ),
            )
        }
        self.assertEqual(result, expected)

    @pytest.mark.unit
    def test_get_scheduled_events_monthly_calculated(self):
        mock_vault = self._setup_mock_vault(
            billing_frequency="monthly",
            due_calculation_time="12:00:00",
            due_calculation_day=28,
        )
        state = initialise_mock_state(vault=mock_vault)

        result = due_calc.get_scheduled_events(state)

        expected = {
            due_calc.DUE_AMOUNT_CALCULATION_EVENT: ScheduledEvent(
                start_datetime=datetime(2020, 2, 28, 0, tzinfo=UTC),
                expression=ScheduleExpression(
                    year="2020",
                    month="2",
                    day="28",
                    hour="12",
                    minute="0",
                    second="0",
                ),
            )
        }
        self.assertEqual(result, expected)

    @pytest.mark.unit
    def test_get_scheduled_events_monthly_calculated_day_before_activation(self):
        mock_vault = self._setup_mock_vault(
            billing_frequency="monthly",
            due_calculation_time="12:00:00",
            due_calculation_day=1,
        )
        state = initialise_mock_state(vault=mock_vault)

        result = due_calc.get_scheduled_events(state)

        expected = {
            due_calc.DUE_AMOUNT_CALCULATION_EVENT: ScheduledEvent(
                start_datetime=datetime(2020, 3, 1, 0, tzinfo=UTC),
                expression=ScheduleExpression(
                    year="2020",
                    month="3",
                    day="1",
                    hour="12",
                    minute="0",
                    second="0",
                ),
            )
        }
        self.assertEqual(result, expected)

    @pytest.mark.unit
    def test_get_scheduled_events_weekly_calculated(self):
        mock_vault = self._setup_mock_vault(
            billing_frequency="weekly",
            due_calculation_time="09:15:30",
            due_calculation_day=1,
        )
        state = initialise_mock_state(vault=mock_vault)

        result = due_calc.get_scheduled_events(state)

        expected = {
            due_calc.DUE_AMOUNT_CALCULATION_EVENT: ScheduledEvent(
                start_datetime=datetime(2020, 1, 13, 0, tzinfo=UTC),
                expression=ScheduleExpression(
                    day_of_week="0",
                    hour="9",
                    minute="15",
                    second="30",
                ),
            )
        }
        self.assertEqual(result, expected)

    @pytest.mark.unit
    def test_get_scheduled_events_fortnightly_calculated(self):
        mock_vault = self._setup_mock_vault(
            billing_frequency="fortnightly",
            due_calculation_time="09:15:30",
            due_calculation_day=1,
        )
        state = initialise_mock_state(vault=mock_vault)

        result = due_calc.get_scheduled_events(state)

        expected = {
            due_calc.DUE_AMOUNT_CALCULATION_EVENT: ScheduledEvent(
                start_datetime=datetime(2020, 1, 20, 0, tzinfo=UTC),
                expression=ScheduleExpression(
                    day_of_week="0",
                    hour="9",
                    minute="15",
                    second="30",
                ),
            )
        }
        self.assertEqual(result, expected)

    @pytest.mark.unit
    def test_get_scheduled_events_override_parameter(self):
        override_date = datetime(2020, 4, 15, 12, 0, 0, tzinfo=UTC)
        mock_vault = self._setup_mock_vault(
            billing_frequency="monthly",
            due_calculation_time="12:00:00",
            first_due_date=override_date,
        )
        state = initialise_mock_state(vault=mock_vault)

        result = due_calc.get_scheduled_events(state)

        expected = {
            due_calc.DUE_AMOUNT_CALCULATION_EVENT: ScheduledEvent(
                start_datetime=datetime(2020, 4, 15, 0, tzinfo=UTC),
                expression=ScheduleExpression(
                    year="2020",
                    month="4",
                    day="15",
                    hour="12",
                    minute="0",
                    second="0",
                ),
            )
        }
        self.assertEqual(result, expected)

    @pytest.mark.unit
    def test_get_scheduled_events_monthly_short_month_clamping(self):
        # Activation (Jan 30, 2021) -> first due should be Feb 28th (non-leap year)
        mock_vault = self._setup_mock_vault(
            billing_frequency="monthly",
            due_calculation_time="12:00:00",
            due_calculation_day=31,
        )
        mock_vault.get_account_activation_datetime.return_value = datetime(2021, 1, 30, tzinfo=UTC)
        state = initialise_mock_state(vault=mock_vault)

        result = due_calc.get_scheduled_events(state)

        expected = {
            due_calc.DUE_AMOUNT_CALCULATION_EVENT: ScheduledEvent(
                start_datetime=datetime(2021, 2, 28, 0, tzinfo=UTC),
                expression=ScheduleExpression(
                    year="2021",
                    month="2",
                    day="28",
                    hour="12",
                    minute="0",
                    second="0",
                ),
            )
        }
        self.assertEqual(result, expected)

    @pytest.mark.unit
    def test_get_scheduled_events_weekly_with_modulo_calc_day(self):
        # Activation (Jan 2, 2020) -> target day 28 modulo 7 is weekday 6 (Sunday)
        mock_vault = self._setup_mock_vault(
            billing_frequency="weekly",
            due_calculation_time="09:15:30",
            due_calculation_day=28,
        )
        state = initialise_mock_state(vault=mock_vault)

        result = due_calc.get_scheduled_events(state)

        # Jan 2 + 1 week = Jan 9 (Thursday, weekday 3)
        # Next Sunday is Jan 12 (weekday 6)
        expected = {
            due_calc.DUE_AMOUNT_CALCULATION_EVENT: ScheduledEvent(
                start_datetime=datetime(2020, 1, 12, 0, tzinfo=UTC),
                expression=ScheduleExpression(
                    day_of_week="6",
                    hour="9",
                    minute="15",
                    second="30",
                ),
            )
        }
        self.assertEqual(result, expected)


class OverdueEventDirectiveTest(DueAmountCalculationTest):
    @pytest.mark.unit
    def test_get_next_overdue_event_directive(self):
        mock_vault = MagicMock()
        mock_vault.events_timezone = UTC
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME,
        )

        directive = due_calc.get_next_overdue_event_directive(
            state=state,
            repayment_period=14,
            check_overdue_time="15:30:00",
        )

        expected_datetime = DEFAULT_DATETIME + relativedelta(days=14)
        expected = UpdateAccountEventTypeDirective(
            event_type="CHECK_OVERDUE",
            expression=ScheduleExpression(
                year=str(expected_datetime.year),
                month=str(expected_datetime.month),
                day=str(expected_datetime.day),
                hour="15",
                minute="30",
                second="0",
            ),
        )
        self.assertEqual(directive, expected)


class ScheduleLogicTest(DueAmountCalculationTest):
    @pytest.mark.unit
    def test_schedule_logic_holiday_active(self):
        mock_vault = self._setup_mock_vault()
        state = initialise_mock_state(vault=mock_vault, effective_datetime=DEFAULT_DATETIME)

        is_repayment_holiday_active_callable = MagicMock(return_value=True)

        result = due_calc.schedule_logic(
            state=state,
            get_expected_eia_callable=MagicMock(),
            interest_application_feature=MagicMock(),
            repayment_hierarchy_config=MagicMock(),
            is_repayment_holiday_active_callable=is_repayment_holiday_active_callable,
        )

        self.assertEqual(result.custom_instructions, [])
        self.assertEqual(result.event_type_directives, [])
        is_repayment_holiday_active_callable.assert_called_once()

    @pytest.mark.unit
    def test_schedule_logic_fortnightly_odd_week_skip(self):
        # Account activated on DEFAULT_DATETIME (2020-01-02)
        # 10 days later: elapsed_weeks is 1 (odd), so it should skip
        effective_datetime = DEFAULT_DATETIME + relativedelta(days=10)
        mock_vault = self._setup_mock_vault(billing_frequency="fortnightly")
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
        )

        result = due_calc.schedule_logic(
            state=state,
            get_expected_eia_callable=MagicMock(),
            interest_application_feature=MagicMock(),
            repayment_hierarchy_config=MagicMock(),
        )

        self.assertEqual(result.custom_instructions, [])
        self.assertEqual(result.event_type_directives, [])

    @pytest.mark.unit
    def test_schedule_logic_fortnightly_even_week_no_skip(self):
        # Account activated on DEFAULT_DATETIME (2020-01-02)
        # 15 days later: elapsed_weeks is 2 (even), so it should NOT skip
        effective_datetime = DEFAULT_DATETIME + relativedelta(days=15)
        mock_vault = self._setup_mock_vault(billing_frequency="fortnightly")
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
        )

        get_expected_eia_callable = MagicMock(return_value=Decimal("100.00"))
        interest_amounts = lending_interfaces.InterestAmounts(
            eia_rounded_accrued=Decimal("10.00"),
            eia_accrued=Decimal("10.00"),
            non_eia_rounded_accrued=Decimal("0.00"),
            non_eia_accrued=Decimal("0.00"),
            total_rounded=Decimal("10.00"),
        )
        interest_application_feature = MagicMock()
        interest_application_feature.apply_interest.return_value = []
        interest_application_feature.get_interest_to_apply.return_value = interest_amounts

        result = due_calc.schedule_logic(
            state=state,
            get_expected_eia_callable=get_expected_eia_callable,
            interest_application_feature=interest_application_feature,
            repayment_hierarchy_config=MagicMock(),
        )

        # Since it's an even week, it shouldn't skip, and since get_expected_eia is 100.00,
        # it should return postings.
        self.assertEqual(len(result.custom_instructions), 1)
        self.assertEqual(result.event_type_directives, [])

    @pytest.mark.unit
    def test_schedule_logic_fortnightly_timezone_awareness(self):
        # NY Time is UTC-5.
        # Activation: 2020-01-02 02:00:00 UTC (local NY: 2020-01-01)
        # Effective:  2020-01-15 06:00:00 UTC (local NY: 2020-01-15)
        # UTC elapsed days: (2020-01-15 - 2020-01-02) = 13 (week 1 - odd - would skip)
        # NY elapsed days:  (2020-01-15 - 2020-01-01) = 14 (week 2 - even - should NOT skip)
        tz_ny = ZoneInfo("America/New_York")
        activation_dt = datetime(2020, 1, 2, 2, tzinfo=UTC)
        effective_dt = datetime(2020, 1, 15, 6, tzinfo=UTC)

        mock_vault = self._setup_mock_vault(billing_frequency="fortnightly")
        mock_vault.events_timezone = tz_ny
        mock_vault.get_account_activation_datetime.return_value = activation_dt

        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=effective_dt,
        )

        get_expected_eia_callable = MagicMock(return_value=Decimal("100.00"))
        interest_amounts = lending_interfaces.InterestAmounts(
            eia_rounded_accrued=Decimal("10.00"),
            eia_accrued=Decimal("10.00"),
            non_eia_rounded_accrued=Decimal("0.00"),
            non_eia_accrued=Decimal("0.00"),
            total_rounded=Decimal("10.00"),
        )
        interest_application_feature = MagicMock()
        interest_application_feature.apply_interest.return_value = []
        interest_application_feature.get_interest_to_apply.return_value = interest_amounts

        result = due_calc.schedule_logic(
            state=state,
            get_expected_eia_callable=get_expected_eia_callable,
            interest_application_feature=interest_application_feature,
            repayment_hierarchy_config=MagicMock(),
        )

        # NYC local calculation elapsed_days is 14 -> elapsed_weeks is 2
        # -> even week -> should NOT skip.
        self.assertEqual(len(result.custom_instructions), 1)
        self.assertEqual(result.event_type_directives, [])

    @pytest.mark.unit
    def test_schedule_logic_no_excess(self):
        mock_vault = self._setup_mock_vault()
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME,
            balances=BalanceDefaultDict(lambda: Balance(), {}),
        )

        get_expected_eia_callable = MagicMock(return_value=Decimal("250.00"))

        interest_postings = [MagicMock(spec=Posting)]
        interest_amounts = lending_interfaces.InterestAmounts(
            eia_rounded_accrued=Decimal("50.00"),
            eia_accrued=Decimal("50.00"),
            non_eia_rounded_accrued=Decimal("0.00"),
            non_eia_accrued=Decimal("0.00"),
            total_rounded=Decimal("50.00"),
        )
        interest_application_feature = MagicMock()
        interest_application_feature.apply_interest.return_value = interest_postings
        interest_application_feature.get_interest_to_apply.return_value = interest_amounts

        repayment_hierarchy_config = MagicMock()

        result = due_calc.schedule_logic(
            state=state,
            get_expected_eia_callable=get_expected_eia_callable,
            interest_application_feature=interest_application_feature,
            repayment_hierarchy_config=repayment_hierarchy_config,
        )

        self.assertEqual(len(result.custom_instructions), 1)
        self.assertIsInstance(result.custom_instructions[0], CustomInstruction)

        # Verify the description and event
        self.assertEqual(
            result.custom_instructions[0].instruction_details["event"],
            due_calc.DUE_AMOUNT_CALCULATION_EVENT,
        )

        # Verify the event type directives
        expected_directive = UpdateAccountEventTypeDirective(
            event_type=due_calc.DUE_AMOUNT_CALCULATION_EVENT,
            expression=ScheduleExpression(
                year="2020",
                month="2",
                day="28",
                hour="0",
                minute="0",
                second="0",
            ),
        )
        self.assertEqual(result.event_type_directives, [expected_directive])

        # Due principal = 250 - 50 = 200.
        # So we expect 1 principal due posting (Credit PRINCIPAL, Debit PRINCIPAL_DUE)
        # plus the interest postings.
        postings = result.custom_instructions[0].postings
        self.assertEqual(len(postings), 3)  # interest_posting + 2 principal postings

        # Check principal postings
        principal_due_posting = [
            p
            for p in postings
            if getattr(p, "account_address", None) == lending_addresses.PRINCIPAL_DUE
        ]
        self.assertEqual(len(principal_due_posting), 1)
        self.assertEqual(principal_due_posting[0].amount, Decimal("200.00"))

    @pytest.mark.unit
    def test_schedule_logic_with_broken_period_interest(self):
        mock_vault = self._setup_mock_vault()
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME,
            balances=BalanceDefaultDict(lambda: Balance(), {}),
        )

        # EMI = 880.04
        get_expected_eia_callable = MagicMock(return_value=Decimal("880.04"))

        interest_postings = [MagicMock(spec=Posting)]
        # Actual interest for month: 82.27, Broken period interest: 41.14, Total interest: 123.41
        interest_amounts = lending_interfaces.InterestAmounts(
            eia_rounded_accrued=Decimal("82.27"),
            eia_accrued=Decimal("82.27"),
            non_eia_rounded_accrued=Decimal("41.14"),
            non_eia_accrued=Decimal("41.14"),
            total_rounded=Decimal("123.41"),
        )
        interest_application_feature = MagicMock()
        interest_application_feature.apply_interest.return_value = interest_postings
        interest_application_feature.get_interest_to_apply.return_value = interest_amounts

        repayment_hierarchy_config = MagicMock()

        result = due_calc.schedule_logic(
            state=state,
            get_expected_eia_callable=get_expected_eia_callable,
            interest_application_feature=interest_application_feature,
            repayment_hierarchy_config=repayment_hierarchy_config,
        )

        self.assertEqual(len(result.custom_instructions), 1)
        self.assertIsInstance(result.custom_instructions[0], CustomInstruction)

        # Verify the description and event
        self.assertEqual(
            result.custom_instructions[0].instruction_details["event"],
            due_calc.DUE_AMOUNT_CALCULATION_EVENT,
        )

        # Verify the event type directives
        expected_directive = UpdateAccountEventTypeDirective(
            event_type=due_calc.DUE_AMOUNT_CALCULATION_EVENT,
            expression=ScheduleExpression(
                year="2020",
                month="2",
                day="28",
                hour="0",
                minute="0",
                second="0",
            ),
        )
        self.assertEqual(result.event_type_directives, [expected_directive])

        # Due principal = EMI - eia_rounded_accrued = 880.04 - 82.27 = 797.77.
        # So we expect 1 principal due posting (Credit PRINCIPAL, Debit PRINCIPAL_DUE)
        # plus the interest postings.
        postings = result.custom_instructions[0].postings
        self.assertEqual(len(postings), 3)  # interest_posting + 2 principal postings

        # Check principal postings
        principal_due_posting = [
            p
            for p in postings
            if getattr(p, "account_address", None) == lending_addresses.PRINCIPAL_DUE
        ]
        self.assertEqual(len(principal_due_posting), 1)
        self.assertEqual(principal_due_posting[0].amount, Decimal("797.77"))

    @pytest.mark.unit
    def test_schedule_logic_with_custom_get_due_principal_callable(self):
        mock_vault = self._setup_mock_vault()
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME,
            balances=BalanceDefaultDict(lambda: Balance(), {}),
        )

        get_expected_eia_callable = MagicMock(return_value=Decimal("250.00"))

        interest_amounts = lending_interfaces.InterestAmounts(
            eia_rounded_accrued=Decimal("50.00"),
            eia_accrued=Decimal("50.00"),
            non_eia_rounded_accrued=Decimal("0.00"),
            non_eia_accrued=Decimal("0.00"),
            total_rounded=Decimal("50.00"),
        )
        interest_application_feature = MagicMock()
        interest_application_feature.apply_interest.return_value = []
        interest_application_feature.get_interest_to_apply.return_value = interest_amounts

        # Custom due principal callable that always returns 123.45 regardless of EMI and interest
        custom_due_principal_callable = MagicMock(return_value=Decimal("123.45"))

        result = due_calc.schedule_logic(
            state=state,
            get_expected_eia_callable=get_expected_eia_callable,
            interest_application_feature=interest_application_feature,
            repayment_hierarchy_config=MagicMock(),
            get_due_principal_callable=custom_due_principal_callable,
        )

        self.assertEqual(len(result.custom_instructions), 1)
        # Verify the event type directives
        expected_directive = UpdateAccountEventTypeDirective(
            event_type=due_calc.DUE_AMOUNT_CALCULATION_EVENT,
            expression=ScheduleExpression(
                year="2020",
                month="2",
                day="28",
                hour="0",
                minute="0",
                second="0",
            ),
        )
        self.assertEqual(result.event_type_directives, [expected_directive])
        postings = result.custom_instructions[0].postings

        # Verify that the custom callable was called with correct parameters
        custom_due_principal_callable.assert_called_once()
        call_args = custom_due_principal_callable.call_args[0]
        self.assertIsInstance(call_args[0], state_utils.SmartContractState)
        self.assertEqual(call_args[1], Decimal("250.00"))
        self.assertEqual(call_args[2], Decimal("50.00"))

        # Check principal postings amount matches 123.45
        principal_due_posting = [
            p
            for p in postings
            if getattr(p, "account_address", None) == lending_addresses.PRINCIPAL_DUE
        ]
        self.assertEqual(len(principal_due_posting), 1)
        self.assertEqual(principal_due_posting[0].amount, Decimal("123.45"))

    @pytest.mark.unit
    def test_schedule_logic_with_excess_knockoff(self):
        # Setup excess balance (-100 net debit -> 100 net credit, meaning customer has 100 overpaid)
        excess_coord = BalanceCoordinate(
            account_address=OVERPAYMENT_ADDRESS,
            asset=DEFAULT_ASSET,
            denomination="GBP",
            phase=Phase.COMMITTED,
        )
        balances = {
            excess_coord: Balance(
                net=Decimal("-100.00"), credit=Decimal("100.00"), debit=Decimal("0.00")
            )
        }

        mock_vault = self._setup_mock_vault(balances=balances)
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME,
            balances=BalanceDefaultDict(lambda: Balance(), balances),
        )

        get_expected_eia_callable = MagicMock(return_value=Decimal("250.00"))

        # Interest application = 50.00
        interest_postings = [
            Posting(
                credit=True,
                amount=Decimal("50.00"),
                denomination="GBP",
                account_id=sentinel.account_id,
                account_address=lending_addresses.INTEREST_DUE,
                asset=DEFAULT_ASSET,
                phase=Phase.COMMITTED,
            )
        ]
        interest_amounts = lending_interfaces.InterestAmounts(
            eia_rounded_accrued=Decimal("50.00"),
            eia_accrued=Decimal("50.00"),
            non_eia_rounded_accrued=Decimal("0.00"),
            non_eia_accrued=Decimal("0.00"),
            total_rounded=Decimal("50.00"),
        )
        interest_application_feature = MagicMock()
        interest_application_feature.apply_interest.return_value = interest_postings
        interest_application_feature.get_interest_to_apply.return_value = interest_amounts

        # Repayment Hierarchy
        repayment_hierarchy_config = MagicMock()
        repayment_order = [
            lending_addresses.INTEREST_DUE,
            lending_addresses.PRINCIPAL_DUE,
        ]
        repayment_hierarchy_config.repayment_hierarchy.get_repayment_hierarchy_order.return_value = (  # noqa: E501
            repayment_order
        )

        result = due_calc.schedule_logic(
            state=state,
            get_expected_eia_callable=get_expected_eia_callable,
            interest_application_feature=interest_application_feature,
            repayment_hierarchy_config=repayment_hierarchy_config,
        )

        self.assertEqual(len(result.custom_instructions), 1)
        self.assertIsInstance(result.custom_instructions[0], CustomInstruction)

        # Verify the event type directives
        expected_directive = UpdateAccountEventTypeDirective(
            event_type=due_calc.DUE_AMOUNT_CALCULATION_EVENT,
            expression=ScheduleExpression(
                year="2020",
                month="2",
                day="28",
                hour="0",
                minute="0",
                second="0",
            ),
        )
        self.assertEqual(result.event_type_directives, [expected_directive])

        # Expected excess postings:
        # NY distribution of 100 excess:
        # 1. 50.00 to INTEREST_DUE (fully paid)
        # 2. 50.00 to PRINCIPAL_DUE (partially paid, as 200 was created)
        # So we expect redistribute_postings for both.
        postings = result.custom_instructions[0].postings
        # In redistribute_postings, it creates postings with debit_address=OVERPAYMENT_ADDRESS.
        debit_overpayment_postings = [
            p
            for p in postings
            if getattr(p, "account_address", None) == OVERPAYMENT_ADDRESS
            and getattr(p, "credit", None) is False
        ]
        self.assertEqual(len(debit_overpayment_postings), 2)
        # Amounts should be 50.00 each
        self.assertEqual(debit_overpayment_postings[0].amount, Decimal("50.00"))
        self.assertEqual(debit_overpayment_postings[1].amount, Decimal("50.00"))

    @pytest.mark.unit
    def test_schedule_logic_monthly_progression_jan_to_feb_clamping(self):
        # Calc day is 31, effective datetime is Jan 31st (non-leap year 2021)
        # Next due should be Feb 28th
        effective_datetime = datetime(2021, 1, 31, 12, 0, 0, tzinfo=UTC)
        mock_vault = self._setup_mock_vault(
            billing_frequency="monthly",
            due_calculation_time="12:00:00",
            due_calculation_day=31,
        )
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            balances=BalanceDefaultDict(lambda: Balance(), {}),
        )

        interest_amounts = lending_interfaces.InterestAmounts(
            eia_rounded_accrued=Decimal("0.00"),
            eia_accrued=Decimal("0.00"),
            non_eia_rounded_accrued=Decimal("0.00"),
            non_eia_accrued=Decimal("0.00"),
            total_rounded=Decimal("0.00"),
        )
        interest_application_feature = MagicMock()
        interest_application_feature.apply_interest.return_value = []
        interest_application_feature.get_interest_to_apply.return_value = interest_amounts

        result = due_calc.schedule_logic(
            state=state,
            get_expected_eia_callable=MagicMock(return_value=Decimal("0.00")),
            interest_application_feature=interest_application_feature,
            repayment_hierarchy_config=MagicMock(),
        )

        # Postings should be empty, but event directives must contain Feb 28th
        self.assertEqual(result.custom_instructions, [])
        expected_directive = UpdateAccountEventTypeDirective(
            event_type=due_calc.DUE_AMOUNT_CALCULATION_EVENT,
            expression=ScheduleExpression(
                year="2021",
                month="2",
                day="28",
                hour="12",
                minute="0",
                second="0",
            ),
        )
        self.assertEqual(result.event_type_directives, [expected_directive])

    @pytest.mark.unit
    def test_schedule_logic_monthly_progression_feb_to_mar_resumption(self):
        # Calc day is 31, effective datetime is Feb 28th (non-leap year 2021)
        # Next due should be Mar 31st
        effective_datetime = datetime(2021, 2, 28, 12, 0, 0, tzinfo=UTC)
        mock_vault = self._setup_mock_vault(
            billing_frequency="monthly",
            due_calculation_time="12:00:00",
            due_calculation_day=31,
        )
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            balances=BalanceDefaultDict(lambda: Balance(), {}),
        )

        interest_amounts = lending_interfaces.InterestAmounts(
            eia_rounded_accrued=Decimal("0.00"),
            eia_accrued=Decimal("0.00"),
            non_eia_rounded_accrued=Decimal("0.00"),
            non_eia_accrued=Decimal("0.00"),
            total_rounded=Decimal("0.00"),
        )
        interest_application_feature = MagicMock()
        interest_application_feature.apply_interest.return_value = []
        interest_application_feature.get_interest_to_apply.return_value = interest_amounts

        result = due_calc.schedule_logic(
            state=state,
            get_expected_eia_callable=MagicMock(return_value=Decimal("0.00")),
            interest_application_feature=interest_application_feature,
            repayment_hierarchy_config=MagicMock(),
        )

        self.assertEqual(result.custom_instructions, [])
        expected_directive = UpdateAccountEventTypeDirective(
            event_type=due_calc.DUE_AMOUNT_CALCULATION_EVENT,
            expression=ScheduleExpression(
                year="2021",
                month="3",
                day="31",
                hour="12",
                minute="0",
                second="0",
            ),
        )
        self.assertEqual(result.event_type_directives, [expected_directive])
