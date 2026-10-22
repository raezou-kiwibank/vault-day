# standard libs
from decimal import ROUND_CEILING, Decimal
from unittest.mock import MagicMock, patch, sentinel

import pytest
from dateutil.relativedelta import relativedelta

import feature_library.common.application_precision as application_precision_module
import feature_library.common.denomination as denomination_module
import feature_library.lending.addresses as lending_addresses

# feature library
import feature_library.lending.amortisations.amortisation_methods.declining_principal as declining_principal  # noqa: E501
import feature_library.lending.principal.principal as principal_module
import feature_library.lending.term.term as term_helpers

# contracts api
from contracts_api import (
    Balance,
    BalanceCoordinate,
    BalanceDefaultDict,
    Phase,
    Posting,
    Tside,
)

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import DEFAULT_DATETIME, FeatureTest

from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.utils import initialise_mock_state


def _create_balances(balances_map: dict) -> BalanceDefaultDict:
    balances = BalanceDefaultDict(lambda: Balance())
    for address, net in balances_map.items():
        balances[
            BalanceCoordinate(
                account_address=address,
                asset="COMMERCIAL_BANK_MONEY",
                denomination=DEFAULT_DENOMINATION,
                phase=Phase.COMMITTED,
            )
        ] = Balance(net=net)
    return balances


class DecliningPrincipalCommon(FeatureTest):
    default_denomination = DEFAULT_DENOMINATION
    tside = Tside.ASSET


class CalculateRemainingTermTest(DecliningPrincipalCommon):
    @pytest.mark.unit
    def test_no_emi_returns_zero(self):
        result = declining_principal.calculate_remaining_term(
            eia=Decimal(0),
            remaining_principal=Decimal(100000),
            monthly_interest_rate=Decimal("0.02"),
        )

        self.assertEqual(result, 0)

    @pytest.mark.unit
    def test_calculates_remaining_term_with_no_interest(self):
        result = declining_principal.calculate_remaining_term(
            eia=Decimal(50),
            remaining_principal=Decimal(1000),
            monthly_interest_rate=Decimal(0),
        )

        self.assertEqual(result, 20)

    @pytest.mark.unit
    def test_calculates_remaining_term_with_eight_percent_interest(self):
        result = declining_principal.calculate_remaining_term(
            eia=Decimal(50),
            remaining_principal=Decimal(1000),
            monthly_interest_rate=Decimal("0.08") / Decimal(12),
        )
        self.assertEqual(result, 22)

    @pytest.mark.unit
    def test_calculates_remaining_term_with_different_rounding(self):
        result = declining_principal.calculate_remaining_term(
            eia=Decimal(50),
            remaining_principal=Decimal(1000),
            monthly_interest_rate=Decimal(0),
            decimal_places=2,
        )

        self.assertEqual(result, 20)

    @pytest.mark.unit
    def test_calculates_remaining_term_with_different_rounding_strategy(self):
        result = declining_principal.calculate_remaining_term(
            eia=Decimal(50),
            remaining_principal=Decimal(1000),
            monthly_interest_rate=Decimal(0),
            rounding=ROUND_CEILING,
        )

        self.assertEqual(result, 20)


