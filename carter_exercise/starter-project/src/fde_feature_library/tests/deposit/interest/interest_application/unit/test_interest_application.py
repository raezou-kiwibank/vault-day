# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, call, patch
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

# features
import feature_library.common.schedule_utils as schedule_utils
import feature_library.deposit.interest.interest_application as interest_application

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    Phase,
    ScheduledEvent,
    ScheduleExpression,
    UpdateAccountEventTypeDirective,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest
from inception_sdk.test_framework.contracts.unit.contracts_api_sentinels import (
    SentinelCustomInstruction,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.utils import initialise_mock_state

DEFAULT_DATETIME = datetime(year=2019, month=1, day=1, tzinfo=ZoneInfo("UTC"))
UTC_ZONE = ZoneInfo("UTC")
ACCRUED_INTEREST_PAYABLE_ADDRESS = "ACCRUED_INTEREST_PAYABLE"
ACCRUED_INTEREST_RECEIVABLE_ADDRESS = "ACCRUED_INTEREST_RECEIVABLE"
APPLICATION_EVENT = "APPLY_INTEREST"
INTEREST_PAID_ACCOUNT = "INTEREST_PAID"
INTEREST_RECEIVED_ACCOUNT = "INTEREST_RECEIVED"


class TestEventTypes(FeatureTest):
    @pytest.mark.unit
    def test_get_event_types_product_name(self):
        result = interest_application.event_types("current_account")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, APPLICATION_EVENT)
        self.assertEqual(result[0].scheduler_tag_ids, ["CURRENT_ACCOUNT_APPLY_INTEREST_AST"])


