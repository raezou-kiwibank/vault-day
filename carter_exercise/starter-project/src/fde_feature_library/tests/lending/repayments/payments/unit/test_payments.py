# standard libs
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

import feature_library.lending.interfaces as lending_interfaces

# features
import feature_library.lending.repayments.payments as payments

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    CustomInstruction,
    Phase,
    Posting,
    PostPostingHookArguments,
)

from inception_sdk.test_framework.contracts.unit.common import FeatureTest


class PaymentsTest(FeatureTest):
    maxDiff = None


class RedistributePostingsTest(PaymentsTest):
    @pytest.mark.unit
    def test_amount_less_than_zero_returns_empty_list(self):
        result = payments.redistribute_postings(
            debit_account="debit_account",
            denomination="GBP",
            amount=Decimal("-10.00"),
            credit_account="credit_account",
            credit_address="CREDIT_ADDRESS",
        )
        self.assertListEqual(result, [])

    @pytest.mark.unit
    def test_amount_equal_zero_returns_empty_list(self):
        result = payments.redistribute_postings(
            debit_account="debit_account",
            denomination="GBP",
            amount=Decimal("0"),
            credit_account="credit_account",
            credit_address="CREDIT_ADDRESS",
        )
        self.assertListEqual(result, [])

    @patch.object(payments.posting_utils, "create_postings")
    @pytest.mark.unit
    def test_amount_greater_than_zero_creates_postings(self, mock_create_postings: MagicMock):
        expected_postings = [MagicMock(spec=Posting), MagicMock(spec=Posting)]
        mock_create_postings.return_value = expected_postings

        result = payments.redistribute_postings(
            debit_account="debit_account",
            denomination="GBP",
            amount=Decimal("10.00"),
            credit_account="credit_account",
            credit_address="CREDIT_ADDRESS",
            debit_address="DEBIT_ADDRESS",
        )

        self.assertListEqual(result, expected_postings)
        mock_create_postings.assert_called_once_with(
            amount=Decimal("10.00"),
            debit_account="debit_account",
            credit_account="credit_account",
            denomination="GBP",
            debit_address="DEBIT_ADDRESS",
            credit_address="CREDIT_ADDRESS",
        )

    @patch.object(payments.posting_utils, "create_postings")
    @pytest.mark.unit
    def test_amount_greater_than_zero_creates_postings_default_address(
        self, mock_create_postings: MagicMock
    ):
        expected_postings = [MagicMock(spec=Posting), MagicMock(spec=Posting)]
        mock_create_postings.return_value = expected_postings

        result = payments.redistribute_postings(
            debit_account="debit_account",
            denomination="GBP",
            amount=Decimal("10.00"),
            credit_account="credit_account",
            credit_address="CREDIT_ADDRESS",
        )

        self.assertListEqual(result, expected_postings)
        mock_create_postings.assert_called_once_with(
            amount=Decimal("10.00"),
            debit_account="debit_account",
            credit_account="credit_account",
            denomination="GBP",
            debit_address=DEFAULT_ADDRESS,
            credit_address="CREDIT_ADDRESS",
        )


