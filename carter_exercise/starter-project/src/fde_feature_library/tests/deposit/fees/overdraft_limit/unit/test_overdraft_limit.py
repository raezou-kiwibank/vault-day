# standard libs
from decimal import Decimal
from unittest.mock import MagicMock, sentinel

import pytest

# features
from feature_library.common.denomination import DENOMINATION_PARAM
from feature_library.deposit.fees import overdraft_limit

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    Phase,
    Rejection,
    RejectionReason,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

import tests.utils as test_utils
from tests.common.test_denomination import DEFAULT_DENOMINATION


class GetParametersTest(FeatureTest):
    @pytest.mark.unit
    def test_get_parameters(self):
        mock_vault = MagicMock()
        mock_vault.get_parameters_observation.return_value.parameters = {"param1": "val1"}

        result = overdraft_limit.get_parameters(mock_vault)

        self.assertEqual(result, {"param1": "val1"})
        mock_vault.get_parameters_observation.assert_called_once_with(
            fetcher_id=overdraft_limit.OVERDRAFT_LIMIT_POF_ID
        )


class AppendToStateTest(FeatureTest):
    @pytest.mark.unit
    def test_append_to_state_no_existing_balances(self):
        mock_vault = MagicMock()
        fetched_balances = BalanceDefaultDict(mapping={})
        mock_vault.get_balances_observation.return_value.balances = fetched_balances
        mock_vault.get_parameters_observation.return_value.parameters = {"param1": "val1"}

        state = test_utils.initialise_mock_state(
            vault=mock_vault, balances=BalanceDefaultDict(mapping={})
        )

        new_state = overdraft_limit._append_to_state(state)

        self.assertEqual(new_state.balances, fetched_balances)
        self.assertEqual(new_state.parameters, {"param1": "val1"})
        mock_vault.get_balances_observation.assert_called_once_with(
            fetcher_id=overdraft_limit.DEFAULT_OVERDRAFT_LIMIT_FETCHERS_CONFIG.balance_fetcher_id
        )

    @pytest.mark.unit
    def test_append_to_state_with_existing_balances(self):
        mock_vault = MagicMock()
        mock_vault.get_parameters_observation.return_value.parameters = {"param1": "val1"}

        existing_balances = BalanceDefaultDict(mapping={sentinel.coord: sentinel.bal})
        state = test_utils.initialise_mock_state(
            vault=mock_vault,
            balances=existing_balances,
        )

        new_state = overdraft_limit._append_to_state(state)

        self.assertEqual(new_state.balances, existing_balances)
        self.assertEqual(new_state.parameters, {"param1": "val1"})
        mock_vault.get_balances_observation.assert_not_called()


class GetOverdraftAvailableBalanceTest(FeatureTest):
    @pytest.mark.unit
    def test_get_overdraft_available_balance(self):
        mock_vault = MagicMock()
        mock_vault.get_parameters_observation.return_value.parameters = {
            DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            overdraft_limit.ARRANGED_OVERDRAFT_AMOUNT_PARAM_ID: Decimal("50"),
            overdraft_limit.UNARRANGED_OVERDRAFT_AMOUNT_PARAM_ID: Decimal("25"),
        }

        coordinate = BalanceCoordinate(
            denomination=DEFAULT_DENOMINATION,
            account_address=DEFAULT_ADDRESS,
            asset=DEFAULT_ASSET,
            phase=Phase.COMMITTED,
        )
        balances = BalanceDefaultDict(
            mapping={
                coordinate: Balance(net=Decimal("100"), credit=Decimal("100"), debit=Decimal("0"))
            }
        )

        state = test_utils.initialise_mock_state(vault=mock_vault, balances=balances)

        result = overdraft_limit.get_overdraft_available_balance(state=state)

        self.assertEqual(result, Decimal("175"))


class ValidateTest(FeatureTest):
    @pytest.mark.unit
    def test_validate_no_rejection_when_sufficient_funds(self):
        mock_vault = MagicMock()
        mock_vault.get_parameters_observation.return_value.parameters = {
            DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            overdraft_limit.ARRANGED_OVERDRAFT_AMOUNT_PARAM_ID: Decimal("50"),
            overdraft_limit.UNARRANGED_OVERDRAFT_AMOUNT_PARAM_ID: Decimal("0"),
        }

        coordinate = BalanceCoordinate(
            denomination=DEFAULT_DENOMINATION,
            account_address=DEFAULT_ADDRESS,
            asset=DEFAULT_ASSET,
            phase=Phase.COMMITTED,
        )
        balances = BalanceDefaultDict(
            mapping={
                coordinate: Balance(net=Decimal("100"), credit=Decimal("100"), debit=Decimal("0"))
            }
        )
        state = test_utils.initialise_mock_state(vault=mock_vault, balances=balances)

        mock_posting_instruction = MagicMock()
        mock_posting_instruction.balances.return_value = BalanceDefaultDict(
            mapping={
                coordinate: Balance(net=Decimal("-150"), credit=Decimal("0"), debit=Decimal("150"))
            }
        )

        result = overdraft_limit.validate(state=state, postings=[mock_posting_instruction])

        self.assertIsNone(result)

    @pytest.mark.unit
    def test_validate_rejection_when_insufficient_funds(self):
        mock_vault = MagicMock()
        mock_vault.get_parameters_observation.return_value.parameters = {
            DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
            overdraft_limit.ARRANGED_OVERDRAFT_AMOUNT_PARAM_ID: Decimal("50"),
            overdraft_limit.UNARRANGED_OVERDRAFT_AMOUNT_PARAM_ID: Decimal("0"),
        }

        coordinate = BalanceCoordinate(
            denomination=DEFAULT_DENOMINATION,
            account_address=DEFAULT_ADDRESS,
            asset=DEFAULT_ASSET,
            phase=Phase.COMMITTED,
        )
        balances = BalanceDefaultDict(
            mapping={
                coordinate: Balance(net=Decimal("100"), credit=Decimal("100"), debit=Decimal("0"))
            }
        )
        state = test_utils.initialise_mock_state(vault=mock_vault, balances=balances)

        mock_posting_instruction = MagicMock()
        mock_posting_instruction.balances.return_value = BalanceDefaultDict(
            mapping={
                coordinate: Balance(net=Decimal("-151"), credit=Decimal("0"), debit=Decimal("151"))
            }
        )

        result = overdraft_limit.validate(state=state, postings=[mock_posting_instruction])

        self.assertEqual(
            result,
            Rejection(
                message="Postings total GBP -151, which exceeds the available balance of GBP 150.",
                reason_code=RejectionReason.INSUFFICIENT_FUNDS,
            ),
        )

    @pytest.mark.unit
    def test_validate_missing_denomination_parameter(self):
        mock_vault = MagicMock()
        mock_vault.get_parameters_observation.return_value.parameters = {}
        state = test_utils.initialise_mock_state(vault=mock_vault)

        result = overdraft_limit.validate(state=state, postings=[])

        self.assertIsInstance(result, Rejection)
        self.assertIn("denomination", result.message)