class TestScheduledEvents(FeatureTest):
    @patch.object(interest_application.schedule_utils, "get_schedule_expression_from_parameters")
    @patch.object(interest_application.schedule_utils, "get_next_schedule_date")
    @patch.object(interest_application, "_append_to_state")
    @pytest.mark.unit
    def test_get_scheduled_events_monthly_frequency(
        self,
        mock_append_to_state: MagicMock,
        mock_get_next_schedule_date: MagicMock,
        mock_get_schedule_expression: MagicMock,
    ):
        # mocks
        mock_vault = self.create_mock()
        mock_vault.events_timezone = UTC_ZONE
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME,
            parameters={
                interest_application.INTEREST_APPLICATION_FREQUENCY_PARAM_ID: (
                    schedule_utils.MONTHLY
                ),
                interest_application.INTEREST_APPLICATION_DAY_PARAM_ID: "1",
                interest_application.INTEREST_APPLICATION_TIME_PARAM_ID: "01:02:03",
            },
        )
        mock_append_to_state.return_value = state
        next_date = datetime(2019, 2, 1, tzinfo=ZoneInfo("UTC"))
        mock_get_next_schedule_date.return_value = next_date
        mock_get_schedule_expression.return_value = ScheduleExpression(hour=1, minute=2, second=3)

        # feature call
        result = interest_application.get_scheduled_events(state=state)

        # assertions
        expected_event = ScheduledEvent(
            start_datetime=DEFAULT_DATETIME + relativedelta(days=1),
            expression=ScheduleExpression(hour=1, minute=2, second=3),
        )
        self.assertEqual(result, {APPLICATION_EVENT: expected_event})
        mock_get_next_schedule_date.assert_called_once_with(
            start_date=DEFAULT_DATETIME, schedule_frequency=schedule_utils.MONTHLY, intended_day=1
        )
        mock_get_schedule_expression.assert_called_once_with(
            time="01:02:03", day=1, month=2, year=2019
        )

    @patch.object(interest_application.schedule_utils, "get_schedule_expression_from_parameters")
    @patch.object(interest_application.schedule_utils, "get_next_schedule_date")
    @patch.object(interest_application, "_append_to_state")
    @pytest.mark.unit
    def test_get_scheduled_events_quarterly_frequency(
        self,
        mock_append_to_state: MagicMock,
        mock_get_next_schedule_date: MagicMock,
        mock_get_schedule_expression: MagicMock,
    ):
        # mocks
        mock_vault = self.create_mock()
        mock_vault.events_timezone = UTC_ZONE
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME,
            parameters={
                interest_application.INTEREST_APPLICATION_FREQUENCY_PARAM_ID: (
                    schedule_utils.QUARTERLY
                ),
                interest_application.INTEREST_APPLICATION_DAY_PARAM_ID: "5",
                interest_application.INTEREST_APPLICATION_TIME_PARAM_ID: "01:02:03",
            },
        )
        mock_append_to_state.return_value = state
        next_date = datetime(2019, 4, 5, tzinfo=ZoneInfo("UTC"))
        mock_get_next_schedule_date.return_value = next_date
        mock_get_schedule_expression.return_value = ScheduleExpression(hour=1, minute=2, second=3)

        # feature call
        result = interest_application.get_scheduled_events(state=state)

        # assertions
        expected_event = ScheduledEvent(
            start_datetime=DEFAULT_DATETIME + relativedelta(days=1),
            expression=ScheduleExpression(hour=1, minute=2, second=3),
        )
        self.assertEqual(result, {APPLICATION_EVENT: expected_event})
        mock_get_next_schedule_date.assert_called_once_with(
            start_date=DEFAULT_DATETIME, schedule_frequency=schedule_utils.QUARTERLY, intended_day=5
        )
        mock_get_schedule_expression.assert_called_once_with(
            time="01:02:03", day=5, month=4, year=2019
        )

    @patch.object(interest_application, "_append_to_state")
    @pytest.mark.unit
    def test_get_scheduled_events_raises_assertion_error_if_params_missing(
        self,
        mock_append_to_state: MagicMock,
    ):
        # mocks
        state = initialise_mock_state(
            effective_datetime=DEFAULT_DATETIME,
            parameters={},
        )
        mock_append_to_state.return_value = state

        # assertions
        with self.assertRaises(AssertionError) as exc:
            interest_application.get_scheduled_events(state=state)
        self.assertIn("The following parameters are missing", str(exc.exception))

    @patch.object(interest_application.schedule_utils, "get_schedule_expression_from_parameters")
    @patch.object(interest_application.schedule_utils, "get_next_schedule_date")
    @patch.object(interest_application, "_append_to_state")
    @pytest.mark.unit
    def test_get_scheduled_events_annually_frequency(
        self,
        mock_append_to_state: MagicMock,
        mock_get_next_schedule_date: MagicMock,
        mock_get_schedule_expression: MagicMock,
    ):
        # mocks
        mock_vault = self.create_mock()
        mock_vault.events_timezone = UTC_ZONE
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME,
            parameters={
                interest_application.INTEREST_APPLICATION_FREQUENCY_PARAM_ID: (
                    schedule_utils.ANNUALLY
                ),
                interest_application.INTEREST_APPLICATION_DAY_PARAM_ID: "5",
                interest_application.INTEREST_APPLICATION_TIME_PARAM_ID: "01:02:03",
            },
        )
        mock_append_to_state.return_value = state
        next_date = datetime(2020, 1, 5, tzinfo=ZoneInfo("UTC"))
        mock_get_next_schedule_date.return_value = next_date
        mock_get_schedule_expression.return_value = ScheduleExpression(hour=1, minute=2, second=3)

        # feature call
        result = interest_application.get_scheduled_events(state=state)

        # assertions
        expected_event = ScheduledEvent(
            start_datetime=DEFAULT_DATETIME + relativedelta(months=1),
            expression=ScheduleExpression(hour=1, minute=2, second=3),
        )
        self.assertEqual(result, {APPLICATION_EVENT: expected_event})
        mock_get_schedule_expression.assert_called_once_with(
            time="01:02:03", day=5, month=1, year=None
        )


