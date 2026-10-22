# standard libs
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel

import pytest

# features
import feature_library.lending.account_attributes as account_attributes
from feature_library.lending.amortisations.amortisation_methods import TermDetails

# contracts api
from contracts_api import DEFAULT_ASSET, Balance, BalanceCoordinate, BalanceDefaultDict, Phase

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

from tests.common.test_denomination import DEFAULT_DENOMINATION


class CalculateTotalDueAmountTest(FeatureTest):
    @pytest.mark.unit
    def test_get_total_due_amount(self):
        mock_state = MagicMock()
        mock_state.parameters = {"denomination": DEFAULT_DENOMINATION}

        mock_state.balances = BalanceDefaultDict(
            mapping={
                BalanceCoordinate(
                    account_address="DUE_1",
                    asset=DEFAULT_ASSET,
                    denomination=DEFAULT_DENOMINATION,
                    phase=Phase.COMMITTED,
                ): Balance(debit=Decimal("150.125"), credit=Decimal(50)),
                BalanceCoordinate(
                    account_address="DUE_2",
                    asset=DEFAULT_ASSET,
                    denomination=DEFAULT_DENOMINATION,
                    phase=Phase.COMMITTED,
                ): Balance(debit=Decimal(20), credit=Decimal(50)),
                BalanceCoordinate(
                    account_address="NOT_DUE",
                    asset=DEFAULT_ASSET,
                    denomination=DEFAULT_DENOMINATION,
                    phase=Phase.COMMITTED,
                ): Balance(debit=Decimal(1000), credit=Decimal(0)),
            }
        )

        mock_fetchers_config = MagicMock()
        mock_fetchers_config.denomination_param_id = "denomination"
        mock_fetchers_config.precision = 2

        due_addresses = ["DUE_1", "DUE_2"]

        total_due_amount = account_attributes.get_total_due_amount(
            state=mock_state,
            due_addresses=due_addresses,
            fetchers_config=mock_fetchers_config,
        )
        self.assertEqual(total_due_amount, Decimal("70.13"))


class CalculateTotalOutstandingDebtTest(FeatureTest):
    @pytest.mark.unit
    def test_get_total_outstanding_debt(self):
        mock_state = MagicMock()
        mock_state.parameters = {"denomination": DEFAULT_DENOMINATION}

        mock_state.balances = BalanceDefaultDict(
            mapping={
                BalanceCoordinate(
                    account_address="DEBT_1",
                    asset=DEFAULT_ASSET,
                    denomination=DEFAULT_DENOMINATION,
                    phase=Phase.COMMITTED,
                ): Balance(debit=Decimal("200.555"), credit=Decimal(100)),
                BalanceCoordinate(
                    account_address="DEBT_2",
                    asset=DEFAULT_ASSET,
                    denomination=DEFAULT_DENOMINATION,
                    phase=Phase.COMMITTED,
                ): Balance(debit=Decimal(50), credit=Decimal(0)),
                BalanceCoordinate(
                    account_address="NOT_DEBT",
                    asset=DEFAULT_ASSET,
                    denomination=DEFAULT_DENOMINATION,
                    phase=Phase.COMMITTED,
                ): Balance(debit=Decimal(1000), credit=Decimal(0)),
            }
        )

        mock_fetchers_config = MagicMock()
        mock_fetchers_config.denomination_param_id = "denomination"
        mock_fetchers_config.precision = 2

        debt_addresses = ["DEBT_1", "DEBT_2"]

        total_outstanding_debt = account_attributes.get_total_outstanding_debt(
            state=mock_state,
            debt_addresses=debt_addresses,
            fetchers_config=mock_fetchers_config,
        )
        self.assertEqual(total_outstanding_debt, Decimal("150.56"))


