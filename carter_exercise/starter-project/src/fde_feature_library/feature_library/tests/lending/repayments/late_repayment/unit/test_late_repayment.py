# standard libs
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel
from zoneinfo import ZoneInfo

import pytest

# features
import feature_library.common.posting_utils as posting_utils
import feature_library.common.schedule_utils as schedule_utils
import feature_library.lending.interfaces as lending_interfaces
import feature_library.lending.repayments.late_repayment as late_repayment

# contracts api
from contracts_api import (
    Balance,
    BalanceDefaultDict,
    CustomInstruction,
    ParametersObservation,
    Phase,
    Posting,
    ScheduledEvent,
    SmartContractEventType,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest
from inception_sdk.test_framework.contracts.unit.contracts_api_sentinels import (
    SentinelScheduleExpression,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION

UTC = ZoneInfo("UTC")
DEFAULT_DATETIME = datetime(2023, 1, 1, tzinfo=UTC)


@pytest.mark.unit
class LateRepaymentTest(FeatureTest):
    def setup_mock_data(
        self,
        late_repayment_fee: Decimal = Decimal("25"),
        late_repayment_fee_income_account: str = "LATE_REPAYMENT_FEE_INCOME",
        check_late_repayment_time: str = "00:00:00",
        denomination: str = DEFAULT_DENOMINATION,
        balances: dict = None,
    ):
        params = {
            late_repayment.LATE_REPAYMENT_FEE_PARAM_ID: late_repayment_fee,
            late_repayment.LATE_REPAYMENT_FEE_INCOME_ACCOUNT_PARAM_ID: (
                late_repayment_fee_income_account
            ),
            late_repayment.CHECK_LATE_REPAYMENT_TIME_PARAM_ID: check_late_repayment_time,
            late_repayment.DEFAULT_FETCHERS_CONFIG.denomination_param_id: denomination,
        }
        self.mock_vault = self.create_mock(
            account_id="customer_account",
            parameters_observation_fetchers_mapping={
                late_repayment.LATE_REPAYMENT_POF_ID: ParametersObservation(
                    parameters=params,
                    value_datetime=DEFAULT_DATETIME,
                )
            },
        )
        self.mock_vault.events_timezone = UTC
        self.state = MagicMock(
            vault=self.mock_vault,
            effective_datetime=DEFAULT_DATETIME,
            parameters=params,
            balances=BalanceDefaultDict(lambda: Balance(), balances or {}),
        )


class EventTypesTest(LateRepaymentTest):
    @pytest.mark.unit
    def test_event_types(self):
        product_name = "TEST_PRODUCT"
        expected_schedule_tag = ["TEST_PRODUCT_CHECK_LATE_REPAYMENT_AST"]
        expected_event_type = [
            SmartContractEventType(
                name=late_repayment.CHECK_LATE_REPAYMENT_EVENT,
                scheduler_tag_ids=expected_schedule_tag,
            )
        ]

        result = late_repayment.event_types(product_name=product_name)

        self.assertListEqual(result, expected_event_type)


class ScheduledEventsTest(LateRepaymentTest):
    @patch.object(late_repayment, "_append_to_state")
    @patch.object(schedule_utils, "get_schedule_expression_from_parameters")
    @pytest.mark.unit
    def test_get_scheduled_events(
        self, mock_get_schedule_expression: MagicMock, mock_append_to_state: MagicMock
    ):
        self.setup_mock_data(check_late_repayment_time="10:15:30")
        mock_append_to_state.return_value = self.state
        mock_get_schedule_expression.return_value = SentinelScheduleExpression(
            "late_repayment_schedule"
        )
        start_datetime = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

        expected_schedule_event = ScheduledEvent(
            start_datetime=start_datetime.astimezone(self.state.vault.events_timezone).replace(
                hour=0, minute=0, second=0
            ),
            expression=SentinelScheduleExpression("late_repayment_schedule"),
            skip=True,
        )

        result = late_repayment.get_scheduled_events(
            state=self.state,
            start_datetime=start_datetime,
            skip=True,
        )

        self.assertEqual(result[late_repayment.CHECK_LATE_REPAYMENT_EVENT], expected_schedule_event)
        mock_get_schedule_expression.assert_called_once_with(
            time="10:15:30",
            day=1,
        )
        mock_append_to_state.assert_called_once_with(
            self.state, late_repayment.DEFAULT_FETCHERS_CONFIG
        )


class ScheduleLogicTest(LateRepaymentTest):
    def setup_mock_config(self, total_overdue_amount: Decimal):
        self.mock_repayment_hierarchy = MagicMock()
        self.mock_repayment_hierarchy.get_total_overdue_amount.return_value = total_overdue_amount
        self.mock_fetchers_config = sentinel.fetchers_config
        self.repayment_hierarchy_config = lending_interfaces.RepaymentHierarchyConfig(
            repayment_hierarchy=self.mock_repayment_hierarchy,
            fetchers_config=self.mock_fetchers_config,
        )

    @patch.object(late_repayment, "_append_to_state")
    @patch.object(posting_utils, "create_postings")
    @patch.object(posting_utils, "standard_instruction_details")
    @pytest.mark.unit
    def test_schedule_logic_with_fee_and_overdue_amount(
        self,
        mock_standard_instruction_details: MagicMock,
        mock_create_postings: MagicMock,
        mock_append_to_state: MagicMock,
    ):
        self.setup_mock_data(
            late_repayment_fee=Decimal("25"),
            late_repayment_fee_income_account="INCOME",
        )
        mock_append_to_state.return_value = self.state
        self.setup_mock_config(total_overdue_amount=Decimal("100"))

        dummy_posting = Posting(
            credit=True,
            amount=Decimal("25"),
            denomination=DEFAULT_DENOMINATION,
            account_id="test",
            account_address="DEFAULT",
            asset="COMMERCIAL_BANK_MONEY",
            phase=Phase.COMMITTED,
        )
        mock_create_postings.return_value = [dummy_posting]
        mock_standard_instruction_details.return_value = {"test": "details"}

        result = late_repayment.schedule_logic(
            state=self.state,
            account_type="test_account",
            repayment_hierarchy_config=self.repayment_hierarchy_config,
        )

        expected_ci = CustomInstruction(
            postings=[dummy_posting],
            instruction_details={"test": "details"},
        )

        self.assertListEqual(result, [expected_ci])
        mock_append_to_state.assert_called_once_with(
            self.state, late_repayment.DEFAULT_FETCHERS_CONFIG
        )
        self.mock_repayment_hierarchy.get_total_overdue_amount.assert_called_once_with(
            state=self.state,
            fetchers_config=sentinel.fetchers_config,
        )
        mock_create_postings.assert_called_once_with(
            amount=Decimal("25"),
            denomination=DEFAULT_DENOMINATION,
            debit_account="customer_account",
            debit_address=late_repayment.lending_addresses.PENALTIES,
            credit_account="INCOME",
            credit_address=posting_utils.DEFAULT_ADDRESS,
        )
        mock_standard_instruction_details.assert_called_once_with(
            description="Charge late repayment fee",
            event_type=late_repayment.CHECK_LATE_REPAYMENT_EVENT,
            account_type="test_account",
        )

    @patch.object(late_repayment, "_append_to_state")
    @pytest.mark.unit
    def test_schedule_logic_with_no_fee_configured(self, mock_append_to_state: MagicMock):
        self.setup_mock_data(late_repayment_fee=Decimal("0"))
        mock_append_to_state.return_value = self.state
        self.setup_mock_config(total_overdue_amount=Decimal("100"))

        result = late_repayment.schedule_logic(
            state=self.state,
            repayment_hierarchy_config=self.repayment_hierarchy_config,
        )

        self.assertListEqual(result, [])
        self.mock_repayment_hierarchy.get_total_overdue_amount.assert_not_called()

    @patch.object(late_repayment, "_append_to_state")
    @pytest.mark.unit
    def test_schedule_logic_with_no_overdue_amount(self, mock_append_to_state: MagicMock):
        self.setup_mock_data(late_repayment_fee=Decimal("25"))
        mock_append_to_state.return_value = self.state
        self.setup_mock_config(total_overdue_amount=Decimal("0"))

        result = late_repayment.schedule_logic(
            state=self.state,
            repayment_hierarchy_config=self.repayment_hierarchy_config,
        )

        self.assertListEqual(result, [])
        self.mock_repayment_hierarchy.get_total_overdue_amount.assert_called_once()

    @patch.object(late_repayment, "_append_to_state")
    @patch.object(posting_utils, "create_postings")
    @patch.object(posting_utils, "standard_instruction_details")
    @pytest.mark.unit
    def test_schedule_logic_with_check_total_overdue_amount_false(
        self,
        mock_standard_instruction_details: MagicMock,
        mock_create_postings: MagicMock,
        mock_append_to_state: MagicMock,
    ):
        self.setup_mock_data(
            late_repayment_fee=Decimal("25"),
            late_repayment_fee_income_account="INCOME",
        )
        mock_append_to_state.return_value = self.state
        # Should charge fee even if overdue is not checked
        self.setup_mock_config(total_overdue_amount=Decimal("0"))

        dummy_posting = Posting(
            credit=True,
            amount=Decimal("25"),
            denomination=DEFAULT_DENOMINATION,
            account_id="test",
            account_address="DEFAULT",
            asset="COMMERCIAL_BANK_MONEY",
            phase=Phase.COMMITTED,
        )
        mock_create_postings.return_value = [dummy_posting]
        mock_standard_instruction_details.return_value = {"test": "details"}

        result = late_repayment.schedule_logic(
            state=self.state,
            check_total_overdue_amount=False,
            account_type="test_account",
            repayment_hierarchy_config=self.repayment_hierarchy_config,
        )

        expected_ci = CustomInstruction(
            postings=[dummy_posting],
            instruction_details={"test": "details"},
        )

        self.assertListEqual(result, [expected_ci])
        # We still call it, but we ignore the result if check_total_overdue_amount is False
        self.mock_repayment_hierarchy.get_total_overdue_amount.assert_called_once()
        mock_create_postings.assert_called_once()