class TestScheduleLogic(FeatureTest):
    @patch.object(interest_application, "update_next_schedule_execution")
    @patch.object(interest_application, "_get_application_instructions")
    @patch.object(interest_application, "_append_to_state")
    @pytest.mark.unit
    def test_schedule_logic_calls_helper_correctly(
        self,
        mock_append_to_state: MagicMock,
        mock_get_app_instr: MagicMock,
        mock_update_next_schedule: MagicMock,
    ):
        # mocks
        mock_vault = self.create_mock(account_id="customer_acc")
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME,
            parameters={
                interest_application.denomination_module.DENOMINATION_PARAM_ID: (
                    DEFAULT_DENOMINATION
                ),
                interest_application.APPLICATION_PRECISION_PARAM_ID: 2,
                interest_application.INTEREST_PAID_ACCOUNT_PARAM_ID: INTEREST_PAID_ACCOUNT,
                interest_application.INTEREST_RECEIVED_ACCOUNT_PARAM_ID: INTEREST_RECEIVED_ACCOUNT,
                interest_application.interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID: (
                    "payable_acc"
                ),
                interest_application.interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID: (  # noqa: E501
                    "receivable_acc"
                ),
            },
        )
        mock_append_to_state.return_value = state
        mock_get_app_instr.side_effect = [
            [SentinelCustomInstruction("receivable")],
            [SentinelCustomInstruction("payable")],
        ]
        mock_update_next_schedule.return_value = UpdateAccountEventTypeDirective(
            event_type=APPLICATION_EVENT,
            expression=ScheduleExpression(hour=0),
        )

        # feature call
        result = interest_application.schedule_logic(state=state, account_type="SAVINGS")

        # assertions
        self.assertEqual(
            result.custom_instructions,
            [SentinelCustomInstruction("receivable"), SentinelCustomInstruction("payable")],
        )
        self.assertEqual(len(result.event_type_directives), 1)
        mock_get_app_instr.assert_has_calls(
            [
                call(
                    state=state,
                    address=ACCRUED_INTEREST_RECEIVABLE_ADDRESS,
                    accrual_internal="receivable_acc",
                    application_internal=INTEREST_RECEIVED_ACCOUNT,
                    denomination=DEFAULT_DENOMINATION,
                    precision=2,
                    account_type="SAVINGS",
                    is_payable=False,
                ),
                call(
                    state=state,
                    address=ACCRUED_INTEREST_PAYABLE_ADDRESS,
                    accrual_internal="payable_acc",
                    application_internal=INTEREST_PAID_ACCOUNT,
                    denomination=DEFAULT_DENOMINATION,
                    precision=2,
                    account_type="SAVINGS",
                    is_payable=True,
                ),
            ]
        )

    @patch.object(interest_application, "update_next_schedule_execution")
    @patch.object(interest_application, "_get_application_instructions")
    @patch.object(interest_application, "_append_to_state")
    @pytest.mark.unit
    def test_schedule_logic_with_only_payable_accrued(
        self,
        mock_append_to_state: MagicMock,
        mock_get_app_instr: MagicMock,
        mock_update_next_schedule: MagicMock,
    ):
        # mocks
        mock_vault = self.create_mock(account_id="customer_acc")
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME,
            parameters={
                interest_application.denomination_module.DENOMINATION_PARAM_ID: (
                    DEFAULT_DENOMINATION
                ),
                interest_application.APPLICATION_PRECISION_PARAM_ID: 2,
                interest_application.INTEREST_PAID_ACCOUNT_PARAM_ID: INTEREST_PAID_ACCOUNT,
                interest_application.INTEREST_RECEIVED_ACCOUNT_PARAM_ID: INTEREST_RECEIVED_ACCOUNT,
                interest_application.interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID: (
                    "payable_acc"
                ),
                interest_application.interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID: (  # noqa: E501
                    "receivable_acc"
                ),
            },
        )
        mock_append_to_state.return_value = state
        mock_get_app_instr.side_effect = [
            [],
            [SentinelCustomInstruction("payable")],
        ]
        mock_update_next_schedule.return_value = None

        # feature call
        result = interest_application.schedule_logic(state=state, account_type="SAVINGS")

        # assertions
        self.assertEqual(result.custom_instructions, [SentinelCustomInstruction("payable")])
        self.assertEqual(len(result.event_type_directives), 0)

    @patch.object(interest_application, "_append_to_state")
    @pytest.mark.unit
    def test_schedule_logic_raises_assertion_error_if_params_missing(
        self,
        mock_append_to_state: MagicMock,
    ):
        # mocks
        state = initialise_mock_state(
            effective_datetime=DEFAULT_DATETIME,
            parameters={},
        )
        mock_append_to_state.return_value = state

        # assertions
        with self.assertRaises(AssertionError) as exc:
            interest_application.schedule_logic(state=state, account_type="SAVINGS")
        self.assertIn("The following parameters are missing", str(exc.exception))


