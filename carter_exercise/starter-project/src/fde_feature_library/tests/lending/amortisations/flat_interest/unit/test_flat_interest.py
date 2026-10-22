# standard libs
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel

import pytest
from dateutil.relativedelta import relativedelta

import feature_library.common.application_precision as application_precision_module
import feature_library.common.denomination as denomination_module
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.interest.interest_application as interest_application
import feature_library.lending.interest.secondary.fixed_rate as fixed_rate
import feature_library.lending.principal.principal as principal_module
import feature_library.lending.term.term as term_helpers

# feature library
from feature_library.lending.amortisations.amortisation_methods import flat_interest

# contracts api
from contracts_api import Posting

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import (
    ACCOUNT_ID,
    DEFAULT_DATETIME,
    FeatureTest,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.utils import initialise_mock_state


class IsFlatInterestLoanTest(FeatureTest):
    @pytest.mark.unit
    def test_is_flat_interest_loan_true(self):
        self.assertEqual(flat_interest.is_flat_interest_loan("FLAT_INTEREST"), True)

    @pytest.mark.unit
    def test_is_flat_interest_loan_lower_case_true(self):
        self.assertEqual(flat_interest.is_flat_interest_loan("flat_interest"), True)

    @pytest.mark.unit
    def test_is_flat_interest_loan_false(self):
        self.assertEqual(flat_interest.is_flat_interest_loan("other"), False)


@patch.object(flat_interest.balance_utils, "balance_at_coordinates")
@patch.object(term_helpers, "get_elapsed_term")
class TermDetailsTest(FeatureTest):
    @pytest.mark.unit
    def test_term_details_with_features(
        self,
        mock_get_elapsed_term: MagicMock,
        mock_balance_at_coordinates: MagicMock,
    ):
        mock_vault = self.create_mock()
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=sentinel.effective_datetime,
            parameters={
                term_helpers.TERM_PARAM_ID: "10",
                denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
            },
            balances=sentinel.balances,
        )
        mock_get_elapsed_term.return_value = 1
        mock_balance_at_coordinates.return_value = Decimal("10")

        result = flat_interest.term_details(
            state=state,
        )
        self.assertEqual(result, (1, 9))
        mock_get_elapsed_term.assert_called_once_with(
            balances=sentinel.balances, denomination=DEFAULT_DENOMINATION
        )
        mock_balance_at_coordinates.assert_called_once_with(
            balances=sentinel.balances,
            address=lending_addresses.PRINCIPAL,
            denomination=DEFAULT_DENOMINATION,
        )

    @pytest.mark.unit
    def test_term_details_effective_date_equals_account_creation(
        self,
        mock_get_elapsed_term: MagicMock,
        mock_balance_at_coordinates: MagicMock,
    ):
        mock_vault = self.create_mock()
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=mock_vault.get_account_creation_datetime(),
            parameters={
                term_helpers.TERM_PARAM_ID: "10",
            },
        )

        result = flat_interest.term_details(
            state=state,
        )

        self.assertEqual(result, (0, 10))
        mock_get_elapsed_term.assert_not_called()
        mock_balance_at_coordinates.assert_not_called()

    @pytest.mark.unit
    def test_term_details_zero_principal(
        self,
        mock_get_elapsed_term: MagicMock,
        mock_balance_at_coordinates: MagicMock,
    ):
        mock_vault = self.create_mock()
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME + relativedelta(seconds=1),
            parameters={
                term_helpers.TERM_PARAM_ID: "10",
                denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
            },
            balances=sentinel.balances,
        )
        mock_get_elapsed_term.return_value = 1
        mock_balance_at_coordinates.return_value = Decimal("0")

        result = flat_interest.term_details(
            state=state,
        )
        self.assertEqual(result, (1, 0))
        mock_get_elapsed_term.assert_called_once_with(
            balances=sentinel.balances, denomination=DEFAULT_DENOMINATION
        )
        mock_balance_at_coordinates.assert_called_once_with(
            balances=sentinel.balances,
            address=lending_addresses.PRINCIPAL,
            denomination=DEFAULT_DENOMINATION,
        )

    @pytest.mark.unit
    def test_term_details_negative_principal(
        self,
        mock_get_elapsed_term: MagicMock,
        mock_balance_at_coordinates: MagicMock,
    ):
        mock_vault = self.create_mock()
        state = initialise_mock_state(
            vault=mock_vault,
            effective_datetime=DEFAULT_DATETIME + relativedelta(seconds=1),
            parameters={
                term_helpers.TERM_PARAM_ID: "10",
                denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
            },
            balances=sentinel.balances,
        )
        mock_get_elapsed_term.return_value = 1
        mock_balance_at_coordinates.return_value = Decimal("-10")

        result = flat_interest.term_details(
            state=state,
        )
        self.assertEqual(result, (1, 0))
        mock_get_elapsed_term.assert_called_once_with(
            balances=sentinel.balances, denomination=DEFAULT_DENOMINATION
        )
        mock_balance_at_coordinates.assert_called_once_with(
            balances=sentinel.balances,
            address=lending_addresses.PRINCIPAL,
            denomination=DEFAULT_DENOMINATION,
        )


