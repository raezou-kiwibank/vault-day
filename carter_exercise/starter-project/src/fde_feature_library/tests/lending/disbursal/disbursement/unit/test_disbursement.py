# standard libs
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel

import pytest

import feature_library.common.denomination as denomination
import feature_library.lending.addresses as lending_addresses

# features
import feature_library.lending.disbursal.disbursement as disbursement
import feature_library.lending.principal.principal as principal

# contracts api
from contracts_api import DEFAULT_ADDRESS, DEFAULT_ASSET, CustomInstruction, Phase, Posting

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

# feature_library
from tests.utils import initialise_mock_state

DEFAULT_DENOMINATION = sentinel.denomination
DEFAULT_PRINCIPAL_AMOUNT = Decimal("456000")
DEFAULT_DEPOSIT_ACCOUNT = sentinel.deposit_account


class TestDisbursement(FeatureTest):
    @patch.object(disbursement, "_append_to_state")
    @pytest.mark.unit
    def test_get_disbursement_custom_instruction(self, mock_append_to_state: MagicMock):
        mock_state = initialise_mock_state(
            vault=self.create_mock(account_id="customer_account"),
            parameters={
                principal.PRINCIPAL_PARAM_ID: DEFAULT_PRINCIPAL_AMOUNT,
                disbursement.DEPOSIT_ACCOUNT_PARAM_ID: DEFAULT_DEPOSIT_ACCOUNT,
                denomination.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
            },
        )
        mock_append_to_state.return_value = mock_state

        expected = [
            CustomInstruction(
                postings=[
                    Posting(
                        credit=False,
                        amount=DEFAULT_PRINCIPAL_AMOUNT,
                        denomination=DEFAULT_DENOMINATION,
                        account_id="customer_account",
                        account_address=lending_addresses.PRINCIPAL,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                    Posting(
                        credit=True,
                        amount=DEFAULT_PRINCIPAL_AMOUNT,
                        denomination=DEFAULT_DENOMINATION,
                        account_id=DEFAULT_DEPOSIT_ACCOUNT,
                        account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                ],
                override_all_restrictions=True,
                instruction_details={
                    "description": f"Principal disbursement of {DEFAULT_PRINCIPAL_AMOUNT}",
                    "event": disbursement.DISBURSEMENT_EVENT,
                },
            )
        ]

        result = disbursement.get_disbursement_custom_instruction(
            state=mock_state,
        )
        self.assertEqual(expected, result)

    @patch.object(disbursement, "_append_to_state")
    @pytest.mark.unit
    def test_get_disbursement_custom_instruction_principal_address_override(
        self, mock_append_to_state: MagicMock
    ):
        new_principal_address = "NEW_PRINCIPAL_ADDRESS"

        mock_state = initialise_mock_state(
            vault=self.create_mock(account_id="customer_account"),
            parameters={
                principal.PRINCIPAL_PARAM_ID: DEFAULT_PRINCIPAL_AMOUNT,
                disbursement.DEPOSIT_ACCOUNT_PARAM_ID: DEFAULT_DEPOSIT_ACCOUNT,
                denomination.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
            },
        )
        mock_append_to_state.return_value = mock_state

        expected = [
            CustomInstruction(
                postings=[
                    Posting(
                        credit=False,
                        amount=DEFAULT_PRINCIPAL_AMOUNT,
                        denomination=DEFAULT_DENOMINATION,
                        account_id="customer_account",
                        account_address=new_principal_address,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                    Posting(
                        credit=True,
                        amount=DEFAULT_PRINCIPAL_AMOUNT,
                        denomination=DEFAULT_DENOMINATION,
                        account_id=DEFAULT_DEPOSIT_ACCOUNT,
                        account_address=DEFAULT_ADDRESS,
                        asset=DEFAULT_ASSET,
                        phase=Phase.COMMITTED,
                    ),
                ],
                override_all_restrictions=True,
                instruction_details={
                    "description": f"Principal disbursement of {DEFAULT_PRINCIPAL_AMOUNT}",
                    "event": disbursement.DISBURSEMENT_EVENT,
                },
            )
        ]

        result = disbursement.get_disbursement_custom_instruction(
            state=mock_state,
            principal_address=new_principal_address,
        )
        self.assertEqual(expected, result)

    @patch.object(disbursement, "_append_to_state")
    @pytest.mark.unit
    def test_get_disbursement_custom_instruction_zero_principal(
        self, mock_append_to_state: MagicMock
    ):
        mock_state = initialise_mock_state(
            vault=self.create_mock(account_id="customer_account"),
            parameters={
                principal.PRINCIPAL_PARAM_ID: Decimal("0"),
                disbursement.DEPOSIT_ACCOUNT_PARAM_ID: DEFAULT_DEPOSIT_ACCOUNT,
                denomination.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
            },
        )
        mock_append_to_state.return_value = mock_state

        result = disbursement.get_disbursement_custom_instruction(
            state=mock_state,
        )
        self.assertEqual([], result)


class TestHelpers(FeatureTest):
    @patch.object(disbursement, "get_parameters")
    @patch.object(disbursement.state_utils, "append_to_state")
    @pytest.mark.unit
    def test_append_to_state(
        self,
        mock_append_to_state: MagicMock,
        mock_get_parameters: MagicMock,
    ):
        mock_vault = self.create_mock()
        initial_parameters = {"INITIAL_PARAM": "INITIAL_VALUE"}
        new_parameters = {"NEW_PARAM": "NEW_VALUE"}

        mock_state = initialise_mock_state(vault=mock_vault, parameters=initial_parameters)

        mock_get_parameters.return_value = new_parameters

        mock_append_to_state.return_value = initialise_mock_state(
            vault=mock_vault,
            parameters=initial_parameters | new_parameters,
            effective_datetime=mock_state.effective_datetime,
        )

        result = disbursement._append_to_state(
            state=mock_state, param_fetcher_id=sentinel.param_fetcher_id
        )

        mock_get_parameters.assert_called_once_with(mock_vault, sentinel.param_fetcher_id)
        mock_append_to_state.assert_called_once_with(
            state=mock_state,
            parameters=new_parameters,
        )
        self.assertEqual(result.parameters["NEW_PARAM"], "NEW_VALUE")

    @patch.object(disbursement.state_utils, "check_parameters_exist")
    @patch.object(disbursement, "_append_to_state")
    @pytest.mark.unit
    def test_get_disbursement_custom_instruction_raises_assertion_error_if_parameter_missing(
        self, mock_append_to_state: MagicMock, mock_check_parameters_exist: MagicMock
    ):
        mock_state = initialise_mock_state()
        mock_append_to_state.return_value = mock_state
        mock_check_parameters_exist.return_value = sentinel.rejection

        with self.assertRaises(AssertionError) as ex:
            disbursement.get_disbursement_custom_instruction(
                state=mock_state,
            )

        self.assertEqual(ex.exception.args[0], sentinel.rejection)
        mock_check_parameters_exist.assert_called_once_with(
            state=mock_state,
            param_ids={
                disbursement.DEFAULT_DISBURSEMENT_FETCHERS_CONFIG.principal_param_id,
                disbursement.DEFAULT_DISBURSEMENT_FETCHERS_CONFIG.deposit_account_param_id,
                disbursement.DEFAULT_DISBURSEMENT_FETCHERS_CONFIG.denomination_param_id,
            },
        )
