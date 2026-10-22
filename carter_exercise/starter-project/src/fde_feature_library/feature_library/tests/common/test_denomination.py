from datetime import datetime
from unittest.mock import MagicMock, patch, sentinel
from zoneinfo import ZoneInfo

import pytest

import feature_library.common.denomination as denomination_module
import feature_library.common.state_utils as state_utils

from contracts_api import (
    ParametersObservation,
    PostingInstructionType,
    Rejection,
    RejectionReason,
)

from inception_sdk.test_framework.contracts.unit.common import FeatureTest

# Assuming these are imported from your actual project structure
# from my_project.vault import get_parameters, DENOMINATION_ET_POF_ID
UTC = ZoneInfo("UTC")
DEFAULT_DATETIME = datetime(2026, 1, 1, tzinfo=UTC)
DEFAULT_DENOMINATION = "GBP"


class DenominationFeatureTest(FeatureTest):
    def _simple_mock(
        self, effective_datetime: datetime, denomination=DEFAULT_DENOMINATION
    ) -> MagicMock:
        return self.create_mock(
            creation_date=effective_datetime,
            parameters_observation_fetchers_mapping={
                denomination_module.DENOMINATION_ET_POF.fetcher_id: ParametersObservation(
                    parameters={
                        denomination_module.DENOMINATION_PARAM.id: denomination,
                    },
                    value_datetime=effective_datetime,
                )
            },
        )


class TestGetParameters(DenominationFeatureTest):
    @pytest.mark.unit
    def test_get_parameters_returns_correct_dictionary(self):
        """Verify that the parameters attribute is returned exactly as provided."""
        effective_datetime = DEFAULT_DATETIME
        mock_vault: MagicMock = self._simple_mock(effective_datetime=effective_datetime)

        expected_result = {
            denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
        }
        result = denomination_module.get_parameters(
            mock_vault, fetcher_id=denomination_module.DENOMINATION_ET_POF.fetcher_id
        )
        self.assertEqual(result, expected_result)
        mock_vault.get_parameters_observation.assert_called_once_with(
            fetcher_id=denomination_module.DENOMINATION_ET_POF.fetcher_id
        )

    @pytest.mark.unit
    def test_get_parameters_uses_default_id(self):
        """Verify the function uses the default constant when fetcher_id is omitted."""
        effective_datetime = DEFAULT_DATETIME
        mock_vault: MagicMock = self._simple_mock(effective_datetime=effective_datetime)

        expected_result = {
            denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
        }
        result = denomination_module.get_parameters(mock_vault)
        self.assertEqual(result, expected_result)
        mock_vault.get_parameters_observation.assert_called_once_with(
            fetcher_id=denomination_module.DENOMINATION_ET_POF.fetcher_id
        )


