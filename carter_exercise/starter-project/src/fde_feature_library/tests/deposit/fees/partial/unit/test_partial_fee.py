# Copyright @ 2023 Thought Machine Group Limited. All rights reserved.
# standard libs
from decimal import Decimal
from unittest.mock import MagicMock, _Sentinel, call, patch, sentinel

import pytest

import feature_library.common.state_utils as state_utils

# features
import feature_library.deposit.fees.partial_fee as partial_fee
import feature_library.deposit.interfaces as deposit_interfaces

# contracts api
from contracts_api import Phase, Posting

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

from tests.common.test_denomination import DEFAULT_DENOMINATION

dummy_posting = Posting(
    credit=True,
    amount=Decimal("1"),
    denomination=DEFAULT_DENOMINATION,
    account_id="1",
    account_address="1",
    asset="1",
    phase=Phase.COMMITTED,
)


def generate_mock_fee_details(
    partial_fee_tracking_address: str | _Sentinel,
    fee_type: str | _Sentinel,
    internal_account_parameter_id: str | _Sentinel,
):
    fee_details = MagicMock(deposit_interfaces.PartialFeeCollection)
    fee_details.fee_type = fee_type
    fee_details.outstanding_fee_address = partial_fee_tracking_address
    fee_details.internal_account_parameter_id = internal_account_parameter_id
    return fee_details


def mock_incoming_fee_custom_instruction():
    incoming_fee_custom_instruction = MagicMock()
    incoming_fee_custom_instruction.balances.return_value = MagicMock()
    incoming_fee_custom_instruction.instruction_details = {"description": "dummy"}
    return incoming_fee_custom_instruction


class PartialFeeTest(FeatureTest):
    def setUp(self) -> None:
        self.effective_datetime = sentinel.effective_datetime

        self.mock_tracking_balance_instructions = patch.object(
            partial_fee, "modify_tracking_balance_utils"
        ).start()
        self.mock_create_postings = patch.object(
            partial_fee.posting_utils, "create_postings"
        ).start()

        self.mock_tracking_balance_instructions.return_value = [sentinel.CustomInstructionPartial]
        self.mock_create_postings.return_value = [dummy_posting]

        self.addCleanup(patch.stopall)
        return super().setUp()


