# standard libs
from decimal import Decimal
from unittest.mock import MagicMock, patch, sentinel

import pytest

import feature_library.common.application_precision as application_precision_module
import feature_library.common.denomination as denomination_module
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.interest.secondary.fixed_rate as fixed_rate
import feature_library.lending.principal.principal as principal_module
import feature_library.lending.term.term as term_helpers

# feature library
from feature_library.lending.amortisations.amortisation_methods import rule_of_78

# contracts api
from contracts_api import Posting

# inception sdk
from inception_sdk.test_framework.contracts.unit.common import FeatureTest

from tests.utils import initialise_mock_state


class RuleOf78(FeatureTest):
    target_test_file_path = "feature_library/lending/amortisations/rule_of_78.py"


class IsRuleOf78LoanTest(RuleOf78):
    @pytest.mark.unit
    def test_is_rule_of_78_loan_true(self):
        self.assertEqual(rule_of_78.is_rule_of_78_loan("RULE_OF_78"), True)

    @pytest.mark.unit
    def test_is_rule_of_78_loan_lower_case_true(self):
        self.assertEqual(rule_of_78.is_rule_of_78_loan("rule_of_78"), True)

    @pytest.mark.unit
    def test_is_rule_of_78_loan_false(self):
        self.assertEqual(rule_of_78.is_rule_of_78_loan("other"), False)


