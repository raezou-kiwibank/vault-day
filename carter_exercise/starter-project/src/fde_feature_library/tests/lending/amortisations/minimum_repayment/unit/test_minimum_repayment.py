# standard libs
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel

import pytest

import feature_library.common.denomination as denomination_module
import feature_library.lending.addresses as lending_addresses

# feature library
import feature_library.lending.amortisations.amortisation_methods.minimum_repayment as minimum_repayment  # noqa: E501
import feature_library.lending.principal.principal as principal_module
import feature_library.lending.term.term as term_helpers

# contracts api
from contracts_api import Posting, Tside

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.utils import initialise_mock_state


class MinimumRepaymentCommon(FeatureTest):
    default_denomination = DEFAULT_DENOMINATION
    tside = Tside.ASSET


@patch.object(term_helpers, "get_elapsed_term")
class TermDetailsTest(FeatureTest):
    @pytest.mark.unit
    def test_term_details_with_features(
        self,
        mock_get_elapsed_term: MagicMock,
    ):
        mock_vault = self.create_mock()
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=sentinel.effective_datetime,
            parameters={
                term_helpers.TERM_PARAM_ID: "12",
                denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination,
            },
            balances=sentinel.balances,
        )
        mock_get_elapsed_term.return_value = 4

        result = minimum_repayment.term_details(
            state=state,
        )

        mock_get_elapsed_term.assert_called_once_with(
            balances=sentinel.balances, denomination=sentinel.denomination
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
            },
        )

        result = minimum_repayment.term_details(
            state=state,
        )

        self.assertEqual(result, (0, 10))