@patch.object(partial_fee.balance_utils, "net_debit")
@patch.object(partial_fee.balance_utils, "get_available_balance")
class TestPartialFeeCharging(PartialFeeTest):
    @pytest.mark.unit
    def test_charge_partial_fee_generates_postings(
        self,
        mock_get_available_balance: MagicMock,
        mock_net_debit: MagicMock,
    ):
        # test parameters
        available_balance = Decimal("15")
        fee_amount = Decimal("20")
        partial_fee_address = "PARTIAL_FEE"
        internal_account_parameter_id = "internal_account_parameter_id"
        internal_address = "INTERNAL_ADDRESS"
        fee_type = "FEE_TYPE"

        expected_charged_fee = Decimal("15")
        expected_remaining_fee = Decimal("5")

        # setup mocks
        incoming_fee_custom_instruction = mock_incoming_fee_custom_instruction()
        mock_net_debit.return_value = fee_amount
        mock_available_balance_obj = MagicMock()
        mock_available_balance_obj.net = available_balance
        mock_get_available_balance.return_value = mock_available_balance_obj

        mock_fee_details = generate_mock_fee_details(
            partial_fee_tracking_address=partial_fee_address,
            fee_type=fee_type,
            internal_account_parameter_id=internal_account_parameter_id,
        )
        mock_vault = self.create_mock(
            balances_observation_fetchers_mapping={
                partial_fee.fetchers.ALL_BALANCES_ET_BOF_ID: MagicMock(balances={})
            }
        )
        mock_state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=self.effective_datetime,
            parameters={
                partial_fee.denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
                internal_account_parameter_id: internal_address,
            },
        )

        # Execute test
        response = partial_fee.charge_partial_fee(
            state=mock_state,
            fee_details=mock_fee_details,
            fee_custom_instruction=incoming_fee_custom_instruction,
        )

        # Assert Relevant Mocks
        self.mock_create_postings.assert_called_once_with(
            amount=expected_charged_fee,
            debit_account=mock_vault.account_id,
            credit_account=internal_address,
            denomination=DEFAULT_DENOMINATION,
        )

        self.mock_tracking_balance_instructions.assert_called_once_with(
            account_id=mock_vault.account_id,
            denomination=DEFAULT_DENOMINATION,
            tracking_address=partial_fee_address,
            value=expected_remaining_fee,
            instruction_details={
                "description": f"Charge outstanding partial fee: {fee_type}",
                "event": f"Charge {fee_type}",
            },
        )

        # Assert results
        # We expect a new Custom Instruction appended to the response, plus tracking
        self.assertEqual(len(response), 2)
        self.assertEqual(response[0].postings, [dummy_posting])
        self.assertEqual(
            response[0].instruction_details,
            {
                "description": "dummy Partially charged, remaining 5 to be charged when the "
                "account has sufficient balance"
            },
        )
        self.assertEqual(response[1], sentinel.CustomInstructionPartial)

    @pytest.mark.unit
    def test_charge_partial_fee_generates_postings_more_debt(
        self,
        mock_get_available_balance: MagicMock,
        mock_net_debit: MagicMock,
    ):
        # test parameters
        available_balance = Decimal("10")
        fee_amount = Decimal("50")
        partial_fee_address = "PARTIAL_FEE"
        internal_account_parameter_id = "internal_account_parameter_id"
        internal_address = "INTERNAL_ADDRESS"
        fee_type = "FEE_TYPE"

        expected_charged_fee = Decimal("10")
        expected_remaining_fee = Decimal("40")

        # setup mocks
        incoming_fee_custom_instruction = mock_incoming_fee_custom_instruction()
        mock_net_debit.return_value = fee_amount
        mock_available_balance_obj = MagicMock()
        mock_available_balance_obj.net = available_balance
        mock_get_available_balance.return_value = mock_available_balance_obj

        mock_fee_details = generate_mock_fee_details(
            partial_fee_tracking_address=partial_fee_address,
            fee_type=fee_type,
            internal_account_parameter_id=internal_account_parameter_id,
        )
        mock_vault = self.create_mock(
            balances_observation_fetchers_mapping={
                partial_fee.fetchers.ALL_BALANCES_ET_BOF_ID: MagicMock(balances={})
            }
        )
        mock_state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=self.effective_datetime,
            parameters={
                partial_fee.denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
                internal_account_parameter_id: internal_address,
            },
        )

        # Execute test
        response = partial_fee.charge_partial_fee(
            state=mock_state,
            fee_details=mock_fee_details,
            fee_custom_instruction=incoming_fee_custom_instruction,
        )

        # Assert Relevant Mocks
        self.mock_create_postings.assert_called_once_with(
            amount=expected_charged_fee,
            debit_account=mock_vault.account_id,
            credit_account=internal_address,
            denomination=DEFAULT_DENOMINATION,
        )

        self.mock_tracking_balance_instructions.assert_called_once_with(
            account_id=mock_vault.account_id,
            denomination=DEFAULT_DENOMINATION,
            tracking_address=partial_fee_address,
            value=expected_remaining_fee,
            instruction_details={
                "description": f"Charge outstanding partial fee: {fee_type}",
                "event": f"Charge {fee_type}",
            },
        )

        # Assert results
        self.assertEqual(len(response), 2)
        self.assertEqual(response[1], sentinel.CustomInstructionPartial)

    @pytest.mark.unit
    def test_charge_partial_fee_generates_postings_no_balance(
        self,
        mock_get_available_balance: MagicMock,
        mock_net_debit: MagicMock,
    ):
        # test parameters
        available_balance = Decimal("0")
        fee_amount = Decimal("50")
        partial_fee_address = "PARTIAL_FEE"
        internal_account_parameter_id = "internal_account_parameter_id"
        internal_address = "INTERNAL_ADDRESS"
        fee_type = "FEE_TYPE"

        expected_remaining_fee = Decimal("50")

        # setup mocks
        incoming_fee_custom_instruction = mock_incoming_fee_custom_instruction()
        mock_net_debit.return_value = fee_amount
        mock_available_balance_obj = MagicMock()
        mock_available_balance_obj.net = available_balance
        mock_get_available_balance.return_value = mock_available_balance_obj

        mock_fee_details = generate_mock_fee_details(
            partial_fee_tracking_address=partial_fee_address,
            fee_type=fee_type,
            internal_account_parameter_id=internal_account_parameter_id,
        )
        mock_vault = self.create_mock(
            balances_observation_fetchers_mapping={
                partial_fee.fetchers.ALL_BALANCES_ET_BOF_ID: MagicMock(balances={})
            }
        )
        mock_state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=self.effective_datetime,
            parameters={
                partial_fee.denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
                internal_account_parameter_id: internal_address,
            },
        )

        # Execute test
        response = partial_fee.charge_partial_fee(
            state=mock_state,
            fee_details=mock_fee_details,
            fee_custom_instruction=incoming_fee_custom_instruction,
        )

        # Assert Relevant Mocks
        self.mock_create_postings.assert_not_called()

        self.mock_tracking_balance_instructions.assert_called_once_with(
            account_id=mock_vault.account_id,
            denomination=DEFAULT_DENOMINATION,
            tracking_address=partial_fee_address,
            value=expected_remaining_fee,
            instruction_details={
                "description": f"Charge outstanding partial fee: {fee_type}",
                "event": f"Charge {fee_type}",
            },
        )

        # Assert results
        self.assertEqual(response, [sentinel.CustomInstructionPartial])

    @pytest.mark.unit
    def test_charge_partial_fee_generates_postings_base_balance_enough(
        self,
        mock_get_available_balance: MagicMock,
        mock_net_debit: MagicMock,
    ):
        # test parameters
        available_balance = Decimal("50")
        fee_amount = Decimal("20")
        partial_fee_address = "PARTIAL_FEE"
        internal_address = "INTERNAL_ADDRESS"
        fee_type = "FEE_TYPE"

        # setup mocks
        incoming_fee_custom_instruction = mock_incoming_fee_custom_instruction()

        mock_net_debit.return_value = fee_amount
        mock_available_balance_obj = MagicMock()
        mock_available_balance_obj.net = available_balance
        mock_get_available_balance.return_value = mock_available_balance_obj

        mock_fee_details = generate_mock_fee_details(
            partial_fee_tracking_address=partial_fee_address,
            fee_type=fee_type,
            internal_account_parameter_id=internal_address,
        )
        mock_vault = self.create_mock(
            balances_observation_fetchers_mapping={
                partial_fee.fetchers.ALL_BALANCES_ET_BOF_ID: MagicMock(balances={})
            }
        )
        mock_state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=self.effective_datetime,
            parameters={
                partial_fee.denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION
            },
        )

        # Execute test
        response = partial_fee.charge_partial_fee(
            state=mock_state,
            fee_details=mock_fee_details,
            fee_custom_instruction=incoming_fee_custom_instruction,
        )

        # Assert Relevant Mocks
        self.mock_create_postings.assert_not_called()
        self.mock_tracking_balance_instructions.assert_not_called()

        # Assert results
        self.assertEqual(response, [incoming_fee_custom_instruction])

    @pytest.mark.unit
    def test_charge_partial_fee_fetches_balances_and_denom_with_available_balance_callable(
        self,
        mock_get_available_balance: MagicMock,
        mock_net_debit: MagicMock,
    ):
        # test parameters
        available_balance = Decimal("15")
        fee_amount = Decimal("20")
        partial_fee_address = "PARTIAL_FEE"
        internal_account_parameter_id = "internal_account_parameter_id"
        internal_address = "INTERNAL_ADDRESS"
        fee_type = "FEE_TYPE"

        expected_charged_fee = Decimal("15")
        expected_remaining_fee = Decimal("5")

        # setup mocks
        incoming_fee_custom_instruction = mock_incoming_fee_custom_instruction()
        del incoming_fee_custom_instruction.instruction_details["description"]

        mock_net_debit.return_value = fee_amount

        mock_fee_details = generate_mock_fee_details(
            partial_fee_tracking_address=partial_fee_address,
            fee_type=fee_type,
            internal_account_parameter_id=internal_account_parameter_id,
        )
        mock_balance_observation = MagicMock()
        mock_balance_observation.balances = {}
        mock_vault = self.create_mock(
            balances_observation_fetchers_mapping={
                partial_fee.fetchers.ALL_BALANCES_ET_BOF_ID: mock_balance_observation
            }
        )
        mock_state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=self.effective_datetime,
            parameters={
                partial_fee.denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
                internal_account_parameter_id: internal_address,
            },
        )
        mock_available_balance = MagicMock()
        mock_calculate_available_balance = MagicMock(return_value=available_balance)
        mock_available_balance.calculate = mock_calculate_available_balance

        # Execute test
        response = partial_fee.charge_partial_fee(
            state=mock_state,
            fee_details=mock_fee_details,
            fee_custom_instruction=incoming_fee_custom_instruction,
            available_balance_feature=mock_available_balance,
        )

        # Assert Relevant Mocks
        self.mock_create_postings.assert_called_once_with(
            amount=expected_charged_fee,
            debit_account=mock_vault.account_id,
            credit_account=internal_address,
            denomination=DEFAULT_DENOMINATION,
        )

        self.mock_tracking_balance_instructions.assert_called_once_with(
            account_id=mock_vault.account_id,
            denomination=DEFAULT_DENOMINATION,
            tracking_address=partial_fee_address,
            value=expected_remaining_fee,
            instruction_details={
                "description": f"Charge outstanding partial fee: {fee_type}",
                "event": f"Charge {fee_type}",
            },
        )

        # Assert results
        self.assertEqual(len(response), 2)
        self.assertEqual(response[1], sentinel.CustomInstructionPartial)
        mock_get_available_balance.assert_not_called()
        mock_calculate_available_balance.assert_called_once_with(state=mock_state)