class RuleOf78InterestApplicationTest(RuleOf78):
    @patch.object(rule_of_78, "get_interest_to_apply")
    @patch.object(rule_of_78.fees, "fee_postings")
    @pytest.mark.unit
    def test_apply_interest(
        self,
        mock_fee_postings: MagicMock,
        mock_get_interest_to_apply: MagicMock,
    ):
        mock_vault = self.create_mock(account_id="account_id")
        state = initialise_mock_state(
            vault=mock_vault,
            parameters={
                denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination,
                term_helpers.TERM_PARAM_ID: "12",
                application_precision_module.APPLICATION_PRECISION_PARAM.id: "2",
                "&{interest_received_account}": sentinel.interest_received_account,
                principal_module.PRINCIPAL_PARAM_ID: sentinel.principal,
                fixed_rate.FIXED_INTEREST_RATE_PARAM_ID: sentinel.fixed_interest_rate,
            },
            balances=sentinel.balances,
        )

        mock_get_interest_to_apply.return_value = rule_of_78.lending_interfaces.InterestAmounts(
            eia_accrued=Decimal("0"),
            eia_rounded_accrued=Decimal("100.22"),
            non_eia_accrued=Decimal("0"),
            non_eia_rounded_accrued=Decimal("0"),
            total_rounded=Decimal("100.22"),
        )
        mock_fee_postings.return_value = [sentinel.application_postings]

        result = rule_of_78.apply_interest(
            state=state,
        )

        self.assertListEqual(result, [sentinel.application_postings])

        mock_get_interest_to_apply.assert_called_once_with(
            state=state,
        )
        mock_fee_postings.assert_called_once_with(
            customer_account_id="account_id",
            customer_account_address=lending_addresses.INTEREST_DUE,
            denomination=sentinel.denomination,
            amount=Decimal("100.22"),
            internal_account=sentinel.interest_received_account,
        )

    @patch.object(rule_of_78, "calculate_non_accruing_loan_total_interest")
    @patch.object(term_helpers, "get_elapsed_term")
    @patch.object(rule_of_78, "_get_sum_1_to_n")
    @patch.object(rule_of_78, "_calculate_interest_due")
    @pytest.mark.unit
    def test_get_interest_to_apply_default_args(
        self,
        mock_calculate_interest_due: MagicMock,
        mock_get_sum_1_to_n: MagicMock,  # noqa: N803
        mock_get_elapsed_term: MagicMock,
        mock_calculate_non_accruing_loan_total_interest: MagicMock,
    ):
        total_term = 12
        state = initialise_mock_state(
            parameters={
                denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination,
                term_helpers.TERM_PARAM_ID: "12",
                application_precision_module.APPLICATION_PRECISION_PARAM.id: "2",
                principal_module.PRINCIPAL_PARAM_ID: sentinel.principal,
                fixed_rate.FIXED_INTEREST_RATE_PARAM_ID: sentinel.fixed_interest_rate,
            },
            balances=sentinel.balances,
        )

        mock_get_elapsed_term.return_value = 5
        mock_calculate_non_accruing_loan_total_interest.return_value = sentinel.total_interest
        mock_get_sum_1_to_n.return_value = sentinel.denominator
        mock_calculate_interest_due.return_value = sentinel.interest_due

        result = rule_of_78.get_interest_to_apply(
            state=state,
        )
        self.assertEqual(
            result,
            rule_of_78.lending_interfaces.InterestAmounts(
                eia_accrued=Decimal("0"),
                eia_rounded_accrued=sentinel.interest_due,
                non_eia_accrued=Decimal("0"),
                non_eia_rounded_accrued=Decimal("0"),
                total_rounded=sentinel.interest_due,
            ),
        )

        mock_get_elapsed_term.assert_called_once_with(
            balances=sentinel.balances,
            denomination=sentinel.denomination,
        )
        mock_calculate_non_accruing_loan_total_interest.assert_called_once_with(
            original_principal=sentinel.principal,
            annual_interest_rate=sentinel.fixed_interest_rate,
            total_term=total_term,
            precision=2,
        )
        mock_get_sum_1_to_n.assert_called_once_with(total_term)
        mock_calculate_interest_due.assert_called_once_with(
            total_interest=sentinel.total_interest,
            total_term=12,
            term_remaining=7,
            denominator=sentinel.denominator,
            application_precision=2,
        )

    @patch.object(rule_of_78, "calculate_non_accruing_loan_total_interest")
    @patch.object(term_helpers, "get_elapsed_term")
    @patch.object(rule_of_78, "_get_sum_1_to_n")
    @patch.object(rule_of_78, "_calculate_interest_due")
    @pytest.mark.unit
    def test_get_interest_to_apply_with_explicit_precision(
        self,
        mock_calculate_interest_due: MagicMock,
        mock_get_sum_1_to_n: MagicMock,  # noqa: N803
        mock_get_elapsed_term: MagicMock,
        mock_calculate_non_accruing_loan_total_interest: MagicMock,
    ):
        total_term = 24
        state = initialise_mock_state(
            parameters={
                denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination,
                term_helpers.TERM_PARAM_ID: str(total_term),
                "&{application_precision}": "2",
                principal_module.PRINCIPAL_PARAM_ID: sentinel.total_principal,
                fixed_rate.FIXED_INTEREST_RATE_PARAM_ID: sentinel.fixed_interest_rate,
            },
            balances=sentinel.balances,
        )

        mock_get_elapsed_term.return_value = 5
        mock_calculate_non_accruing_loan_total_interest.return_value = sentinel.total_interest
        mock_get_sum_1_to_n.return_value = sentinel.denominator
        mock_calculate_interest_due.return_value = sentinel.interest_due

        result = rule_of_78.get_interest_to_apply(
            state=state,
        )
        self.assertEqual(
            result,
            rule_of_78.lending_interfaces.InterestAmounts(
                eia_accrued=Decimal("0"),
                eia_rounded_accrued=sentinel.interest_due,
                non_eia_accrued=Decimal("0"),
                non_eia_rounded_accrued=Decimal("0"),
                total_rounded=sentinel.interest_due,
            ),
        )

        mock_get_elapsed_term.assert_called_once_with(
            balances=sentinel.balances,
            denomination=sentinel.denomination,
        )
        mock_calculate_non_accruing_loan_total_interest.assert_called_once_with(
            original_principal=sentinel.total_principal,
            annual_interest_rate=sentinel.fixed_interest_rate,
            total_term=total_term,
            precision=2,
        )
        mock_get_sum_1_to_n.assert_called_once_with(total_term)
        mock_calculate_interest_due.assert_called_once_with(
            total_interest=sentinel.total_interest,
            total_term=24,
            term_remaining=19,
            denominator=sentinel.denominator,
            application_precision=2,
        )

    @patch.object(
        rule_of_78,
        "_calculate_final_month_interest",
        MagicMock(return_value=sentinel.final_interest_due),
    )
    @pytest.mark.unit
    def test_calculate_interest_due_24_month(
        self,
    ):
        test_cases = [
            {"remaining_term": 24, "interest_due": Decimal("99.88")},
            {"remaining_term": 23, "interest_due": Decimal("95.72")},
            {"remaining_term": 22, "interest_due": Decimal("91.56")},
            {"remaining_term": 21, "interest_due": Decimal("87.39")},
            {"remaining_term": 20, "interest_due": Decimal("83.23")},
            {"remaining_term": 19, "interest_due": Decimal("79.07")},
            {"remaining_term": 18, "interest_due": Decimal("74.91")},
            {"remaining_term": 17, "interest_due": Decimal("70.75")},
            {"remaining_term": 16, "interest_due": Decimal("66.59")},
            {"remaining_term": 15, "interest_due": Decimal("62.42")},
            {"remaining_term": 14, "interest_due": Decimal("58.26")},
            {"remaining_term": 13, "interest_due": Decimal("54.1")},
            {"remaining_term": 12, "interest_due": Decimal("49.94")},
            {"remaining_term": 11, "interest_due": Decimal("45.78")},
            {"remaining_term": 10, "interest_due": Decimal("41.62")},
            {"remaining_term": 9, "interest_due": Decimal("37.45")},
            {"remaining_term": 8, "interest_due": Decimal("33.29")},
            {"remaining_term": 7, "interest_due": Decimal("29.13")},
            {"remaining_term": 6, "interest_due": Decimal("24.97")},
            {"remaining_term": 5, "interest_due": Decimal("20.81")},
            {"remaining_term": 4, "interest_due": Decimal("16.65")},
            {"remaining_term": 3, "interest_due": Decimal("12.48")},
            {"remaining_term": 2, "interest_due": Decimal("8.32")},
            {"remaining_term": 1, "interest_due": sentinel.final_interest_due},
        ]

        results = []

        for test_case in test_cases:
            result = rule_of_78._calculate_interest_due(
                total_interest=Decimal("1248.48"),
                total_term=24,
                term_remaining=test_case["remaining_term"],
                denominator=300,
                application_precision=2,
            )

            results.append({"remaining_term": test_case["remaining_term"], "interest_due": result})

        self.assertEqual(results, test_cases)

    @patch.object(
        rule_of_78,
        "_calculate_final_month_interest",
        MagicMock(return_value=sentinel.final_interest_due),
    )
    @pytest.mark.unit
    def test_calculate_interest_due_12_month(
        self,
    ):
        test_cases = [
            {"remaining_term": 12, "interest_due": Decimal("47.08")},
            {"remaining_term": 11, "interest_due": Decimal("43.15")},
            {"remaining_term": 10, "interest_due": Decimal("39.23")},
            {"remaining_term": 9, "interest_due": Decimal("35.31")},
            {"remaining_term": 8, "interest_due": Decimal("31.38")},
            {"remaining_term": 7, "interest_due": Decimal("27.46")},
            {"remaining_term": 6, "interest_due": Decimal("23.54")},
            {"remaining_term": 5, "interest_due": Decimal("19.62")},
            {"remaining_term": 4, "interest_due": Decimal("15.69")},
            {"remaining_term": 3, "interest_due": Decimal("11.77")},
            {"remaining_term": 2, "interest_due": Decimal("7.85")},
            {"remaining_term": 1, "interest_due": sentinel.final_interest_due},
        ]

        results = []

        for test_case in test_cases:
            result = rule_of_78._calculate_interest_due(
                total_interest=Decimal("306"),
                total_term=12,
                term_remaining=test_case["remaining_term"],
                denominator=78,
                application_precision=2,
            )

            results.append({"remaining_term": test_case["remaining_term"], "interest_due": result})

        self.assertEqual(results, test_cases)

    @pytest.mark.unit
    def test_calculate_final_month_interest(self):
        result = rule_of_78._calculate_final_month_interest(
            total_interest=Decimal("100"),
            total_term=12,
            rule_of_78_denominator=78,
            application_precision=2,
        )
        # note that if we use the rule of 78 formula instead we would get 1.28,
        # e.g. round(100*1/78,2) = 1.28
        # which would mean the total interest becoming due would be 99.99 instead of 100
        self.assertEqual(result, Decimal("1.29"))

    @pytest.mark.unit
    def test_get_sum_1_to_n(  # noqa E803
        self,
    ):
        self.assertEqual(
            1830,
            rule_of_78._get_sum_1_to_n(N=60),
        )

    @pytest.mark.unit
    def test_calculate_non_accruing_loan_total_interest_1_year(self):
        test_case = {
            "description": "£1000, 1 year loan",
            "input": {
                "original_principal": Decimal("1000"),
                "annual_interest_rate": Decimal("0.135"),
                "total_term": 12,
                "precision": 2,
            },
            # (1000 * 0.135 * 12) / 12 rounded to 2 dp = 135.00
            "expected_result": Decimal("135.00"),
        }

        result = rule_of_78.calculate_non_accruing_loan_total_interest(**test_case["input"])
        self.assertEqual(result, test_case["expected_result"], test_case["description"])

    @pytest.mark.unit
    def test_calculate_non_accruing_loan_total_interest_2_year(self):
        test_case = {
            "description": "£20400, 2 year loan",
            "input": {
                "original_principal": Decimal("20400"),
                "annual_interest_rate": Decimal("0.0306"),
                "total_term": 24,
                "precision": 2,
            },
            # (20400 * 0.0306 * 24) / 12 rounded to 2 dp = 1248.48
            "expected_result": Decimal("1248.48"),
        }

        result = rule_of_78.calculate_non_accruing_loan_total_interest(**test_case["input"])
        self.assertEqual(result, test_case["expected_result"], test_case["description"])