@patch.object(declining_principal, "calculate_remaining_term")
@patch.object(term_helpers, "get_elapsed_term")
class TermDetailsTest(DecliningPrincipalCommon):
    @pytest.mark.unit
    def test_term_details_with_features(
        self,
        mock_get_elapsed_term: MagicMock,
        mock_calculate_remaining_term: MagicMock,
    ):
        # can't use a sentinel for these return values they're used subtracted from original term
        #  and converted to int respectively
        mock_get_elapsed_term.return_value = 1
        mock_calculate_remaining_term.return_value = 8
        mock_principal_adjustments = [
            MagicMock(calculate_principal_adjustment=MagicMock(return_value=Decimal(1))),
            MagicMock(calculate_principal_adjustment=MagicMock(return_value=Decimal(10))),
        ]

        balances = _create_balances(
            {
                lending_addresses.EIA: Decimal(1),
                lending_addresses.PRINCIPAL: Decimal(2),
            }
        )

        # create_mock uses DEFAULT_DATETIME as account_creation time
        mock_vault = self.create_mock()
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME + relativedelta(seconds=1),
            parameters={
                term_helpers.TERM_PARAM_ID: "10",
                denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
            },
            balances=balances,
        )
        result = declining_principal.term_details(
            state=state,
            use_expected_term=False,
            get_annual_interest_rate=None,
            principal_adjustments=mock_principal_adjustments,  # type: ignore
        )

        mock_get_elapsed_term.assert_called_once_with(
            balances=balances, denomination=DEFAULT_DENOMINATION
        )
        mock_calculate_remaining_term.assert_called_once_with(
            eia=Decimal(1),
            # this is principal balance (2) + principal adjustments (1 + 10)
            remaining_principal=Decimal(13),
            monthly_interest_rate=Decimal(0),
        )
        self.assertEqual(result, declining_principal.TermDetails(elapsed=1, remaining=8))

    @pytest.mark.unit
    def test_term_details_with_calculated_greater_than_original_minus_elapsed(
        self,
        mock_get_elapsed_term: MagicMock,
        mock_calculate_remaining_term: MagicMock,
    ):
        mock_get_elapsed_term.return_value = 1
        mock_calculate_remaining_term.return_value = 10
        mock_principal_adjustments = [
            MagicMock(calculate_principal_adjustment=MagicMock(return_value=Decimal(1))),
            MagicMock(calculate_principal_adjustment=MagicMock(return_value=Decimal(10))),
        ]

        balances = _create_balances(
            {
                lending_addresses.EIA: Decimal(1),
                lending_addresses.PRINCIPAL: Decimal(2),
            }
        )

        # create_mock uses DEFAULT_DATETIME as account_creation time
        mock_vault = self.create_mock()
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME + relativedelta(seconds=1),
            parameters={
                term_helpers.TERM_PARAM_ID: "10",
                denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
            },
            balances=balances,
        )
        result = declining_principal.term_details(
            state=state,
            use_expected_term=False,
            get_annual_interest_rate=None,
            principal_adjustments=mock_principal_adjustments,  # type: ignore
        )

        mock_get_elapsed_term.assert_called_once_with(
            balances=balances, denomination=DEFAULT_DENOMINATION
        )
        mock_calculate_remaining_term.assert_called_once_with(
            eia=Decimal(1),
            # this is principal balance (2) + principal adjustments (1 + 10)
            remaining_principal=Decimal(13),
            monthly_interest_rate=Decimal(0),
        )
        self.assertEqual(result, declining_principal.TermDetails(elapsed=1, remaining=9))

    @pytest.mark.unit
    def test_term_details_without_features(
        self,
        mock_get_elapsed_term: MagicMock,
        mock_calculate_remaining_term: MagicMock,
    ):
        mock_get_elapsed_term.return_value = 1
        mock_calculate_remaining_term.return_value = 8

        balances = _create_balances(
            {
                lending_addresses.EIA: Decimal(1),
                lending_addresses.PRINCIPAL: Decimal(2),
            }
        )

        # create_mock uses DEFAULT_DATETIME as account_creation time
        mock_vault = self.create_mock()
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME + relativedelta(seconds=1),
            parameters={
                term_helpers.TERM_PARAM_ID: "10",
                denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
            },
            balances=balances,
        )

        result = declining_principal.term_details(
            state=state,
            use_expected_term=False,
            get_annual_interest_rate=None,
        )

        mock_get_elapsed_term.assert_called_once_with(
            balances=balances, denomination=DEFAULT_DENOMINATION
        )
        mock_calculate_remaining_term.assert_called_once_with(
            # eia and principal as per the mock_balances as there are no adjustment features
            eia=Decimal(1),
            remaining_principal=Decimal(2),
            monthly_interest_rate=Decimal(0),
        )
        self.assertEqual(result, declining_principal.TermDetails(elapsed=1, remaining=8))

    @pytest.mark.unit
    def test_term_details_effective_date_equals_account_creation(
        self,
        mock_get_elapsed_term: MagicMock,
        mock_calculate_remaining_term: MagicMock,
    ):
        balances = _create_balances(
            {
                lending_addresses.PRINCIPAL: Decimal(0),
            }
        )

        mock_vault = self.create_mock()
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=mock_vault.get_account_creation_datetime(),
            parameters={
                term_helpers.TERM_PARAM_ID: "10",
                denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
            },
            balances=balances,
        )
        result = declining_principal.term_details(
            state=state,
            use_expected_term=False,
            get_annual_interest_rate=None,
        )

        self.assertEqual(result, declining_principal.TermDetails(elapsed=0, remaining=10))

    @pytest.mark.unit
    def test_term_details_without_emi_uses_elapsed_and_original_term(
        self,
        mock_get_elapsed_term: MagicMock,
        mock_calculate_remaining_term: MagicMock,
    ):
        mock_get_elapsed_term.return_value = 1

        balances = _create_balances(
            {
                lending_addresses.EIA: Decimal(0),
                lending_addresses.PRINCIPAL: Decimal(10),
            }
        )

        # create_mock uses DEFAULT_DATETIME as account_creation time
        mock_vault = self.create_mock()
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME + relativedelta(seconds=1),
            parameters={
                term_helpers.TERM_PARAM_ID: "10",
                denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
            },
            balances=balances,
        )

        result = declining_principal.term_details(
            state=state,
            use_expected_term=False,
            get_annual_interest_rate=None,
        )

        self.assertEqual(result, (1, 9))
        mock_get_elapsed_term.assert_called_once_with(
            balances=balances, denomination=DEFAULT_DENOMINATION
        )
        mock_calculate_remaining_term.assert_not_called()

    @pytest.mark.unit
    def test_term_details_with_use_expected_term_uses_elapsed_and_original_term(
        self,
        mock_get_elapsed_term: MagicMock,
        mock_calculate_remaining_term: MagicMock,
    ):
        mock_get_elapsed_term.return_value = 1

        balances = _create_balances(
            {
                lending_addresses.PRINCIPAL: Decimal(10),
            }
        )

        # create_mock uses DEFAULT_DATETIME as account_creation time
        mock_vault = self.create_mock()
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME + relativedelta(seconds=1),
            parameters={
                term_helpers.TERM_PARAM_ID: "10",
                denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
            },
            balances=balances,
        )

        result = declining_principal.term_details(
            state=state,
            use_expected_term=True,
            get_annual_interest_rate=None,
        )

        self.assertEqual(result, (1, 9))
        mock_get_elapsed_term.assert_called_once_with(
            balances=balances, denomination=DEFAULT_DENOMINATION
        )
        mock_calculate_remaining_term.assert_not_called()

    @pytest.mark.unit
    def test_term_details_with_use_expected_term_with_zero_principal(
        self,
        mock_get_elapsed_term: MagicMock,
        mock_calculate_remaining_term: MagicMock,
    ):
        mock_get_elapsed_term.return_value = 1

        balances = _create_balances(
            {
                lending_addresses.PRINCIPAL: Decimal(0),
            }
        )

        # create_mock uses DEFAULT_DATETIME as account_creation time
        mock_vault = self.create_mock()
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME + relativedelta(seconds=1),
            parameters={
                term_helpers.TERM_PARAM_ID: "10",
                denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
            },
            balances=balances,
        )

        result = declining_principal.term_details(
            state=state,
            use_expected_term=True,
            get_annual_interest_rate=None,
        )

        self.assertEqual(result, (1, 0))
        mock_get_elapsed_term.assert_called_once_with(
            balances=balances, denomination=DEFAULT_DENOMINATION
        )
        mock_calculate_remaining_term.assert_not_called()

    @pytest.mark.unit
    def test_term_details_with_use_expected_term_with_negative_principal(
        self,
        mock_get_elapsed_term: MagicMock,
        mock_calculate_remaining_term: MagicMock,
    ):
        mock_get_elapsed_term.return_value = 1

        balances = _create_balances(
            {
                lending_addresses.PRINCIPAL: Decimal("-10"),
            }
        )

        # create_mock uses DEFAULT_DATETIME as account_creation time
        mock_vault = self.create_mock()
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME + relativedelta(seconds=1),
            parameters={
                term_helpers.TERM_PARAM_ID: "10",
                denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
            },
            balances=balances,
        )

        result = declining_principal.term_details(
            state=state,
            use_expected_term=True,
            get_annual_interest_rate=None,
        )

        self.assertEqual(result, (1, 0))
        mock_get_elapsed_term.assert_called_once_with(
            balances=balances, denomination=DEFAULT_DENOMINATION
        )
        mock_calculate_remaining_term.assert_not_called()


