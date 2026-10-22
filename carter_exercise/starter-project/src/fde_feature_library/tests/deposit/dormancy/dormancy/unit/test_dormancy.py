# standard libs
from json import dumps
from unittest.mock import MagicMock, patch, sentinel

# third party
import pytest

# features
import feature_library.common.state_utils as state_utils
from feature_library.deposit.dormancy import dormancy

# contracts api
from contracts_api import (
    FlagsObservation,
    ParametersObservation,
    Rejection,
    RejectionReason,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import (
    DEFAULT_DATETIME,
    FeatureTest,
)


@pytest.mark.unit
class DormancyTest(FeatureTest):
    def test_get_parameters(self):
        expected_parameters = {dormancy.DORMANCY_FLAGS_PARAM_ID: dumps(["ACCOUNT_DORMANT"])}
        mock_vault = self.create_mock(
            parameters_observation_fetchers_mapping={
                dormancy.DORMANCY_PARAMS_ET_POF_ID: ParametersObservation(
                    parameters=expected_parameters, value_datetime=DEFAULT_DATETIME
                )
            }
        )

        result = dormancy.get_parameters(vault=mock_vault)

        self.assertEqual(result, expected_parameters)

    @patch.object(dormancy, "get_parameters")
    def test_append_to_state(self, mock_get_parameters: MagicMock):
        mock_vault = self.create_mock()
        state = state_utils.initialise_state(vault=mock_vault, effective_datetime=DEFAULT_DATETIME)
        expected_parameters = {dormancy.DORMANCY_FLAGS_PARAM_ID: dumps(["ACCOUNT_DORMANT"])}
        mock_get_parameters.return_value = expected_parameters

        result_state = dormancy._append_to_state(state=state)

        self.assertEqual(result_state.parameters, expected_parameters)
        mock_get_parameters.assert_called_once_with(
            mock_vault, dormancy.DEFAULT_DORMANCY_FETCHERS_CONFIG.param_fetcher_id
        )

    def test_account_dormant(self):
        # construct mocks
        flags_fetcher_id = dormancy.DEFAULT_DORMANCY_FETCHERS_CONFIG.flags_fetcher_id
        mock_vault = self.create_mock(
            flags_observation_fetchers_mapping={
                flags_fetcher_id: FlagsObservation(flags={"ACCOUNT_DORMANT": True})
            }
        )

        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME,
            parameters={dormancy.DORMANCY_FLAGS_PARAM_ID: dumps(["ACCOUNT_DORMANT"])},
        )

        # run function
        result = dormancy.is_account_dormant(state=state)

        self.assertTrue(result)

    def test_account_not_dormant_with_false_flag(self):
        # construct mocks
        flags_fetcher_id = dormancy.DEFAULT_DORMANCY_FETCHERS_CONFIG.flags_fetcher_id
        mock_vault = self.create_mock(
            flags_observation_fetchers_mapping={
                flags_fetcher_id: FlagsObservation(flags={"ACCOUNT_DORMANT": False})
            }
        )

        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME,
            parameters={dormancy.DORMANCY_FLAGS_PARAM_ID: dumps(["ACCOUNT_DORMANT"])},
        )

        # run function
        result = dormancy.is_account_dormant(state=state)

        self.assertFalse(result)

    def test_account_not_dormant_with_no_flags_observation(self):
        # construct mocks
        mock_vault = self.create_mock()
        # Override the side_effect to return None when called
        mock_vault.get_flags_observation.side_effect = None
        mock_vault.get_flags_observation.return_value = None

        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME,
            parameters={dormancy.DORMANCY_FLAGS_PARAM_ID: dumps(["ACCOUNT_DORMANT"])},
        )

        # run function
        result = dormancy.is_account_dormant(state=state)

        self.assertFalse(result)

    def test_account_not_dormant_with_missing_flag(self):
        # construct mocks
        flags_fetcher_id = dormancy.DEFAULT_DORMANCY_FETCHERS_CONFIG.flags_fetcher_id
        mock_vault = self.create_mock(
            flags_observation_fetchers_mapping={
                flags_fetcher_id: FlagsObservation(flags={"OTHER_FLAG": True})
            }
        )

        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME,
            parameters={dormancy.DORMANCY_FLAGS_PARAM_ID: dumps(["ACCOUNT_DORMANT"])},
        )

        # run function
        result = dormancy.is_account_dormant(state=state)

        self.assertFalse(result)

    @patch.object(dormancy, "is_account_dormant")
    @patch.object(dormancy, "_append_to_state")
    def test_validate_account_transaction_with_account_dormant(
        self,
        mock_append_to_state: MagicMock,
        mock_is_account_dormant: MagicMock,
    ):
        # construct values
        mock_is_account_dormant.return_value = True
        mock_append_to_state.return_value = sentinel.state

        expected_result = Rejection(
            message="Account flagged 'Dormant' does not accept external transactions.",
            reason_code=RejectionReason.AGAINST_TNC,
        )

        # run function
        result = dormancy.validate_account_transaction(
            state=sentinel.state,
        )

        self.assertEqual(result, expected_result)
        mock_append_to_state.assert_called_once_with(
            state=sentinel.state, fetchers_config=dormancy.DEFAULT_DORMANCY_FETCHERS_CONFIG
        )
        mock_is_account_dormant.assert_called_once_with(
            state=sentinel.state, fetchers_config=dormancy.DEFAULT_DORMANCY_FETCHERS_CONFIG
        )

    @patch.object(dormancy, "is_account_dormant")
    @patch.object(dormancy, "_append_to_state")
    def test_validate_account_transaction_with_account_not_dormant(
        self,
        mock_append_to_state: MagicMock,
        mock_is_account_dormant: MagicMock,
    ):
        # construct values
        mock_is_account_dormant.return_value = False
        mock_append_to_state.return_value = sentinel.state

        # run function
        result = dormancy.validate_account_transaction(
            state=sentinel.state,
        )

        self.assertIsNone(result)
        mock_append_to_state.assert_called_once_with(
            state=sentinel.state, fetchers_config=dormancy.DEFAULT_DORMANCY_FETCHERS_CONFIG
        )
        mock_is_account_dormant.assert_called_once_with(
            state=sentinel.state, fetchers_config=dormancy.DEFAULT_DORMANCY_FETCHERS_CONFIG
        )