class TestAddDenominationToState(DenominationFeatureTest):
    @patch.object(
        denomination_module.state_utils, denomination_module.state_utils.append_to_state.__name__
    )
    @patch.object(denomination_module, denomination_module.get_parameters.__name__)
    @pytest.mark.unit
    def test_add_denomination_success(
        self, mock_get_params: MagicMock, mock_append_to_state: MagicMock
    ):
        """Verify that parameters are fetched and appended to state correctly."""
        effective_datetime = DEFAULT_DATETIME
        denomination = DEFAULT_DENOMINATION
        mock_vault = self._simple_mock(
            effective_datetime=effective_datetime, denomination=denomination
        )
        mock_get_params.return_value = {
            denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
        }
        state = state_utils.initialise_state(
            vault=mock_vault,
            effective_datetime=effective_datetime,
        )
        mock_append_to_state.return_value = MagicMock(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters=mock_get_params.return_value,
        )
        result = denomination_module.add_denomination_to_state(
            state=state, param_fetcher_id=denomination_module.DENOMINATION_ET_POF.fetcher_id
        )

        # Assert
        # Check that get_parameters was called with the vault from the state
        mock_get_params.assert_called_once_with(
            mock_vault, denomination_module.DENOMINATION_ET_POF.fetcher_id
        )

        # Check that append_to_state received the original state and the fetched params
        mock_append_to_state.assert_called_once_with(
            state=state, parameters=mock_get_params.return_value
        )

        # Ensure the final returned object is the one produced by append_to_state
        self.assertEqual(result, mock_append_to_state.return_value)

    @patch.object(
        denomination_module.state_utils, denomination_module.state_utils.append_to_state.__name__
    )
    @patch.object(denomination_module, denomination_module.get_parameters.__name__)
    @pytest.mark.unit
    def test_add_denomination_uses_default_id(
        self, mock_get_params: MagicMock, mock_append_to_state: MagicMock
    ):
        """Verify the function defaults to DENOMINATION_ET_POF_ID."""
        effective_datetime = DEFAULT_DATETIME
        denomination = DEFAULT_DENOMINATION
        mock_vault = self._simple_mock(
            effective_datetime=effective_datetime, denomination=denomination
        )
        mock_get_params.return_value = {
            denomination_module.DENOMINATION_PARAM.id: DEFAULT_DENOMINATION,
        }
        state = MagicMock(
            vault=mock_vault,
            effective_datetime=effective_datetime,
        )
        mock_append_to_state.return_value = MagicMock(
            vault=mock_vault,
            effective_datetime=effective_datetime,
            parameters=mock_get_params.return_value,
        )
        result = denomination_module.add_denomination_to_state(
            state=state,
        )

        # Assert
        # Check that get_parameters was called with the vault from the state
        mock_get_params.assert_called_once_with(
            mock_vault, denomination_module.DENOMINATION_ET_POF.fetcher_id
        )

        # Check that append_to_state received the original state and the fetched params
        mock_append_to_state.assert_called_once_with(
            state=state, parameters=mock_get_params.return_value
        )

        # Ensure the final returned object is the one produced by append_to_state
        self.assertEqual(result, mock_append_to_state.return_value)