class CalculateTotalRemainingPrincipalTest(FeatureTest):
    @pytest.mark.unit
    def test_get_total_remaining_principal(self):
        mock_state = MagicMock()
        mock_state.parameters = {"denomination": DEFAULT_DENOMINATION}

        mock_state.balances = BalanceDefaultDict(
            mapping={
                BalanceCoordinate(
                    account_address="PRINCIPAL_1",
                    asset=DEFAULT_ASSET,
                    denomination=DEFAULT_DENOMINATION,
                    phase=Phase.COMMITTED,
                ): Balance(debit=Decimal(500), credit=Decimal("100.111")),
                BalanceCoordinate(
                    account_address="PRINCIPAL_2",
                    asset=DEFAULT_ASSET,
                    denomination=DEFAULT_DENOMINATION,
                    phase=Phase.COMMITTED,
                ): Balance(debit=Decimal(0), credit=Decimal(0)),
                BalanceCoordinate(
                    account_address="NOT_PRINCIPAL",
                    asset=DEFAULT_ASSET,
                    denomination=DEFAULT_DENOMINATION,
                    phase=Phase.COMMITTED,
                ): Balance(debit=Decimal(1000), credit=Decimal(0)),
            }
        )

        mock_fetchers_config = MagicMock()
        mock_fetchers_config.denomination_param_id = "denomination"
        mock_fetchers_config.precision = 2

        principal_addresses = ["PRINCIPAL_1", "PRINCIPAL_2"]

        total_remaining_principal = account_attributes.get_total_remaining_principal(
            state=mock_state,
            principal_addresses=principal_addresses,
            fetchers_config=mock_fetchers_config,
        )
        self.assertEqual(total_remaining_principal, Decimal("399.89"))


@patch.object(account_attributes, "get_total_remaining_principal")
class CalculatePrincipalPaidToDateTest(FeatureTest):
    @pytest.mark.unit
    def test_get_principal_paid_to_date(self, mock_get_total_remaining_principal: MagicMock):
        mock_get_total_remaining_principal.return_value = Decimal(88)
        principal_paid_to_date = account_attributes.get_principal_paid_to_date(
            state=sentinel.state,
            original_principal=Decimal(100),
            principal_addresses=sentinel.principal_addresses,
            fetchers_config=sentinel.fetchers_config,
        )
        expected = Decimal(12)
        self.assertEqual(principal_paid_to_date, expected)
        mock_get_total_remaining_principal.assert_called_with(
            state=sentinel.state,
            principal_addresses=sentinel.principal_addresses,
            fetchers_config=sentinel.fetchers_config,
        )


class RemainingTermTest(FeatureTest):
    @pytest.mark.unit
    def test_get_remaining_term(self):
        mock_term_details_feature = MagicMock()
        mock_term_details_feature.return_value = TermDetails(
            elapsed=sentinel.elapsed_term,
            remaining=sentinel.remaining_term,
        )

        result = account_attributes.get_remaining_term(
            state=sentinel.state,
            term_details_feature=mock_term_details_feature,
            get_annual_interest_rate=sentinel.get_annual_interest_rate,
            principal_adjustments=[sentinel.principal_adjustments],
            use_expected_term=sentinel.use_expected_term,
        )
        self.assertEqual(result, sentinel.remaining_term)
        mock_term_details_feature.assert_called_once_with(
            state=sentinel.state,
            get_annual_interest_rate=sentinel.get_annual_interest_rate,
            use_expected_term=sentinel.use_expected_term,
            principal_adjustments=[sentinel.principal_adjustments],
        )

    @pytest.mark.unit
    def test_get_remaining_term_defaults(self):
        mock_term_details_feature = MagicMock()
        mock_term_details_feature.return_value = TermDetails(
            elapsed=sentinel.elapsed_term,
            remaining=sentinel.remaining_term,
        )

        result = account_attributes.get_remaining_term(
            state=sentinel.state,
            term_details_feature=mock_term_details_feature,
        )
        self.assertEqual(result, sentinel.remaining_term)
        mock_term_details_feature.assert_called_once_with(
            state=sentinel.state,
            get_annual_interest_rate=None,
            use_expected_term=True,
            principal_adjustments=None,
        )