class TestGetApplicationInstructions(FeatureTest):
    @patch.object(
        interest_application.accrual_utils, "create_payable_accrual_application_custom_instruction"
    )
    @pytest.mark.unit
    def test_get_application_instructions_returns_empty_if_balance_is_zero(self, mock_accrual_ci):
        state = initialise_mock_state(balances=BalanceDefaultDict(lambda: Balance(), {}))
        result = interest_application._get_application_instructions(
            state=state,
            address="ANY",
            accrual_internal="accrual",
            application_internal="app",
            denomination=DEFAULT_DENOMINATION,
            precision=2,
            account_type="SAVINGS",
            is_payable=True,
        )
        self.assertEqual(result, [])
        mock_accrual_ci.assert_not_called()

    @patch.object(
        interest_application.accrual_utils, "create_payable_accrual_application_custom_instruction"
    )
    @pytest.mark.unit
    def test_get_application_instructions_returns_instructions_for_payable(self, mock_accrual_ci):
        mock_vault = self.create_mock(account_id="customer_acc")
        balances = BalanceDefaultDict(
            lambda: Balance(),
            {
                BalanceCoordinate(
                    ACCRUED_INTEREST_PAYABLE_ADDRESS,
                    DEFAULT_ASSET,
                    DEFAULT_DENOMINATION,
                    Phase.COMMITTED,
                ): Balance(net=Decimal("20.75")),
            },
        )
        state = initialise_mock_state(vault=mock_vault, balances=balances)
        mock_accrual_ci.return_value = [SentinelCustomInstruction("payable")]

        result = interest_application._get_application_instructions(
            state=state,
            address=ACCRUED_INTEREST_PAYABLE_ADDRESS,
            accrual_internal="payable_acc",
            application_internal=INTEREST_PAID_ACCOUNT,
            denomination=DEFAULT_DENOMINATION,
            precision=2,
            account_type="SAVINGS",
            is_payable=True,
        )

        self.assertEqual(result, [SentinelCustomInstruction("payable")])
        mock_accrual_ci.assert_called_once_with(
            customer_account="customer_acc",
            denomination=DEFAULT_DENOMINATION,
            application_amount=Decimal("20.75"),
            accrual_amount=Decimal("20.75"),
            instruction_details=interest_application.posting_utils.standard_instruction_details(
                description=(
                    "Apply 20.75 GBP interest of 20.75 rounded to 2 and consolidate "
                    "20.75 GBP to customer_acc"
                ),
                event_type=APPLICATION_EVENT,
                gl_impacted=True,
                account_type="SAVINGS",
            ),
            accrual_customer_address=ACCRUED_INTEREST_PAYABLE_ADDRESS,
            accrual_internal_account="payable_acc",
            application_customer_address=DEFAULT_ADDRESS,
            application_internal_account=INTEREST_PAID_ACCOUNT,
        )

    @patch.object(
        interest_application.accrual_utils,
        "create_receivable_accrual_application_custom_instruction",
    )
    @pytest.mark.unit
    def test_get_application_instructions_returns_instructions_for_receivable(
        self, mock_accrual_ci
    ):
        mock_vault = self.create_mock(account_id="customer_acc")
        balances = BalanceDefaultDict(
            lambda: Balance(),
            {
                BalanceCoordinate(
                    ACCRUED_INTEREST_RECEIVABLE_ADDRESS,
                    DEFAULT_ASSET,
                    DEFAULT_DENOMINATION,
                    Phase.COMMITTED,
                ): Balance(net=Decimal("-5.50")),
            },
        )
        state = initialise_mock_state(vault=mock_vault, balances=balances)
        mock_accrual_ci.return_value = [SentinelCustomInstruction("receivable")]

        result = interest_application._get_application_instructions(
            state=state,
            address=ACCRUED_INTEREST_RECEIVABLE_ADDRESS,
            accrual_internal="receivable_acc",
            application_internal=INTEREST_RECEIVED_ACCOUNT,
            denomination=DEFAULT_DENOMINATION,
            precision=2,
            account_type="SAVINGS",
            is_payable=False,
        )

        self.assertEqual(result, [SentinelCustomInstruction("receivable")])
        mock_accrual_ci.assert_called_once_with(
            customer_account="customer_acc",
            denomination=DEFAULT_DENOMINATION,
            application_amount=Decimal("5.50"),
            accrual_amount=Decimal("5.50"),
            instruction_details=interest_application.posting_utils.standard_instruction_details(
                description=(
                    "Apply -5.50 GBP interest of -5.50 rounded to 2 and consolidate "
                    "-5.50 GBP to customer_acc"
                ),
                event_type=APPLICATION_EVENT,
                gl_impacted=True,
                account_type="SAVINGS",
            ),
            accrual_customer_address=ACCRUED_INTEREST_RECEIVABLE_ADDRESS,
            accrual_internal_account="receivable_acc",
            application_customer_address=DEFAULT_ADDRESS,
            application_internal_account=INTEREST_RECEIVED_ACCOUNT,
        )