@patch.object(flat_interest, "calculate_non_accruing_loan_total_interest")
class CalculateEmi(FeatureTest):
    @pytest.mark.unit
    def test_calculate_eia_no_optional_params_provided(
        self,
        mock_calculate_non_accruing_loan_total_interest: MagicMock,
    ):
        state = initialise_mock_state(
            parameters={
                principal_module.PRINCIPAL_PARAM_ID: Decimal("5000"),
                term_helpers.TERM_PARAM_ID: "12",
                application_precision_module.APPLICATION_PRECISION_PARAM.id: "2",
            }
        )
        mock_calculate_non_accruing_loan_total_interest.return_value = Decimal("1000")

        result = flat_interest.calculate_eia(state=state, get_annual_interest_rate=None)
        self.assertEqual(result, Decimal("500"))

        mock_calculate_non_accruing_loan_total_interest.assert_called_once_with(
            original_principal=Decimal("5000"),
            annual_interest_rate=Decimal(0),
            total_term=12,
            precision=2,
        )

    @pytest.mark.unit
    def test_calculate_eia_all_optional_params_provided(
        self,
        mock_calculate_non_accruing_loan_total_interest: MagicMock,
    ):
        state = initialise_mock_state(
            parameters={
                principal_module.PRINCIPAL_PARAM_ID: sentinel.principal,
                term_helpers.TERM_PARAM_ID: "12",
                application_precision_module.APPLICATION_PRECISION_PARAM.id: "2",
            }
        )
        mock_calculate_non_accruing_loan_total_interest.return_value = Decimal("1000")

        mock_interest_feature = MagicMock()
        mock_interest_feature.get_annual_interest_rate.return_value = sentinel.annual_int_rate

        mock_principal_adjustments = [
            MagicMock(calculate_principal_adjustment=MagicMock(return_value=Decimal(1))),
            MagicMock(calculate_principal_adjustment=MagicMock(return_value=Decimal(49))),
        ]

        result = flat_interest.calculate_eia(
            state=state,
            principal_amount=Decimal("5000"),
            get_annual_interest_rate=mock_interest_feature.get_annual_interest_rate,
            principal_adjustments=mock_principal_adjustments,  # type: ignore
        )

        # (principal + adjustments + total interest) / term
        # (5000 + 50 + 1000)/12 = 504.1666... -> 504.17
        self.assertEqual(result, Decimal("504.17"))

        mock_calculate_non_accruing_loan_total_interest.assert_called_once_with(
            original_principal=Decimal("5050"),
            annual_interest_rate=sentinel.annual_int_rate,
            total_term=12,
            precision=2,
        )


@patch.object(flat_interest.parameter_utils, "yearly_to_monthly_rate")
@patch.object(flat_interest.utils, "round_decimal")
class TotalInterestTest(FeatureTest):
    @pytest.mark.unit
    def test_calculate_non_accruing_loan_total_interest_default_precision(
        self, mock_round_decimal: MagicMock, mock_yearly_to_monthly_rate: MagicMock
    ):
        mock_round_decimal.return_value = sentinel.total_interest
        mock_yearly_to_monthly_rate.return_value = Decimal("0.1")
        result = flat_interest.calculate_non_accruing_loan_total_interest(
            original_principal=Decimal("10"),
            annual_interest_rate=sentinel.annual_rate,
            total_term=6,
        )
        self.assertEqual(result, sentinel.total_interest)
        mock_round_decimal.assert_called_once_with(amount=Decimal("6"), decimal_places=2)

    @pytest.mark.unit
    def test_calculate_non_accruing_loan_total_interest_custom_precision(
        self, mock_round_decimal: MagicMock, mock_yearly_to_monthly_rate: MagicMock
    ):
        mock_round_decimal.return_value = sentinel.total_interest
        mock_yearly_to_monthly_rate.return_value = Decimal("0.1")
        result = flat_interest.calculate_non_accruing_loan_total_interest(
            original_principal=Decimal("10"),
            annual_interest_rate=sentinel.annual_rate,
            total_term=6,
            precision=sentinel.precision,
        )
        self.assertEqual(result, sentinel.total_interest)
        mock_round_decimal.assert_called_once_with(
            amount=Decimal("6"), decimal_places=sentinel.precision
        )