class TestValidateDenomination(DenominationFeatureTest):
    @patch.object(
        denomination_module.state_utils,
        denomination_module.state_utils.check_parameters_exist.__name__,
    )
    @pytest.mark.unit
    def test_returns_rejection_if_parameters_missing(self, mock_check_params):
        """Test that it bails early if parameters are missing from state."""
        effective_datetime = DEFAULT_DATETIME
        mock_vault: MagicMock = self._simple_mock(effective_datetime=effective_datetime)
        mock_state = MagicMock(vault=mock_vault)

        mock_check_params.return_value = sentinel.rejection
        result = denomination_module.validate_denomination(mock_state, [])

        # Assert
        self.assertEqual(result, mock_check_params.return_value)
        mock_check_params.assert_called_once_with(
            mock_state, {denomination_module.DENOMINATION_PARAM.id}
        )

    @patch.object(
        denomination_module.state_utils,
        denomination_module.state_utils.check_parameters_exist.__name__,
    )
    @pytest.mark.unit
    def test_returns_none_for_valid_denominations(self, mock_check_params):
        """Test standard and custom instructions with valid denominations."""
        effective_datetime = DEFAULT_DATETIME
        mock_vault: MagicMock = self._simple_mock(effective_datetime=effective_datetime)

        valid_denom = "GBP"
        mock_state = MagicMock(
            vault=mock_vault, parameters={denomination_module.DENOMINATION_PARAM.id: valid_denom}
        )
        mock_check_params.return_value = None

        # 1 Custom Instruction (requires nested postings)
        custom_posting_instruction = MagicMock(
            type=PostingInstructionType.CUSTOM_INSTRUCTION,
            postings=[MagicMock(denomination=valid_denom)],
        )
        # 1 Standard Instruction (requires top-level denomination)
        standard_posting_instruction = MagicMock(
            type=PostingInstructionType.TRANSFER, denomination=valid_denom
        )
        result = denomination_module.validate_denomination(
            mock_state, [custom_posting_instruction, standard_posting_instruction]
        )

        # Assert
        self.assertIsNone(result)

    @patch.object(
        denomination_module.state_utils,
        denomination_module.state_utils.check_parameters_exist.__name__,
    )
    @pytest.mark.unit
    def test_returns_rejection_for_invalid_denomination_standard_posting_type(
        self, mock_check_params
    ):
        """Test rejection when an invalid denomination is present in instructions."""
        effective_datetime = DEFAULT_DATETIME
        mock_vault: MagicMock = self._simple_mock(effective_datetime=effective_datetime)

        valid_denom = "GBP"
        invalid_denom = "USD"
        mock_state = MagicMock(
            vault=mock_vault, parameters={denomination_module.DENOMINATION_PARAM.id: valid_denom}
        )
        mock_check_params.return_value = None
        bad_pi = MagicMock(
            type=PostingInstructionType.OUTBOUND_HARD_SETTLEMENT, denomination=invalid_denom
        )
        result = denomination_module.validate_denomination(mock_state, [bad_pi])
        self.assertIsInstance(result, Rejection)
        self.assertEqual(result.reason_code, RejectionReason.WRONG_DENOMINATION)  # ty: ignore[possibly-missing-attribute]  # noqa: E501
        self.assertIn(f"Valid denomination: {valid_denom}", result.message)  # ty: ignore[possibly-missing-attribute]  # noqa: E501
        self.assertIn(f"Received denomination(s): {invalid_denom}", result.message)  # ty: ignore[possibly-missing-attribute]  # noqa: E501

    @patch.object(
        denomination_module.state_utils,
        denomination_module.state_utils.check_parameters_exist.__name__,
    )
    @pytest.mark.unit
    def test_returns_rejection_for_invalid_denomination_custom_instruction(self, mock_check_params):
        """Test rejection when an invalid denomination is present in instructions."""
        effective_datetime = DEFAULT_DATETIME
        mock_vault: MagicMock = self._simple_mock(effective_datetime=effective_datetime)

        valid_denom = "GBP"
        invalid_denom = "USD"
        mock_state = MagicMock(
            vault=mock_vault, parameters={denomination_module.DENOMINATION_PARAM.id: valid_denom}
        )
        mock_check_params.return_value = None
        bad_pi = MagicMock(
            type=PostingInstructionType.CUSTOM_INSTRUCTION,
            postings=[MagicMock(denomination=invalid_denom)],
        )
        result = denomination_module.validate_denomination(mock_state, [bad_pi])
        self.assertIsInstance(result, Rejection)
        self.assertEqual(result.reason_code, RejectionReason.WRONG_DENOMINATION)  # ty: ignore[possibly-missing-attribute]  # noqa: E501
        self.assertIn(f"Valid denomination: {valid_denom}", result.message)  # ty: ignore[possibly-missing-attribute]  # noqa: E501
        self.assertIn(f"Received denomination(s): {invalid_denom}", result.message)  # ty: ignore[possibly-missing-attribute]  # noqa: E501

    @patch.object(
        denomination_module.state_utils,
        denomination_module.state_utils.check_parameters_exist.__name__,
    )
    @pytest.mark.unit
    def test_handles_multiple_offending_denominations_sorted(self, mock_check_params):
        """Verify multiple invalid denoms are joined and alphabetically sorted."""
        # Arrange
        effective_datetime = DEFAULT_DATETIME
        mock_vault: MagicMock = self._simple_mock(effective_datetime=effective_datetime)

        mock_state = MagicMock(vault=mock_vault)
        mock_state.parameters = {denomination_module.DENOMINATION_PARAM.id: "GBP"}
        mock_check_params.return_value = None

        invalid_posting_instruction_1 = MagicMock(
            type=PostingInstructionType.CUSTOM_INSTRUCTION, postings=[MagicMock(denomination="EUR")]
        )
        invalid_posting_instruction_2 = MagicMock(
            type=PostingInstructionType.TRANSFER, denomination="AUD"
        )
        result = denomination_module.validate_denomination(
            mock_state, [invalid_posting_instruction_1, invalid_posting_instruction_2]
        )

        # Assert
        # Check for sorted output "AUD,EUR"
        self.assertIn("AUD,EUR", result.message)  # ty: ignore[possibly-missing-attribute]