class DistributeRepaymentForSingleTargetTest(PaymentsTest):
    @pytest.mark.unit
    def test_distribute_repayment_multiple_addresses(self):
        # mock balances
        balances = BalanceDefaultDict(lambda: Balance())
        address_1 = "ADDR_1"
        address_2 = "ADDR_2"
        coord_1 = BalanceCoordinate(address_1, DEFAULT_ASSET, "GBP", Phase.COMMITTED)
        coord_2 = BalanceCoordinate(address_2, DEFAULT_ASSET, "GBP", Phase.COMMITTED)
        balances[coord_1] = Balance(debit=Decimal("10.00"))
        balances[coord_2] = Balance(debit=Decimal("10.00"))

        repayment_amount = Decimal("15.00")
        hierarchy = [address_1, address_2]

        result_per_address, remaining = payments.distribute_repayment_for_single_target(
            balances=balances,
            repayment_amount=repayment_amount,
            denomination="GBP",
            repayment_hierarchy=hierarchy,
        )

        self.assertEqual(remaining, Decimal("0"))
        self.assertEqual(result_per_address[address_1].rounded_amount, Decimal("10.00"))
        self.assertEqual(result_per_address[address_2].rounded_amount, Decimal("5.00"))

    @pytest.mark.unit
    def test_distribute_repayment_remainder(self):
        # mock balances
        balances = BalanceDefaultDict(lambda: Balance())
        address_1 = "ADDR_1"
        coord_1 = BalanceCoordinate(address_1, DEFAULT_ASSET, "GBP", Phase.COMMITTED)
        balances[coord_1] = Balance(debit=Decimal("5.00"))

        repayment_amount = Decimal("7.00")
        hierarchy = [address_1]

        result_per_address, remaining = payments.distribute_repayment_for_single_target(
            balances=balances,
            repayment_amount=repayment_amount,
            denomination="GBP",
            repayment_hierarchy=hierarchy,
        )

        self.assertEqual(remaining, Decimal("2.00"))
        self.assertEqual(result_per_address[address_1].rounded_amount, Decimal("5.00"))

    @pytest.mark.unit
    def test_distribute_repayment_unrounded_vs_rounded(self):
        # mock balances
        balances = BalanceDefaultDict(lambda: Balance())
        address_1 = "ADDR_1"
        coord_1 = BalanceCoordinate(address_1, DEFAULT_ASSET, "GBP", Phase.COMMITTED)
        balances[coord_1] = Balance(debit=Decimal("5.005"))

        repayment_amount = Decimal("5.00")
        hierarchy = [address_1]

        result_per_address, remaining = payments.distribute_repayment_for_single_target(
            balances=balances,
            repayment_amount=repayment_amount,
            denomination="GBP",
            repayment_hierarchy=hierarchy,
        )

        self.assertEqual(remaining, Decimal("0"))
        self.assertIn(address_1, result_per_address)
        self.assertEqual(result_per_address[address_1].rounded_amount, Decimal("5.00"))
        self.assertEqual(result_per_address[address_1].unrounded_amount, Decimal("5.00"))


