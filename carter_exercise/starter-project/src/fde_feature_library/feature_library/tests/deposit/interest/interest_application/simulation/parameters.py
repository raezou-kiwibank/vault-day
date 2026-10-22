# standard libs
from decimal import Decimal

# library
import feature_library.common.denomination as denomination
import feature_library.deposit.interest.interest_accrual as interest_accrual
import feature_library.deposit.interest.interest_application as interest_application

# inception sdk
from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    DecimalParameterValue,
    EnumerationParameterValue,
    ParameterValue,
    StringParameterValue,
)

import tests.deposit.interest.interest_application.simulation.accounts as accounts
from tests.common.test_denomination import DEFAULT_DENOMINATION

# Accounts V2 endpoint requires parameters to be uploaded using the ParameterValue syntax,
# including instance parameters
default_parameter_values: dict[str, ParameterValue] = {
    denomination.DENOMINATION_PARAM_ID: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    interest_application.INTEREST_APPLICATION_DAY_PARAM_ID: DecimalParameterValue(
        decimal_value=Decimal("1")
    ),
    interest_application.INTEREST_APPLICATION_FREQUENCY_PARAM_ID: EnumerationParameterValue(
        enumeration_value="monthly"
    ),
    interest_application.INTEREST_APPLICATION_TIME_PARAM_ID: StringParameterValue(
        string_value="00:00:01"
    ),
    interest_application.APPLICATION_PRECISION_PARAM_ID: DecimalParameterValue(
        decimal_value=Decimal("2")
    ),
    interest_application.INTEREST_PAID_ACCOUNT_PARAM_ID: AccountIdParameterValue(
        account_id_value=accounts.DUMMY_INTERNAL_ACCOUNT
    ),
    interest_application.INTEREST_RECEIVED_ACCOUNT_PARAM_ID: AccountIdParameterValue(
        account_id_value=accounts.DUMMY_INTERNAL_ACCOUNT
    ),
    interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID: AccountIdParameterValue(
        account_id_value=accounts.DUMMY_INTERNAL_ACCOUNT
    ),
    interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID: AccountIdParameterValue(
        account_id_value=accounts.DUMMY_INTERNAL_ACCOUNT
    ),
}
