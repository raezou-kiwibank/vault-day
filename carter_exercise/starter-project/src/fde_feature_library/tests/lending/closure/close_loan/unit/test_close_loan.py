# Copyright @ 2023 Thought Machine Group Limited. All rights reserved.

# standard libs
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch, sentinel

import pytest

# features
import feature_library.lending.closure.close_loan as close_loan
import feature_library.lending.interfaces as lending_interfaces

# contracts api
from contracts_api import (
    AccountNotificationDirective,
    BalanceDefaultDict,
    CustomInstruction,
    Posting,
    Rejection,
    RejectionReason,
    Tside,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest
from inception_sdk.test_framework.contracts.unit.contracts_api_sentinels import (
    SentinelPosting,
)


class CloseLoanTestCommon(FeatureTest):
    default_denomination = "AUD"
    tside = Tside.ASSET

    def setUp(self):
        super().setUp()
        self.mock_vault = self.create_mock(account_id=sentinel.account_id)
        self.state = MagicMock(
            vault=self.mock_vault,
            balances=BalanceDefaultDict(),
            parameters={
                close_loan.denomination_module.DENOMINATION_PARAM_ID: self.default_denomination
            },
        )


@pytest.mark.unit
class TestDoesRepaymentFullyRepayLoan(CloseLoanTestCommon):
    def setUp(self):
        super().setUp()
        self.mock_repayment_hierarchy = MagicMock()
        self.repayment_hierarchy_config = lending_interfaces.RepaymentHierarchyConfig(
            repayment_hierarchy=self.mock_repayment_hierarchy,
            fetchers_config=sentinel.hierarchy_fetchers_config,
        )

    def test_loan_paid_off_notification_type(self):
        # expected values
        product_name = "PRODUCT_A"
        # construct expected result
        expected_notification_type = f"{product_name}{close_loan.LOAN_PAID_OFF_NOTIFICATION_SUFFIX}"
        # run function
        notification_type = close_loan.notification_type(product_name=product_name)
        # validate results
        self.assertEqual(notification_type, expected_notification_type)

    @patch.object(close_loan, "notification_type")
    def test_send_loan_paid_off_notification(self, mock_notification_type: MagicMock):
        # expected values
        product_name = "PRODUCT_A"

        # construct expected result
        expected_notification_type = f"{product_name}{close_loan.LOAN_PAID_OFF_NOTIFICATION_SUFFIX}"
        expected_notification_details = {
            "account_id": sentinel.account_id,
        }
        expected_notification: AccountNotificationDirective = AccountNotificationDirective(
            notification_type=expected_notification_type,
            notification_details=expected_notification_details,
        )
        # construct mocks
        mock_notification_type.return_value = expected_notification_type
        # run function
        result_notification = close_loan.send_loan_paid_off_notification(
            state=self.state,
            product_name=product_name,
        )
        # validate results
        self.assertEqual(result_notification, expected_notification)

    @patch.object(close_loan.posting_utils, "get_posting_instructions_balances")
    @patch.object(close_loan.balance_utils, "sum_balances")
    @patch.object(close_loan.balance_utils, "net_credit")
    def test_repayment_logic_calls_dependencies_correctly(
        self,
        mock_net_credit: MagicMock,
        mock_sum_balances: MagicMock,
        mock_get_posting_balances: MagicMock,
    ):
        # mock values
        self.mock_repayment_hierarchy.get_total_outstanding_debt.return_value = Decimal("100")
        mock_get_posting_balances.return_value = sentinel.repayment_balances
        mock_sum_balances.return_value = sentinel.summed_balances
        mock_net_credit.return_value = Decimal("125")

        result = close_loan.does_repayment_fully_repay_loan(
            state=self.state,
            repayment_posting_instructions=sentinel.postings,
            repayment_hierarchy_config=self.repayment_hierarchy_config,
        )

        # assertions
        self.mock_repayment_hierarchy.get_total_outstanding_debt.assert_called_once_with(
            state=self.state,
            fetchers_config=sentinel.hierarchy_fetchers_config,
        )
        mock_get_posting_balances.assert_called_once_with(
            posting_instructions=sentinel.postings,
            account_id=sentinel.account_id,
            tside=Tside.ASSET,
        )
        mock_sum_balances.assert_called_once_with(
            balances=sentinel.repayment_balances,
            denomination=self.default_denomination,
        )
        mock_net_credit.assert_called_once_with(bal=sentinel.summed_balances)
        self.assertTrue(result)

    @patch.object(close_loan.posting_utils, "get_posting_instructions_balances")
    @patch.object(close_loan.balance_utils, "sum_balances")
    @patch.object(close_loan.balance_utils, "net_credit")
    def test_repayment_less_than_debt_returns_false(
        self,
        mock_net_credit: MagicMock,
        mock_sum_balances: MagicMock,
        mock_get_posting_balances: MagicMock,
    ):
        self.mock_repayment_hierarchy.get_total_outstanding_debt.return_value = Decimal("100")
        mock_net_credit.return_value = Decimal("75")

        result = close_loan.does_repayment_fully_repay_loan(
            state=self.state,
            repayment_posting_instructions=[],
            repayment_hierarchy_config=self.repayment_hierarchy_config,
        )

        self.assertFalse(result)


@pytest.mark.unit
@patch.object(close_loan.balance_utils, "balance_at_coordinates")
class TestSetBalancesToZero(CloseLoanTestCommon):
    @patch.object(close_loan.posting_utils, "create_postings")
    def test_creates_net_postings_for_positive_eia_amount(
        self, mock_create_postings: MagicMock, mock_balance_at_coordinates: MagicMock
    ):
        mock_balance_at_coordinates.return_value = Decimal("24")
        self.state.balances = sentinel.balances
        mock_postings: list[Posting] = [SentinelPosting("dummy_posting")] * 2  # type: ignore
        mock_create_postings.return_value = mock_postings

        net_posting_instructions = close_loan.set_balances_to_zero(
            state=self.state,
        )

        # assertions
        mock_balance_at_coordinates.assert_called_once_with(
            balances=sentinel.balances,
            address="EIA",
            denomination=self.default_denomination,
        )
        mock_create_postings.assert_called_once_with(
            amount=Decimal("24"),
            debit_account=sentinel.account_id,
            credit_account=sentinel.account_id,
            debit_address="INTERNAL_CONTRA",
            credit_address="EIA",
            denomination=self.default_denomination,
        )
        expected_posting_instructions = [
            CustomInstruction(
                postings=mock_postings,  # type: ignore
                instruction_details={
                    "description": "Clearing all residual balances",
                    "event": "END_OF_LOAN",
                },
            )
        ]
        self.assertEqual(net_posting_instructions, expected_posting_instructions)

    @patch.object(close_loan.posting_utils, "create_postings")
    def test_creates_net_postings_for_positive_eia_amount_with_cleanup_feature(
        self, mock_create_postings: MagicMock, mock_balance_at_coordinates: MagicMock
    ):
        self.maxDiff = None
        mock_balance_at_coordinates.return_value = Decimal("24")
        self.state.balances = sentinel.balances
        mock_eia_postings: list[Posting] = [SentinelPosting("eia_posting")] * 2  # type: ignore
        mock_feature_postings: list[Posting] = [SentinelPosting("feature_posting")] * 2  # type: ignore
        mock_create_postings.return_value = mock_eia_postings

        residual_cleanup_feature = Mock(
            get_residual_cleanup_postings=Mock(return_value=mock_feature_postings)
        )

        net_posting_instructions = close_loan.set_balances_to_zero(
            state=self.state,
            residual_cleanup_features=[residual_cleanup_feature],
        )

        # assertions
        mock_balance_at_coordinates.assert_called_once_with(
            balances=sentinel.balances,
            address="EIA",
            denomination=self.default_denomination,
        )
        mock_create_postings.assert_called_once_with(
            amount=Decimal("24"),
            debit_account=sentinel.account_id,
            credit_account=sentinel.account_id,
            debit_address="INTERNAL_CONTRA",
            credit_address="EIA",
            denomination=self.default_denomination,
        )
        expected_posting_instructions = [
            CustomInstruction(
                postings=mock_eia_postings + mock_feature_postings,  # type: ignore
                instruction_details={
                    "description": "Clearing all residual balances",
                    "event": "END_OF_LOAN",
                },
            )
        ]
        self.assertEqual(net_posting_instructions, expected_posting_instructions)

    def test_no_balances_to_zero_returns_empty_list(self, mock_balance_at_coordinates: MagicMock):
        mock_balance_at_coordinates.return_value = Decimal()
        self.state.balances = sentinel.balances
        net_posting_instructions = close_loan.set_balances_to_zero(
            state=self.state,
        )

        # assertions
        mock_balance_at_coordinates.assert_called_once_with(
            balances=sentinel.balances,
            address="EIA",
            denomination=self.default_denomination,
        )
        self.assertEqual(net_posting_instructions, [])


@pytest.mark.unit
class TestRejectClosureWhenOutstandingDebt(CloseLoanTestCommon):
    def setUp(self):
        super().setUp()
        self.mock_repayment_hierarchy = MagicMock()
        self.repayment_hierarchy_config = lending_interfaces.RepaymentHierarchyConfig(
            repayment_hierarchy=self.mock_repayment_hierarchy,
            fetchers_config=sentinel.hierarchy_fetchers_config,
        )

    def test_rejects_if_outstanding_debt_is_positive(self):
        self.mock_repayment_hierarchy.get_total_outstanding_debt.return_value = Decimal("1.25")

        outstanding_debt_rejection = close_loan.reject_closure_when_outstanding_debt(
            state=self.state,
            repayment_hierarchy_config=self.repayment_hierarchy_config,
        )

        # assertions
        self.mock_repayment_hierarchy.get_total_outstanding_debt.assert_called_once_with(
            state=self.state,
            fetchers_config=sentinel.hierarchy_fetchers_config,
        )
        self.assertEqual(
            outstanding_debt_rejection,
            Rejection(
                message="The loan cannot be closed until all outstanding debt is repaid",
                reason_code=RejectionReason.AGAINST_TNC,
            ),
        )

    def test_does_not_reject_if_outstanding_debt_is_zero(self):
        self.mock_repayment_hierarchy.get_total_outstanding_debt.return_value = Decimal("0.00")

        outstanding_debt_rejection = close_loan.reject_closure_when_outstanding_debt(
            state=self.state,
            repayment_hierarchy_config=self.repayment_hierarchy_config,
        )

        # assertions
        self.mock_repayment_hierarchy.get_total_outstanding_debt.assert_called_once_with(
            state=self.state,
            fetchers_config=sentinel.hierarchy_fetchers_config,
        )
        self.assertIsNone(outstanding_debt_rejection)
