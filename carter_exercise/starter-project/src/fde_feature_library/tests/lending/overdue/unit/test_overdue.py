# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, call, patch, sentinel
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

# features
import feature_library.lending.overdue.overdue as overdue

# contracts api
from contracts_api import (
    AccountNotificationDirective,
    AttributeHookArguments,
    AttributeHookResult,
    BalanceDefaultDict,
    CustomInstruction,
    ScheduledEvent,
    ScheduledEventHookArguments,
    SmartContractEventType,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest
from inception_sdk.test_framework.contracts.unit.contracts_api_sentinels import (
    SentinelPosting,
)

UTC = ZoneInfo("UTC")
DEFAULT_DATETIME = datetime(2020, 1, 2, 3, tzinfo=UTC)


class OverdueTest(FeatureTest):
    maxDiff = None


sentinel_instruction_details = {"sentinel": "details"}  # TODO: sentinel-ize in the future


class ScheduleLogicTest(OverdueTest):
    @pytest.mark.unit
    def test_overdue_repayment_notification_type(
        self,
    ):
        product_name = "product_a"
        expected_notification_type = (
            f"{product_name.upper()}{overdue.OVERDUE_REPAYMENT_NOTIFICATION_SUFFIX}"
        )
        # run function
        result_notification_type = overdue.notification_type(product_name=product_name)
        # validate results
        self.assertEqual(result_notification_type, expected_notification_type)

    @patch.object(overdue, "notification_type")
    @pytest.mark.unit
    def test_get_overdue_repayment_notification_has_due_principal_only(
        self, mock_notification_type: MagicMock
    ):
        # expected values
        product_name = "PRODUCT_A"
        effective_datetime = DEFAULT_DATETIME
        due_principal_amount = Decimal("700")
        due_interest_amount = Decimal("0")
        late_repayment_fee = Decimal("0")

        expected_notification_type = (
            f"{product_name}{overdue.OVERDUE_REPAYMENT_NOTIFICATION_SUFFIX}"
        )
        mock_notification_type.return_value = expected_notification_type

        # construct expected result
        expected_notification_details = {
            "account_id": sentinel.account_id,
            "overdue_principal": str(due_principal_amount),
            "overdue_interest": str(due_interest_amount),
            "late_repayment_fee": str(late_repayment_fee),
            "overdue_date": str(effective_datetime.date()),
        }
        expected_notifications: list[AccountNotificationDirective] = [
            AccountNotificationDirective(
                notification_type=expected_notification_type,
                notification_details=expected_notification_details,
            )
        ]

        # run function
        result_notifications = overdue.get_overdue_repayment_notification(
            account_id=sentinel.account_id,
            product_name=product_name,
            effective_datetime=effective_datetime,
            overdue_principal_amount=due_principal_amount,
            overdue_interest_amount=due_interest_amount,
        )
        # validate results
        self.assertListEqual(expected_notifications, result_notifications)

    @patch.object(overdue, "notification_type")
    @pytest.mark.unit
    def test_get_overdue_repayment_notification_has_due_interest_only(
        self, mock_notification_type: MagicMock
    ):
        # expected values
        product_name = "PRODUCT_A"
        effective_datetime = DEFAULT_DATETIME
        due_principal_amount = Decimal("0")
        due_interest_amount = Decimal("12")
        late_repayment_fee = Decimal("0")

        expected_notification_type = (
            f"{product_name}{overdue.OVERDUE_REPAYMENT_NOTIFICATION_SUFFIX}"
        )
        mock_notification_type.return_value = expected_notification_type

        # construct expected result
        expected_notification_details = {
            "account_id": sentinel.account_id,
            "overdue_principal": str(due_principal_amount),
            "overdue_interest": str(due_interest_amount),
            "late_repayment_fee": str(late_repayment_fee),
            "overdue_date": str(effective_datetime.date()),
        }
        expected_notifications: list[AccountNotificationDirective] = [
            AccountNotificationDirective(
                notification_type=expected_notification_type,
                notification_details=expected_notification_details,
            )
        ]

        # run function
        result_notifications = overdue.get_overdue_repayment_notification(
            account_id=sentinel.account_id,
            product_name=product_name,
            effective_datetime=effective_datetime,
            overdue_principal_amount=due_principal_amount,
            overdue_interest_amount=due_interest_amount,
        )
        # validate results
        self.assertListEqual(expected_notifications, result_notifications)

    @patch.object(overdue, "notification_type")
    @pytest.mark.unit
    def test_get_overdue_repayment_notification_has_both_due_principal_and_due_interest(
        self, mock_notification_type: MagicMock
    ):
        # expected values
        product_name = "PRODUCT_A"
        effective_datetime = DEFAULT_DATETIME
        due_principal_amount = Decimal("120")
        due_interest_amount = Decimal("12")
        late_repayment_fee = Decimal("10")

        expected_notification_type = (
            f"{product_name}{overdue.OVERDUE_REPAYMENT_NOTIFICATION_SUFFIX}"
        )
        mock_notification_type.return_value = expected_notification_type

        # construct expected result
        expected_notification_details = {
            "account_id": sentinel.account_id,
            "overdue_principal": str(due_principal_amount),
            "overdue_interest": str(due_interest_amount),
            "late_repayment_fee": str(late_repayment_fee),
            "overdue_date": str(effective_datetime.date()),
        }
        expected_notifications: list[AccountNotificationDirective] = [
            AccountNotificationDirective(
                notification_type=expected_notification_type,
                notification_details=expected_notification_details,
            )
        ]

        # run function
        result_notifications = overdue.get_overdue_repayment_notification(
            account_id=sentinel.account_id,
            product_name=product_name,
            effective_datetime=effective_datetime,
            overdue_principal_amount=due_principal_amount,
            overdue_interest_amount=due_interest_amount,
            late_repayment_fee=late_repayment_fee,
        )
        # validate results
        self.assertListEqual(expected_notifications, result_notifications)

    @patch.object(overdue, "notification_type")
    @pytest.mark.unit
    def test_get_overdue_repayment_notification_has_late_repayment_fee(
        self, mock_notification_type: MagicMock
    ):
        # expected values
        product_name = "PRODUCT_A"
        effective_datetime = DEFAULT_DATETIME
        due_principal_amount = Decimal("12")
        due_interest_amount = Decimal("0")
        late_repayment_fee = Decimal("10")

        expected_notification_type = (
            f"{product_name}{overdue.OVERDUE_REPAYMENT_NOTIFICATION_SUFFIX}"
        )
        mock_notification_type.return_value = expected_notification_type

        # construct expected result
        expected_notification_details = {
            "account_id": sentinel.account_id,
            "overdue_principal": str(due_principal_amount),
            "overdue_interest": str(due_interest_amount),
            "late_repayment_fee": str(late_repayment_fee),
            "overdue_date": str(effective_datetime.date()),
        }
        expected_notifications: list[AccountNotificationDirective] = [
            AccountNotificationDirective(
                notification_type=expected_notification_type,
                notification_details=expected_notification_details,
            )
        ]

        # run function
        result_notifications = overdue.get_overdue_repayment_notification(
            account_id=sentinel.account_id,
            product_name=product_name,
            effective_datetime=effective_datetime,
            overdue_principal_amount=due_principal_amount,
            overdue_interest_amount=due_interest_amount,
            late_repayment_fee=late_repayment_fee,
        )
        # validate results
        self.assertListEqual(expected_notifications, result_notifications)

    @pytest.mark.unit
    def test_get_overdue_repayment_notification_no_due_principal_and_due_interest(self):
        # expected values
        product_name = "PRODUCT_A"
        effective_datetime = DEFAULT_DATETIME
        due_principal_amount = Decimal("0")
        due_interest_amount = Decimal("0")
        late_repayment_fee = Decimal("10")
        # run function
        result_notifications = overdue.get_overdue_repayment_notification(
            account_id=sentinel.account_id,
            product_name=product_name,
            effective_datetime=effective_datetime,
            overdue_principal_amount=due_principal_amount,
            overdue_interest_amount=due_interest_amount,
            late_repayment_fee=late_repayment_fee,
        )
        # validate results
        self.assertListEqual(result_notifications, [])

    @patch.object(overdue.posting_utils, "create_postings")
    @patch.object(overdue.posting_utils, "standard_instruction_details")
    @pytest.mark.unit
    def test_scheduled_logic_without_overdue_accumulation(
        self,
        mock_standard_instruction_details: MagicMock,
        mock_create_postings: MagicMock,
    ):
        # construct mocks
        mock_state = MagicMock(
            parameters={overdue.denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination},
            balances=BalanceDefaultDict(mapping={}),
            vault=self.create_mock(),
        )
        mock_create_postings.return_value = []

        # run function
        result = overdue.schedule_logic(
            state=mock_state,
            account_type=sentinel.account_type,
            hook_arguments=ScheduledEventHookArguments(
                event_type=sentinel.event_type,
                effective_datetime=DEFAULT_DATETIME,
            ),
        )
        # validate results
        self.assertListEqual(result.custom_instructions, [])
        self.assertListEqual(result.notification_directives, [])

    @patch.object(overdue.posting_utils, "create_postings")
    @patch.object(overdue.balance_utils, "balance_at_coordinates")
    @patch.object(overdue, "get_overdue_repayment_notification")
    @pytest.mark.unit
    def test_scheduled_logic_with_overdue_accumulation(
        self,
        mock_get_overdue_repayment_notification: MagicMock,
        mock_get_balance_at_coordinates: MagicMock,
        mock_create_postings: MagicMock,
    ):
        # expected values
        principal_postings = [SentinelPosting(f"principal_{i}") for i in range(2)]
        interest_postings = [SentinelPosting(f"interest_{i}") for i in range(2)]
        # construct expected result
        expected_instructions = [
            CustomInstruction(
                postings=[*principal_postings, *interest_postings],  # type: ignore
                override_all_restrictions=True,
                instruction_details={
                    "description": "Move outstanding due debt into overdue debt.",
                    "event_type": sentinel.event_type,
                    "gl_impacted": "False",
                    "account_type": sentinel.account_type,
                },
            )
        ]
        # construct mocks

        mock_create_postings.side_effect = [principal_postings, interest_postings]
        mock_state = MagicMock(
            parameters={overdue.denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination},
            vault=self.create_mock(),
            balances=sentinel.balances_overdue,
        )
        mock_get_overdue_repayment_notification.return_value = []
        # run function
        result = overdue.schedule_logic(
            state=mock_state,
            account_type=sentinel.account_type,
            hook_arguments=ScheduledEventHookArguments(
                event_type=sentinel.event_type,
                effective_datetime=DEFAULT_DATETIME,
            ),
        )
        # validate results
        self.assertListEqual(result.custom_instructions, expected_instructions)

        mock_get_balance_at_coordinates.assert_has_calls(
            calls=[
                call(
                    balances=sentinel.balances_overdue,
                    address=overdue.lending_addresses.PRINCIPAL_DUE,
                    denomination=sentinel.denomination,
                ),
                call(
                    balances=sentinel.balances_overdue,
                    address=overdue.lending_addresses.INTEREST_DUE,
                    denomination=sentinel.denomination,
                ),
            ]
        )

    @patch.object(overdue.posting_utils, "create_postings")
    @patch.object(overdue.balance_utils, "balance_at_coordinates")
    @patch.object(overdue, "get_overdue_repayment_notification")
    @pytest.mark.unit
    def test_scheduled_logic_with_notification_and_late_repayment_fee(
        self,
        mock_get_overdue_repayment_notification: MagicMock,
        mock_get_balance_at_coordinates: MagicMock,
        mock_create_postings: MagicMock,
    ):
        # expected_values
        product_name = "product_a"
        dummy_amount = Decimal("100")
        due_principal_amount = dummy_amount
        due_interest_amount = dummy_amount
        late_repayment_fee = Decimal("10")
        effective_datetime = DEFAULT_DATETIME

        principal_postings = [SentinelPosting(f"principal_{i}") for i in range(2)]
        interest_postings = [SentinelPosting(f"interest_{i}") for i in range(2)]

        mock_state = MagicMock(
            parameters={overdue.denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination},
            balances=sentinel.balances_overdue,
            vault=self.create_mock(),
        )

        # construct expected result
        expected_instructions = [
            CustomInstruction(
                postings=[*principal_postings, *interest_postings],  # type: ignore
                override_all_restrictions=True,
                instruction_details={
                    "description": "Move outstanding due debt into overdue debt.",
                    "event_type": sentinel.event_type,
                    "gl_impacted": "False",
                    "account_type": product_name,
                },
            )
        ]
        expected_notification_details = {
            "account_id": str(mock_state.vault.account_id),
            "overdue_principal": str(due_principal_amount),
            "overdue_interest": str(due_interest_amount),
            "late_repayment_fee": str(late_repayment_fee),
            "overdue_date": str(effective_datetime),
        }
        expected_notifications: list[AccountNotificationDirective] = [
            AccountNotificationDirective(
                notification_type=overdue.notification_type(product_name),
                notification_details=expected_notification_details,
            )
        ]

        # construct mocks

        mock_create_postings.side_effect = [principal_postings, interest_postings]
        mock_get_balance_at_coordinates.return_value = dummy_amount
        mock_get_overdue_repayment_notification.return_value = expected_notifications

        # run function
        result = overdue.schedule_logic(
            state=mock_state,
            account_type=product_name,
            hook_arguments=ScheduledEventHookArguments(
                event_type=sentinel.event_type,
                effective_datetime=effective_datetime,
            ),
            late_repayment_fee=late_repayment_fee,
        )

        # validate results
        self.assertListEqual(result.custom_instructions, expected_instructions)
        self.assertListEqual(result.notification_directives, expected_notifications)

        mock_get_balance_at_coordinates.assert_has_calls(
            calls=[
                call(
                    balances=sentinel.balances_overdue,
                    address=overdue.lending_addresses.PRINCIPAL_DUE,
                    denomination=sentinel.denomination,
                ),
                call(
                    balances=sentinel.balances_overdue,
                    address=overdue.lending_addresses.INTEREST_DUE,
                    denomination=sentinel.denomination,
                ),
            ]
        )
        mock_get_overdue_repayment_notification.assert_called_with(
            account_id=mock_state.vault.account_id,
            product_name=product_name,
            effective_datetime=effective_datetime,
            overdue_principal_amount=due_principal_amount,
            overdue_interest_amount=due_interest_amount,
            late_repayment_fee=late_repayment_fee,
        )

    @patch.object(overdue.posting_utils, "create_postings")
    @patch.object(overdue.balance_utils, "balance_at_coordinates")
    @patch.object(overdue, "get_overdue_repayment_notification")
    @pytest.mark.unit
    def test_scheduled_logic_with_notification_and_without_late_repayment_fee(
        self,
        mock_get_overdue_repayment_notification: MagicMock,
        mock_get_balance_at_coordinates: MagicMock,
        mock_create_postings: MagicMock,
    ):
        # expected_values
        product_name = "product_a"
        dummy_amount = Decimal("100")
        due_principal_amount = dummy_amount
        due_interest_amount = dummy_amount
        late_repayment_fee = Decimal("0")
        effective_datetime = DEFAULT_DATETIME

        principal_postings = [SentinelPosting(f"principal_{i}") for i in range(2)]
        interest_postings = [SentinelPosting(f"interest_{i}") for i in range(2)]
        mock_state = MagicMock(
            parameters={overdue.denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination},
            balances=sentinel.balances_overdue,
            vault=self.create_mock(),
        )

        # construct expected result
        expected_instructions = [
            CustomInstruction(
                postings=[*principal_postings, *interest_postings],  # type: ignore
                override_all_restrictions=True,
                instruction_details={
                    "description": "Move outstanding due debt into overdue debt.",
                    "event_type": sentinel.event_type,
                    "gl_impacted": "False",
                    "account_type": product_name,
                },
            )
        ]
        expected_notification_details = {
            "account_id": str(mock_state.vault.account_id),
            "overdue_principal": str(due_principal_amount),
            "overdue_interest": str(due_interest_amount),
            "late_repayment_fee": str(late_repayment_fee),
            "overdue_date": str(effective_datetime),
        }
        expected_notifications: list[AccountNotificationDirective] = [
            AccountNotificationDirective(
                notification_type=overdue.notification_type(product_name),
                notification_details=expected_notification_details,
            )
        ]

        # construct mocks

        mock_create_postings.side_effect = [principal_postings, interest_postings]
        mock_get_balance_at_coordinates.return_value = dummy_amount
        mock_get_overdue_repayment_notification.return_value = expected_notifications

        # run function
        result = overdue.schedule_logic(
            state=mock_state,
            account_type=product_name,
            hook_arguments=ScheduledEventHookArguments(
                event_type=sentinel.event_type,
                effective_datetime=effective_datetime,
            ),
        )

        # validate results
        self.assertListEqual(result.custom_instructions, expected_instructions)
        self.assertListEqual(result.notification_directives, expected_notifications)

        mock_get_balance_at_coordinates.assert_has_calls(
            calls=[
                call(
                    balances=sentinel.balances_overdue,
                    address=overdue.lending_addresses.PRINCIPAL_DUE,
                    denomination=sentinel.denomination,
                ),
                call(
                    balances=sentinel.balances_overdue,
                    address=overdue.lending_addresses.INTEREST_DUE,
                    denomination=sentinel.denomination,
                ),
            ]
        )
        mock_get_overdue_repayment_notification.assert_called_with(
            account_id=mock_state.vault.account_id,
            product_name=product_name,
            effective_datetime=effective_datetime,
            overdue_principal_amount=due_principal_amount,
            overdue_interest_amount=due_interest_amount,
            late_repayment_fee=late_repayment_fee,
        )


class ScheduleEventsTest(OverdueTest):
    @pytest.mark.unit
    def test_overdue_event_types(self):
        # run function
        event_types = overdue.event_types(product_name="product_a")
        # validate results
        self.assertListEqual(
            event_types,
            [
                SmartContractEventType(
                    name="CHECK_OVERDUE",
                    scheduler_tag_ids=["PRODUCT_A_CHECK_OVERDUE_AST"],
                )
            ],
        )

    @pytest.mark.unit
    def test_overdue_check_after_specified_days_after_due_calculation(
        self,
    ):
        # expected values
        due_calc_dt = datetime(2020, 1, 2, 3, 4, 5, tzinfo=UTC)
        # construct mocks
        mock_vault = MagicMock(events_timezone=UTC)
        mock_state = MagicMock(
            parameters={
                overdue.REPAYMENT_PERIOD_PARAM_ID: "7",
                overdue.CHECK_OVERDUE_TIME_PARAM_ID: "00:00:00",
            },
            vault=mock_vault,
        )
        sched_expr = overdue.ScheduleExpression(
            year=None,
            month=None,
            day="9",
            hour="0",
            minute="0",
            second="0",
        )
        # construct expected result
        expected = {
            overdue.CHECK_OVERDUE_EVENT: ScheduledEvent(
                start_datetime=due_calc_dt.replace(hour=0, minute=0, second=0)
                + relativedelta(days=7),
                expression=sched_expr,
                skip=False,
            )
        }
        # run function
        scheduled_events = overdue.scheduled_events(
            state=mock_state,
            first_due_amount_calculation_datetime=due_calc_dt,
        )
        # validate results

        self.assertDictEqual(scheduled_events, expected)

    @pytest.mark.unit
    def test_overdue_check_after_specified_days_after_due_calculation_skip(
        self,
    ):
        # expected values
        due_calc_dt = datetime(2020, 1, 2, 3, 4, 5, tzinfo=UTC)
        # construct mocks
        mock_vault = MagicMock(events_timezone=UTC)
        mock_state = MagicMock(
            parameters={
                overdue.REPAYMENT_PERIOD_PARAM_ID: "7",
                overdue.CHECK_OVERDUE_TIME_PARAM_ID: "00:00:00",
            },
            vault=mock_vault,
        )
        sched_expr = overdue.ScheduleExpression(
            year=None,
            month=None,
            day="9",
            hour="0",
            minute="0",
            second="0",
        )
        # construct expected result
        expected = {
            overdue.CHECK_OVERDUE_EVENT: ScheduledEvent(
                start_datetime=due_calc_dt.replace(hour=0, minute=0, second=0)
                + relativedelta(days=7),
                expression=sched_expr,
                skip=True,
            )
        }
        # run function
        scheduled_events = overdue.scheduled_events(
            state=mock_state, first_due_amount_calculation_datetime=due_calc_dt, skip=True
        )

        # validate results
        self.assertDictEqual(scheduled_events, expected)

    @pytest.mark.unit
    def test_overdue_check_after_specified_days_after_due_calculation_one_off(
        self,
    ):
        # expected values
        due_calc_dt = datetime(2020, 1, 2, 3, 4, 5, tzinfo=UTC)
        # construct mocks
        mock_vault = MagicMock(events_timezone=UTC)
        mock_state = MagicMock(
            parameters={
                overdue.REPAYMENT_PERIOD_PARAM_ID: "7",
                overdue.CHECK_OVERDUE_TIME_PARAM_ID: "00:00:00",
            },
            vault=mock_vault,
        )
        sched_expr = overdue.ScheduleExpression(
            year="2020",
            month="1",
            day="9",
            hour="0",
            minute="0",
            second="0",
        )
        # construct expected result
        expected = {
            overdue.CHECK_OVERDUE_EVENT: ScheduledEvent(
                start_datetime=due_calc_dt.replace(hour=0, minute=0, second=0)
                + relativedelta(days=7),
                expression=sched_expr,
                skip=False,
            )
        }
        # run function
        scheduled_events = overdue.scheduled_events(
            state=mock_state, first_due_amount_calculation_datetime=due_calc_dt, is_one_off=True
        )

        # validate results
        self.assertDictEqual(scheduled_events, expected)


class OverdueHelperTest(OverdueTest):
    @pytest.mark.unit
    def test_get_overdue_datetime(self):
        # expected values
        notification_period = 2
        repayment_period = 2
        due_amount_notification_datetime = datetime(2020, 2, 4, 3, 4, 5, tzinfo=UTC)

        # construct expected result
        # expected_overdue_datetime = due_amount_notification_datetime
        # + repayment_period + notification_period
        # hour minute second is not considered and will remain the same
        expected_due_amount_notification_datetime = datetime(2020, 2, 8, 3, 4, 5, tzinfo=UTC)

        # run function
        next_due_amount_notification_datetime = overdue.get_overdue_datetime(
            due_amount_notification_datetime=due_amount_notification_datetime,
            repayment_period=repayment_period,
            notification_period=notification_period,
        )

        # validate results
        self.assertEqual(
            next_due_amount_notification_datetime, expected_due_amount_notification_datetime
        )


class GetParametersTest(OverdueTest):
    @pytest.mark.unit
    def test_get_repayment_period_parameter(self):
        repayment_period_parameter = 100

        mock_state = MagicMock(
            parameters={overdue.REPAYMENT_PERIOD_PARAM_ID: repayment_period_parameter}
        )

        result = overdue.get_repayment_period_parameter(state=mock_state)

        self.assertEqual(
            repayment_period_parameter,
            result,
        )

    @pytest.mark.unit
    def test_next_overdue_attribute_handler(self):
        mock_state = MagicMock(parameters={overdue.REPAYMENT_PERIOD_PARAM_ID: 5})
        previous_event = DEFAULT_DATETIME - relativedelta(months=1)
        expected = previous_event + relativedelta(days=5)

        mock_state.vault.get_last_scheduled_event_datetimes_observation.return_value.last_scheduled_event_datetimes = {
            "DUE_AMOUNT_CALCULATION": previous_event
        }

        hook_arguments = AttributeHookArguments(
            attribute_name=overdue.PARAM_NEXT_OVERDUE_DATE, effective_datetime=DEFAULT_DATETIME
        )

        self.assertEqual(
            overdue.next_overdue_attribute_handler(
                state=mock_state,
                hook_arguments=hook_arguments,
            ),
            AttributeHookResult(attribute_value=expected.isoformat()),
        )
