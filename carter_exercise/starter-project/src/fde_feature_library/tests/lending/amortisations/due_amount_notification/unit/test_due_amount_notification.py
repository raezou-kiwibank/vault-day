# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

# features
from feature_library.lending.amortisations import (
    due_amount_notification as due_amount_notification,
)

# contracts api
from contracts_api import AccountNotificationDirective, SmartContractEventType

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest


class DueNotificationAmountTest(FeatureTest):
    maxDiff = None


class ScheduleLogicTest(DueNotificationAmountTest):
    @pytest.mark.unit
    def test_due_amount_notification_type(
        self,
    ):
        product_name = "PRODUCT_A"
        expected_notification_type = (
            f"{product_name}{due_amount_notification.REPAYMENT_NOTIFICATION_SUFFIX}"
        )
        notification_type = due_amount_notification.notification_type(product_name=product_name)
        self.assertEqual(notification_type, expected_notification_type)

    @pytest.mark.unit
    def test_send_repayment_notification(
        self,
    ):
        product_name = "PRODUCT_A"
        due_principal = Decimal("50")
        due_interest = Decimal("0")
        overdue_datetime = datetime(2020, 1, 4, 3, 4, 5, tzinfo=ZoneInfo("UTC"))

        expected_notification_details = {
            "account_id": "account_id",
            "principal_due": str(due_principal),
            "interest_due": str(due_interest),
            "overdue_date": str(overdue_datetime.date()),
        }
        expected_notification_directive = AccountNotificationDirective(
            notification_type=due_amount_notification.notification_type(product_name),
            notification_details=expected_notification_details,
        )

        result = due_amount_notification.send_due_amount_notification(
            account_id="account_id",
            due_principal=due_principal,
            due_interest=due_interest,
            overdue_datetime=overdue_datetime,
            product_name=product_name,
        )

        self.assertEqual(expected_notification_directive, result)

    @pytest.mark.unit
    def test_schedule_logic_no_notification_no_values_provided(self):
        product_name = "PRODUCT_A"
        overdue_datetime = datetime(2019, 12, 31, 3, 4, 5, tzinfo=ZoneInfo("UTC"))
        mock_vault = self.create_mock(account_id="account_id")
        mock_state = MagicMock(vault=mock_vault)

        result = due_amount_notification.schedule_logic(
            state=mock_state,
            product_name=product_name,
            overdue_datetime=overdue_datetime,
        )

        self.assertEqual([], result)

    @pytest.mark.unit
    def test_schedule_logic_no_notification(self):
        product_name = "PRODUCT_A"
        due_principal = Decimal("0")
        due_interest = Decimal("0")
        overdue_datetime = datetime(2019, 12, 31, 3, 4, 5, tzinfo=ZoneInfo("UTC"))
        mock_vault = self.create_mock(account_id="account_id")
        mock_state = MagicMock(vault=mock_vault)

        result = due_amount_notification.schedule_logic(
            state=mock_state,
            product_name=product_name,
            overdue_datetime=overdue_datetime,
            due_interest=due_interest,
            due_principal=due_principal,
        )

        self.assertEqual([], result)

    @patch.object(due_amount_notification, "send_due_amount_notification")
    @pytest.mark.unit
    def test_schedule_logic_notification_sent_only_due_amount_provided(
        self,
        mock_send_due_amount_notification: MagicMock,
    ):
        product_name = "PRODUCT_A"
        due_principal = Decimal("70")
        due_interest = Decimal("0")
        overdue_datetime = datetime(2020, 1, 4, 3, 4, 5, tzinfo=ZoneInfo("UTC"))
        mock_vault = self.create_mock(account_id="account_id")
        mock_state = MagicMock(vault=mock_vault)

        expected_notification_directive = sentinel.notification_directive
        mock_send_due_amount_notification.return_value = expected_notification_directive

        result = due_amount_notification.schedule_logic(
            state=mock_state,
            product_name=product_name,
            overdue_datetime=overdue_datetime,
            due_interest=due_interest,
            due_principal=due_principal,
        )

        self.assertEqual([expected_notification_directive], result)
        mock_send_due_amount_notification.assert_called_once_with(
            account_id="account_id",
            due_principal=due_principal,
            due_interest=due_interest,
            overdue_datetime=overdue_datetime,
            product_name=product_name,
        )

    @patch.object(due_amount_notification, "send_due_amount_notification")
    @pytest.mark.unit
    def test_schedule_logic_notification_sent_only_interest_provided(
        self,
        mock_send_due_amount_notification: MagicMock,
    ):
        product_name = "PRODUCT_A"
        due_principal = Decimal("0")
        due_interest = Decimal("0.1")
        overdue_datetime = datetime(2019, 12, 31, 3, 4, 5, tzinfo=ZoneInfo("UTC"))
        mock_vault = self.create_mock(account_id="account_id")
        mock_state = MagicMock(vault=mock_vault)

        expected_notification_directive = sentinel.notification_directive
        mock_send_due_amount_notification.return_value = expected_notification_directive

        result = due_amount_notification.schedule_logic(
            state=mock_state,
            product_name=product_name,
            overdue_datetime=overdue_datetime,
            due_interest=due_interest,
            due_principal=due_principal,
        )

        self.assertEqual([expected_notification_directive], result)
        mock_send_due_amount_notification.assert_called_once_with(
            account_id="account_id",
            due_principal=due_principal,
            due_interest=due_interest,
            overdue_datetime=overdue_datetime,
            product_name=product_name,
        )

    @pytest.mark.unit
    def test_due_notification_amount_event_types(self):
        product_name = "PRODUCT_A"
        event_types = due_amount_notification.event_types(product_name=product_name)
        self.assertListEqual(
            event_types,
            [
                SmartContractEventType(
                    name=due_amount_notification.NOTIFY_DUE_AMOUNT_EVENT,
                    scheduler_tag_ids=[
                        f"{product_name}_{due_amount_notification.NOTIFY_DUE_AMOUNT_EVENT}_AST"
                    ],
                )
            ],
        )

    @patch.object(due_amount_notification, "get_next_due_amount_notification_schedule")
    @pytest.mark.unit
    def test_due_notification_amount_scheduled_events(
        self,
        mock_get_next_due_amount_notification_schedule: MagicMock,
    ):
        due_amount_datetime = datetime(2020, 2, 5, 3, 4, 5, tzinfo=ZoneInfo("UTC"))
        due_amount_notification_datetime = datetime(2020, 2, 3, 3, 4, 5, tzinfo=ZoneInfo("UTC"))

        mock_get_next_due_amount_notification_schedule.return_value = (
            due_amount_notification_datetime
        )
        mock_state = MagicMock()

        scheduled_events = due_amount_notification.scheduled_events(
            state=mock_state, next_due_amount_calc_datetime=due_amount_datetime
        )

        self.assertEqual(len(scheduled_events), 1)
        event = scheduled_events[due_amount_notification.NOTIFY_DUE_AMOUNT_EVENT]
        self.assertEqual(
            event.start_datetime, due_amount_notification_datetime - relativedelta(seconds=1)
        )

        mock_get_next_due_amount_notification_schedule.assert_called_once_with(
            state=mock_state, next_due_amount_calc_datetime=due_amount_datetime
        )

    @pytest.mark.unit
    def test_get_next_due_amount_notification_schedule(self):
        due_amount_datetime = datetime(2020, 2, 4, 3, 4, 5, tzinfo=ZoneInfo("UTC"))
        mock_state = MagicMock(
            parameters={
                due_amount_notification.NOTIFICATION_PERIOD_PARAM_ID: "2",
                due_amount_notification.DUE_NOTIFICATION_TIME_PARAM_ID: "00:00:00",
            }
        )

        expected_due_amount_notification_datetime = datetime(
            2020, 2, 2, 0, 0, 0, tzinfo=ZoneInfo("UTC")
        )

        next_due_amount_notification_datetime = (
            due_amount_notification.get_next_due_amount_notification_schedule(
                state=mock_state, next_due_amount_calc_datetime=due_amount_datetime
            )
        )

        self.assertEqual(
            next_due_amount_notification_datetime, expected_due_amount_notification_datetime
        )


class GetParametersTest(DueNotificationAmountTest):
    @pytest.mark.unit
    def test_get_repayment_period_parameter(self):
        notification_period_parameter = 100
        mock_state = MagicMock(
            parameters={
                due_amount_notification.NOTIFICATION_PERIOD_PARAM_ID: notification_period_parameter
            }
        )

        result = due_amount_notification.get_notification_period_parameter(state=mock_state)

        self.assertEqual(
            notification_period_parameter,
            result,
        )
