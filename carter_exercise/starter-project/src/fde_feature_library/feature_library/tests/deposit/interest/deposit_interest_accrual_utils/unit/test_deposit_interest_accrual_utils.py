# standard libs
from decimal import Decimal
from unittest.mock import MagicMock, call, patch, sentinel

import pytest

# features
import feature_library.common.accrual_utils as accrual_utils
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.state_utils as state_utils
import feature_library.deposit.addresses as deposit_addresses
import feature_library.deposit.interest.deposit_interest_accrual_utils as deposit_interest_accrual_utils  # noqa: E501
import feature_library.deposit.interest.interest_accrual as interest_accrual

# contracts api
from contracts_api import DEFAULT_ADDRESS, Balance, BalanceDefaultDict

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest
from inception_sdk.test_framework.contracts.unit.contracts_api_sentinels import (
    SentinelBalancesObservation,
    SentinelCustomInstruction,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.utils import initialise_mock_state

EFFECTIVE_SENTINEL_FETCHER = {
    deposit_interest_accrual_utils.fetchers.ALL_BALANCES_ET_BOF_ID: (
        SentinelBalancesObservation("effective")
    )
}


class TestInterestAccrualCapital(FeatureTest):
    def setUp(self) -> None:
        # mock vault
        self.mock_vault = self.create_mock(
            balances_observation_fetchers_mapping=EFFECTIVE_SENTINEL_FETCHER
        )

        # mock state
        self.mock_state = initialise_mock_state(
            vault=self.mock_vault,
            parameters={denomination_module.DENOMINATION_PARAM.id: sentinel.denomination},
            balances=BalanceDefaultDict(lambda: Balance(), {}),
        )

        # state_utils patches
        patch_append_to_state = patch.object(state_utils, "append_to_state")
        self.mock_append_to_state = patch_append_to_state.start()
        self.addCleanup(patch_append_to_state.stop)
        self.mock_append_to_state.return_value = self.mock_state

        patch_is_coordinates_in_state = patch.object(state_utils, "is_coordinates_in_state")
        self.mock_is_coordinates_in_state = patch_is_coordinates_in_state.start()
        self.addCleanup(patch_is_coordinates_in_state.stop)
        self.mock_is_coordinates_in_state.return_value = True

        # balance_utils patches
        patch_get_coordinates = patch.object(balance_utils, "get_coordinates")
        self.mock_get_coordinates = patch_get_coordinates.start()
        self.addCleanup(patch_get_coordinates.stop)
        self.mock_get_coordinates.return_value = sentinel.coordinates

        # sum_balances
        patch_sum_balances = patch.object(balance_utils, "sum_balances")
        self.mock_sum_balances = patch_sum_balances.start()
        self.addCleanup(patch_sum_balances.stop)
        self.mock_sum_balances.side_effect = [
            Balance(
                net=Decimal(100),
                credit=Decimal(100),
                debit=Decimal(0),
            )
        ]
        return super().setUp()

    @pytest.mark.unit
    def test_get_accrual_capital(self):
        self.assertEqual(
            deposit_interest_accrual_utils.get_accrual_capital(
                state=self.mock_state,
                capital_addresses=["DEFAULT"],
            ),
            Balance(credit=Decimal(100), debit=Decimal(0), net=Decimal(100)),
        )

        self.mock_is_coordinates_in_state.assert_called_once_with(
            state=self.mock_state, coordinates=sentinel.coordinates
        )
        self.mock_get_coordinates.assert_called_once_with(
            addresses=["DEFAULT"], denomination=sentinel.denomination
        )
        self.mock_append_to_state.assert_not_called()
        self.mock_sum_balances.assert_called_once_with(
            balances=self.mock_state.balances,
            addresses=["DEFAULT"],
            denomination=sentinel.denomination,
        )

    @pytest.mark.unit
    def test_get_accrual_capital_default_address(self):
        self.assertEqual(
            deposit_interest_accrual_utils.get_accrual_capital(state=self.mock_state),
            Balance(credit=Decimal(100), debit=Decimal(0), net=Decimal(100)),
        )

        self.mock_is_coordinates_in_state.assert_called_once_with(
            state=self.mock_state, coordinates=sentinel.coordinates
        )
        self.mock_get_coordinates.assert_called_once_with(
            addresses=[DEFAULT_ADDRESS], denomination=sentinel.denomination
        )
        self.mock_append_to_state.assert_not_called()

        self.mock_sum_balances.assert_called_once_with(
            balances=self.mock_state.balances,
            addresses=[DEFAULT_ADDRESS],
            denomination=sentinel.denomination,
        )

    @pytest.mark.unit
    def test_get_accrual_capital_negative_balance(self):
        self.mock_sum_balances.side_effect = [
            Balance(
                net=Decimal(-100),
                debit=Decimal(100),
                credit=Decimal(0),
            )
        ]
        self.assertEqual(
            deposit_interest_accrual_utils.get_accrual_capital(
                state=self.mock_state,
                capital_addresses=["DEFAULT"],
            ),
            Balance(credit=Decimal(0), debit=Decimal(100), net=Decimal(-100)),
        )

        self.mock_get_coordinates.assert_called_once_with(
            addresses=["DEFAULT"], denomination=sentinel.denomination
        )
        self.mock_is_coordinates_in_state.assert_called_once_with(
            state=self.mock_state, coordinates=sentinel.coordinates
        )
        self.mock_append_to_state.assert_not_called()
        self.mock_sum_balances.assert_called_once_with(
            balances=self.mock_state.balances,
            addresses=["DEFAULT"],
            denomination=sentinel.denomination,
        )

    @patch.object(state_utils, "check_parameters_exist")
    @pytest.mark.unit
    def test_get_accrual_capital_raises_assertion_error_if_parameter_missing(
        self, mock_check_parameters_exist: MagicMock
    ):
        mock_check_parameters_exist.return_value = sentinel.rejection

        with self.assertRaises(AssertionError) as ex:
            deposit_interest_accrual_utils.get_accrual_capital(state=self.mock_state)

        self.assertEqual(ex.exception.args[0], sentinel.rejection)
        mock_check_parameters_exist.assert_called_once_with(
            state=self.mock_state, param_ids={denomination_module.DENOMINATION_PARAM.id}
        )

    @pytest.mark.unit
    def test_get_accrual_capital_uses_provided_balances(self):
        self.assertEqual(
            deposit_interest_accrual_utils.get_accrual_capital(
                state=self.mock_state,
                balances=sentinel.provided_balances,
                capital_addresses=["DEFAULT"],
            ),
            Balance(credit=Decimal(100), debit=Decimal(0), net=Decimal(100)),
        )

        self.mock_get_coordinates.assert_called_once_with(
            addresses=["DEFAULT"], denomination=sentinel.denomination
        )
        self.mock_is_coordinates_in_state.assert_called_once_with(
            state=self.mock_state, coordinates=sentinel.coordinates
        )
        self.mock_append_to_state.assert_not_called()
        self.mock_sum_balances.assert_called_once_with(
            balances=sentinel.provided_balances,
            addresses=["DEFAULT"],
            denomination=sentinel.denomination,
        )

    @pytest.mark.unit
    def test_get_accrual_capital_is_debit_interest(self):
        self.mock_sum_balances.side_effect = [
            Balance(
                net=Decimal(-100),
                credit=Decimal(0),
                debit=Decimal(100),
            )
        ]

        self.assertEqual(
            deposit_interest_accrual_utils.get_accrual_capital(
                state=self.mock_state,
                capital_addresses=["DEFAULT"],
            ),
            Balance(credit=Decimal(0), debit=Decimal(100), net=Decimal(-100)),
        )

        self.mock_get_coordinates.assert_called_once_with(
            addresses=["DEFAULT"], denomination=sentinel.denomination
        )
        self.mock_is_coordinates_in_state.assert_called_once_with(
            state=self.mock_state, coordinates=sentinel.coordinates
        )
        self.mock_append_to_state.assert_not_called()
        self.mock_sum_balances.assert_called_once_with(
            balances=self.mock_state.balances,
            addresses=["DEFAULT"],
            denomination=sentinel.denomination,
        )

    @pytest.mark.unit
    def test_get_accrual_capital_updates_state_if_balances_missing(self):
        self.mock_is_coordinates_in_state.return_value = False

        # mock observation result
        mock_observation_balances = SentinelBalancesObservation("all_balances")
        # We must clear the side_effect set by create_mock in setUp so return_value is used
        self.mock_vault.get_balances_observation.side_effect = None
        self.mock_vault.get_balances_observation.return_value = mock_observation_balances

        # result of append_to_state
        mock_new_state = initialise_mock_state(
            vault=self.mock_state.vault,
            parameters=self.mock_state.parameters,
            balances=mock_observation_balances.balances,
        )
        self.mock_append_to_state.return_value = mock_new_state

        self.assertEqual(
            deposit_interest_accrual_utils.get_accrual_capital(
                state=self.mock_state,
                capital_addresses=["DEFAULT"],
            ),
            Balance(credit=Decimal(100), debit=Decimal(0), net=Decimal(100)),
        )

        self.mock_get_coordinates.assert_called_once_with(
            addresses=["DEFAULT"], denomination=sentinel.denomination
        )
        self.mock_is_coordinates_in_state.assert_called_once_with(
            state=self.mock_state, coordinates=sentinel.coordinates
        )
        self.mock_append_to_state.assert_called_once_with(
            state=self.mock_state, balances=sentinel.balances_all_balances
        )
        self.mock_sum_balances.assert_called_once_with(
            balances=mock_new_state.balances,
            addresses=["DEFAULT"],
            denomination=sentinel.denomination,
        )


class TestReverseInterestAccrual(FeatureTest):
    def setUp(self) -> None:
        # mock vault
        self.mock_vault = self.create_mock(
            balances_observation_fetchers_mapping=EFFECTIVE_SENTINEL_FETCHER
        )

        # mock state
        self.mock_state = initialise_mock_state(
            vault=self.mock_vault,
            parameters={
                denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
                interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID: "payable_acc",
                interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID: "receivable_acc",
            },
        )

        # state_utils patches
        patch_append_to_state = patch.object(state_utils, "append_to_state")
        self.mock_append_to_state = patch_append_to_state.start()
        self.addCleanup(patch_append_to_state.stop)
        self.mock_append_to_state.return_value = self.mock_state

        patch_check_parameters_exist = patch.object(state_utils, "check_parameters_exist")
        self.mock_check_parameters_exist = patch_check_parameters_exist.start()
        self.addCleanup(patch_check_parameters_exist.stop)
        self.mock_check_parameters_exist.return_value = None

        # sum_balances
        patch_sum_balances = patch.object(balance_utils, "sum_balances")
        self.mock_sum_balances = patch_sum_balances.start()
        self.addCleanup(patch_sum_balances.stop)

        # create_payable_accrual_custom_instruction
        patch_create_payable_accrual_custom_instruction = patch.object(
            accrual_utils, "create_payable_accrual_custom_instruction"
        )
        self.mock_create_payable_accrual_custom_instruction = (
            patch_create_payable_accrual_custom_instruction.start()
        )
        self.addCleanup(patch_create_payable_accrual_custom_instruction.stop)

        return super().setUp()

    @pytest.mark.unit
    def test_reverse_payable_interest(self):
        mock_receivable_balance = MagicMock()
        mock_receivable_balance.net = Decimal("0")
        mock_payable_balance = MagicMock()
        mock_payable_balance.net = Decimal("1.5")

        self.mock_sum_balances.side_effect = [
            mock_receivable_balance,
            mock_payable_balance,
        ]
        self.mock_create_payable_accrual_custom_instruction.return_value = [
            SentinelCustomInstruction("internal_payable")
        ]

        reversal_postings = deposit_interest_accrual_utils.get_interest_reversal_postings(
            state=self.mock_state,
            event_name=sentinel.event,
            accrued_payable_account_param_id=interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID,  # noqa: E501
            accrued_receivable_account_param_id=interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID,  # noqa: E501
        )

        self.mock_create_payable_accrual_custom_instruction.assert_called_once_with(
            customer_account=self.mock_vault.account_id,
            customer_address=deposit_addresses.ACCRUED_INTEREST_PAYABLE,
            denomination=DEFAULT_DENOMINATION,
            amount=Decimal("1.5"),
            internal_account="payable_acc",
            instruction_details={
                "description": "Reversing 1.5 GBP of accrued interest",
                "event": sentinel.event,
                "gl_impacted": "True",
                "account_type": "",
            },
            reversal=True,
        )

        self.assertEqual(len(reversal_postings), 1)
        self.assertListEqual(reversal_postings, [SentinelCustomInstruction("internal_payable")])

    @pytest.mark.unit
    def test_reverse_receivable_interest(
        self,
    ):
        mock_receivable_balance = MagicMock()
        mock_receivable_balance.net = Decimal("-1.5")
        mock_payable_balance = MagicMock()
        mock_payable_balance.net = Decimal("0")

        self.mock_sum_balances.side_effect = [
            mock_receivable_balance,
            mock_payable_balance,
        ]
        self.mock_create_payable_accrual_custom_instruction.return_value = [
            SentinelCustomInstruction("internal receivable")
        ]

        _ = deposit_interest_accrual_utils.get_interest_reversal_postings(
            state=self.mock_state,
            event_name=sentinel.event,
            accrued_payable_account_param_id=interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID,  # noqa: E501
            accrued_receivable_account_param_id=interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID,  # noqa: E501
        )

        self.mock_create_payable_accrual_custom_instruction.assert_called_once_with(
            customer_account=self.mock_vault.account_id,
            customer_address=deposit_addresses.ACCRUED_INTEREST_RECEIVABLE,
            denomination=DEFAULT_DENOMINATION,
            amount=Decimal("-1.5"),
            internal_account="receivable_acc",
            instruction_details={
                "description": "Reversing -1.5 GBP of accrued interest",
                "event": sentinel.event,
                "gl_impacted": "True",
                "account_type": "",
            },
            reversal=True,
        )

    @pytest.mark.unit
    def test_no_reverse_interest_balance_0(self):
        mock_receivable_balance = MagicMock()
        mock_receivable_balance.net = Decimal("0")
        mock_payable_balance = MagicMock()
        mock_payable_balance.net = Decimal("0")

        self.mock_sum_balances.side_effect = [
            mock_receivable_balance,
            mock_payable_balance,
        ]

        reversal_postings = deposit_interest_accrual_utils.get_interest_reversal_postings(
            state=self.mock_state,
            event_name=sentinel.event,
            accrued_payable_account_param_id=interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID,  # noqa: E501
            accrued_receivable_account_param_id=interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID,  # noqa: E501
        )

        self.assertListEqual(reversal_postings, [])
        self.mock_create_payable_accrual_custom_instruction.assert_not_called()

    @pytest.mark.unit
    def test_reverse_interest_balances_provided(self):
        mock_receivable_balance = MagicMock()
        mock_receivable_balance.net = Decimal("-1.5")
        mock_payable_balance = MagicMock()
        mock_payable_balance.net = Decimal("0")

        # construct mocks
        self.mock_sum_balances.side_effect = [
            mock_receivable_balance,
            mock_payable_balance,
        ]
        self.mock_create_payable_accrual_custom_instruction.return_value = [
            SentinelCustomInstruction("internal_receivable")
        ]

        # run function with balances provided
        reversal_postings = deposit_interest_accrual_utils.get_interest_reversal_postings(
            state=self.mock_state,
            event_name=sentinel.event,
            balances=sentinel.balances,
            accrued_payable_account_param_id=interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID,  # noqa: E501
            accrued_receivable_account_param_id=interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID,  # noqa: E501
        )
        self.assertEqual(reversal_postings, [SentinelCustomInstruction("internal_receivable")])

        # call assertions
        self.mock_sum_balances.assert_has_calls(
            calls=[
                call(
                    balances=sentinel.balances,
                    addresses=[deposit_addresses.ACCRUED_INTEREST_RECEIVABLE],
                    denomination=DEFAULT_DENOMINATION,
                ),
                call(
                    balances=sentinel.balances,
                    addresses=[deposit_addresses.ACCRUED_INTEREST_PAYABLE],
                    denomination=DEFAULT_DENOMINATION,
                ),
            ]
        )
        self.mock_create_payable_accrual_custom_instruction.assert_called_once_with(
            customer_account=self.mock_vault.account_id,
            customer_address=deposit_addresses.ACCRUED_INTEREST_RECEIVABLE,
            denomination=DEFAULT_DENOMINATION,
            amount=Decimal("-1.5"),
            internal_account="receivable_acc",
            instruction_details={
                "description": "Reversing -1.5 GBP of accrued interest",
                "event": sentinel.event,
                "gl_impacted": "True",
                "account_type": "",
            },
            reversal=True,
        )

    @pytest.mark.unit
    def test_get_interest_reversal_postings_raises_assertion_error_if_parameter_missing(self):
        self.mock_check_parameters_exist.return_value = sentinel.rejection

        with self.assertRaises(AssertionError) as ex:
            deposit_interest_accrual_utils.get_interest_reversal_postings(
                state=self.mock_state,
                event_name=sentinel.event,
                accrued_payable_account_param_id="payable_acc",
                accrued_receivable_account_param_id="receivable_acc",
            )

        self.assertEqual(ex.exception.args[0], sentinel.rejection)
        self.mock_check_parameters_exist.assert_called_once_with(
            state=self.mock_state,
            param_ids={
                denomination_module.DENOMINATION_PARAM.id,
                "payable_acc",
                "receivable_acc",
            },
        )


class TestGetTargetCustomerAddressAndInternalAccount(FeatureTest):
    @pytest.mark.unit
    def test_positive_accrual_amount_returns_payable_address_and_account(
        self,
    ):
        result = deposit_interest_accrual_utils.get_target_customer_address_and_internal_account(
            accrual_amount=Decimal("10"),
            accrued_interest_payable_account=interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID,  # noqa: E501
            accrued_interest_receivable_account=interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID,  # noqa: E501
        )
        self.assertTupleEqual(
            result,
            (
                deposit_addresses.ACCRUED_INTEREST_PAYABLE,
                interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID,
            ),
        )

    @pytest.mark.unit
    def test_negative_accrual_amount_returns_receivable_address_and_account(
        self,
    ):
        result = deposit_interest_accrual_utils.get_target_customer_address_and_internal_account(
            accrual_amount=Decimal("-10"),
            accrued_interest_payable_account=interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID,  # noqa: E501
            accrued_interest_receivable_account=interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID,  # noqa: E501
        )
        self.assertTupleEqual(
            result,
            (
                deposit_addresses.ACCRUED_INTEREST_RECEIVABLE,
                interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID,
            ),
        )

    @pytest.mark.unit
    def test_positive_accrual_amount_returns_payable_address_and_provided_account(
        self,
    ):
        result = deposit_interest_accrual_utils.get_target_customer_address_and_internal_account(
            accrual_amount=Decimal("10"),
            accrued_interest_payable_account="PAYABLE",
            accrued_interest_receivable_account="RECEIVABLE",
        )
        self.assertTupleEqual(
            result,
            (
                deposit_addresses.ACCRUED_INTEREST_PAYABLE,
                "PAYABLE",
            ),
        )

    @pytest.mark.unit
    def test_negative_accrual_amount_returns_receivable_address_and_provided_account(
        self,
    ):
        result = deposit_interest_accrual_utils.get_target_customer_address_and_internal_account(
            accrual_amount=Decimal("-10"),
            accrued_interest_payable_account="PAYABLE",
            accrued_interest_receivable_account="RECEIVABLE",
        )
        self.assertTupleEqual(
            result,
            (
                deposit_addresses.ACCRUED_INTEREST_RECEIVABLE,
                "RECEIVABLE",
            ),
        )
