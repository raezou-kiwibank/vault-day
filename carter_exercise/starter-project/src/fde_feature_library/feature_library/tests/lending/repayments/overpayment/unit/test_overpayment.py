# standard libs
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel

import pytest

import feature_library.lending.addresses as lending_addresses

# features
import feature_library.lending.repayments.overpayment as overpayment

# contracts api
from contracts_api import (
    Phase,
    Rejection,
    RejectionReason,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest
from inception_sdk.test_framework.contracts.unit.contracts_api_sentinels import SentinelPosting

from tests.utils import initialise_mock_state


class OverpaymentTest(FeatureTest):
    maxDiff = None


@pytest.mark.unit
class GetParametersTest(OverpaymentTest):
    def test_get_parameters(self):
        mock_obs = MagicMock(parameters={"param1": "value1"})
        mock_vault = self.create_mock(
            parameters_observation_fetchers_mapping={"fetcher_id": mock_obs}
        )

        result = overpayment.get_parameters(vault=mock_vault, param_fetcher_id="fetcher_id")

        self.assertEqual(result, {"param1": "value1"})


@pytest.mark.unit
class AppendToStateTest(OverpaymentTest):
    @patch.object(overpayment.state_utils, "append_to_state")
    @patch.object(overpayment, "get_parameters")
    def test_append_to_state(self, mock_get_parameters: MagicMock, mock_append_to_state: MagicMock):
        mock_vault = self.create_mock(account_id="mock_account")
        mock_state = initialise_mock_state(
            vault=mock_vault,
        )
        mock_get_parameters.return_value = {"param": "val"}
        mock_append_to_state.return_value = sentinel.new_state

        result = overpayment._append_to_state(mock_state)

        self.assertEqual(result, sentinel.new_state)
        mock_get_parameters.assert_called_once_with(
            mock_state.vault, overpayment.DEFAULT_OVERPAYMENT_FETCHERS_CONFIG.param_fetcher_id
        )
        mock_append_to_state.assert_called_once_with(state=mock_state, parameters={"param": "val"})


@pytest.mark.unit
class GetMaxOverpaymentFeeTest(OverpaymentTest):
    @patch.object(overpayment.balance_utils, "net_debit")
    @patch.object(overpayment.balance_utils, "get_current_net_balance")
    @patch.object(overpayment, "get_overpayment_fee")
    def test_get_max_overpayment_fee(
        self,
        mock_get_overpayment_fee: MagicMock,
        mock_get_current_net_balance: MagicMock,
        mock_net_debit: MagicMock,
    ):
        mock_net_debit.return_value = Decimal("100")
        mock_get_overpayment_fee.return_value = Decimal("10")

        result = overpayment.get_max_overpayment_fee(
            fee_rate=Decimal("0.5"),
            balances=sentinel.balances,
            denomination="GBP",
            precision=2,
            principal_address="PRINCIPAL",
        )

        self.assertEqual(result, Decimal("10"))
        mock_get_current_net_balance.assert_called_once_with(
            balances=sentinel.balances,
            address="PRINCIPAL",
            denomination="GBP",
            phase=Phase.COMMITTED,
        )
        mock_net_debit.assert_called_once()
        mock_get_overpayment_fee.assert_called_once_with(
            principal_repaid=Decimal("200.00"),
            overpayment_fee_rate=Decimal("0.5"),
            precision=2,
        )

    def test_get_max_overpayment_fee_rate_1(self):
        result = overpayment.get_max_overpayment_fee(
            fee_rate=Decimal("1"),
            balances=sentinel.balances,
            denomination="GBP",
        )
        self.assertEqual(result, Decimal("0"))

    def test_get_max_overpayment_fee_rate_above_1(self):
        result = overpayment.get_max_overpayment_fee(
            fee_rate=Decimal("1.5"),
            balances=sentinel.balances,
            denomination="GBP",
        )
        self.assertEqual(result, Decimal("0"))


@pytest.mark.unit
class GetOverpaymentFeeTest(OverpaymentTest):
    def test_get_overpayment_fee(self):
        result = overpayment.get_overpayment_fee(
            principal_repaid=Decimal("100"),
            overpayment_fee_rate=Decimal("0.05"),
            precision=2,
        )
        self.assertEqual(result, Decimal("5.00"))

    def test_get_overpayment_fee_rate_1(self):
        result = overpayment.get_overpayment_fee(
            principal_repaid=Decimal("100"),
            overpayment_fee_rate=Decimal("1"),
            precision=2,
        )
        self.assertEqual(result, Decimal("0"))

    def test_get_overpayment_fee_rate_above_1(self):
        result = overpayment.get_overpayment_fee(
            principal_repaid=Decimal("100"),
            overpayment_fee_rate=Decimal("1.5"),
            precision=2,
        )
        self.assertEqual(result, Decimal("0"))


@pytest.mark.unit
class ChargeOverpaymentFeeAsPenaltyTest(OverpaymentTest):
    @patch.object(overpayment, "_append_to_state")
    @patch.object(overpayment.state_utils, "check_parameters_exist")
    @patch.object(overpayment, "get_overpayment_fee")
    @patch.object(overpayment, "get_overpayment_fee_postings")
    @patch.object(overpayment.posting_utils, "standard_instruction_details")
    def test_charge_overpayment_fee_as_penalty(
        self,
        mock_standard_instruction_details: MagicMock,
        mock_get_overpayment_fee_postings: MagicMock,
        mock_get_overpayment_fee: MagicMock,
        mock_check_parameters_exist: MagicMock,
        mock_append_to_state: MagicMock,
    ):
        parameters = {
            overpayment.denomination.DENOMINATION_PARAM_ID: "GBP",
            "overpayment_fee_rate": Decimal("0.05"),
            "overpayment_fee_income_account": "income_acc",
        }
        mock_vault = self.create_mock(account_id="mock_account")
        mock_state = initialise_mock_state(
            vault=mock_vault,
            parameters=parameters,
        )
        mock_append_to_state.return_value = mock_state
        mock_check_parameters_exist.return_value = None
        mock_get_overpayment_fee.return_value = Decimal("5.00")

        mock_posting = SentinelPosting("fee_posting")
        mock_get_overpayment_fee_postings.return_value = [mock_posting]
        mock_standard_instruction_details.return_value = {"desc": "Charge fee"}

        result = overpayment.charge_overpayment_fee_as_penalty(
            state=mock_state,
            vault=mock_state.vault,
            overpayment_amount=Decimal("100"),
            precision=2,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].postings, [mock_posting])
        self.assertEqual(result[0].instruction_details, {"desc": "Charge fee"})

        mock_get_overpayment_fee.assert_called_once_with(
            principal_repaid=Decimal("100"),
            overpayment_fee_rate=Decimal("0.05"),
            precision=2,
        )
        mock_get_overpayment_fee_postings.assert_called_once_with(
            overpayment_fee=Decimal("5.00"),
            denomination="GBP",
            customer_account_id="mock_account",
            customer_account_address=lending_addresses.PENALTIES,
            internal_account="income_acc",
        )