class GenerateRepaymentPostingsTest(PaymentsTest):
    def setUp(self):
        self.mock_is_posting_early_repayment = MagicMock(return_value=False)
        self.mock_handle_penalties = MagicMock(return_value=[])
        self.mock_repay_accrued_interest = MagicMock()
        self.mock_repayment_hierarchy_config = MagicMock(
            spec=lending_interfaces.RepaymentHierarchyConfig
        )
        repayment_hierarchy = self.mock_repayment_hierarchy_config.repayment_hierarchy
        repayment_hierarchy.get_repayment_hierarchy_order.return_value = ["ADDR_1"]
        self.mock_state = MagicMock()
        self.mock_state.parameters = {payments.denomination_module.DENOMINATION_PARAM_ID: "GBP"}
        self.mock_state.balances = BalanceDefaultDict(lambda: Balance())

        self.hook_args = MagicMock(spec=PostPostingHookArguments)
        self.mock_posting_instruction = MagicMock()
        balances = BalanceDefaultDict(lambda: Balance())
        balances[BalanceCoordinate(DEFAULT_ADDRESS, DEFAULT_ASSET, "GBP", Phase.COMMITTED)] = (
            Balance(credit=Decimal("10.00"))
        )
        self.mock_posting_instruction.balances.return_value = balances
        self.hook_args.posting_instructions = [self.mock_posting_instruction]

    @pytest.mark.unit
    @patch.object(payments, "distribute_repayment_for_single_target")
    @patch.object(payments, "redistribute_postings")
    def test_repayment_amount_greater_than_zero_processes_repayment(
        self, mock_redistribute_postings: MagicMock, mock_distribute: MagicMock
    ):
        mock_distribute.return_value = payments.RepaymentDistribution(
            repayment_per_address={
                "ADDR_1": payments.RepaymentAmounts(
                    unrounded_amount=Decimal("5.00"), rounded_amount=Decimal("5.00")
                )
            },
            remaining_repayment_amount=Decimal("5.00"),
        )
        expected_posting = MagicMock(spec=Posting)
        mock_redistribute_postings.return_value = [expected_posting]

        result = payments.generate_repayment_postings(
            state=self.mock_state,
            hook_arguments=self.hook_args,
            repayment_hierarchy_config=self.mock_repayment_hierarchy_config,
            is_posting_early_repayment_callable=self.mock_is_posting_early_repayment,
            handle_penalties_pending_capitalisation_callable=self.mock_handle_penalties,
        )

        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], CustomInstruction)
        self.assertListEqual(result[0].postings, [expected_posting])
        mock_redistribute_postings.assert_called_once_with(
            debit_account=self.mock_state.vault.account_id,
            amount=Decimal("5.00"),
            denomination="GBP",
            credit_account=self.mock_state.vault.account_id,
            credit_address="ADDR_1",
        )

    @pytest.mark.unit
    @patch.object(payments, "distribute_repayment_for_single_target")
    @patch.object(payments, "redistribute_postings")
    def test_overpayment_features_called_when_remaining_amount_greater_than_zero(
        self, mock_redistribute_postings: MagicMock, mock_distribute: MagicMock
    ):
        mock_distribute.return_value = payments.RepaymentDistribution(
            repayment_per_address={}, remaining_repayment_amount=Decimal("10.00")
        )
        mock_overpayment_feature = MagicMock(spec=lending_interfaces.Overpayment)
        expected_posting = MagicMock(spec=Posting)
        mock_overpayment_feature.handle_overpayment.return_value = [expected_posting]

        result = payments.generate_repayment_postings(
            state=self.mock_state,
            hook_arguments=self.hook_args,
            repayment_hierarchy_config=self.mock_repayment_hierarchy_config,
            is_posting_early_repayment_callable=self.mock_is_posting_early_repayment,
            handle_penalties_pending_capitalisation_callable=self.mock_handle_penalties,
            overpayment_features=[mock_overpayment_feature],
            repay_accrued_interest_callable=self.mock_repay_accrued_interest,
        )

        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], CustomInstruction)
        self.assertListEqual(result[0].postings, [expected_posting])
        mock_overpayment_feature.handle_overpayment.assert_called_once_with(
            state=self.mock_state,
            overpayment_amount=Decimal("10.00"),
            repay_accrued_interest_callable=self.mock_repay_accrued_interest,
        )

    @pytest.mark.unit
    @patch.object(payments, "distribute_repayment_for_single_target")
    @patch.object(payments, "redistribute_postings")
    def test_early_repayment_fees_charged_when_callable_returns_true(
        self, mock_redistribute_postings: MagicMock, mock_distribute: MagicMock
    ):
        mock_distribute.return_value = payments.RepaymentDistribution(
            repayment_per_address={}, remaining_repayment_amount=Decimal("10.00")
        )
        self.mock_is_posting_early_repayment.return_value = True
        expected_ci = MagicMock(spec=CustomInstruction)
        self.mock_handle_penalties.return_value = [expected_ci]

        mock_early_repayment_fee = MagicMock(spec=lending_interfaces.EarlyRepaymentFee)
        mock_early_repayment_fee.get_early_repayment_fee_amount.return_value = Decimal("2.00")
        expected_fee_ci = MagicMock(spec=CustomInstruction)
        mock_early_repayment_fee.charge_early_repayment_fee.return_value = [expected_fee_ci]
        mock_early_repayment_fee.fee_name = "early_repayment_fee"

        result = payments.generate_repayment_postings(
            state=self.mock_state,
            hook_arguments=self.hook_args,
            repayment_hierarchy_config=self.mock_repayment_hierarchy_config,
            is_posting_early_repayment_callable=self.mock_is_posting_early_repayment,
            handle_penalties_pending_capitalisation_callable=self.mock_handle_penalties,
            early_repayment_fees=[mock_early_repayment_fee],
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], expected_ci)
        self.assertEqual(result[1], expected_fee_ci)
        mock_early_repayment_fee.charge_early_repayment_fee.assert_called_once_with(
            state=self.mock_state, amount_to_charge=Decimal("2.00"), fee_name="early_repayment_fee"
        )
