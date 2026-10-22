# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta

import feature_library.common.balance_utils as balance_utils
import feature_library.common.posting_utils as posting_utils
import feature_library.common.schedule_utils as schedule_utils

# features
import feature_library.deposit.temporal_features.deposit_period as deposit_period

# contracts api
from contracts_api import (
    AccountNotificationDirective,
    Balance,
    BalanceDefaultDict,
    ParametersObservation,
    Rejection,
    RejectionReason,
    ScheduledEvent,
    SmartContractEventType,
)

# inception sdk
from inception_sdk.test_framework.common.utils import ac_coverage
from inception_sdk.test_framework.contracts.unit.common import DEFAULT_DATETIME, FeatureTest
from inception_sdk.test_framework.contracts.unit.contracts_api_sentinels import (
    SentinelScheduleExpression,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION

UTC = ZoneInfo("UTC")


@pytest.mark.unit
class DepositPeriodTest(FeatureTest):
    def setup_mock_data(
        self,
        deposit_period_days: int = 7,
        number_of_permitted_deposits: str = deposit_period.UNLIMITED,
        balances: dict = None,
        denomination: str = DEFAULT_DENOMINATION,
    ):
        params = {
            deposit_period.DEPOSIT_PERIOD_PARAM_ID: deposit_period_days,
            deposit_period.NUMBER_OF_PERMITTED_DEPOSITS_PARAM_ID: number_of_permitted_deposits,
            deposit_period.DEFAULT_FETCHERS_CONFIG.denomination_param_id: denomination,
        }
        self.mock_vault = self.create_mock(
            account_id="customer_account",
            parameters_observation_fetchers_mapping={
                deposit_period.DEPOSIT_PERIOD_PARAMS_ET_POF_ID: ParametersObservation(
                    parameters=params,
                    value_datetime=DEFAULT_DATETIME,
                )
            },
        )
        self.mock_vault.get_account_activation_datetime.return_value = DEFAULT_DATETIME
        self.state = MagicMock(
            vault=self.mock_vault,
            effective_datetime=DEFAULT_DATETIME,
            parameters=params,
            balances=BalanceDefaultDict(lambda: Balance(), balances or {}),
        )

    @pytest.mark.unit
    def test_notification_type(self):
        product_name = "TEST_PRODUCT"
        expected_result = "TEST_PRODUCT_DEPOSIT_PERIOD_END"
        result = deposit_period.notification_type(product_name=product_name)
        self.assertEqual(result, expected_result)

    @pytest.mark.unit
    def test_event_types(self):
        product_name = "TEST_PRODUCT"
        expected_schedule_tag = ["TEST_PRODUCT_DEPOSIT_PERIOD_END_AST"]
        expected_event_type: list[SmartContractEventType] = [
            SmartContractEventType(
                name=deposit_period.DEPOSIT_PERIOD_END_EVENT,
                scheduler_tag_ids=expected_schedule_tag,
            )
        ]

        result = deposit_period.event_types(product_name=product_name)

        self.assertListEqual(result, expected_event_type)

    @ac_coverage(["CPP-2082-AC03"])
    @pytest.mark.unit
    def test_get_deposit_period_end_datetime(self):
        self.setup_mock_data(deposit_period_days=2)
        # 2019-01-01 + 2 days = 2019-01-03
        # Start of day (00:00:00)
        # Note: deposit_period.py uses state.vault.events_timezone
        self.mock_vault.events_timezone = UTC
        expected_result = datetime(2019, 1, 3, 0, 0, 0, tzinfo=UTC)
        result = deposit_period.get_deposit_period_end_datetime(state=self.state)

        self.assertEqual(result, expected_result)

    @patch.object(schedule_utils, "one_off_schedule_expression")
    @pytest.mark.unit
    def test_get_scheduled_events(self, mock_one_off_schedule_expression: MagicMock):
        self.setup_mock_data(deposit_period_days=2)
        self.mock_vault.events_timezone = UTC
        mock_one_off_schedule_expression.return_value = SentinelScheduleExpression(
            "deposit_period_end"
        )

        test_deposit_period_end_datetime = datetime(2019, 1, 3, 0, 0, 0, tzinfo=UTC)
        expected_schedule_event = ScheduledEvent(
            start_datetime=test_deposit_period_end_datetime - relativedelta(seconds=1),
            expression=SentinelScheduleExpression("deposit_period_end"),
            end_datetime=test_deposit_period_end_datetime,
        )

        result = deposit_period.get_scheduled_events(state=self.state)

        self.assertEqual(result["DEPOSIT_PERIOD_END"], expected_schedule_event)
        mock_one_off_schedule_expression.assert_called_once_with(
            schedule_datetime=test_deposit_period_end_datetime
        )

    @patch.object(balance_utils, "get_current_net_balance")
    @patch.object(posting_utils, "get_posting_instructions_balances")
    @ac_coverage(["CPP-2082-AC04", "CPP-2082-AC08"])
    @pytest.mark.unit
    def test_validate_unlimited_deposits_before_end(
        self, mock_get_pi_balances: MagicMock, mock_get_current_net_balance: MagicMock
    ):
        self.setup_mock_data(number_of_permitted_deposits=deposit_period.UNLIMITED)
        self.mock_vault.events_timezone = UTC
        mock_get_pi_balances.return_value = sentinel.instruction_balances
        mock_get_current_net_balance.side_effect = [
            Balance(credit=Decimal("12")),  # deposit_proposed_amount
        ]

        result = deposit_period.validate(
            state=self.state,
            posting_instructions=sentinel.instructions,
        )

        self.assertIsNone(result)

    @patch.object(balance_utils, "get_current_net_balance")
    @patch.object(posting_utils, "get_posting_instructions_balances")
    @ac_coverage(["CPP-2082-AC05"])
    @pytest.mark.unit
    def test_validate_unlimited_deposits_after_end(
        self, mock_get_pi_balances: MagicMock, mock_get_current_net_balance: MagicMock
    ):
        self.setup_mock_data(number_of_permitted_deposits=deposit_period.UNLIMITED)
        self.mock_vault.events_timezone = UTC
        self.state.effective_datetime = DEFAULT_DATETIME + relativedelta(days=10)
        mock_get_pi_balances.return_value = sentinel.instruction_balances
        mock_get_current_net_balance.side_effect = [
            Balance(credit=Decimal("12")),  # deposit_proposed_amount
        ]

        expected_rejection = Rejection(
            message="No deposits are allowed after the deposit period end datetime.",
            reason_code=RejectionReason.AGAINST_TNC,
        )
        result = deposit_period.validate(
            state=self.state,
            posting_instructions=sentinel.instructions,
        )

        self.assertEqual(result, expected_rejection)

    @patch.object(balance_utils, "get_current_net_balance")
    @patch.object(posting_utils, "get_posting_instructions_balances")
    @ac_coverage(["CPP-2082-AC04", "CPP-2082-AC06"])
    @pytest.mark.unit
    def test_validate_single_deposit_accepted_when_no_previous(
        self, mock_get_pi_balances: MagicMock, mock_get_current_net_balance: MagicMock
    ):
        self.setup_mock_data(number_of_permitted_deposits=deposit_period.SINGLE)
        self.mock_vault.events_timezone = UTC
        mock_get_pi_balances.return_value = sentinel.instruction_balances
        mock_get_current_net_balance.side_effect = [
            Balance(credit=Decimal("12")),  # deposit_proposed_amount
            Balance(credit=Decimal("0")),  # credit_default_balance
        ]

        result = deposit_period.validate(
            state=self.state,
            posting_instructions=sentinel.instructions,
        )

        self.assertIsNone(result)

    @patch.object(balance_utils, "get_current_net_balance")
    @patch.object(posting_utils, "get_posting_instructions_balances")
    @ac_coverage(["CPP-2082-AC07"])
    @pytest.mark.unit
    def test_validate_single_deposit_rejected_when_previous_exists(
        self, mock_get_pi_balances: MagicMock, mock_get_current_net_balance: MagicMock
    ):
        self.setup_mock_data(number_of_permitted_deposits=deposit_period.SINGLE)
        self.mock_vault.events_timezone = UTC
        mock_get_pi_balances.return_value = sentinel.instruction_balances
        mock_get_current_net_balance.side_effect = [
            Balance(credit=Decimal("12")),  # deposit_proposed_amount
            Balance(credit=Decimal("5")),  # credit_default_balance
        ]

        expected_rejection = Rejection(
            message="Only a single deposit is allowed.",
            reason_code=RejectionReason.AGAINST_TNC,
        )

        result = deposit_period.validate(
            state=self.state,
            posting_instructions=sentinel.instructions,
        )

        self.assertEqual(result, expected_rejection)

    @patch.object(balance_utils, "get_current_net_balance")
    @ac_coverage(["CPP-2082-AC09"])
    @pytest.mark.unit
    def test_schedule_logic_notification_when_no_funds(
        self, mock_get_current_net_balance: MagicMock
    ):
        self.setup_mock_data()
        mock_get_current_net_balance.return_value = Balance(credit=Decimal("0"), debit=Decimal("0"))
        product_name = "TEST_PRODUCT"

        expected_notification_details = {
            "account_id": self.mock_vault.account_id,
            "deposit_balance": str(Decimal("0")),
            "deposit_period_end_datetime": str(DEFAULT_DATETIME),
            "reason": "Close account due to lack of deposits at the end of deposit period",
        }
        expected_notification = [
            AccountNotificationDirective(
                notification_type="TEST_PRODUCT_DEPOSIT_PERIOD_END",
                notification_details=expected_notification_details,
            )
        ]
        result = deposit_period.schedule_logic(
            state=self.state,
            product_name=product_name,
        )

        self.assertListEqual(result, expected_notification)

    @patch.object(balance_utils, "get_current_net_balance")
    @pytest.mark.unit
    def test_schedule_logic_no_notification_when_funds_exist(
        self, mock_get_current_net_balance: MagicMock
    ):
        self.setup_mock_data()
        mock_get_current_net_balance.return_value = Balance(
            credit=Decimal("100"), debit=Decimal("0")
        )
        product_name = "TEST_PRODUCT"

        result = deposit_period.schedule_logic(
            state=self.state,
            product_name=product_name,
        )

        self.assertListEqual(result, [])