@patch.object(partial_fee.balance_utils, "balance_at_coordinates")
@patch.object(partial_fee.balance_utils, "get_available_balance")
class TestPartialOutstandingFeeCharging(PartialFeeTest):
    @pytest.mark.unit
    def test_charge_outstanding_fee_generates_postings(
        self,
        mock_get_available_balance: MagicMock,
        mock_balance_at_coordinates: MagicMock,
    ):
        # test parameters
        available_balance = Decimal("15")
        fee_amount = Decimal("20")
        partial_fee_address = "PARTIAL_FEE"
        internal_account_parameter_id = "internal_account_parameter_id"
        internal_address = "INTERNAL_ADDRESS"
        fee_type = "FEE_TYPE"

        expected_charged_fee = Decimal("15")

        # setup mocks
        mock_balance_at_coordinates.return_value = fee_amount
        mock_available_balance_obj = MagicMock()
        mock_available_balance_obj.net = available_balance
        mock_get_available_balance.return_value = mock_available_balance_obj

        mock_fee_details = generate_mock_fee_details(
            partial_fee_tracking_address=partial_fee_address,
            fee_type=fee_type,
            internal_account_parameter_id=internal_account_parameter_id,
        )

        mock_balance_observation = MagicMock()
        mock_balance_observation.balances = {}
        mock_vault = self.create_mock(
            balances_observation_fetchers_mapping={
                partial_fee.fetchers.ALL_BALANCES_LIVE_BOF.fetcher_id: mock_balance_observation
            }
        )
        mock_state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=self.effective_datetime,
            parameters={
                partial_fee.denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
                internal_account_parameter_id: internal_address,
            },
        )

        # Execute test
        response = partial_fee.charge_outstanding_fees(
            state=mock_state,
            fee_collection=[mock_fee_details],
        )

        # Assert Relevant Mocks
        self.mock_create_postings.assert_called_once_with(
            amount=expected_charged_fee,
            debit_account=mock_vault.account_id,
            credit_account=internal_address,
            denomination=DEFAULT_DENOMINATION,
        )

        self.mock_tracking_balance_instructions.assert_called_once_with(
            account_id=mock_vault.account_id,
            denomination=DEFAULT_DENOMINATION,
            tracking_address=partial_fee_address,
            value=expected_charged_fee,
            payment_deduction=True,
            instruction_details={
                "description": f"Charge outstanding partial fee: {fee_type}",
                "event": f"Charge {fee_type}",
            },
        )

        # Assert results
        self.assertEqual(len(response), 2)
        self.assertEqual(response[1], sentinel.CustomInstructionPartial)

    @pytest.mark.unit
    def test_charge_partial_fee_generates_postings_sufficient_funds(
        self,
        mock_get_available_balance: MagicMock,
        mock_balance_at_coordinates: MagicMock,
    ):
        # test parameters
        available_balance = Decimal("400")
        fee_amount = Decimal("20")
        partial_fee_address = "PARTIAL_FEE"
        internal_account_parameter_id = "internal_account_parameter_id"
        internal_address = "INTERNAL_ADDRESS"
        fee_type = "FEE_TYPE"

        expected_charged_fee = Decimal("20")

        mock_balance_at_coordinates.return_value = fee_amount
        mock_available_balance_obj = MagicMock()
        mock_available_balance_obj.net = available_balance
        mock_get_available_balance.return_value = mock_available_balance_obj

        mock_fee_details = generate_mock_fee_details(
            partial_fee_tracking_address=partial_fee_address,
            fee_type=fee_type,
            internal_account_parameter_id=internal_account_parameter_id,
        )
        mock_vault = self.create_mock(
            balances_observation_fetchers_mapping={
                partial_fee.fetchers.ALL_BALANCES_LIVE_BOF.fetcher_id: MagicMock(balances={})
            }
        )
        mock_state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=self.effective_datetime,
            parameters={
                partial_fee.denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
                internal_account_parameter_id: internal_address,
            },
        )

        # Execute test
        response = partial_fee.charge_outstanding_fees(
            state=mock_state,
            fee_collection=[mock_fee_details],
        )

        # Assert Relevant Mocks
        self.mock_create_postings.assert_called_once_with(
            amount=expected_charged_fee,
            debit_account=mock_vault.account_id,
            credit_account=internal_address,
            denomination=DEFAULT_DENOMINATION,
        )

        self.mock_tracking_balance_instructions.assert_called_once_with(
            account_id=mock_vault.account_id,
            denomination=DEFAULT_DENOMINATION,
            tracking_address=partial_fee_address,
            value=expected_charged_fee,
            payment_deduction=True,
            instruction_details={
                "description": f"Charge outstanding partial fee: {fee_type}",
                "event": f"Charge {fee_type}",
            },
        )

        # Assert results
        self.assertEqual(len(response), 2)
        self.assertEqual(response[1], sentinel.CustomInstructionPartial)

    @pytest.mark.unit
    def test_charge_multiple_outstanding_fee_generates_postings_sufficient_funds(
        self,
        mock_get_available_balance: MagicMock,
        mock_balance_at_coordinates: MagicMock,
    ):
        # test parameters
        available_balance = Decimal("40")
        # fee 1
        fee_amount_1 = Decimal("10")
        partial_fee_address_1 = "PARTIAL_FEE_1"
        internal_account_parameter_id_1 = "internal_account_parameter_id_1"
        internal_address_1 = "INTERNAL_ADDRESS_1"
        fee_type_1 = "FEE_TYPE"
        expected_charged_fee_1 = Decimal("10")

        # fee 2
        fee_amount_2 = Decimal("30")
        partial_fee_address_2 = "PARTIAL_FEE_2"
        internal_account_parameter_id_2 = "internal_account_parameter_id_2"
        internal_address_2 = "INTERNAL_ADDRESS_2"
        fee_type_2 = "FEE_TYPE"
        expected_charged_fee_2 = Decimal("30")

        # setup mocks
        mock_balance_at_coordinates.side_effect = [fee_amount_1, fee_amount_2]
        mock_available_balance_obj = MagicMock()
        mock_available_balance_obj.net = available_balance
        mock_get_available_balance.return_value = mock_available_balance_obj

        mock_fee_details_1 = generate_mock_fee_details(
            partial_fee_tracking_address=partial_fee_address_1,
            fee_type=fee_type_1,
            internal_account_parameter_id=internal_account_parameter_id_1,
        )
        mock_fee_details_2 = generate_mock_fee_details(
            partial_fee_tracking_address=partial_fee_address_2,
            fee_type=fee_type_2,
            internal_account_parameter_id=internal_account_parameter_id_2,
        )

        mock_balance_observation = MagicMock()
        mock_balance_observation.balances = {}
        mock_vault = self.create_mock(
            balances_observation_fetchers_mapping={
                partial_fee.fetchers.ALL_BALANCES_LIVE_BOF.fetcher_id: mock_balance_observation
            }
        )
        mock_state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=self.effective_datetime,
            parameters={
                partial_fee.denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
                internal_account_parameter_id_1: internal_address_1,
                internal_account_parameter_id_2: internal_address_2,
            },
        )

        # Execute test
        response = partial_fee.charge_outstanding_fees(
            state=mock_state,
            fee_collection=[mock_fee_details_1, mock_fee_details_2],
        )

        # Assert Relevant Mocks
        self.mock_create_postings.assert_has_calls(
            [
                call(
                    amount=expected_charged_fee_1,
                    debit_account=mock_vault.account_id,
                    credit_account=internal_address_1,
                    denomination=DEFAULT_DENOMINATION,
                ),
                call(
                    amount=expected_charged_fee_2,
                    debit_account=mock_vault.account_id,
                    credit_account=internal_address_2,
                    denomination=DEFAULT_DENOMINATION,
                ),
            ]
        )

        self.mock_tracking_balance_instructions.assert_has_calls(
            [
                call(
                    account_id=mock_vault.account_id,
                    denomination=DEFAULT_DENOMINATION,
                    tracking_address=partial_fee_address_1,
                    value=expected_charged_fee_1,
                    payment_deduction=True,
                    instruction_details={
                        "description": f"Charge outstanding partial fee: {fee_type_1}",
                        "event": f"Charge {fee_type_1}",
                    },
                ),
                call(
                    account_id=mock_vault.account_id,
                    denomination=DEFAULT_DENOMINATION,
                    tracking_address=partial_fee_address_2,
                    value=expected_charged_fee_2,
                    payment_deduction=True,
                    instruction_details={
                        "description": f"Charge outstanding partial fee: {fee_type_2}",
                        "event": f"Charge {fee_type_2}",
                    },
                ),
            ]
        )

        # Assert results
        self.assertEqual(len(response), 4)
        self.assertEqual(response[1], sentinel.CustomInstructionPartial)
        self.assertEqual(response[3], sentinel.CustomInstructionPartial)

    @pytest.mark.unit
    def test_charge_multiple_outstanding_fee_generates_postings_insufficient_funds(
        self,
        mock_get_available_balance: MagicMock,
        mock_balance_at_coordinates: MagicMock,
    ):
        # test parameters
        available_balance = Decimal("30")
        # fee 1
        fee_amount_1 = Decimal("20")
        partial_fee_address_1 = "PARTIAL_FEE_1"
        internal_account_parameter_id_1 = "internal_account_parameter_id_1"
        internal_address_1 = "INTERNAL_ADDRESS_1"
        fee_type_1 = "FEE_TYPE"
        expected_charged_fee_1 = Decimal("20")

        # fee 2
        fee_amount_2 = Decimal("20")
        partial_fee_address_2 = "PARTIAL_FEE_2"
        internal_account_parameter_id_2 = "internal_account_parameter_id_2"
        internal_address_2 = "INTERNAL_ADDRESS_2"
        fee_type_2 = "FEE_TYPE"
        expected_charged_fee_2 = Decimal("10")

        # fee 3
        fee_amount_3 = Decimal("20")
        partial_fee_address_3 = "PARTIAL_FEE_3"
        internal_account_parameter_id_3 = "internal_account_parameter_id_3"
        internal_address_3 = "INTERNAL_ADDRESS_3"
        fee_type_3 = "FEE_TYPE"

        # setup mocks
        mock_balance_at_coordinates.side_effect = [fee_amount_1, fee_amount_2, fee_amount_3]
        mock_available_balance_obj = MagicMock()
        mock_available_balance_obj.net = available_balance
        mock_get_available_balance.return_value = mock_available_balance_obj

        mock_fee_details_1 = generate_mock_fee_details(
            partial_fee_tracking_address=partial_fee_address_1,
            fee_type=fee_type_1,
            internal_account_parameter_id=internal_account_parameter_id_1,
        )
        mock_fee_details_2 = generate_mock_fee_details(
            partial_fee_tracking_address=partial_fee_address_2,
            fee_type=fee_type_2,
            internal_account_parameter_id=internal_account_parameter_id_2,
        )
        mock_fee_details_3 = generate_mock_fee_details(
            partial_fee_tracking_address=partial_fee_address_3,
            fee_type=fee_type_3,
            internal_account_parameter_id=internal_account_parameter_id_3,
        )

        mock_balance_observation = MagicMock()
        mock_balance_observation.balances = {}
        mock_vault = self.create_mock(
            balances_observation_fetchers_mapping={
                partial_fee.fetchers.ALL_BALANCES_LIVE_BOF.fetcher_id: mock_balance_observation
            }
        )
        mock_state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=self.effective_datetime,
            parameters={
                partial_fee.denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
                internal_account_parameter_id_1: internal_address_1,
                internal_account_parameter_id_2: internal_address_2,
                internal_account_parameter_id_3: internal_address_3,
            },
        )

        # Execute test
        response = partial_fee.charge_outstanding_fees(
            state=mock_state,
            fee_collection=[mock_fee_details_1, mock_fee_details_2, mock_fee_details_3],
        )

        # Assert Relevant Mocks
        self.mock_create_postings.assert_has_calls(
            [
                call(
                    amount=expected_charged_fee_1,
                    debit_account=mock_vault.account_id,
                    credit_account=internal_address_1,
                    denomination=DEFAULT_DENOMINATION,
                ),
                call(
                    amount=expected_charged_fee_2,
                    debit_account=mock_vault.account_id,
                    credit_account=internal_address_2,
                    denomination=DEFAULT_DENOMINATION,
                ),
            ]
        )

        self.mock_tracking_balance_instructions.assert_has_calls(
            [
                call(
                    account_id=mock_vault.account_id,
                    denomination=DEFAULT_DENOMINATION,
                    tracking_address=partial_fee_address_1,
                    value=expected_charged_fee_1,
                    payment_deduction=True,
                    instruction_details={
                        "description": f"Charge outstanding partial fee: {fee_type_1}",
                        "event": f"Charge {fee_type_1}",
                    },
                ),
                call(
                    account_id=mock_vault.account_id,
                    denomination=DEFAULT_DENOMINATION,
                    tracking_address=partial_fee_address_2,
                    value=expected_charged_fee_2,
                    payment_deduction=True,
                    instruction_details={
                        "description": f"Charge outstanding partial fee: {fee_type_2}",
                        "event": f"Charge {fee_type_2}",
                    },
                ),
            ]
        )

        # Assert results
        self.assertEqual(len(response), 4)
        self.assertEqual(response[1], sentinel.CustomInstructionPartial)
        self.assertEqual(response[3], sentinel.CustomInstructionPartial)


