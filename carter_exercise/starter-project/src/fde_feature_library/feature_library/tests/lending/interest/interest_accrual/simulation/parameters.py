# standard libs
from decimal import Decimal

# feature library
import feature_library.common.denomination as denomination
import feature_library.lending.interest.interest_accrual as interest_accrual
import feature_library.lending.interest.secondary.fixed_rate as fixed_rate
import feature_library.lending.interest.secondary.variable_rate as variable_rate

# inception sdk
from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    DecimalParameterValue,
    EnumerationParameterValue,
    ParameterValue,
    StringParameterValue,
)

import tests.lending.interest.interest_accrual.simulation.accounts as accounts
from tests.common.test_denomination import DEFAULT_DENOMINATION

fixed_rate_parameter_values: dict[str, ParameterValue] = {
    denomination.DENOMINATION_PARAM_ID: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    fixed_rate.FIXED_INTEREST_RATE_PARAM_ID: DecimalParameterValue(decimal_value=Decimal("0.12")),
    interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID: AccountIdParameterValue(
        account_id_value=accounts.ACCRUAL_RECEIVABLE
    ),
    interest_accrual.DAYS_IN_YEAR_PARAM_ID: EnumerationParameterValue(enumeration_value="365"),
    interest_accrual.ACCRUAL_PRECISION_PARAM_ID: DecimalParameterValue(decimal_value=Decimal("5")),
    interest_accrual.ACCRUAL_TIME_PARAM_ID: StringParameterValue(string_value="23:59:59"),
}

variable_rate_parameter_values: dict[str, ParameterValue] = {
    denomination.DENOMINATION_PARAM_ID: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    variable_rate.VARIABLE_INTEREST_RATE_PARAM_ID: DecimalParameterValue(
        decimal_value=Decimal("0.05")
    ),
    variable_rate.VARIABLE_RATE_ADJUSTMENT_PARAM_ID: DecimalParameterValue(
        decimal_value=Decimal("0.01")
    ),
    variable_rate.BASE_RATE_PARAM_ID: DecimalParameterValue(decimal_value=Decimal("0.04")),
    variable_rate.ANNUAL_INTEREST_RATE_CAP_PARAM_ID: DecimalParameterValue(
        decimal_value=Decimal("0.6")
    ),
    variable_rate.ANNUAL_INTEREST_RATE_FLOOR_PARAM_ID: DecimalParameterValue(
        decimal_value=Decimal("0.01")
    ),
    interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID: AccountIdParameterValue(
        account_id_value=accounts.ACCRUAL_RECEIVABLE
    ),
    interest_accrual.DAYS_IN_YEAR_PARAM_ID: EnumerationParameterValue(enumeration_value="360"),
    interest_accrual.ACCRUAL_PRECISION_PARAM_ID: DecimalParameterValue(decimal_value=Decimal("5")),
    interest_accrual.ACCRUAL_TIME_PARAM_ID: StringParameterValue(string_value="23:59:59"),
}