class DecliningPrincipalTest(FeatureTest):
    @pytest.mark.unit
    def test_calculate_declining_principal_0_lump_sum(self):
        # (100*0.02)*((1+0.02)^2)/(((1+0.02)^1)-1) = 51.50
        expected = Decimal("51.50")
        actual = declining_principal.apply_declining_principal_formula(
            remaining_principal=Decimal(100),
            interest_rate=Decimal("0.02"),
            remaining_term=2,
            fulfillment_precision=2,
            lump_sum_amount=Decimal(0),
        )
        self.assertEqual(expected, actual)

    @pytest.mark.unit
    def test_calculate_declining_principal_lump_sum_set_to_none(self):
        # (100*0.02)*((1+0.02)^2)/(((1+0.02)^1)-1) = 51.50
        expected = Decimal("51.50")
        actual = declining_principal.apply_declining_principal_formula(
            remaining_principal=Decimal(100),
            interest_rate=Decimal("0.02"),
            remaining_term=2,
            fulfillment_precision=2,
            lump_sum_amount=None,
        )
        self.assertEqual(expected, actual)

    @pytest.mark.unit
    def test_calculate_declining_principal_lump_sum_greater_than_zero(self):
        # (100000-(50000/(1+0.02/12)^2))*0.02/12*(1+0.02/12)^2/(1+0.02/12)^2-1 =1515.46
        expected = Decimal("1515.46")
        actual = declining_principal.apply_declining_principal_formula(
            remaining_principal=Decimal(100000),
            interest_rate=Decimal("0.02") / Decimal(12),
            remaining_term=36,
            fulfillment_precision=2,
            lump_sum_amount=Decimal(50000),
        )
        self.assertEqual(expected, actual)

    @pytest.mark.unit
    def test_calculate_declining_principal_zero_interest_rate(self):
        # (100/2)
        expected = Decimal(50)
        actual = declining_principal.apply_declining_principal_formula(
            remaining_principal=Decimal(100),
            interest_rate=Decimal(0),
            remaining_term=2,
            fulfillment_precision=2,
            lump_sum_amount=Decimal(0),
        )
        self.assertEqual(expected, actual)

    @pytest.mark.unit
    def test_calculate_declining_principal_zero_remaining_term(self):
        expected = Decimal(100)
        actual = declining_principal.apply_declining_principal_formula(
            remaining_principal=Decimal(100),
            interest_rate=Decimal("0.01"),
            remaining_term=0,
        )
        self.assertEqual(expected, actual)

    @pytest.mark.unit
    def test_calculate_declining_principal_zero_remaining_term_and_principal(self):
        expected = Decimal(0)
        actual = declining_principal.apply_declining_principal_formula(
            remaining_principal=Decimal(0),
            interest_rate=Decimal("0.01"),
            remaining_term=0,
        )
        self.assertEqual(expected, actual)


