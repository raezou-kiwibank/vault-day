# standard libs
from decimal import Decimal
from typing import Callable
from unittest.mock import MagicMock, patch, sentinel

import pytest

import feature_library.common.denomination as denomination_module
import feature_library.lending.addresses as lending_addresses

# feature library
import feature_library.lending.amortisations.amortisation_methods.interest_only as interest_only
import feature_library.lending.term.term as term_helpers

# contracts api
from contracts_api import Posting, Tside

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.utils import initialise_mock_state


class InterestOnlyCommon(FeatureTest):
    default_denomination = DEFAULT_DENOMINATION
    tside = Tside.ASSET


@patch.object(term_helpers, "get_elapsed_term")
class TermDetailsTest(FeatureTest):
    @pytest.mark.unit
    def test_term_details_with_optional_args(
        self,
        mock_get_elapsed_term: MagicMock,
    ):
        mock_vault = self.create_mock()
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=sentinel.effective_datetime,
            parameters={
                term_helpers.TERM_PARAM_ID: "12",
                denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
            },
            balances=sentinel.balances,
        )
        mock_get_elapsed_term.return_value = 4

        result = interest_only.term_details(
            state=state,
        )

        mock_get_elapsed_term.assert_called_once_with(
            balances=sentinel.balances,
            denomination=DEFAULT_DENOMINATION,
        )
        self.assertEqual(result, (4, 8))

    @pytest.mark.unit
    def test_term_details_effective_date_equals_account_creation(
        self,
        mock_get_elapsed_term: MagicMock,
    ):
        mock_vault = self.create_mock()
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=mock_vault.get_account_creation_datetime(),
            parameters={
                term_helpers.TERM_PARAM_ID: "10",
                denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
            },
        )

        result = interest_only.term_details(
            state=state,
        )

        mock_get_elapsed_term.assert_not_called()
        self.assertEqual(result, (0, 10))


def mock_interest_get_annual_interest_rate(rate: Decimal) -> Callable:
    def get_annual_interest_rate(vault, effective_datetime, *args, **kwargs):
        return rate

    return get_annual_interest_rate


class CalculateEmi(FeatureTest):
    @pytest.mark.unit
    def test_calculate_eia(
        self,
    ):
        result = interest_only.calculate_eia()

        self.assertEqual(result, Decimal("0"))


class IsInterestOnlyLoanTest(FeatureTest):
    @pytest.mark.unit
    def test_is_interest_only_loan_true(self):
        self.assertEqual(
            interest_only.is_interest_only_loan("INTEREST_ONLY"),
            True,
        )

    @pytest.mark.unit
    def test_is_interest_only_lower_case_true(self):
        self.assertEqual(
            interest_only.is_interest_only_loan("interest_only"),
            True,
        )

    @pytest.mark.unit
    def test_is_interest_only_loan_false(self):
        self.assertEqual(interest_only.is_interest_only_loan("other"), False)


@patch.object(interest_only.balance_utils, "balance_at_coordinates")
@patch.object(interest_only.eia_module, "update_eia")
@patch.object(interest_only, "calculate_eia")
class AmortiseTest(FeatureTest):
    @pytest.mark.unit
    def test_amortise_returns_instructions_when_eia_updated(
        self,
        mock_calculate_eia: MagicMock,
        mock_update_eia: MagicMock,
        mock_balance_at_coordinates: MagicMock,
    ):
        mock_calculate_eia.return_value = Decimal("100")
        mock_posting = MagicMock(spec=Posting)
        mock_update_eia.return_value = [mock_posting]
        mock_balance_at_coordinates.return_value = Decimal("50")

        mock_vault = self.create_mock(account_id=sentinel.account_id)
        state = initialise_mock_state(
            vault=mock_vault,
            parameters={denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION},
            balances=sentinel.balances,
        )

        result = interest_only.amortise(
            state=state,
        )

        mock_calculate_eia.assert_called_once_with()
        mock_balance_at_coordinates.assert_called_once_with(
            balances=sentinel.balances,
            address=lending_addresses.EIA,
            denomination=DEFAULT_DENOMINATION,
        )
        mock_update_eia.assert_called_once_with(
            account_id=sentinel.account_id,
            denomination=DEFAULT_DENOMINATION,
            current_eia=Decimal("50"),
            updated_eia=Decimal("100"),
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].postings, [mock_posting])
        self.assertEqual(result[0].instruction_details["event"], "ACCOUNT_ACTIVATION")

    @pytest.mark.unit
    def test_amortise_returns_empty_list_when_no_eia_update(
        self,
        mock_calculate_eia: MagicMock,
        mock_update_eia: MagicMock,
        mock_balance_at_coordinates: MagicMock,
    ):
        mock_calculate_eia.return_value = Decimal("50")
        mock_update_eia.return_value = []
        mock_balance_at_coordinates.return_value = Decimal("50")

        mock_vault = self.create_mock(account_id=sentinel.account_id)
        state = initialise_mock_state(
            vault=mock_vault,
            parameters={denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION},
            balances=sentinel.balances,
        )

        result = interest_only.amortise(
            state=state,
        )

        self.assertEqual(result, [])