@pytest.mark.unit
class GetOverpaymentFeePostingsTest(OverpaymentTest):
    @patch.object(overpayment.fee_utils, "fee_postings")
    def test_get_overpayment_fee_postings(self, mock_fee_postings: MagicMock):
        mock_fee_postings.return_value = [SentinelPosting("fee")]

        result = overpayment.get_overpayment_fee_postings(
            overpayment_fee=Decimal("5"),
            denomination="GBP",
            customer_account_id="customer",
            customer_account_address="address",
            internal_account="internal",
        )

        self.assertEqual(result, [SentinelPosting("fee")])
        mock_fee_postings.assert_called_once_with(
            customer_account_id="customer",
            customer_account_address="address",
            denomination="GBP",
            amount=Decimal("5"),
            internal_account="internal",
        )


@pytest.mark.unit
class IsPostingAnOverpaymentTest(OverpaymentTest):
    @patch.object(overpayment, "_append_to_state")
    def test_is_posting_an_overpayment_true(self, mock_append_to_state: MagicMock):
        mock_state = initialise_mock_state(vault=self.create_mock(account_id="mock_account"))
        mock_append_to_state.return_value = mock_state
        mock_rh_config = MagicMock()
        mock_rh_config.repayment_hierarchy.get_total_due_amount.return_value = Decimal("5")

        result = overpayment.is_posting_an_overpayment(
            state=mock_state,
            repayment_hierarchy_config=mock_rh_config,
            repayment_amount=Decimal("10"),
        )

        self.assertTrue(result)

    @patch.object(overpayment, "_append_to_state")
    def test_is_posting_an_overpayment_false_negative_amount(self, mock_append_to_state: MagicMock):
        mock_state = initialise_mock_state(vault=self.create_mock(account_id="mock_account"))
        mock_append_to_state.return_value = mock_state

        result = overpayment.is_posting_an_overpayment(
            state=mock_state,
            repayment_hierarchy_config=MagicMock(),
            repayment_amount=Decimal("-10"),
        )

        self.assertFalse(result)

    @patch.object(overpayment, "_append_to_state")
    def test_is_posting_an_overpayment_false_less_than_due(self, mock_append_to_state: MagicMock):
        mock_state = initialise_mock_state(vault=self.create_mock(account_id="mock_account"))
        mock_append_to_state.return_value = mock_state
        mock_rh_config = MagicMock()
        mock_rh_config.repayment_hierarchy.get_total_due_amount.return_value = Decimal("50")

        result = overpayment.is_posting_an_overpayment(
            state=mock_state,
            repayment_hierarchy_config=mock_rh_config,
            repayment_amount=Decimal("10"),
        )

        self.assertFalse(result)