@patch.object(declining_principal, "apply_declining_principal_formula")
@patch.object(declining_principal, "_get_declining_principal_formula_terms")
@patch.object(declining_principal, "term_details")
class CalculateEmi(FeatureTest):
    @pytest.mark.unit
    def test_calculate_eia_no_optional_params_provided(
        self,
        mock_term_details: MagicMock,
        mock_get_declining_principal_formula_terms: MagicMock,
        mock_apply_declining_principal_formula: MagicMock,
    ):
        mock_get_declining_principal_formula_terms.return_value = (
            declining_principal.PrincipalAndInterestRate(
                principal=sentinel.principal,
                interest_rate=declining_principal.parameter_utils.yearly_to_monthly_rate(
                    Decimal("0.12")
                ),
            )
        )
        mock_term_details.return_value = declining_principal.TermDetails(
            elapsed=sentinel.elapsed_term, remaining=sentinel.remaining_term
        )
        mock_apply_declining_principal_formula.return_value = sentinel.eia

        state = initialise_mock_state(
            parameters={application_precision_module.APPLICATION_PRECISION_PARAM_ID: 2}
        )
        result = declining_principal.calculate_eia(state=state, get_annual_interest_rate=None)
        self.assertEqual(result, sentinel.eia)

        mock_get_declining_principal_formula_terms.assert_called_once_with(
            state=state,
            principal_amount=None,
            get_annual_interest_rate=None,
            fetchers_config=declining_principal.DEFAULT_CALCULATE_EIA_FETCHERS_CONFIG,
        )

        mock_apply_declining_principal_formula.assert_called_once_with(
            remaining_principal=sentinel.principal,
            interest_rate=declining_principal.parameter_utils.yearly_to_monthly_rate(
                Decimal("0.12")
            ),
            remaining_term=sentinel.remaining_term,
            fulfillment_precision=2,
        )
        mock_term_details.assert_called_once_with(
            state=state,
            use_expected_term=True,
            get_annual_interest_rate=None,
            principal_adjustments=None,
        )

    @pytest.mark.unit
    def test_calculate_eia_all_optional_params_provided(
        self,
        mock_term_details: MagicMock,
        mock_get_declining_principal_formula_terms: MagicMock,
        mock_apply_declining_principal_formula: MagicMock,
    ):
        mock_interest_feature = MagicMock()
        mock_interest_feature.get_annual_interest_rate.return_value = Decimal("0.12")
        mock_apply_declining_principal_formula.return_value = sentinel.eia

        mock_principal_adjustments = [
            MagicMock(calculate_principal_adjustment=MagicMock(return_value=Decimal(1))),
            MagicMock(calculate_principal_adjustment=MagicMock(return_value=Decimal(49))),
        ]

        mock_get_declining_principal_formula_terms.return_value = (
            declining_principal.PrincipalAndInterestRate(
                principal=Decimal(100),
                interest_rate=declining_principal.parameter_utils.yearly_to_monthly_rate(
                    Decimal("0.12")
                ),
            )
        )
        mock_term_details.return_value = declining_principal.TermDetails(
            elapsed=sentinel.elapsed_term, remaining=sentinel.remaining_term
        )

        state = initialise_mock_state(
            parameters={application_precision_module.APPLICATION_PRECISION_PARAM_ID: 2}
        )
        result = declining_principal.calculate_eia(
            state=state,
            use_expected_term=False,
            principal_amount=Decimal(100),
            get_annual_interest_rate=mock_interest_feature.get_annual_interest_rate,
            principal_adjustments=mock_principal_adjustments,  # type: ignore
        )

        mock_get_declining_principal_formula_terms.assert_called_once_with(
            state=state,
            principal_amount=Decimal(100),
            get_annual_interest_rate=mock_interest_feature.get_annual_interest_rate,
            fetchers_config=declining_principal.DEFAULT_CALCULATE_EIA_FETCHERS_CONFIG,
        )

        mock_apply_declining_principal_formula.assert_called_once_with(
            remaining_principal=Decimal(150),
            interest_rate=declining_principal.parameter_utils.yearly_to_monthly_rate(
                Decimal("0.12")
            ),
            remaining_term=sentinel.remaining_term,
            fulfillment_precision=2,
        )
        mock_term_details.assert_called_once_with(
            state=state,
            use_expected_term=False,
            get_annual_interest_rate=mock_interest_feature.get_annual_interest_rate,
            principal_adjustments=mock_principal_adjustments,
        )
        self.assertEqual(result, sentinel.eia)