@patch.object(flat_interest, "get_interest_to_apply")
@patch.object(flat_interest.fees, "fee_postings")
class ApplyInterestTest(FeatureTest):
    @pytest.mark.unit
    def test_apply_interest(
        self,
        mock_fee_postings: MagicMock,
        mock_get_interest_to_apply: MagicMock,
    ):
        mock_vault = self.create_mock()
        state = initialise_mock_state(
            vault=mock_vault,
            parameters={
                interest_application.INTEREST_RECEIVED_ACCOUNT_PARAM_ID: sentinel.internal_account,  # noqa: E501
                denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
            },
            balances=sentinel.balances,
        )
        mock_get_interest_to_apply.return_value = flat_interest.lending_interfaces.InterestAmounts(
            eia_accrued=sentinel.eia_accrued,
            eia_rounded_accrued=sentinel.eia_rounded_accrued,
            non_eia_accrued=sentinel.non_eia_accrued,
            non_eia_rounded_accrued=sentinel.non_eia_rounded_accrued,
            total_rounded=sentinel.total_rounded,
        )
        mock_fee_postings.return_value = sentinel.postings

        self.assertEqual(
            flat_interest.apply_interest(
                state=state,
                previous_application_datetime=sentinel.previous_application_datetime,
            ),
            sentinel.postings,
        )
        mock_fee_postings.assert_called_once_with(
            customer_account_id=ACCOUNT_ID,
            customer_account_address="INTEREST_DUE",
            denomination=DEFAULT_DENOMINATION,
            amount=sentinel.total_rounded,
            internal_account=sentinel.internal_account,
        )
        mock_get_interest_to_apply.assert_called_once_with(
            state=state,
        )


