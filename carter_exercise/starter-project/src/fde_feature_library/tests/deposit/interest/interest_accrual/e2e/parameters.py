# standard libs
from decimal import Decimal

import feature_library.common.denomination as denomination
import feature_library.deposit.interest.interest_accrual as interest_accrual
import feature_library.deposit.interest.secondary.flat_interest as flat_interest

# inception sdk
from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    DecimalParameterValue,
    EnumerationParameterValue,
    ParameterValue,
    StringParameterValue,
)

import tests.deposit.interest.interest_accrual.e2e.accounts as accounts
from tests.common.test_denomination import DEFAULT_DENOMINATION

default_parameter_values: dict[str, ParameterValue] = {
    denomination.DENOMINATION_PARAM_ID: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    interest_accrual.INTEREST_ACCRUAL_TIME_PARAM_ID: StringParameterValue(string_value="00:00:00"),
    interest_accrual.DAYS_IN_YEAR_PARAM_ID: EnumerationParameterValue(enumeration_value="actual"),
    interest_accrual.ACCRUAL_PRECISION_PARAM_ID: DecimalParameterValue(decimal_value=Decimal(5)),
    interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID: AccountIdParameterValue(
        account_id_value=accounts.ACCRUED_INTEREST_PAYABLE_ACCOUNT
    ),
    interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID: AccountIdParameterValue(
        account_id_value=accounts.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT
    ),
    flat_interest.FIXED_INTEREST_RATE_PARAM_ID: DecimalParameterValue(
        decimal_value=Decimal("0.01")
    ),
}
