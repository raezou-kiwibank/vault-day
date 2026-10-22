# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

# features
import feature_library.common.denomination as denomination
import feature_library.lending.principal.maximum_loan_principal as maximum_loan_principal

# contracts api
from contracts_api import Balance, Rejection, RejectionReason

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.utils import initialise_mock_state

DEFAULT_MAXIMUM_LOAN_AMOUNT = Decimal("1000")


@pytest.mark.unit
class MaximumLoanPrincipalTest(FeatureTest):
    def setup_mock_data(
        self,
        maximum_loan_principal_val: Decimal | None = DEFAULT_MAXIMUM_LOAN_AMOUNT,
        denomination_val: str = DEFAULT_DENOMINATION,
    ):
        self.mock_vault = self.create_mock()
        self.state = initialise_mock_state(
            vault=self.mock_vault,
            parameters={
                maximum_loan_principal.MAXIMUM_LOAN_PRINCIPAL_PARAM_ID: (
                    maximum_loan_principal_val
                ),
                denomination.DENOMINATION_PARAM_ID: denomination_val,
            },
        )

    @patch.object(maximum_loan_principal.balance_utils, "get_available_balance")
    @patch.object(maximum_loan_principal, "_append_to_state")
    @pytest.mark.unit
    def test_validate_returns_none_if_amount_within_limit(
        self, mock_append_to_state: MagicMock, mock_get_available_balance: MagicMock
    ):
        self.setup_mock_data()
        mock_append_to_state.return_value = self.state

        mock_posting = MagicMock()
        mock_posting.balances.return_value = MagicMock()

        mock_get_available_balance.return_value = Balance(debit=Decimal("500"))

        result = maximum_loan_principal.validate(
            state=self.state,
            postings=[mock_posting],
        )

        self.assertIsNone(result)

    @patch.object(maximum_loan_principal.balance_utils, "get_available_balance")
    @patch.object(maximum_loan_principal, "_append_to_state")
    @pytest.mark.unit
    def test_validate_returns_rejection_if_amount_exceeds_limit(
        self, mock_append_to_state: MagicMock, mock_get_available_balance: MagicMock
    ):
        self.setup_mock_data()
        mock_append_to_state.return_value = self.state

        mock_posting = MagicMock()
        mock_posting.balances.return_value = MagicMock()

        mock_get_available_balance.return_value = Balance(debit=Decimal("1500"))

        result = maximum_loan_principal.validate(
            state=self.state,
            postings=[mock_posting],
        )

        expected_rejection = Rejection(
            message=(
                f"Cannot create loan larger than maximum loan amount limit of: "
                f"{DEFAULT_MAXIMUM_LOAN_AMOUNT}."
            ),
            reason_code=RejectionReason.AGAINST_TNC,
        )
        self.assertEqual(result, expected_rejection)

    @patch.object(maximum_loan_principal.balance_utils, "get_available_balance")
    @patch.object(maximum_loan_principal, "_append_to_state")
    @pytest.mark.unit
    def test_validate_returns_none_if_no_limit_defined(
        self, mock_append_to_state: MagicMock, mock_get_available_balance: MagicMock
    ):
        self.setup_mock_data(maximum_loan_principal_val=None)
        mock_append_to_state.return_value = self.state

        mock_posting = MagicMock()
        mock_posting.balances.return_value = MagicMock()

        mock_get_available_balance.return_value = Balance(debit=Decimal("5000"))

        result = maximum_loan_principal.validate(
            state=self.state,
            postings=[mock_posting],
        )

        self.assertIsNone(result)

    @patch.object(maximum_loan_principal, "_append_to_state")
    @pytest.mark.unit
    def test_validate_raises_assertion_if_denomination_missing(
        self, mock_append_to_state: MagicMock
    ):
        self.mock_vault = self.create_mock()
        self.state = initialise_mock_state(
            vault=self.mock_vault,
            parameters={
                maximum_loan_principal.MAXIMUM_LOAN_PRINCIPAL_PARAM_ID: (
                    DEFAULT_MAXIMUM_LOAN_AMOUNT
                ),
            },
        )
        mock_append_to_state.return_value = self.state

        with self.assertRaises(AssertionError):
            maximum_loan_principal.validate(
                state=self.state,
                postings=[MagicMock()],
            )