@patch.object(flat_interest, "_calculate_interest_due")
@patch.object(term_helpers, "get_elapsed_term")
@patch.object(flat_interest, "calculate_non_accruing_loan_total_interest")
class GetInterestToApplyTest(FeatureTest):
    elapsed_term = 1
    expected_result = flat_interest.lending_interfaces.InterestAmounts(
        eia_accrued=Decimal("0"),
        eia_rounded_accrued=sentinel.interest_due,
        non_eia_accrued=Decimal("0"),
        non_eia_rounded_accrued=Decimal("0"),
        total_rounded=sentinel.interest_due,
    )

    @pytest.mark.unit
    def test_get_interest_to_apply_default_args(
        self,
        mock_calculate_non_accruing_loan_total_interest: MagicMock,
        mock_get_elapsed_term: MagicMock,
        mock_calculate_interest_due: MagicMock,
    ):
        state = initialise_mock_state(
            parameters={
                principal_module.PRINCIPAL_PARAM_ID: sentinel.principal,
                term_helpers.TERM_PARAM_ID: Decimal("12"),
                fixed_rate.FIXED_INTEREST_RATE_PARAM_ID: sentinel.fixed_interest_rate,
                denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
                application_precision_module.APPLICATION_PRECISION_PARAM.id: "2",
            },
            balances=sentinel.balances,
        )
        mock_calculate_non_accruing_loan_total_interest.return_value = sentinel.total_interest
        mock_get_elapsed_term.return_value = self.elapsed_term
        mock_calculate_interest_due.return_value = sentinel.interest_due

        self.assertEqual(
            flat_interest.get_interest_to_apply(
                state=state,
            ),
            self.expected_result,
        )
        mock_calculate_non_accruing_loan_total_interest.assert_called_once_with(
            original_principal=sentinel.principal,
            annual_interest_rate=sentinel.fixed_interest_rate,
            total_term=12,
            precision=2,
        )
        mock_get_elapsed_term.assert_called_once_with(
            balances=sentinel.balances, denomination=DEFAULT_DENOMINATION
        )
        mock_calculate_interest_due.assert_called_once_with(
            total_interest=sentinel.total_interest,
            total_term=12,
            remaining_term=11,
            precision=2,
        )

    @pytest.mark.unit
    def test_get_interest_to_apply_all_args_provided(
        self,
        mock_calculate_non_accruing_loan_total_interest: MagicMock,
        mock_get_elapsed_term: MagicMock,
        mock_calculate_interest_due: MagicMock,
    ):
        state = initialise_mock_state(
            parameters={
                principal_module.PRINCIPAL_PARAM_ID: sentinel.principal,
                term_helpers.TERM_PARAM_ID: Decimal("12"),
                fixed_rate.FIXED_INTEREST_RATE_PARAM_ID: sentinel.fixed_interest_rate,
                denomination_module.DENOMINATION_PARAM_ID: DEFAULT_DENOMINATION,
                application_precision_module.APPLICATION_PRECISION_PARAM.id: "2",
            },
            balances=sentinel.balances,
        )
        mock_calculate_non_accruing_loan_total_interest.return_value = sentinel.total_interest
        mock_get_elapsed_term.return_value = self.elapsed_term
        mock_calculate_interest_due.return_value = sentinel.interest_due

        mock_fetchers_config = MagicMock()
        mock_fetchers_config.denomination_param_id = denomination_module.DENOMINATION_PARAM_ID
        mock_fetchers_config.principal_param_id = principal_module.PRINCIPAL_PARAM_ID
        mock_fetchers_config.term_param_id = term_helpers.TERM_PARAM_ID
        mock_fetchers_config.fixed_interest_rate_param_id = fixed_rate.FIXED_INTEREST_RATE_PARAM_ID
        mock_fetchers_config.application_precision_param_id = (
            application_precision_module.APPLICATION_PRECISION_PARAM.id
        )

        self.assertEqual(
            flat_interest.get_interest_to_apply(
                state=state,
                fetchers_config=mock_fetchers_config,
            ),
            self.expected_result,
        )
        mock_calculate_non_accruing_loan_total_interest.assert_called_once_with(
            original_principal=sentinel.principal,
            annual_interest_rate=sentinel.fixed_interest_rate,
            total_term=12,
            precision=2,
        )
        mock_get_elapsed_term.assert_called_once_with(
            balances=sentinel.balances, denomination=DEFAULT_DENOMINATION
        )
        mock_calculate_interest_due.assert_called_once_with(
            total_interest=sentinel.total_interest,
            total_term=12,
            remaining_term=11,
            precision=2,
        )


@patch.object(flat_interest.utils, "round_decimal")
class CalculateInterestDueTest(FeatureTest):
    @pytest.mark.unit
    def test_calculate_interest_due_not_final_term(self, mock_round_decimal: MagicMock):
        mock_round_decimal.return_value = Decimal("120.12")

        result = flat_interest._calculate_interest_due(
            total_interest=Decimal("1000"),
            total_term=10,
            remaining_term=2,
            precision=sentinel.precision,
        )
        self.assertEqual(result, Decimal("120.12"))
        mock_round_decimal.assert_called_once_with(
            amount=Decimal("100"), decimal_places=sentinel.precision
        )

    @pytest.mark.unit
    def test_calculate_interest_due_final_term(self, mock_round_decimal: MagicMock):
        # 1000 / 12
        mock_round_decimal.return_value = Decimal("83.33")

        result = flat_interest._calculate_interest_due(
            total_interest=Decimal("1000"),
            total_term=12,
            remaining_term=1,
            precision=sentinel.precision,
        )
        # since remaining term is 1, we're on the final event and so the total remaining interest
        # (total loan interest - interest paid) should be become due
        # elapsed = 11 so total interest paid so far is 83.33 * 11 = 916.63
        # so we expected 1000 - 916.63 = 83.37 to be due
        self.assertEqual(result, Decimal("83.37"))
        mock_round_decimal.assert_called_once_with(
            amount=(Decimal("1000") / 12), decimal_places=sentinel.precision
        )


@patch.object(flat_interest.balance_utils, "balance_at_coordinates")
@patch.object(flat_interest.eia_module, "update_eia")
@patch.object(flat_interest, "calculate_eia")
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

        result = flat_interest.amortise(
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

        result = flat_interest.amortise(
            state=state,
            get_annual_interest_rate=sentinel.get_annual_interest_rate,
        )

        self.assertEqual(result, [])
