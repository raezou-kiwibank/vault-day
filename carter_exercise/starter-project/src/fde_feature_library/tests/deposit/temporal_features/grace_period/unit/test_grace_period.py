# Copyright @ 2023 Thought Machine Group Limited. All rights reserved.

# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

# features
import feature_library.deposit.temporal_features.grace_period as grace_period

# contracts api
from contracts_api import (
    AccountNotificationDirective,
    Rejection,
    RejectionReason,
    ScheduledEvent,
    SmartContractEventType,
    Tside,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import DEFAULT_DATETIME, FeatureTest
from inception_sdk.test_framework.contracts.unit.contracts_api_sentinels import (
    SentinelScheduleExpression,
)

# tests
from tests.utils import initialise_mock_state


class GracePeriodTestCommon(FeatureTest):
    tside = Tside.LIABILITY
    default_denomination = "GBP"

    def setUp(self) -> None:
        super().setUp()
        self.mock_vault = self.create_mock(
            account_id=sentinel.account_id,
            activation_datetime=DEFAULT_DATETIME,
            parameters_observation_fetchers_mapping={
                grace_period.GRACE_PERIOD_PARAMS_ET_POF_ID: sentinel.params_observation
            },
        )
        self.mock_vault.events_timezone = ZoneInfo("UTC")
        sentinel.params_observation.parameters = {
            grace_period.GRACE_PERIOD_PARAM_ID: 5,
        }
        self.state = initialise_mock_state(
            vault=self.mock_vault,
            effective_datetime=DEFAULT_DATETIME,
            parameters={
                grace_period.denomination_module.DENOMINATION_PARAM_ID: self.default_denomination,
            },
        )


@pytest.mark.unit
class GracePeriodGeneralTest(FeatureTest):
    def test_notification_type(self):
        product_name = "TEST_PRODUCT"

        result = grace_period.notification_type(product_name=product_name)

        self.assertEqual(result, "TEST_PRODUCT_GRACE_PERIOD_END")

    def test_event_types(self):
        product_name = "TEST_PRODUCT"
        expected_schedule_tag = ["TEST_PRODUCT_GRACE_PERIOD_END_AST"]
        expected_event_type: list[SmartContractEventType] = [
            SmartContractEventType(
                name=grace_period.GRACE_PERIOD_END_EVENT,
                scheduler_tag_ids=expected_schedule_tag,
            )
        ]

        result = grace_period.event_types(product_name=product_name)

        self.assertListEqual(result, expected_event_type)


@pytest.mark.unit
class DerivedParameterTest(GracePeriodTestCommon):
    def test_derived_params_grace_period_end_datetime(self):
        # ensure grace_period param is in state for this test
        self.state.parameters[grace_period.GRACE_PERIOD_PARAM_ID] = Decimal(5)
        # Activation is 2019-01-01 00:00:00. End is 5 days later at midnight.
        expected_result = datetime(2019, 1, 6, 0, 0, 0, tzinfo=ZoneInfo("UTC"))
        result = grace_period.get_grace_period_end_datetime(state=self.state)

        self.assertEqual(result, expected_result)


@pytest.mark.unit
class ScheduleEventTest(GracePeriodTestCommon):
    def setUp(self) -> None:
        super().setUp()

        # get parameter
        patch_get_grace_period_end_datetime = patch.object(
            grace_period, "get_grace_period_end_datetime"
        )
        self.mock_get_grace_period_end_datetime = patch_get_grace_period_end_datetime.start()
        self.mock_get_grace_period_end_datetime.return_value = DEFAULT_DATETIME

        # get one off schedule expression
        patch_one_off_schedule_expression = patch.object(
            grace_period.schedule_utils, "one_off_schedule_expression"
        )
        self.mock_one_off_schedule_expression = patch_one_off_schedule_expression.start()
        self.mock_one_off_schedule_expression.return_value = SentinelScheduleExpression(
            "grace_period_end"
        )

        patch_append_to_state = patch.object(grace_period, "_append_to_state")
        self.mock_append_to_state = patch_append_to_state.start()
        self.mock_append_to_state.return_value = self.state

        self.addCleanup(patch.stopall)

    def test_scheduled_events(self):
        expected_schedule_event = {
            grace_period.GRACE_PERIOD_END_EVENT: ScheduledEvent(
                start_datetime=DEFAULT_DATETIME - relativedelta(seconds=1),
                expression=SentinelScheduleExpression("grace_period_end"),
                end_datetime=DEFAULT_DATETIME,
            )
        }

        result = grace_period.get_scheduled_events(state=self.state)

        self.assertDictEqual(result, expected_schedule_event)
        self.mock_one_off_schedule_expression.assert_called_once_with(
            schedule_datetime=DEFAULT_DATETIME
        )
        self.mock_get_grace_period_end_datetime.assert_called_once_with(
            state=self.state, fetchers_config=grace_period.DEFAULT_FETCHERS_CONFIG
        )


@pytest.mark.unit
class WithinGracePeriodTest(GracePeriodTestCommon):
    def setUp(self) -> None:
        super().setUp()
        self.state.parameters[grace_period.GRACE_PERIOD_PARAM_ID] = Decimal(5)

    def test_within_grace_period_returns_true(self):
        # end is 2019-01-06 00:00:00. effective < end
        self.state = initialise_mock_state(
            vault=self.mock_vault,
            effective_datetime=datetime(2019, 1, 5, 23, 59, 59, tzinfo=ZoneInfo("UTC")),
            parameters=self.state.parameters,
        )
        result = grace_period.is_within_grace_period(state=self.state)

        self.assertTrue(result)

    def test_at_grace_period_end_time_returns_false(self):
        # new logic is state.effective_datetime < get_grace_period_end_datetime
        self.state = initialise_mock_state(
            vault=self.mock_vault,
            effective_datetime=datetime(2019, 1, 6, 0, 0, 0, tzinfo=ZoneInfo("UTC")),
            parameters=self.state.parameters,
        )
        result = grace_period.is_within_grace_period(state=self.state)

        self.assertFalse(result)

    def test_outside_grace_period_returns_false(self):
        self.state = initialise_mock_state(
            vault=self.mock_vault,
            effective_datetime=datetime(2019, 1, 7, 0, 0, 0, tzinfo=ZoneInfo("UTC")),
            parameters=self.state.parameters,
        )
        result = grace_period.is_within_grace_period(state=self.state)

        self.assertFalse(result)


@pytest.mark.unit
class ValidateDepositGracePeriodTest(GracePeriodTestCommon):
    def setUp(self) -> None:
        super().setUp()

        # sum_balances
        patch_sum_balances = patch.object(grace_period.balance_utils, "sum_balances")
        self.mock_sum_balances = patch_sum_balances.start()
        self.mock_sum_balances.return_value = sentinel.summed_balances

        # net_credit
        patch_net_credit = patch.object(grace_period.balance_utils, "net_credit")
        self.mock_net_credit = patch_net_credit.start()
        self.mock_net_credit.return_value = Decimal("10")

        # get_posting_instructions_balances
        patch_get_posting_instructions_balances = patch.object(
            grace_period.posting_utils, "get_posting_instructions_balances"
        )
        self.mock_get_posting_instructions_balances = (
            patch_get_posting_instructions_balances.start()
        )
        self.mock_get_posting_instructions_balances.return_value = sentinel.instruction_balances

        # is_within_grace_period
        patch_is_within_grace_period = patch.object(grace_period, "is_within_grace_period")
        self.mock_is_within_grace_period = patch_is_within_grace_period.start()
        self.mock_is_within_grace_period.return_value = True

        patch_append_to_state = patch.object(grace_period, "_append_to_state")
        self.mock_append_to_state = patch_append_to_state.start()
        self.mock_append_to_state.return_value = self.state

        self.addCleanup(patch.stopall)

    def test_withdrawals_are_accepted(self):
        self.mock_net_credit.return_value = Decimal("0")

        result = grace_period.validate_deposit(
            state=self.state,
            posting_instructions=sentinel.instructions,
        )
        self.assertIsNone(result)

    def test_deposits_accepted_within_grace_period(self):
        self.mock_net_credit.return_value = Decimal("10")

        result = grace_period.validate_deposit(
            state=self.state,
            posting_instructions=sentinel.instructions,
        )
        self.assertIsNone(result)

    def test_deposits_rejected_outside_grace_period(self):
        self.mock_is_within_grace_period.return_value = False
        self.mock_net_credit.return_value = Decimal("10")

        expected_result = Rejection(
            message="No deposits are allowed after the grace period end",
            reason_code=RejectionReason.AGAINST_TNC,
        )

        result = grace_period.validate_deposit(
            state=self.state,
            posting_instructions=sentinel.instructions,
        )
        self.assertEqual(result, expected_result)


@pytest.mark.unit
class WithdrawalSubjectToFeesTest(GracePeriodTestCommon):
    def setUp(self) -> None:
        super().setUp()
        patch_is_within_grace_period = patch.object(grace_period, "is_within_grace_period")
        self.mock_is_within_grace_period = patch_is_within_grace_period.start()
        self.mock_is_within_grace_period.return_value = True

        patch_posting_balances = patch.object(
            grace_period.posting_utils, "get_posting_instructions_balances"
        )
        self.mock_get_posting_instructions_balances = patch_posting_balances.start()
        self.mock_get_posting_instructions_balances.return_value = sentinel.posting_balances

        # sum_balances
        patch_sum_balances = patch.object(grace_period.balance_utils, "sum_balances")
        self.mock_sum_balances = patch_sum_balances.start()
        self.mock_sum_balances.return_value = sentinel.summed_balances

        # net_debit
        patch_net_debit = patch.object(grace_period.balance_utils, "net_debit")
        self.mock_net_debit = patch_net_debit.start()
        self.mock_net_debit.return_value = Decimal("10")

        patch_append_to_state = patch.object(grace_period, "_append_to_state")
        self.mock_append_to_state = patch_append_to_state.start()
        self.mock_append_to_state.return_value = self.state

        self.addCleanup(patch.stopall)

    def test_is_withdrawal_subject_to_fees_withdrawal_within_grace_period(self):
        result = grace_period.is_withdrawal_subject_to_fees(
            state=self.state,
            posting_instructions=sentinel.posting_instructions,
        )
        self.assertFalse(result)
        self.mock_get_posting_instructions_balances.assert_called_once_with(
            posting_instructions=sentinel.posting_instructions
        )
        self.mock_is_within_grace_period.assert_called_once_with(
            state=self.state,
            fetchers_config=grace_period.DEFAULT_FETCHERS_CONFIG,
        )

    def test_is_withdrawal_subject_to_fees_withdrawal_outside_grace_period(self):
        self.mock_is_within_grace_period.return_value = False
        result = grace_period.is_withdrawal_subject_to_fees(
            state=self.state,
            posting_instructions=sentinel.posting_instructions,
        )
        self.assertTrue(result)
        self.mock_get_posting_instructions_balances.assert_called_once_with(
            posting_instructions=sentinel.posting_instructions
        )
        self.mock_is_within_grace_period.assert_called_once_with(
            state=self.state,
            fetchers_config=grace_period.DEFAULT_FETCHERS_CONFIG,
        )

    def test_is_withdrawal_subject_to_fees_deposit_within_grace_period(self):
        self.mock_net_debit.return_value = Decimal("0")
        result = grace_period.is_withdrawal_subject_to_fees(
            state=self.state,
            posting_instructions=sentinel.posting_instructions,
        )
        self.assertFalse(result)
        self.mock_get_posting_instructions_balances.assert_called_once_with(
            posting_instructions=sentinel.posting_instructions
        )
        self.mock_is_within_grace_period.assert_not_called()

    def test_is_withdrawal_subject_to_fees_deposit_outside_grace_period(self):
        self.mock_net_debit.return_value = Decimal("0")
        self.mock_is_within_grace_period.return_value = False
        result = grace_period.is_withdrawal_subject_to_fees(
            state=self.state,
            posting_instructions=sentinel.posting_instructions,
        )
        self.assertFalse(result)
        self.mock_get_posting_instructions_balances.assert_called_once_with(
            posting_instructions=sentinel.posting_instructions
        )
        self.mock_is_within_grace_period.assert_not_called()


@pytest.mark.unit
class ValidateTermParameterChangeTest(GracePeriodTestCommon):
    def setUp(self) -> None:
        super().setUp()
        patch_append_to_state = patch.object(grace_period, "_append_to_state")
        self.mock_append_to_state = patch_append_to_state.start()
        self.mock_append_to_state.return_value = self.state
        self.addCleanup(patch.stopall)

    @patch.object(grace_period, "is_within_grace_period")
    def test_accept_term_parameter_change_within_grace_period(
        self, mock_is_within_grace_period: MagicMock
    ):
        mock_is_within_grace_period.return_value = True

        result = grace_period.validate_term_parameter_change(state=self.state)
        self.assertIsNone(result)
        mock_is_within_grace_period.assert_called_once_with(
            state=self.state,
            fetchers_config=grace_period.DEFAULT_FETCHERS_CONFIG,
        )

    @patch.object(grace_period, "is_within_grace_period")
    def test_reject_term_parameter_change_outside_grace_period(
        self, mock_is_within_grace_period: MagicMock
    ):
        mock_is_within_grace_period.return_value = False
        expected_result = Rejection(
            message="Term length cannot be changed outside the grace period",
            reason_code=RejectionReason.AGAINST_TNC,
        )

        result = grace_period.validate_term_parameter_change(state=self.state)
        self.assertEqual(result, expected_result)
        mock_is_within_grace_period.assert_called_once_with(
            state=self.state,
            fetchers_config=grace_period.DEFAULT_FETCHERS_CONFIG,
        )


@pytest.mark.unit
class HandleAccountClosureNotificationTest(GracePeriodTestCommon):
    def setUp(self) -> None:
        super().setUp()
        self.product_name = "TEST_PRODUCT"

        # get current credit balance
        patch_get_current_net_balance = patch.object(
            grace_period.balance_utils, "get_current_net_balance"
        )
        self.mock_get_current_net_balance = patch_get_current_net_balance.start()
        self.mock_get_current_net_balance.return_value = Decimal("0")

        patch_append_to_state = patch.object(grace_period, "_append_to_state")
        self.mock_append_to_state = patch_append_to_state.start()
        self.mock_append_to_state.return_value = self.state

        self.addCleanup(patch.stopall)

    def test_no_notification_when_non_zero_net_balance(self):
        self.mock_get_current_net_balance.return_value = MagicMock(net=Decimal("100"))

        result = grace_period.handle_account_closure_notification(
            state=self.state,
            product_name=self.product_name,
        )

        self.assertListEqual(result, [])
        self.mock_get_current_net_balance.assert_called_once_with(
            balances=self.state.balances, denomination=self.default_denomination
        )

    def test_notification_sent_when_no_funds(self):
        self.mock_get_current_net_balance.return_value = MagicMock(net=Decimal("0"))
        expected_notification_details = {
            "account_id": sentinel.account_id,
            "grace_period_end_datetime": str(DEFAULT_DATETIME),
            "reason": "Close account due to lack of funds at the end of grace period",
        }
        expected_notification_type = "TEST_PRODUCT_GRACE_PERIOD_END"
        expected_notification = [
            AccountNotificationDirective(
                notification_type=expected_notification_type,
                notification_details=expected_notification_details,
            )
        ]

        result = grace_period.handle_account_closure_notification(
            state=self.state,
            product_name=self.product_name,
        )

        self.assertListEqual(result, expected_notification)
        self.mock_get_current_net_balance.assert_called_once_with(
            balances=self.state.balances, denomination=self.default_denomination
        )