class IsDecliningPrincipalLoanTest(FeatureTest):
    @pytest.mark.unit
    def test_is_declining_principal_loan_true(self):
        self.assertEqual(
            declining_principal.is_declining_principal_loan("DECLINING_PRINCIPAL"), True
        )

    @pytest.mark.unit
    def test_is_declining_principal_lower_case_true(self):
        self.assertEqual(
            declining_principal.is_declining_principal_loan("declining_principal"), True
        )

    @pytest.mark.unit
    def test_is_declining_principal_loan_false(self):
        self.assertEqual(declining_principal.is_declining_principal_loan("other"), False)


class GetDecliningPrincipalFormulaTerms(FeatureTest):
    @pytest.mark.unit
    def test_get_declining_principal_formula_terms_no_optional_params_provided(self):
        state = initialise_mock_state(
            parameters={principal_module.PRINCIPAL_PARAM_ID: sentinel.principal}
        )

        expected = declining_principal.PrincipalAndInterestRate(
            principal=sentinel.principal, interest_rate=Decimal(0)
        )

        result = declining_principal._get_declining_principal_formula_terms(
            state=state,
            get_annual_interest_rate=None,
        )
        self.assertEqual(result, expected)

    @pytest.mark.unit
    def test_get_declining_principal_formula_terms_all_optional_params_provided(self):
        state = initialise_mock_state(
            parameters={principal_module.PRINCIPAL_PARAM_ID: sentinel.principal}
        )
        mock_interest_feature = MagicMock()
        mock_interest_feature.get_annual_interest_rate.return_value = Decimal("0.12")

        expected = declining_principal.PrincipalAndInterestRate(
            principal=Decimal(100),
            interest_rate=declining_principal.parameter_utils.yearly_to_monthly_rate(
                Decimal("0.12")
            ),
        )

        result = declining_principal._get_declining_principal_formula_terms(
            state=state,
            principal_amount=Decimal(100),
            get_annual_interest_rate=mock_interest_feature.get_annual_interest_rate,
        )
        self.assertEqual(result, expected)