@pytest.mark.unit
class ValidateIfOverpaymentIsGreaterThanMaxTest(OverpaymentTest):
    def test_validate_negative_amount(self):
        result = overpayment.validate_if_overpayment_is_greater_than_max(
            state=initialise_mock_state(vault=self.create_mock(account_id="mock_account")),
            repayment_amount=Decimal("-10"),
            repayment_hierarchy_config=MagicMock(),
        )
        self.assertIsNone(result)

    @patch.object(overpayment, "get_max_overpayment_amount")
    def test_validate_exceeds_max(self, mock_get_max_overpayment_amount: MagicMock):
        mock_get_max_overpayment_amount.return_value = Decimal("100")

        result = overpayment.validate_if_overpayment_is_greater_than_max(
            state=initialise_mock_state(vault=self.create_mock(account_id="mock_account")),
            repayment_amount=Decimal("150"),
            repayment_hierarchy_config=MagicMock(),
        )

        self.assertEqual(
            result,
            Rejection(
                message="Cannot pay more than is owed.",
                reason_code=RejectionReason.AGAINST_TNC,
            ),
        )

    @patch.object(overpayment, "get_max_overpayment_amount")
    def test_validate_within_max(self, mock_get_max_overpayment_amount: MagicMock):
        mock_get_max_overpayment_amount.return_value = Decimal("100")

        result = overpayment.validate_if_overpayment_is_greater_than_max(
            state=initialise_mock_state(vault=self.create_mock(account_id="mock_account")),
            repayment_amount=Decimal("50"),
            repayment_hierarchy_config=MagicMock(),
        )

        self.assertIsNone(result)


@pytest.mark.unit
class GetMaxOverpaymentAmountTest(OverpaymentTest):
    @patch.object(overpayment, "_append_to_state")
    @patch.object(overpayment.state_utils, "check_parameters_exist")
    @patch.object(overpayment, "get_max_overpayment_fee")
    def test_get_max_overpayment_amount(
        self,
        mock_get_max_overpayment_fee: MagicMock,
        mock_check_parameters_exist: MagicMock,
        mock_append_to_state: MagicMock,
    ):
        parameters = {
            "overpayment_fee_rate": Decimal("0.1"),
            overpayment.denomination.DENOMINATION_PARAM_ID: "GBP",
        }
        mock_vault = self.create_mock(account_id="mock_account")
        mock_state = initialise_mock_state(
            vault=mock_vault,
            parameters=parameters,
        )
        mock_append_to_state.return_value = mock_state
        mock_check_parameters_exist.return_value = None
        mock_rh_config = MagicMock()
        mock_rh_config.repayment_hierarchy.get_total_outstanding_debt.return_value = Decimal("100")
        mock_get_max_overpayment_fee.return_value = Decimal("10")

        result = overpayment.get_max_overpayment_amount(
            state=mock_state,
            repayment_hierarchy_config=mock_rh_config,
        )

        self.assertEqual(result, Decimal("110"))