class TestUpdateNextScheduleExecution(FeatureTest):
    @patch.object(interest_application, "get_scheduled_events")
    @pytest.mark.unit
    def test_update_next_schedule_execution_monthly(self, mock_get_scheduled_events: MagicMock):
        state = initialise_mock_state(
            effective_datetime=DEFAULT_DATETIME,
            parameters={
                interest_application.INTEREST_APPLICATION_FREQUENCY_PARAM_ID: (
                    schedule_utils.MONTHLY
                ),
                interest_application.INTEREST_APPLICATION_DAY_PARAM_ID: "1",
            },
        )
        mock_event = ScheduledEvent(expression=ScheduleExpression(hour=1, minute=2, second=3))
        mock_get_scheduled_events.return_value = {APPLICATION_EVENT: mock_event}
        result = interest_application.update_next_schedule_execution(state=state)

        self.assertIsNotNone(result)
        self.assertEqual(result.event_type, APPLICATION_EVENT)
        self.assertEqual(result.expression, mock_event.expression)
        mock_get_scheduled_events.assert_called_once_with(
            state=state, reference_datetime=state.effective_datetime
        )

    @patch.object(interest_application, "get_scheduled_events")
    @pytest.mark.unit
    def test_update_next_schedule_execution_annually_not_february(
        self, mock_get_scheduled_events: MagicMock
    ):
        state = initialise_mock_state(
            effective_datetime=datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC")),
            parameters={
                interest_application.INTEREST_APPLICATION_FREQUENCY_PARAM_ID: (
                    schedule_utils.ANNUALLY
                ),
                interest_application.INTEREST_APPLICATION_DAY_PARAM_ID: "1",
            },
        )
        result = interest_application.update_next_schedule_execution(state=state)
        self.assertIsNone(result)
        mock_get_scheduled_events.assert_not_called()

    @patch.object(interest_application, "get_scheduled_events")
    @pytest.mark.unit
    def test_update_next_schedule_execution_annually_february_29th(
        self, mock_get_scheduled_events: MagicMock
    ):
        state = initialise_mock_state(
            effective_datetime=datetime(2020, 2, 1, tzinfo=ZoneInfo("UTC")),
            parameters={
                interest_application.INTEREST_APPLICATION_FREQUENCY_PARAM_ID: (
                    schedule_utils.ANNUALLY
                ),
                interest_application.INTEREST_APPLICATION_DAY_PARAM_ID: "29",
            },
        )
        mock_event = ScheduledEvent(expression=ScheduleExpression(year=2021))
        mock_get_scheduled_events.return_value = {APPLICATION_EVENT: mock_event}

        result = interest_application.update_next_schedule_execution(state=state)
        self.assertIsNotNone(result)
        self.assertEqual(result.event_type, APPLICATION_EVENT)
        self.assertEqual(result.expression, mock_event.expression)
        mock_get_scheduled_events.assert_called_once_with(
            state=state, reference_datetime=state.effective_datetime
        )

    @pytest.mark.unit
    def test_update_next_schedule_execution_raises_assertion_error_if_params_missing(
        self,
    ):
        # mocks
        state = initialise_mock_state(
            effective_datetime=DEFAULT_DATETIME,
            parameters={},
        )

        # assertions
        with self.assertRaises(AssertionError) as exc:
            interest_application.update_next_schedule_execution(state=state)
        self.assertIn("The following parameters are missing", str(exc.exception))
