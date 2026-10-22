from decimal import Decimal

import feature_library.common.denomination as denomination_module
import feature_library.deposit.fees.early_closure_fee as early_closure_fee_module

from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    DecimalParameterValue,
    ParameterValue,
    StringParameterValue,
)

import tests.deposit.fees.early_closure.e2e.accounts as accounts
from tests.common.test_denomination import DEFAULT_DENOMINATION

default_parameter_values: dict[str, ParameterValue] = {
    denomination_module.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    early_closure_fee_module.EARLY_CLOSURE_FEE_PARAM.id: DecimalParameterValue(
        decimal_value=Decimal(10)
    ),
    early_closure_fee_module.EARLY_CLOSURE_DAYS_PARAM.id: DecimalParameterValue(
        decimal_value=Decimal(7)
    ),
    early_closure_fee_module.EARLY_CLOSURE_FEE_INCOME_ACCOUNT_PARAM.id: AccountIdParameterValue(  # noqa: E501
        account_id_value=accounts.DUMMY_INTERNAL_ACCOUNT
    ),
}
