# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel
from zoneinfo import ZoneInfo

import pytest

# features
import feature_library.lending.delinquency.delinquency as delinquency

# contracts api
from contracts_api import (
    AccountNotificationDirective,
    ScheduledEvent,
    ScheduleExpression,
    SmartContractEventType,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

DEFAULT_DATE = datetime(2020, 1, 2, 3, tzinfo=ZoneInfo("UTC"))


class DelinquencyTest(FeatureTest):
    maxDiff = None


class ScheduleLogicTest(DelinquencyTest):
    def setUp(self):
        self.mock_vault = self.create_mock(account_id="account_id")
        self.product_name = "PRODUCT_A"

    @pytest.mark.unit
    def test_delinquency_notification_type(
        self,
    ):
        expected_notification_type = (
            f"{self.product_name}{delinquency.MARK_DELINQUENT_NOTIFICATION_SUFFIX}"
        )
        notification_type = delinquency.notification_type(product_name=self.product_name)
        self.assertEqual(notification_type, expected_notification_type)

    @patch.object(delinquency.balance_utils, "net_debit")
    @patch.object(delinquency.balance_utils, "sum_balances")
    @pytest.mark.unit
    def test_schedule_logic_has_remaining_debt_notification_sent(
        self, mock_sum_balances: MagicMock, mock_net_debit: MagicMock
    ):
        mock_net_debit.return_value = Decimal("0.1")
        expected_notification_details = {"account_id": str(self.mock_vault.account_id)}
        expected_notification_directive = [
            AccountNotificationDirective(
                notification_type=delinquency.notification_type(self.product_name),
                notification_details=expected_notification_details,
            )
        ]

        mock_state = MagicMock(vault=self.mock_vault, balances=sentinel.balances)

        result = delinquency.schedule_logic(
            state=mock_state,
            product_name=self.product_name,
            addresses=sentinel.addresses,
            denomination=sentinel.denomination,
        )
        self.assertEqual(expected_notification_directive, result)
        mock_sum_balances.assert_called_once_with(
            balances=sentinel.balances,
            addresses=sentinel.addresses,
            denomination=sentinel.denomination,
        )

    @patch.object(delinquency.balance_utils, "net_debit")
    @patch.object(delinquency.balance_utils, "sum_balances")
    @pytest.mark.unit
    def test_schedule_logic_has_no_remaining_debt_no_notification_sent(
        self, mock_sum_balances: MagicMock, mock_net_debit: MagicMock
    ):
        mock_net_debit.return_value = Decimal("0")
        mock_state = MagicMock(vault=self.mock_vault, balances=sentinel.balances)

        result = delinquency.schedule_logic(
            state=mock_state,
            product_name=self.product_name,
            addresses=sentinel.addresses,
            denomination=sentinel.denomination,
        )
        self.assertListEqual(result, [])
        mock_sum_balances.assert_called_once_with(
            balances=sentinel.balances,
            addresses=sentinel.addresses,
            denomination=sentinel.denomination,
        )

    @patch.object(delinquency.balance_utils, "net_debit")
    @patch.object(delinquency.balance_utils, "sum_balances")
    @pytest.mark.unit
    def test_schedule_logic_has_negative_remaining_debt_no_notification_sent(
        self, mock_sum_balances: MagicMock, mock_net_debit: MagicMock
    ):
        mock_net_debit.return_value = Decimal("-0.1")
        mock_state = MagicMock(vault=self.mock_vault, balances=sentinel.balances)

        result = delinquency.schedule_logic(
            state=mock_state,
            product_name=self.product_name,
            addresses=sentinel.addresses,
            denomination=sentinel.denomination,
        )
        self.assertListEqual(result, [])
        mock_sum_balances.assert_called_once_with(
            balances=sentinel.balances,
            addresses=sentinel.addresses,
            denomination=sentinel.denomination,
        )


class ScheduleEventsTest(DelinquencyTest):
    @pytest.mark.unit
    def test_delinquency_event_types(
        self,
    ):
        product_name = "PRODUCT_A"
        event_types = delinquency.event_types(product_name=product_name)
        self.assertListEqual(
            event_types,
            [
                SmartContractEventType(
                    name=delinquency.CHECK_DELINQUENCY_EVENT,
                    scheduler_tag_ids=[f"{product_name}_{delinquency.CHECK_DELINQUENCY_EVENT}_AST"],
                )
            ],
        )

    @pytest.mark.unit
    def test_delinquency_check_scheduled_events_recurring(
        self,
    ):
        start_dt = datetime(2020, 1, 2, 3, 4, 5, tzinfo=ZoneInfo("UTC"))

        mock_vault = MagicMock(events_timezone=ZoneInfo("UTC"))
        mock_state = MagicMock(
            parameters={delinquency.CHECK_DELINQUENCY_TIME_PARAM_ID: "00:00:00"},
            vault=mock_vault,
        )

        result = delinquency.scheduled_events(state=mock_state, start_datetime=start_dt)
        expected = {
            delinquency.CHECK_DELINQUENCY_EVENT: ScheduledEvent(
                start_datetime=start_dt.replace(hour=0, minute=0, second=0),
                expression=ScheduleExpression(
                    year=None,
                    month=None,
                    day=str(start_dt.day),
                    hour="0",
                    minute="0",
                    second="0",
                ),
                skip=False,
            )
        }

        self.assertDictEqual(result, expected)

    @pytest.mark.unit
    def test_delinquency_check_scheduled_events_one_off(
        self,
    ):
        start_dt = datetime(2020, 1, 2, 3, 4, 5, tzinfo=ZoneInfo("UTC"))
        mock_vault = MagicMock(events_timezone=ZoneInfo("UTC"))
        mock_state = MagicMock(
            parameters={delinquency.CHECK_DELINQUENCY_TIME_PARAM_ID: "00:00:00"},
            vault=mock_vault,
        )

        result = delinquency.scheduled_events(
            state=mock_state, start_datetime=start_dt, is_one_off=True
        )
        expected = {
            delinquency.CHECK_DELINQUENCY_EVENT: ScheduledEvent(
                start_datetime=start_dt.replace(hour=0, minute=0, second=0),
                expression=ScheduleExpression(
                    year=str(start_dt.year),
                    month=str(start_dt.month),
                    day=str(start_dt.day),
                    hour="0",
                    minute="0",
                    second="0",
                ),
                skip=False,
            )
        }

        self.assertDictEqual(result, expected)

    @pytest.mark.unit
    def test_delinquency_check_scheduled_events_skipped(
        self,
    ):
        start_dt = datetime(2020, 1, 2, 3, 4, 5, tzinfo=ZoneInfo("UTC"))
        mock_vault = MagicMock(events_timezone=ZoneInfo("UTC"))
        mock_state = MagicMock(
            parameters={delinquency.CHECK_DELINQUENCY_TIME_PARAM_ID: "00:00:00"},
            vault=mock_vault,
        )

        result = delinquency.scheduled_events(state=mock_state, start_datetime=start_dt, skip=True)
        expected = {
            delinquency.CHECK_DELINQUENCY_EVENT: ScheduledEvent(
                start_datetime=start_dt.replace(hour=0, minute=0, second=0),
                expression=ScheduleExpression(
                    year=None,
                    month=None,
                    day=str(start_dt.day),
                    hour="0",
                    minute="0",
                    second="0",
                ),
                skip=True,
            )
        }

        self.assertDictEqual(result, expected)
