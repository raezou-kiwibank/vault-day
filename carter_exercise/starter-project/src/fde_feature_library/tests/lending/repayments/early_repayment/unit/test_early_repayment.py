# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel

import pytest

# features
import feature_library.lending.interfaces as lending_interfaces
import feature_library.lending.repayments.early_repayment as early_repayment
from feature_library.lending.addresses import PRINCIPAL

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest
from inception_sdk.test_framework.contracts.unit.contracts_api_sentinels import SentinelPosting

from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.utils import initialise_mock_state


@pytest.mark.unit
class EarlyRepaymentTest(FeatureTest):
    def setup_mock_data(
        self,
        early_repayment_fee_income_account: str = "EARLY_REPAYMENT_FEE_INCOME",
        early_repayment_flat_fee: Decimal = Decimal("50"),
        early_repayment_fee_rate: Decimal = Decimal("0.05"),
        denomination: str = DEFAULT_DENOMINATION,
    ):
        self.mock_vault = self.create_mock()
        self.state = initialise_mock_state(
            vault=self.mock_vault,
            parameters={
                early_repayment.EARLY_REPAYMENT_FEE_INCOME_ACCOUNT_PARAM_ID: (
                    early_repayment_fee_income_account
                ),
                early_repayment.EARLY_REPAYMENT_FLAT_FEE_PARAM_ID: early_repayment_flat_fee,
                early_repayment.EARLY_REPAYMENT_FEE_RATE_PARAM_ID: early_repayment_fee_rate,
                early_repayment.DEFAULT_EARLY_REPAYMENT_FETCHERS_CONFIG.denomination_param_id: (
                    denomination
                ),
            },
        )
        self.mock_repayment_hierarchy = MagicMock(spec=lending_interfaces.RepaymentHierarchy)
        self.mock_repayment_hierarchy_config = lending_interfaces.RepaymentHierarchyConfig(
            repayment_hierarchy=self.mock_repayment_hierarchy,
            fetchers_config=MagicMock(),
        )


@patch.object(early_repayment, "_is_zero_principal")
@patch.object(early_repayment, "get_total_early_repayment_amount")
@patch.object(early_repayment, "_append_to_state")
class IsPostingAnEarlyRepaymentTest(EarlyRepaymentTest):
    @pytest.mark.unit
    def test_is_posting_an_early_repayment_false(
        self,
        mock_append_to_state: MagicMock,
        mock_get_total_early_repayment_amount: MagicMock,
        mock_is_zero_principal: MagicMock,
    ):
        self.setup_mock_data()
        mock_append_to_state.return_value = self.state
        mock_get_total_early_repayment_amount.return_value = Decimal("300")
        mock_is_zero_principal.return_value = False

        result = early_repayment.is_posting_an_early_repayment(
            state=self.state,
            repayment_amount=Decimal("500"),
            repayment_hierarchy_config=self.mock_repayment_hierarchy_config,
            early_repayment_fees=[],
        )
        self.assertFalse(result)
        mock_get_total_early_repayment_amount.assert_called_once_with(
            state=self.state,
            repayment_hierarchy_config=self.mock_repayment_hierarchy_config,
            early_repayment_fees=[],
            precision=2,
            fetchers_config=early_repayment.DEFAULT_EARLY_REPAYMENT_FETCHERS_CONFIG,
        )

    @pytest.mark.unit
    def test_is_posting_an_early_repayment_true(
        self,
        mock_append_to_state: MagicMock,
        mock_get_total_early_repayment_amount: MagicMock,
        mock_is_zero_principal: MagicMock,
    ):
        self.setup_mock_data()
        mock_append_to_state.return_value = self.state
        mock_get_total_early_repayment_amount.return_value = Decimal("300")
        mock_is_zero_principal.return_value = False

        result = early_repayment.is_posting_an_early_repayment(
            state=self.state,
            repayment_amount=Decimal("300"),
            repayment_hierarchy_config=self.mock_repayment_hierarchy_config,
            early_repayment_fees=[],
        )
        self.assertTrue(result)

    @pytest.mark.unit
    def test_is_posting_an_early_repayment_negative_amount(
        self,
        mock_append_to_state: MagicMock,
        mock_get_total_early_repayment_amount: MagicMock,
        mock_is_zero_principal: MagicMock,
    ):
        self.setup_mock_data()
        result = early_repayment.is_posting_an_early_repayment(
            state=self.state,
            repayment_amount=Decimal("-300"),
            repayment_hierarchy_config=self.mock_repayment_hierarchy_config,
            early_repayment_fees=[],
        )
        self.assertFalse(result)
        mock_get_total_early_repayment_amount.assert_not_called()

    @pytest.mark.unit
    def test_is_posting_an_early_repayment_zero_principal(
        self,
        mock_append_to_state: MagicMock,
        mock_get_total_early_repayment_amount: MagicMock,
        mock_is_zero_principal: MagicMock,
    ):
        self.setup_mock_data()
        mock_append_to_state.return_value = self.state
        mock_is_zero_principal.return_value = True

        result = early_repayment.is_posting_an_early_repayment(
            state=self.state,
            repayment_amount=Decimal("300"),
            repayment_hierarchy_config=self.mock_repayment_hierarchy_config,
            early_repayment_fees=[],
        )
        self.assertFalse(result)
        mock_get_total_early_repayment_amount.assert_not_called()


