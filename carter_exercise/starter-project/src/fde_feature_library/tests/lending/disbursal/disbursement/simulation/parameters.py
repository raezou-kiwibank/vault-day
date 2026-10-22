# standard libs
from decimal import Decimal

# feature library
import feature_library.common.denomination as denomination
import feature_library.lending.disbursal.disbursement as disbursement
import feature_library.lending.principal.principal as principal

# inception sdk
from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    DecimalParameterValue,
    ParameterValue,
    StringParameterValue,
)

import tests.lending.disbursal.disbursement.simulation.accounts as accounts
from tests.common.test_denomination import DEFAULT_DENOMINATION

# default_parameter_values: dict[str, ParameterValue]
default_parameter_values: dict[str, ParameterValue] = {
    denomination.DENOMINATION_PARAM_ID: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    principal.PRINCIPAL_PARAM_ID: DecimalParameterValue(decimal_value=Decimal("1000")),
    disbursement.DEPOSIT_ACCOUNT_PARAM_ID: AccountIdParameterValue(
        account_id_value=accounts.DEPOSIT_ACCOUNT
    ),
}
