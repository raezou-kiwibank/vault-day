# standard libs
from typing import Any
from unittest.mock import MagicMock, patch, sentinel

import pytest

# third party
from parameterized import parameterized

# feature_library
from feature_library.common import state_utils

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

from tests.utils import initialise_mock_state


class StateUtilsTest(FeatureTest):
    @pytest.mark.unit
    def test_initialise_state_no_optional_args(self):
        mock_vault = self.create_mock()

        result = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=sentinel.effective_datetime,
        )

        self.assertEqual(
            result,
            state_utils.SmartContractState(
                vault=mock_vault,
                effective_datetime=sentinel.effective_datetime,
                parameters={},
                balances={},
                inflight_postings=[],
            ),
        )

    @pytest.mark.unit
    def test_initialise_state_optional_args(self):
        mock_vault = self.create_mock()

        result = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=sentinel.effective_datetime,
            parameters=sentinel.parameters,
            balances=sentinel.balances,
        )

        self.assertEqual(
            result,
            state_utils.SmartContractState(
                vault=mock_vault,
                effective_datetime=sentinel.effective_datetime,
                parameters=sentinel.parameters,
                balances=sentinel.balances,
                inflight_postings=[],
            ),
        )

    @pytest.mark.unit
    def test_append_to_state(self):
        mock_vault = self.create_mock()
        mock_vault_2 = self.create_mock()

        initial_state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=sentinel.effective_datetime,
            parameters={"initial": sentinel.initial_val},
            balances={"initial_bal": sentinel.initial_bal_val},
        )

        result = state_utils.append_to_state(
            state=initial_state,
            vault=mock_vault_2,
            effective_datetime=sentinel.effective_datetime_2,
            parameters={"new": sentinel.new_val},
            balances={"new_bal": sentinel.new_bal_val},
        )

        self.assertEqual(
            result,
            state_utils.SmartContractState(
                vault=mock_vault_2,
                effective_datetime=sentinel.effective_datetime_2,
                parameters={"initial": sentinel.initial_val, "new": sentinel.new_val},
                balances={"initial_bal": sentinel.initial_bal_val, "new_bal": sentinel.new_bal_val},
                inflight_postings=[],
            ),
        )

    @parameterized.expand(
        input=[
            # state_balances, observation_val, observation_called, expected_result
            # Case 1: State is empty. utils function called.
            (None, sentinel.observation_value, True, sentinel.observation_value),
            # Case 2: State has entry for coordinate and fetcher. Cached value returned.
            (
                {sentinel.balance_coordinate: {"FETCHER_ID": sentinel.stored_value}},
                sentinel.observation_value,
                False,
                sentinel.stored_value,
            ),
            # Case 3: State has entry for coordinate, but different fetcher. utils function called.
            (
                {sentinel.balance_coordinate: {"OTHER_FETCHER_ID": sentinel.stored_value}},
                sentinel.observation_value,
                True,
                sentinel.observation_value,
            ),
            # Case 4: State has entry for different coordinate. utils function called.
            (
                {sentinel.other_coordinate: {"FETCHER_ID": sentinel.stored_value}},
                sentinel.observation_value,
                True,
                sentinel.observation_value,
            ),
        ]
    )
    @patch.object(state_utils, "BalanceCoordinate")
    @patch.object(state_utils.balance_utils, "get_balance_from_observation")
    @pytest.mark.unit
    def test_get_balance_from_state(
        self,
        state_balances: dict,
        observation_val: Any,
        observation_called: bool,
        expected_result: Any,
        mock_get_balance_from_observation: MagicMock,
        mock_balance_coordinate_cls: MagicMock,
    ):
        # Setup
        # We mock the BalanceCoordinate constructor to return a specific sentinel.
        # This ensures the dictionary key lookup in the function matches the key in our test data.
        mock_balance_coordinate_cls.return_value = sentinel.balance_coordinate

        mock_state = initialise_mock_state(
            vault=sentinel.vault,
            balances=state_balances,
        )
        mock_get_balance_from_observation.return_value = observation_val

        # Run
        result = state_utils.get_balance_from_state(
            state=mock_state,
            fetcher_id="FETCHER_ID",
            account_address="ACCOUNT_ADDRESS",
            denomination="DENOMINATION",
            asset="ASSET",
            phase=sentinel.phase,
        )

        # Verify
        self.assertEqual(result, expected_result)

        # Verify BalanceCoordinate was instantiated correctly
        mock_balance_coordinate_cls.assert_called_once_with(
            account_address="ACCOUNT_ADDRESS",
            asset="ASSET",
            denomination="DENOMINATION",
            phase=sentinel.phase,
        )

        if observation_called:
            mock_get_balance_from_observation.assert_called_once_with(
                sentinel.vault,
                sentinel.balance_coordinate,
                fetcher_id="FETCHER_ID",
            )
        else:
            mock_get_balance_from_observation.assert_not_called()