@pytest.mark.unit
class HandleOverpaymentTest(OverpaymentTest):
    def test_handle_overpayment_zero(self):
        result = overpayment.handle_overpayment(
            state=initialise_mock_state(vault=self.create_mock(account_id="mock_account")),
            overpayment_amount=Decimal("0"),
        )
        self.assertEqual(result, [])

    @patch.object(overpayment, "_append_to_state")
    @patch.object(overpayment.state_utils, "check_parameters_exist")
    @patch.object(overpayment.balance_utils, "net_debit")
    @patch.object(overpayment.balance_utils, "get_current_net_balance")
    @patch.object(overpayment.posting_utils, "create_postings")
    def test_handle_overpayment_with_callable(
        self,
        mock_create_postings: MagicMock,
        mock_get_current_net_balance: MagicMock,
        mock_net_debit: MagicMock,
        mock_check_parameters_exist: MagicMock,
        mock_append_to_state: MagicMock,
    ):
        parameters = {overpayment.denomination.DENOMINATION_PARAM_ID: "GBP"}
        mock_vault = self.create_mock(account_id="mock_account")
        mock_state = initialise_mock_state(
            vault=mock_vault,
            parameters=parameters,
        )
        mock_append_to_state.return_value = mock_state
        mock_check_parameters_exist.return_value = None

        mock_net_debit.return_value = Decimal("50")

        mock_create_postings.side_effect = [
            [SentinelPosting("posting1")],
            [SentinelPosting("posting2")],
        ]

        mock_callable = MagicMock(return_value=[SentinelPosting("posting3")])

        result = overpayment.handle_overpayment(
            state=mock_state,
            overpayment_amount=Decimal("100"),
            repay_accrued_interest_callable=mock_callable,
        )

        self.assertEqual(
            result,
            [SentinelPosting("posting1"), SentinelPosting("posting2"), SentinelPosting("posting3")],
        )

        mock_callable.assert_called_once_with(mock_state, Decimal("50"))


@pytest.mark.unit
class GetEarlyRepaymentOverpaymentFeeTest(OverpaymentTest):
    @patch.object(overpayment, "_append_to_state")
    @patch.object(overpayment.state_utils, "check_parameters_exist")
    @patch.object(overpayment, "get_max_overpayment_fee")
    def test_get_early_repayment_overpayment_fee(
        self,
        mock_get_max_overpayment_fee: MagicMock,
        mock_check_parameters_exist: MagicMock,
        mock_append_to_state: MagicMock,
    ):
        parameters = {
            overpayment.denomination.DENOMINATION_PARAM_ID: "GBP",
            "overpayment_fee_rate": Decimal("0.1"),
        }
        mock_vault = self.create_mock(account_id="mock_account")
        mock_state = initialise_mock_state(
            vault=mock_vault,
            parameters=parameters,
        )
        mock_append_to_state.return_value = mock_state
        mock_check_parameters_exist.return_value = None
        mock_get_max_overpayment_fee.return_value = Decimal("15")

        result = overpayment.get_early_repayment_overpayment_fee(
            state=mock_state,
            precision=2,
        )

        self.assertEqual(result, Decimal("15"))


@pytest.mark.unit
class SkipChargeEarlyRepaymentFeeForOverpaymentTest(OverpaymentTest):
    def test_skip_charge(self):
        result = overpayment.skip_charge_early_repayment_fee_for_overpayment(
            state=initialise_mock_state(vault=self.create_mock(account_id="mock_account")),
            amount_to_charge=Decimal("10"),
            fee_name="fee",
        )
        self.assertEqual(result, [])


@pytest.mark.unit
class GetResidualCleanupPostingsTest(OverpaymentTest):
    @patch.object(overpayment.posting_utils, "create_postings")
    @patch.object(overpayment.balance_utils, "net_debit")
    @patch.object(overpayment.balance_utils, "get_current_net_balance")
    def test_get_residual_cleanup_postings(
        self,
        mock_get_current_net_balance: MagicMock,
        mock_net_debit: MagicMock,
        mock_create_postings: MagicMock,
    ):
        mock_balances = {"mock_balance_coordinate": "mock_balance"}
        mock_get_current_net_balance.return_value = "mock_net_balance"
        mock_net_debit.return_value = Decimal("100")
        mock_create_postings.return_value = [SentinelPosting("posting1")]

        result = overpayment.get_residual_cleanup_postings(
            balances=mock_balances,
            account_id="mock_account",
            denomination="GBP",
        )

        mock_get_current_net_balance.assert_called_once_with(
            balances=mock_balances,
            address=overpayment.OVERPAYMENT_ADDRESS,
            denomination="GBP",
        )
        mock_net_debit.assert_called_once_with(bal="mock_net_balance")
        mock_create_postings.assert_called_once_with(
            amount=Decimal("100"),
            debit_account="mock_account",
            credit_account="mock_account",
            debit_address=overpayment.common_addresses.INTERNAL_CONTRA,
            credit_address=overpayment.OVERPAYMENT_ADDRESS,
            denomination="GBP",
        )

        self.assertEqual(result, [SentinelPosting("posting1")])