@patch.object(minimum_repayment.declining_principal, "apply_declining_principal_formula")
@patch.object(minimum_repayment, "term_details")
class CalculateEmi(FeatureTest):
    @pytest.mark.unit
    def test_calculate_eia_no_optional_params_provided(
        self,
        mock_term_details: MagicMock,
        mock_apply_declining_principal_formula: MagicMock,
    ):
        mock_term_details.return_value = minimum_repayment.declining_principal.TermDetails(
            elapsed=sentinel.elapsed, remaining=sentinel.remaining
        )
        state = initialise_mock_state(
            parameters={
                principal_module.PRINCIPAL_PARAM_ID: sentinel.principal,
                term_helpers.TERM_PARAM_ID: "12",
                minimum_repayment.BALLOON_EMI_AMOUNT_PARAM_ID: None,
                minimum_repayment.BALLOON_EMI_AMOUNT_PARAM_ID: None,
                minimum_repayment.BALLOON_PAYMENT_AMOUNT_PARAM_ID: sentinel.balloon_payment_amount,
                "&{application_precision}": "2",
                denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination,
            }
        )
        mock_apply_declining_principal_formula.return_value = sentinel.eia

        result = minimum_repayment.calculate_eia(state=state, get_annual_interest_rate=None)

        mock_term_details.assert_called_once_with(
            state=state,
        )
        mock_apply_declining_principal_formula.assert_called_once_with(
            remaining_principal=sentinel.principal,
            interest_rate=Decimal(0),
            remaining_term=sentinel.remaining,
            lump_sum_amount=sentinel.balloon_payment_amount,
            fulfillment_precision=2,
        )
        self.assertEqual(result, sentinel.eia)

    @pytest.mark.unit
    def test_calculate_eia_all_optional_params_provided(
        self,
        mock_term_details: MagicMock,
        mock_apply_declining_principal_formula: MagicMock,
    ):
        mock_interest_feature = MagicMock()
        mock_interest_feature.get_annual_interest_rate.return_value = Decimal("0.12")
        mock_term_details.return_value = minimum_repayment.declining_principal.TermDetails(
            elapsed=sentinel.elapsed, remaining=sentinel.remaining
        )
        state = initialise_mock_state(
            parameters={
                principal_module.PRINCIPAL_PARAM_ID: sentinel.principal,
                term_helpers.TERM_PARAM_ID: "12",
                minimum_repayment.BALLOON_EMI_AMOUNT_PARAM_ID: None,
                minimum_repayment.BALLOON_PAYMENT_AMOUNT_PARAM_ID: sentinel.balloon_payment_amount,
                denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination,
                "&{application_precision}": "2",
                denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination,
            },
            balances=sentinel.balances,
        )
        mock_principal_adjustments = [
            MagicMock(calculate_principal_adjustment=MagicMock(return_value=Decimal(1))),
            MagicMock(calculate_principal_adjustment=MagicMock(return_value=Decimal(49))),
        ]
        mock_apply_declining_principal_formula.return_value = sentinel.eia

        result = minimum_repayment.calculate_eia(
            state=state,
            principal_amount=Decimal("100"),
            get_annual_interest_rate=mock_interest_feature.get_annual_interest_rate,
            principal_adjustments=mock_principal_adjustments,  # type: ignore
        )

        mock_term_details.assert_called_once_with(
            state=state,
        )

        mock_apply_declining_principal_formula.assert_called_once_with(
            remaining_principal=Decimal("150"),
            interest_rate=minimum_repayment.declining_principal.parameter_utils.yearly_to_monthly_rate(
                Decimal("0.12")
            ),
            remaining_term=sentinel.remaining,
            lump_sum_amount=sentinel.balloon_payment_amount,
            fulfillment_precision=2,
        )
        self.assertEqual(result, sentinel.eia)

    @pytest.mark.unit
    def test_calculate_eia_with_principal_0(
        self,
        mock_term_details: MagicMock,
        mock_apply_declining_principal_formula: MagicMock,
    ):
        mock_interest_feature = MagicMock()
        mock_interest_feature.get_annual_interest_rate.return_value = Decimal("0.12")
        mock_apply_declining_principal_formula.return_value = sentinel.eia
        mock_term_details.return_value = minimum_repayment.declining_principal.TermDetails(
            elapsed=sentinel.elapsed, remaining=sentinel.remaining
        )
        state = initialise_mock_state(
            parameters={
                principal_module.PRINCIPAL_PARAM_ID: sentinel.principal,
                term_helpers.TERM_PARAM_ID: "12",
                minimum_repayment.BALLOON_EMI_AMOUNT_PARAM_ID: None,
                minimum_repayment.BALLOON_EMI_AMOUNT_PARAM_ID: None,
                minimum_repayment.BALLOON_PAYMENT_AMOUNT_PARAM_ID: sentinel.balloon_payment_amount,
                "&{application_precision}": "2",
                denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination,
            }
        )

        result = minimum_repayment.calculate_eia(
            state=state,
            principal_amount=Decimal("0"),
            get_annual_interest_rate=mock_interest_feature.get_annual_interest_rate,
            principal_adjustments=None,
        )

        mock_term_details.assert_called_once_with(
            state=state,
        )

        mock_apply_declining_principal_formula.assert_called_once_with(
            remaining_principal=Decimal("0"),
            interest_rate=minimum_repayment.declining_principal.parameter_utils.yearly_to_monthly_rate(
                Decimal("0.12")
            ),
            remaining_term=sentinel.remaining,
            lump_sum_amount=sentinel.balloon_payment_amount,
            fulfillment_precision=2,
        )

        self.assertEqual(result, sentinel.eia)

    @pytest.mark.unit
    def test_calculate_eia_with_pre_defined_emi(
        self,
        mock_term_details: MagicMock,
        mock_apply_declining_principal_formula: MagicMock,
    ):
        # Setup Mock Values to capture a wrong return in the test.
        mock_interest_feature = MagicMock()
        mock_interest_feature.get_annual_interest_rate.return_value = Decimal("0.12")
        mock_apply_declining_principal_formula.return_value = sentinel.eia
        mock_term_details.return_value = minimum_repayment.declining_principal.TermDetails(
            elapsed=sentinel.elapsed, remaining=sentinel.remaining
        )
        state = initialise_mock_state(
            parameters={
                principal_module.PRINCIPAL_PARAM_ID: sentinel.principal,
                term_helpers.TERM_PARAM_ID: "12",
                minimum_repayment.BALLOON_EMI_AMOUNT_PARAM_ID: sentinel.balloon_emi_amount,
                minimum_repayment.BALLOON_PAYMENT_AMOUNT_PARAM_ID: sentinel.balloon_payment_amount,
                "&{application_precision}": "2",
                denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination,
            }
        )

        result = minimum_repayment.calculate_eia(
            state=state,
            principal_amount=Decimal("0"),
            get_annual_interest_rate=mock_interest_feature.get_annual_interest_rate,
            principal_adjustments=None,
        )

        mock_term_details.assert_not_called()

        mock_apply_declining_principal_formula.assert_not_called()

        self.assertEqual(result, sentinel.balloon_emi_amount)


class IsMinimumRepaymentLoanTest(FeatureTest):
    @pytest.mark.unit
    def test_is_minimum_repayment_loan_true(self):
        self.assertEqual(
            minimum_repayment.is_minimum_repayment_loan("MINIMUM_REPAYMENT_WITH_BALLOON_PAYMENT"),
            True,
        )

    @pytest.mark.unit
    def test_is_minimum_repayment_lower_case_true(self):
        self.assertEqual(
            minimum_repayment.is_minimum_repayment_loan("minimum_repayment_with_balloon_payment"),
            True,
        )

    @pytest.mark.unit
    def test_is_minimum_repayment_loan_false(self):
        self.assertEqual(minimum_repayment.is_minimum_repayment_loan("other"), False)


@patch.object(minimum_repayment.balance_utils, "balance_at_coordinates")
@patch.object(minimum_repayment.eia_module, "update_eia")
@patch.object(minimum_repayment, "calculate_eia")
class AmortiseTest(MinimumRepaymentCommon):
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

        result = minimum_repayment.amortise(
            state=state,
            get_annual_interest_rate=sentinel.get_annual_interest_rate,
        )

        mock_calculate_eia.assert_called_once_with(
            state=state,
            get_annual_interest_rate=sentinel.get_annual_interest_rate,
            principal_amount=None,
            principal_adjustments=None,
        )
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
            eia_address=lending_addresses.EIA,
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

        result = minimum_repayment.amortise(
            state=state,
            get_annual_interest_rate=sentinel.get_annual_interest_rate,
        )

        self.assertEqual(result, [])