@patch.object(rule_of_78, "calculate_non_accruing_loan_total_interest")
class CalculateEmi(FeatureTest):
    @pytest.mark.unit
    def test_calculate_eia_no_optional_args_provided(
        self,
        mock_calculate_non_accruing_loan_total_interest: MagicMock,
    ):
        mock_calculate_non_accruing_loan_total_interest.return_value = Decimal(0)
        state = initialise_mock_state(
            parameters={
                principal_module.PRINCIPAL_PARAM_ID: Decimal(1000),
                "&{application_precision}": Decimal(2),
                term_helpers.TERM_PARAM_ID: "12",
            }
        )

        result = rule_of_78.calculate_eia(state=state, get_annual_interest_rate=None)

        mock_calculate_non_accruing_loan_total_interest.assert_called_once_with(
            original_principal=Decimal("1000"),
            annual_interest_rate=Decimal("0"),
            total_term=12,
            precision=Decimal("2"),
        )

        # round((principal + total_loan_interest) / total_term, application_precision)
        # round((1000 + 0) / 12, 2) = 83.33
        self.assertEqual(result, Decimal("83.33"))

    @pytest.mark.unit
    def test_calculate_eia_all_optional_args_and_params_provided(
        self,
        mock_calculate_non_accruing_loan_total_interest: MagicMock,
    ):
        mock_calculate_non_accruing_loan_total_interest.return_value = Decimal("10.5")
        state = initialise_mock_state(
            parameters={
                principal_module.PRINCIPAL_PARAM_ID: Decimal("1000"),
                application_precision_module.APPLICATION_PRECISION_PARAM.id: "2",
                denomination_module.DENOMINATION_PARAM_ID: "dummy",
                term_helpers.TERM_PARAM_ID: "12",
            },
            balances=sentinel.balances,
        )
        mock_interest_feature = MagicMock()
        mock_interest_feature.get_annual_interest_rate.return_value = Decimal("0.01")
        mock_principal_adjustments = [
            MagicMock(calculate_principal_adjustment=MagicMock(return_value=Decimal("1"))),
            MagicMock(calculate_principal_adjustment=MagicMock(return_value=Decimal("49"))),
        ]

        result = rule_of_78.calculate_eia(
            state=state,
            get_annual_interest_rate=mock_interest_feature.get_annual_interest_rate,
            principal_amount=Decimal("1000"),
            principal_adjustments=mock_principal_adjustments,  # type: ignore
        )

        mock_calculate_non_accruing_loan_total_interest.assert_called_once_with(
            original_principal=Decimal("1050"),
            annual_interest_rate=Decimal("0.01"),
            total_term=12,
            precision=2,
        )

        # total_loan_interest = round(P * annual_interest_rate * term / term, 2)
        # total_loan_interest = round(1050 * 0.01 * 12 / 12, 2) = 10.5
        # EIA = round((principal + total_loan_interest) / total_term, application_precision)
        # EIA = round((1050 + 10.5) / 12, 2) = 88.38
        self.assertEqual(result, Decimal("88.38"))


