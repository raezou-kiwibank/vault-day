# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel

import pytest

# features
import feature_library.lending.repayments.secondary.vertical_repayment_hierarchy as vertical_repayment_hierarchy  # noqa: E501

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.utils import initialise_mock_state


@pytest.mark.unit
class VerticalRepaymentHierarchyTest(FeatureTest):
    def setup_mock_data(
        self,
        denomination: str = DEFAULT_DENOMINATION,
    ):
        self.mock_vault = self.create_mock()
        self.state = initialise_mock_state(
            vault=self.mock_vault,
            parameters={
                vertical_repayment_hierarchy.denomination_module.DENOMINATION_PARAM_ID: (
                    denomination
                ),
            },
        )

    @patch.object(vertical_repayment_hierarchy.balance_utils, "net_debit")
    @patch.object(vertical_repayment_hierarchy.balance_utils, "sum_balances")
    @patch.object(vertical_repayment_hierarchy.state_utils, "check_parameters_exist")
    @pytest.mark.unit
    def test_get_total_outstanding_debt(
        self,
        mock_check_parameters_exist: MagicMock,
        mock_sum_balances: MagicMock,
        mock_net_debit: MagicMock,
    ):
        self.setup_mock_data()
        mock_check_parameters_exist.return_value = None
        mock_sum_balances.return_value = sentinel.balances_sum
        mock_net_debit.return_value = Decimal("100.50")

        result = vertical_repayment_hierarchy.get_total_outstanding_debt(
            state=self.state,
        )

        self.assertEqual(Decimal("100.50"), result)
        mock_check_parameters_exist.assert_called_once_with(
            state=self.state,
            param_ids={vertical_repayment_hierarchy.denomination_module.DENOMINATION_PARAM_ID},
        )
        mock_sum_balances.assert_called_once_with(
            balances=self.state.balances,
            denomination=DEFAULT_DENOMINATION,
            addresses=vertical_repayment_hierarchy.ALL_OUTSTANDING,
        )
        mock_net_debit.assert_called_once_with(bal=sentinel.balances_sum)

    @patch.object(vertical_repayment_hierarchy.balance_utils, "net_debit")
    @patch.object(vertical_repayment_hierarchy.balance_utils, "sum_balances")
    @patch.object(vertical_repayment_hierarchy.state_utils, "check_parameters_exist")
    @pytest.mark.unit
    def test_get_total_overdue_amount(
        self,
        mock_check_parameters_exist: MagicMock,
        mock_sum_balances: MagicMock,
        mock_net_debit: MagicMock,
    ):
        self.setup_mock_data()
        mock_check_parameters_exist.return_value = None
        mock_sum_balances.return_value = sentinel.balances_sum
        mock_net_debit.return_value = Decimal("50.25")

        result = vertical_repayment_hierarchy.get_total_overdue_amount(
            state=self.state,
        )

        self.assertEqual(Decimal("50.25"), result)
        mock_check_parameters_exist.assert_called_once_with(
            state=self.state,
            param_ids={vertical_repayment_hierarchy.denomination_module.DENOMINATION_PARAM_ID},
        )
        mock_sum_balances.assert_called_once_with(
            balances=self.state.balances,
            denomination=DEFAULT_DENOMINATION,
            addresses=vertical_repayment_hierarchy.OVERDUE_ADDRESSES,
        )
        mock_net_debit.assert_called_once_with(bal=sentinel.balances_sum)

    @patch.object(vertical_repayment_hierarchy.balance_utils, "net_debit")
    @patch.object(vertical_repayment_hierarchy.balance_utils, "sum_balances")
    @patch.object(vertical_repayment_hierarchy.state_utils, "check_parameters_exist")
    @pytest.mark.unit
    def test_get_total_outstanding_debt_custom_config(
        self,
        mock_check_parameters_exist: MagicMock,
        mock_sum_balances: MagicMock,
        mock_net_debit: MagicMock,
    ):
        custom_config = vertical_repayment_hierarchy.VerticalFetchersConfig(
            repayment_hierarchy=["address_1"],
            all_outstanding_addresses=["address_1", "address_2"],
            overdue_addresses=["address_1"],
            denomination_param_id="custom_denomination",
        )
        self.setup_mock_data()
        self.state.parameters["custom_denomination"] = "USD"
        mock_check_parameters_exist.return_value = None
        mock_sum_balances.return_value = sentinel.balances_sum
        mock_net_debit.return_value = Decimal("50.00")

        result = vertical_repayment_hierarchy.get_total_outstanding_debt(
            state=self.state,
            fetchers_config=custom_config,
        )

        self.assertEqual(Decimal("50.00"), result)
        mock_check_parameters_exist.assert_called_once_with(
            state=self.state,
            param_ids={"custom_denomination"},
        )
        mock_sum_balances.assert_called_once_with(
            balances=self.state.balances,
            denomination="USD",
            addresses=["address_1", "address_2"],
        )
        mock_net_debit.assert_called_once_with(bal=sentinel.balances_sum)

    @patch.object(vertical_repayment_hierarchy.balance_utils, "net_debit")
    @patch.object(vertical_repayment_hierarchy.balance_utils, "sum_balances")
    @patch.object(vertical_repayment_hierarchy.state_utils, "check_parameters_exist")
    @pytest.mark.unit
    def test_get_total_due_amount(
        self,
        mock_check_parameters_exist: MagicMock,
        mock_sum_balances: MagicMock,
        mock_net_debit: MagicMock,
    ):
        self.setup_mock_data()
        mock_check_parameters_exist.return_value = None
        mock_sum_balances.return_value = sentinel.balances_sum
        mock_net_debit.return_value = Decimal("75.00")

        result = vertical_repayment_hierarchy.get_total_due_amount(
            state=self.state,
        )

        self.assertEqual(Decimal("75.00"), result)
        mock_check_parameters_exist.assert_called_once_with(
            state=self.state,
            param_ids={vertical_repayment_hierarchy.denomination_module.DENOMINATION_PARAM_ID},
        )
        mock_sum_balances.assert_called_once_with(
            balances=self.state.balances,
            denomination=DEFAULT_DENOMINATION,
            addresses=vertical_repayment_hierarchy.REPAYMENT_HIERARCHY,
        )
        mock_net_debit.assert_called_once_with(bal=sentinel.balances_sum)

    @pytest.mark.unit
    def test_get_repayment_hierarchy_order(self):
        self.setup_mock_data()
        result = vertical_repayment_hierarchy.get_repayment_hierarchy_order(
            state=self.state,
        )
        self.assertListEqual(vertical_repayment_hierarchy.REPAYMENT_HIERARCHY, result)
