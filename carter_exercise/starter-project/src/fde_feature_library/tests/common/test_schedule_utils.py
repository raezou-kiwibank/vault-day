# standard libs
from datetime import datetime
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest

# features
import feature_library.common.schedule_utils as schedule_utils

# contracts api
from contracts_api import EndOfMonthSchedule, ScheduleExpression, ScheduleFailover

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

UTC = ZoneInfo("UTC")

DEFAULT_DATETIME = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)


class TestGetScheduleExpressionFromParameters(FeatureTest):
    @pytest.mark.unit
    def test_get_schedule_expression_only_time(self):
        result = schedule_utils.get_schedule_expression_from_parameters(time="12:34:56")
        expected = ScheduleExpression(hour=12, minute=34, second=56)
        self.assertEqual(result, expected)

    @pytest.mark.unit
    def test_get_schedule_expression_with_day_and_month(self):
        result = schedule_utils.get_schedule_expression_from_parameters(
            time="01:02:03", day=15, month=6
        )
        expected = ScheduleExpression(hour=1, minute=2, second=3, day="15", month="6")
        self.assertEqual(result, expected)

    @pytest.mark.unit
    def test_get_schedule_expression_all_params(self):
        result = schedule_utils.get_schedule_expression_from_parameters(
            time="23:59:59", day="1", month="12", year="2026", day_of_week=5
        )
        expected = ScheduleExpression(
            hour=23, minute=59, second=59, day="1", month="12", year="2026", day_of_week="5"
        )
        self.assertEqual(result, expected)


class TestMonthlyScheduledEvent(FeatureTest):
    @pytest.mark.unit
    def test_monthly_scheduled_event_standard(self):
        mock_vault = MagicMock()
        mock_vault.get_account_activation_datetime.return_value = datetime(2024, 1, 1, tzinfo=UTC)
        start_dt = datetime(2025, 1, 1, tzinfo=UTC)

        result = schedule_utils.monthly_scheduled_event(
            vault=mock_vault, start_datetime=start_dt, time="12:00:00", day=28
        )

        # start_datetime is adjusted by -1s
        expected_start = datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC)
        self.assertEqual(result.start_datetime, expected_start)
        self.assertIsInstance(result.schedule_method, EndOfMonthSchedule)
        self.assertEqual(result.schedule_method.day, 28)
        self.assertEqual(result.schedule_method.hour, 12)
        self.assertEqual(result.schedule_method.failover, ScheduleFailover.FIRST_VALID_DAY_BEFORE)

    @pytest.mark.unit
    def test_monthly_scheduled_event_capped_to_activation(self):
        activation_dt = datetime(2025, 1, 1, tzinfo=UTC)
        mock_vault = MagicMock()
        mock_vault.get_account_activation_datetime.return_value = activation_dt

        # Start is same as activation, so -1s would be before activation
        result = schedule_utils.monthly_scheduled_event(
            vault=mock_vault, start_datetime=activation_dt, time="00:00:00", day=1
        )

        self.assertEqual(result.start_datetime, activation_dt)


class TestGetNextScheduleDate(FeatureTest):
    @pytest.mark.unit
    def test_get_next_schedule_date_monthly_future_day_in_month(self):
        start = datetime(2025, 1, 1, tzinfo=UTC)
        result = schedule_utils.get_next_schedule_date(
            start_date=start, schedule_frequency=schedule_utils.MONTHLY, intended_day=15
        )
        # Should be Jan 15th
        self.assertEqual(result, datetime(2025, 1, 15, tzinfo=UTC))

    @pytest.mark.unit
    def test_get_next_schedule_date_monthly_past_day_in_month(self):
        start = datetime(2025, 1, 20, tzinfo=UTC)
        result = schedule_utils.get_next_schedule_date(
            start_date=start, schedule_frequency=schedule_utils.MONTHLY, intended_day=15
        )
        # Should be Feb 15th
        self.assertEqual(result, datetime(2025, 2, 15, tzinfo=UTC))

    @pytest.mark.unit
    def test_get_next_schedule_date_quarterly(self):
        start = datetime(2025, 1, 1, tzinfo=UTC)
        result = schedule_utils.get_next_schedule_date(
            start_date=start, schedule_frequency=schedule_utils.QUARTERLY, intended_day=1
        )
        # Should be April 1st (1 + 3 months)
        self.assertEqual(result, datetime(2025, 4, 1, tzinfo=UTC))

    @pytest.mark.unit
    def test_get_next_schedule_date_annually(self):
        start = datetime(2025, 1, 1, tzinfo=UTC)
        result = schedule_utils.get_next_schedule_date(
            start_date=start, schedule_frequency=schedule_utils.ANNUALLY, intended_day=1
        )
        # Should be Jan 1st next year
        self.assertEqual(result, datetime(2026, 1, 1, tzinfo=UTC))

    @pytest.mark.unit
    def test_get_next_schedule_date_leap_year_failover(self):
        # February 30th intended day in a non-leap year Feb -> should fall to Feb 28th
        # relativedelta handles this: datetime(2025, 1, 1) + relativedelta(months=1, day=30)
        start = datetime(2025, 1, 1, tzinfo=UTC)
        result = schedule_utils.get_next_schedule_date(
            start_date=start, schedule_frequency=schedule_utils.MONTHLY, intended_day=30
        )
        self.assertEqual(result, datetime(2025, 1, 30, tzinfo=UTC))

        # From Jan 31st, next monthly 30th
        start = datetime(2025, 1, 31, tzinfo=UTC)
        result = schedule_utils.get_next_schedule_date(
            start_date=start, schedule_frequency=schedule_utils.MONTHLY, intended_day=30
        )
        # Feb 30th -> Feb 28th
        self.assertEqual(result, datetime(2025, 2, 28, tzinfo=UTC))
