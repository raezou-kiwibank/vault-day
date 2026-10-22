# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel

import pytest

# features
import feature_library.lending.repayments.secondary.horizontal_repayment_hierarchy as horizontal_repayment_hierarchy  # noqa: E501

# contracts api
from contracts_api import (
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    Phase,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.utils import initialise_mock_state


@pytest.mark.unit
class HorizontalRepaymentHierarchyTest(FeatureTest):
    def setup_mock_data(
        self,
        denomination: str = DEFAULT_DENOMINATION,
        balances: BalanceDefaultDict | None = None,
    ):
        self.mock_vault = self.create_mock()
        self.state = initialise_mock_state(
            vault=self.mock_vault,
            parameters={
                horizontal_repayment_hierarchy.denomination_module.DENOMINATION_PARAM_ID: (
                    denomination
                ),
            },
            balances=balances,
        )

    @pytest.mark.unit
    def test_is_target_address(self):
        target_prefixes = ["OVERDUE", "PENALTY"]
        self.assertTrue(
            horizontal_repayment_hierarchy.is_target_address(
                address="OVERDUE_20260101", target_address_prefixes=target_prefixes
            )
        )
        self.assertTrue(
            horizontal_repayment_hierarchy.is_target_address(
                address="PENALTY", target_address_prefixes=target_prefixes
            )
        )
        self.assertFalse(
            horizontal_repayment_hierarchy.is_target_address(
                address="OVERDUE_PRINCIPAL", target_address_prefixes=target_prefixes
            )
        )
        self.assertFalse(
            horizontal_repayment_hierarchy.is_target_address(
                address="PRINCIPAL", target_address_prefixes=target_prefixes
            )
        )

    @pytest.mark.unit
    def test_get_late_repayment_balances(self):
        late_addresses = ["LATE"]
        coordinate_late = BalanceCoordinate(
            account_address="LATE",
            asset=DEFAULT_ASSET,
            denomination=DEFAULT_DENOMINATION,
            phase=Phase.COMMITTED,
        )
        coordinate_normal = BalanceCoordinate(
            account_address="NORMAL_ADDRESS",
            asset=DEFAULT_ASSET,
            denomination=DEFAULT_DENOMINATION,
            phase=Phase.COMMITTED,
        )

        balances = BalanceDefaultDict(
            lambda: Balance(),
            {
                coordinate_late: Balance(net=Decimal("10")),
                coordinate_normal: Balance(net=Decimal("20")),
            },
        )
        self.setup_mock_data(balances=balances)

        result = horizontal_repayment_hierarchy.get_late_repayment_balances(
            state=self.state,
            late_repayment_addresses=late_addresses,
        )

        self.assertEqual(1, len(result))
        self.assertIn(coordinate_late, result)
        self.assertEqual(Decimal("10"), result[coordinate_late].net)

    @pytest.mark.unit
    def test_get_overdue_balances(self):
        overdue_prefixes = ["OVERDUE"]
        coordinate_overdue = BalanceCoordinate(
            account_address="OVERDUE",
            asset=DEFAULT_ASSET,
            denomination=DEFAULT_DENOMINATION,
            phase=Phase.COMMITTED,
        )
        coordinate_normal = BalanceCoordinate(
            account_address="NORMAL_ADDRESS",
            asset=DEFAULT_ASSET,
            denomination=DEFAULT_DENOMINATION,
            phase=Phase.COMMITTED,
        )

        balances = BalanceDefaultDict(
            lambda: Balance(),
            {
                coordinate_overdue: Balance(net=Decimal("15")),
                coordinate_normal: Balance(net=Decimal("25")),
            },
        )
        self.setup_mock_data(balances=balances)

        result = horizontal_repayment_hierarchy.get_overdue_balances(
            state=self.state,
            overdue_addresses=overdue_prefixes,
        )

        self.assertEqual(1, len(result))
        self.assertIn(coordinate_overdue, result)
        self.assertEqual(Decimal("15"), result[coordinate_overdue].net)

    @patch.object(horizontal_repayment_hierarchy, "get_late_repayment_balances")
    @patch.object(horizontal_repayment_hierarchy.balance_utils, "net_debit")
    @patch.object(horizontal_repayment_hierarchy.balance_utils, "sum_balances")
    @patch.object(horizontal_repayment_hierarchy.state_utils, "check_parameters_exist")
    @pytest.mark.unit
    def test_get_total_outstanding_debt(
        self,
        mock_check_parameters_exist: MagicMock,
        mock_sum_balances: MagicMock,
        mock_net_debit: MagicMock,
        mock_get_late_repayment_balances: MagicMock,
    ):
        self.setup_mock_data()
        mock_check_parameters_exist.return_value = None

        # Mock late repayment balances
        coord_late = BalanceCoordinate(
            "LATE_ADDR", DEFAULT_ASSET, DEFAULT_DENOMINATION, Phase.COMMITTED
        )
        late_balances = BalanceDefaultDict(
            lambda: Balance(), {coord_late: Balance(net=Decimal("10"))}
        )
        mock_get_late_repayment_balances.return_value = late_balances

        mock_sum_balances.return_value = sentinel.balances_sum
        mock_net_debit.return_value = Decimal("150.00")

        result = horizontal_repayment_hierarchy.get_total_outstanding_debt(
            state=self.state,
        )

        self.assertEqual(Decimal("150.00"), result)

        expected_other_addresses = [
            addr
            for addr in horizontal_repayment_hierarchy.ALL_OUTSTANDING
            if addr not in horizontal_repayment_hierarchy.LATE_REPAYMENT_ADDRESSES
        ]
        expected_combined_addresses = ["LATE_ADDR"] + expected_other_addresses

        mock_sum_balances.assert_called_once_with(
            balances=self.state.balances,
            denomination=DEFAULT_DENOMINATION,
            addresses=expected_combined_addresses,
        )
        mock_net_debit.assert_called_once_with(bal=sentinel.balances_sum)

    @patch.object(horizontal_repayment_hierarchy, "get_overdue_balances")
    @patch.object(horizontal_repayment_hierarchy.balance_utils, "net_debit")
    @patch.object(horizontal_repayment_hierarchy.balance_utils, "sum_balances")
    @patch.object(horizontal_repayment_hierarchy.state_utils, "check_parameters_exist")
    @pytest.mark.unit
    def test_get_total_overdue_amount(
        self,
        mock_check_parameters_exist: MagicMock,
        mock_sum_balances: MagicMock,
        mock_net_debit: MagicMock,
        mock_get_overdue_balances: MagicMock,
    ):
        self.setup_mock_data()
        mock_check_parameters_exist.return_value = None

        # Mock overdue balances
        coord_overdue = BalanceCoordinate(
            "OVERDUE_ADDR", DEFAULT_ASSET, DEFAULT_DENOMINATION, Phase.COMMITTED
        )
        overdue_balances = BalanceDefaultDict(
            lambda: Balance(), {coord_overdue: Balance(net=Decimal("20"))}
        )
        mock_get_overdue_balances.return_value = overdue_balances

        mock_sum_balances.return_value = sentinel.balances_sum
        mock_net_debit.return_value = Decimal("20.00")

        result = horizontal_repayment_hierarchy.get_total_overdue_amount(
            state=self.state,
        )

        self.assertEqual(Decimal("20.00"), result)

        mock_sum_balances.assert_called_once_with(
            balances=self.state.balances,
            denomination=DEFAULT_DENOMINATION,
            addresses=["OVERDUE_ADDR"],
        )
        mock_net_debit.assert_called_once_with(bal=sentinel.balances_sum)

    @pytest.mark.unit
    def test_get_repayment_hierarchy_order_with_date_suffixes(self):
        coordinate_overdue_1 = BalanceCoordinate(
            account_address="OVERDUE_PRINCIPAL_20260201",
            asset=DEFAULT_ASSET,
            denomination=DEFAULT_DENOMINATION,
            phase=Phase.COMMITTED,
        )
        coordinate_overdue_2 = BalanceCoordinate(
            account_address="OVERDUE_PRINCIPAL_20260101",
            asset=DEFAULT_ASSET,
            denomination=DEFAULT_DENOMINATION,
            phase=Phase.COMMITTED,
        )
        coordinate_due = BalanceCoordinate(
            account_address="PRINCIPAL_DUE",
            asset=DEFAULT_ASSET,
            denomination=DEFAULT_DENOMINATION,
            phase=Phase.COMMITTED,
        )

        balances = BalanceDefaultDict(
            lambda: Balance(),
            {
                coordinate_overdue_1: Balance(net=Decimal("15")),
                coordinate_overdue_2: Balance(net=Decimal("25")),
                coordinate_due: Balance(net=Decimal("35")),
            },
        )
        self.setup_mock_data(balances=balances)

        # We override the default config for simplicity in this test
        custom_config = horizontal_repayment_hierarchy.HorizontalFetchersConfig(
            repayment_hierarchy=["OVERDUE_PRINCIPAL", "PRINCIPAL_DUE"],
            late_repayment_addresses=["OVERDUE_PRINCIPAL"],
            all_outstanding_addresses=[],
            overdue_addresses=[],
            denomination_param_id=horizontal_repayment_hierarchy.denomination_module.DENOMINATION_PARAM_ID,
        )

        result = horizontal_repayment_hierarchy.get_repayment_hierarchy_order(
            state=self.state,
            fetchers_config=custom_config,
        )

        # Should be oldest first for late repayments, then others in hierarchy order
        expected_result = [
            "OVERDUE_PRINCIPAL_20260101",
            "OVERDUE_PRINCIPAL_20260201",
            "PRINCIPAL_DUE",
        ]
        self.assertListEqual(expected_result, result)

    @pytest.mark.unit
    def test_get_repayment_hierarchy_order_with_overlapping_prefixes(self):
        coordinate_interest = BalanceCoordinate(
            account_address="INTEREST",
            asset=DEFAULT_ASSET,
            denomination=DEFAULT_DENOMINATION,
            phase=Phase.COMMITTED,
        )
        coordinate_interest_due = BalanceCoordinate(
            account_address="INTEREST_DUE",
            asset=DEFAULT_ASSET,
            denomination=DEFAULT_DENOMINATION,
            phase=Phase.COMMITTED,
        )

        balances = BalanceDefaultDict(
            lambda: Balance(),
            {
                coordinate_interest: Balance(net=Decimal("15")),
                coordinate_interest_due: Balance(net=Decimal("25")),
            },
        )
        self.setup_mock_data(balances=balances)

        # Repayment hierarchy has both INTEREST and INTEREST_DUE
        # We want to make sure INTEREST search doesn't pick up INTEREST_DUE
        custom_config = horizontal_repayment_hierarchy.HorizontalFetchersConfig(
            repayment_hierarchy=["INTEREST", "INTEREST_DUE"],
            late_repayment_addresses=[],
            all_outstanding_addresses=[],
            overdue_addresses=[],
            denomination_param_id=horizontal_repayment_hierarchy.denomination_module.DENOMINATION_PARAM_ID,
        )

        result = horizontal_repayment_hierarchy.get_repayment_hierarchy_order(
            state=self.state,
            fetchers_config=custom_config,
        )

        expected_result = ["INTEREST", "INTEREST_DUE"]
        self.assertListEqual(expected_result, result)

    @pytest.mark.unit
    def test_get_repayment_hierarchy_order_date_above_type(self):
        # We have Feb Principal and Jan Interest.
        # "Oldest first" means Jan Interest should come before Feb Principal.
        coordinate_overdue_p_feb = BalanceCoordinate(
            account_address="OVERDUE_PRINCIPAL_20260201",
            asset=DEFAULT_ASSET,
            denomination=DEFAULT_DENOMINATION,
            phase=Phase.COMMITTED,
        )
        coordinate_overdue_i_jan = BalanceCoordinate(
            account_address="OVERDUE_INTEREST_20260101",
            asset=DEFAULT_ASSET,
            denomination=DEFAULT_DENOMINATION,
            phase=Phase.COMMITTED,
        )

        balances = BalanceDefaultDict(
            lambda: Balance(),
            {
                coordinate_overdue_p_feb: Balance(net=Decimal("15")),
                coordinate_overdue_i_jan: Balance(net=Decimal("25")),
            },
        )
        self.setup_mock_data(balances=balances)

        custom_config = horizontal_repayment_hierarchy.HorizontalFetchersConfig(
            repayment_hierarchy=["OVERDUE_PRINCIPAL", "OVERDUE_INTEREST"],
            late_repayment_addresses=["OVERDUE_PRINCIPAL", "OVERDUE_INTEREST"],
            all_outstanding_addresses=[],
            overdue_addresses=[],
            denomination_param_id=horizontal_repayment_hierarchy.denomination_module.DENOMINATION_PARAM_ID,
        )

        result = horizontal_repayment_hierarchy.get_repayment_hierarchy_order(
            state=self.state,
            fetchers_config=custom_config,
        )

        # Jan Interest should be first because it is older than Feb Principal
        expected_result = [
            "OVERDUE_INTEREST_20260101",
            "OVERDUE_PRINCIPAL_20260201",
        ]
        self.assertListEqual(expected_result, result)