@patch.object(early_repayment, "_is_zero_principal")
@patch.object(early_repayment, "_append_to_state")
class GetTotalEarlyRepaymentAmountTest(EarlyRepaymentTest):
    @pytest.mark.unit
    def test_get_total_early_repayment_amount(
        self,
        mock_append_to_state: MagicMock,
        mock_is_zero_principal: MagicMock,
    ):
        self.setup_mock_data()
        mock_append_to_state.return_value = self.state
        mock_is_zero_principal.return_value = False
        self.mock_repayment_hierarchy.get_total_outstanding_debt.return_value = Decimal("100")

        mock_fee = MagicMock(spec=lending_interfaces.EarlyRepaymentFee)
        mock_fee.get_early_repayment_fee_amount.return_value = Decimal("5")

        result = early_repayment.get_total_early_repayment_amount(
            state=self.state,
            repayment_hierarchy_config=self.mock_repayment_hierarchy_config,
            early_repayment_fees=[mock_fee, mock_fee],
        )
        self.assertEqual(Decimal("110"), result)
        self.mock_repayment_hierarchy.get_total_outstanding_debt.assert_called_once_with(
            state=self.state,
            fetchers_config=self.mock_repayment_hierarchy_config.fetchers_config,
        )
        self.assertEqual(2, mock_fee.get_early_repayment_fee_amount.call_count)

    @pytest.mark.unit
    def test_get_total_early_repayment_amount_zero_principal(
        self,
        mock_append_to_state: MagicMock,
        mock_is_zero_principal: MagicMock,
    ):
        self.setup_mock_data()
        mock_append_to_state.return_value = self.state
        mock_is_zero_principal.return_value = True

        result = early_repayment.get_total_early_repayment_amount(
            state=self.state,
            repayment_hierarchy_config=self.mock_repayment_hierarchy_config,
            early_repayment_fees=[],
        )
        self.assertEqual(Decimal("0"), result)
        self.mock_repayment_hierarchy.get_total_outstanding_debt.assert_not_called()


@patch.object(early_repayment, "_append_to_state")
class FlatFeeTest(EarlyRepaymentTest):
    @pytest.mark.unit
    def test_get_early_repayment_flat_fee(self, mock_append_to_state: MagicMock):
        self.setup_mock_data()
        mock_append_to_state.return_value = self.state

        result = early_repayment.get_early_repayment_flat_fee(
            state=self.state,
        )
        self.assertEqual(Decimal("50"), result)


@patch.object(early_repayment.balance_utils, "net_debit")
@patch.object(early_repayment.balance_utils, "sum_balances")
@patch.object(early_repayment, "_append_to_state")
class PercentageFeeTest(EarlyRepaymentTest):
    @pytest.mark.unit
    def test_calculate_early_repayment_percentage_fee(
        self,
        mock_append_to_state: MagicMock,
        mock_sum_balances: MagicMock,
        mock_net_debit: MagicMock,
    ):
        self.setup_mock_data(early_repayment_fee_rate=Decimal("0.1"))
        mock_append_to_state.return_value = self.state
        mock_sum_balances.return_value = sentinel.balances_sum
        mock_net_debit.return_value = Decimal("100")

        result = early_repayment.calculate_early_repayment_percentage_fee(
            state=self.state,
        )
        self.assertEqual(Decimal("10"), result)
        mock_sum_balances.assert_called_once_with(
            balances=self.state.balances,
            denomination=DEFAULT_DENOMINATION,
            addresses=early_repayment.DEFAULT_EARLY_REPAYMENT_FETCHERS_CONFIG.principal_addresses,
        )
        mock_net_debit.assert_called_once_with(sentinel.balances_sum)


@patch.object(early_repayment.posting_utils, "create_postings")
@patch.object(early_repayment, "_append_to_state")
class ChargeFeeTest(EarlyRepaymentTest):
    @pytest.mark.unit
    def test_charge_early_repayment_fee(
        self, mock_append_to_state: MagicMock, mock_create_postings: MagicMock
    ):
        self.setup_mock_data(early_repayment_fee_income_account="INCOME_ACCOUNT")
        mock_append_to_state.return_value = self.state
        mock_create_postings.return_value = [SentinelPosting("dummy")]

        result = early_repayment.charge_early_repayment_fee(
            state=self.state,
            amount_to_charge=Decimal("10"),
            fee_name="Test Fee",
        )

        mock_create_postings.assert_called_once_with(
            amount=Decimal("10"),
            debit_account=self.mock_vault.account_id,
            credit_account="INCOME_ACCOUNT",
            denomination=DEFAULT_DENOMINATION,
        )

        self.assertEqual(1, len(result))
        self.assertEqual([SentinelPosting("dummy")], result[0].postings)
        self.assertEqual(
            {"description": "Early Repayment Fee: Test Fee", "event": "EARLY_REPAYMENT"},
            result[0].instruction_details,
        )


@patch.object(early_repayment.balance_utils, "net_debit")
@patch.object(early_repayment.balance_utils, "sum_balances")
class IsZeroPrincipalTest(EarlyRepaymentTest):
    @pytest.mark.unit
    def test_is_zero_principal_true(self, mock_sum_balances: MagicMock, mock_net_debit: MagicMock):
        mock_sum_balances.return_value = sentinel.balances_sum
        mock_net_debit.return_value = Decimal("0")
        result = early_repayment._is_zero_principal(
            balances=sentinel.balances,
            denomination=DEFAULT_DENOMINATION,
        )
        self.assertTrue(result)
        mock_sum_balances.assert_called_once_with(
            balances=sentinel.balances,
            denomination=DEFAULT_DENOMINATION,
            addresses={PRINCIPAL},
        )
        mock_net_debit.assert_called_once_with(sentinel.balances_sum)

    @pytest.mark.unit
    def test_is_zero_principal_false(self, mock_sum_balances: MagicMock, mock_net_debit: MagicMock):
        mock_sum_balances.return_value = sentinel.balances_sum
        mock_net_debit.return_value = Decimal("10")
        result = early_repayment._is_zero_principal(
            balances=sentinel.balances,
            denomination=DEFAULT_DENOMINATION,
        )
        self.assertFalse(result)
