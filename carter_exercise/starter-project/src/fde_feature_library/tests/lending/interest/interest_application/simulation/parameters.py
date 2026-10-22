from decimal import Decimal

# feature library
import feature_library.common.application_precision as application_precision_module
import feature_library.common.denomination as denomination
import feature_library.lending.interest.interest_accrual as interest_accrual
import feature_library.lending.interest.interest_application as interest_application

# inception sdk
from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    DecimalParameterValue,
    ParameterValue,
    StringParameterValue,
)

import tests.lending.interest.interest_application.simulation.accounts as accounts
from tests.common.test_denomination import DEFAULT_DENOMINATION

default_parameter_values: dict[str, ParameterValue] = {
    denomination.DENOMINATION_PARAM_ID: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    interest_application.INTEREST_RECEIVED_ACCOUNT_PARAM_ID: AccountIdParameterValue(
        account_id_value=accounts.INTEREST_RECEIVED_ACCOUNT
    ),
    application_precision_module.APPLICATION_PRECISION_PARAM_ID: DecimalParameterValue(
        decimal_value=Decimal("2")
    ),
    interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID: AccountIdParameterValue(
        account_id_value=accounts.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT
    ),
}