@patch.object(rule_of_78.balance_utils, "balance_at_coordinates")
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
                application_precision_module.APPLICATION_PRECISION_PARAM.id: "2",
                denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination,
                term_helpers.TERM_PARAM_ID: "12",
            },
            balances=sentinel.balances,
        )
        mock_get_elapsed_term.return_value = 4
        mock_balance_at_coordinates.return_value = Decimal("10")

        result = rule_of_78.term_details(
            state=state,
        )

        mock_get_elapsed_term.assert_called_once_with(
            balances=sentinel.balances, denomination=sentinel.denomination
        )
        mock_balance_at_coordinates.assert_called_once_with(
            balances=sentinel.balances,
            address=lending_addresses.PRINCIPAL,
            denomination=sentinel.denomination,
        )
        self.assertEqual(result, (4, 8))

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
                denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination,
            },
        )

        result = rule_of_78.term_details(
            state=state,
        )

        self.assertEqual(result, (0, 10))
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
            effective_datetime=sentinel.effective_datetime,
            parameters={
                term_helpers.TERM_PARAM_ID: "10",
                denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination,
            },
            balances=sentinel.balances,
        )
        mock_get_elapsed_term.return_value = 1
        mock_balance_at_coordinates.return_value = Decimal("0")

        result = rule_of_78.term_details(
            state=state,
        )
        self.assertEqual(result, (1, 0))
        mock_get_elapsed_term.assert_called_once_with(
            balances=sentinel.balances, denomination=sentinel.denomination
        )
        mock_balance_at_coordinates.assert_called_once_with(
            balances=sentinel.balances,
            address=lending_addresses.PRINCIPAL,
            denomination=sentinel.denomination,
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
            effective_datetime=sentinel.effective_datetime,
            parameters={
                term_helpers.TERM_PARAM_ID: "10",
                denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination,
            },
            balances=sentinel.balances,
        )
        mock_get_elapsed_term.return_value = 1
        mock_balance_at_coordinates.return_value = Decimal("-10")

        result = rule_of_78.term_details(
            state=state,
        )
        self.assertEqual(result, (1, 0))
        mock_get_elapsed_term.assert_called_once_with(
            balances=sentinel.balances, denomination=sentinel.denomination
        )
        mock_balance_at_coordinates.assert_called_once_with(
            balances=sentinel.balances,
            address=lending_addresses.PRINCIPAL,
            denomination=sentinel.denomination,
        )


@patch.object(rule_of_78.balance_utils, "balance_at_coordinates")
@patch.object(rule_of_78.eia_module, "update_eia")
@patch.object(rule_of_78, "calculate_eia")
class AmortiseTest(RuleOf78):
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
            parameters={denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination},
            balances=sentinel.balances,
        )

        result = rule_of_78.amortise(
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
            denomination=sentinel.denomination,
        )
        mock_update_eia.assert_called_once_with(
            account_id=sentinel.account_id,
            denomination=sentinel.denomination,
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
            parameters={denomination_module.DENOMINATION_PARAM_ID: sentinel.denomination},
            balances=sentinel.balances,
        )

        result = rule_of_78.amortise(
            state=state,
            get_annual_interest_rate=sentinel.get_annual_interest_rate,
        )

        self.assertEqual(result, [])
