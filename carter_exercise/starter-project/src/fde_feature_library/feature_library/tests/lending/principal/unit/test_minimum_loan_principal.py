# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

import feature_library.common.denomination as denomination

# features
import feature_library.lending.principal.minimum_loan_principal as minimum_loan_principal

# contracts api
from contracts_api import Balance, Rejection, RejectionReason

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

from tests.common.test_denomination import DEFAULT_DENOMINATION

# feature_library
from tests.utils import initialise_mock_state

DEFAULT_MINIMUM_LOAN_AMOUNT = Decimal("50")


@pytest.mark.unit
class MinimumLoanPrincipalTest(FeatureTest):
    def setup_mock_data(
        self,
        minimum_loan_principal_val: Decimal | None = DEFAULT_MINIMUM_LOAN_AMOUNT,
        denomination_val: str = DEFAULT_DENOMINATION,
    ):
        self.mock_vault = self.create_mock()
        self.state = initialise_mock_state(
            vault=self.mock_vault,
            parameters={
                minimum_loan_principal.MINIMUM_LOAN_PRINCIPAL_PARAM_ID: (
                    minimum_loan_principal_val
                ),
                denomination.DENOMINATION_PARAM_ID: denomination_val,
            },
        )

    @patch.object(minimum_loan_principal.balance_utils, "get_available_balance")
    @patch.object(minimum_loan_principal, "_append_to_state")
    @pytest.mark.unit
    def test_validate_returns_none_if_amount_above_limit(
        self, mock_append_to_state: MagicMock, mock_get_available_balance: MagicMock
    ):
        self.setup_mock_data()
        mock_append_to_state.return_value = self.state

        mock_posting = MagicMock()
        mock_posting.balances.return_value = MagicMock()

        mock_get_available_balance.return_value = Balance(debit=Decimal("100"))

        result = minimum_loan_principal.validate(
            state=self.state,
            postings=[mock_posting],
        )

        self.assertIsNone(result)

    @patch.object(minimum_loan_principal.balance_utils, "get_available_balance")
    @patch.object(minimum_loan_principal, "_append_to_state")
    @pytest.mark.unit
    def test_validate_returns_none_if_amount_is_zero(
        self, mock_append_to_state: MagicMock, mock_get_available_balance: MagicMock
    ):
        self.setup_mock_data()
        mock_append_to_state.return_value = self.state

        mock_posting = MagicMock()
        mock_posting.balances.return_value = MagicMock()

        mock_get_available_balance.return_value = Balance(debit=Decimal("0"))

        result = minimum_loan_principal.validate(
            state=self.state,
            postings=[mock_posting],
        )

        self.assertIsNone(result)

    @patch.object(minimum_loan_principal.balance_utils, "get_available_balance")
    @patch.object(minimum_loan_principal, "_append_to_state")
    @pytest.mark.unit
    def test_validate_returns_rejection_if_amount_below_limit(
        self, mock_append_to_state: MagicMock, mock_get_available_balance: MagicMock
    ):
        self.setup_mock_data()
        mock_append_to_state.return_value = self.state

        mock_posting = MagicMock()
        mock_posting.balances.return_value = MagicMock()

        mock_get_available_balance.return_value = Balance(debit=Decimal("10"))

        result = minimum_loan_principal.validate(
            state=self.state,
            postings=[mock_posting],
        )

        expected_rejection = Rejection(
            message=(
                f"Cannot create loan smaller than minimum loan amount limit of: "
                f"{DEFAULT_MINIMUM_LOAN_AMOUNT}."
            ),
            reason_code=RejectionReason.AGAINST_TNC,
        )
        self.assertEqual(result, expected_rejection)

    @patch.object(minimum_loan_principal.balance_utils, "get_available_balance")
    @patch.object(minimum_loan_principal, "_append_to_state")
    @pytest.mark.unit
    def test_validate_returns_none_if_no_limit_defined(
        self, mock_append_to_state: MagicMock, mock_get_available_balance: MagicMock
    ):
        self.setup_mock_data(minimum_loan_principal_val=None)
        mock_append_to_state.return_value = self.state

        mock_posting = MagicMock()
        mock_posting.balances.return_value = MagicMock()

        mock_get_available_balance.return_value = Balance(debit=Decimal("10"))

        result = minimum_loan_principal.validate(
            state=self.state,
            postings=[mock_posting],
        )

        self.assertIsNone(result)

    @patch.object(minimum_loan_principal, "_append_to_state")
    @pytest.mark.unit
    def test_validate_raises_assertion_if_denomination_missing(
        self, mock_append_to_state: MagicMock
    ):
        self.mock_vault = self.create_mock()
        self.state = initialise_mock_state(
            vault=self.mock_vault,
            parameters={
                minimum_loan_principal.MINIMUM_LOAN_PRINCIPAL_PARAM_ID: (
                    DEFAULT_MINIMUM_LOAN_AMOUNT
                ),
            },
        )
        mock_append_to_state.return_value = self.state

        with self.assertRaises(AssertionError):
            minimum_loan_principal.validate(
                state=self.state,
                postings=[MagicMock()],
            )