@patch.object(declining_principal.eia_module, "update_eia")
@patch.object(declining_principal, "calculate_eia")
class AmortiseTest(FeatureTest):
    @pytest.mark.unit
    def test_amortise_returns_instructions_when_eia_updated(
        self, mock_calculate_eia: MagicMock, mock_update_eia: MagicMock
    ):
        mock_calculate_eia.return_value = Decimal("100")
        mock_posting = MagicMock(spec=Posting)
        mock_update_eia.return_value = [mock_posting]

        mock_vault = self.create_mock(account_id=sentinel.account_id)
        state = initialise_mock_state(
            vault=mock_vault,
            parameters={denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION},
            balances=_create_balances({lending_addresses.EIA: Decimal("50")}),
        )

        result = declining_principal.amortise(
            state=state,
            get_annual_interest_rate=sentinel.get_annual_interest_rate,
        )

        mock_calculate_eia.assert_called_once_with(
            state=state,
            get_annual_interest_rate=sentinel.get_annual_interest_rate,
            use_expected_term=True,
            principal_amount=None,
            principal_adjustments=None,
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
        self, mock_calculate_eia: MagicMock, mock_update_eia: MagicMock
    ):
        mock_calculate_eia.return_value = Decimal("50")
        mock_update_eia.return_value = []

        mock_vault = self.create_mock(account_id=sentinel.account_id)
        state = initialise_mock_state(
            vault=mock_vault,
            parameters={denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION},
            balances=_create_balances({lending_addresses.EIA: Decimal("50")}),
        )

        result = declining_principal.amortise(
            state=state,
            get_annual_interest_rate=sentinel.get_annual_interest_rate,
        )

        self.assertEqual(result, [])