@patch.object(partial_fee.balance_utils, "balance_at_coordinates")
@patch.object(partial_fee.denomination_module, "get_parameters")
class HasOutstandingFeesTest(PartialFeeTest):
    @pytest.mark.unit
    def test_has_no_outstanding_fees(
        self,
        mock_get_parameters: MagicMock,
        mock_balance_at_coordinates: MagicMock,
    ):
        # construct mocks
        mock_fee_details = generate_mock_fee_details(
            partial_fee_tracking_address="PARTIAL_FEE",
            fee_type="FEE_TYPE",
            internal_account_parameter_id="INTERNAL_ADDRESS",
        )
        mock_balance_at_coordinates.return_value = Decimal("0")
        mock_vault = self.create_mock(
            balances_observation_fetchers_mapping={
                partial_fee.fetchers.ALL_BALANCES_LIVE_BOF.fetcher_id: MagicMock(balances={})
            }
        )
        mock_state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=self.effective_datetime,
            parameters={
                partial_fee.denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION
            },
        )

        # run function
        result = partial_fee.has_outstanding_fees(
            state=mock_state,
            fee_collection=[mock_fee_details],
        )
        self.assertFalse(result)

    @pytest.mark.unit
    def test_has_no_outstanding_fees_balances_and_denomination_not_provided(
        self,
        mock_get_parameters: MagicMock,
        mock_balance_at_coordinates: MagicMock,
    ):
        # construct mocks
        mock_get_parameters.return_value = {
            partial_fee.denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION
        }
        mock_vault = self.create_mock(
            balances_observation_fetchers_mapping={
                partial_fee.fetchers.ALL_BALANCES_LIVE_BOF.fetcher_id: MagicMock(balances={})
            }
        )
        mock_state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=self.effective_datetime,
            parameters={
                partial_fee.denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION
            },
        )
        mock_fee_details = generate_mock_fee_details(
            partial_fee_tracking_address="PARTIAL_FEE",
            fee_type="FEE_TYPE",
            internal_account_parameter_id="INTERNAL_ADDRESS",
        )
        mock_balance_at_coordinates.return_value = Decimal("0")

        # run function
        result = partial_fee.has_outstanding_fees(
            state=mock_state,
            fee_collection=[mock_fee_details],
        )
        self.assertFalse(result)

    @pytest.mark.unit
    def test_has_outstanding_fees(
        self,
        mock_get_parameters: MagicMock,
        mock_balance_at_coordinates: MagicMock,
    ):
        # construct mocks
        mock_get_parameters.return_value = {
            partial_fee.denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION
        }
        mock_vault = self.create_mock(
            balances_observation_fetchers_mapping={
                partial_fee.fetchers.ALL_BALANCES_LIVE_BOF.fetcher_id: MagicMock(balances={})
            }
        )
        mock_state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=self.effective_datetime,
            parameters={
                partial_fee.denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION
            },
        )
        mock_fee_details_1 = generate_mock_fee_details(
            partial_fee_tracking_address="PARTIAL_FEE",
            fee_type="FEE_TYPE_1",
            internal_account_parameter_id="INTERNAL_ADDRESS",
        )
        mock_fee_details_2 = generate_mock_fee_details(
            partial_fee_tracking_address="PARTIAL_FEE",
            fee_type="FEE_TYPE_2",
            internal_account_parameter_id="INTERNAL_ADDRESS",
        )
        mock_balance_at_coordinates.side_effect = [Decimal("0"), Decimal("1")]

        # run function
        result = partial_fee.has_outstanding_fees(
            state=mock_state,
            fee_collection=[mock_fee_details_1, mock_fee_details_2],
        )
        self.assertTrue(result)
