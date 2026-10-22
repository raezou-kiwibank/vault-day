# standard libs
from decimal import Decimal

# inception sdk
from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    DecimalParameterValue,
    ParameterValue,
    StringParameterValue,
)

import tests.deposit.fees.early_closure.simulation.accounts as accounts
import tests.deposit.fees.early_closure.simulation.smart_contract as smart_contract
from tests.common.test_denomination import DEFAULT_DENOMINATION

# Accounts V2 endpoint requires parameters to be uploaded using the ParameterValue syntax,
# including instance parameters
default_parameter_values: dict[str, ParameterValue] = {
    smart_contract.denomination_module.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    smart_contract.early_closure_fee_module.EARLY_CLOSURE_FEE_PARAM.id: DecimalParameterValue(
        decimal_value=Decimal(10)
    ),
    smart_contract.early_closure_fee_module.EARLY_CLOSURE_DAYS_PARAM.id: DecimalParameterValue(
        decimal_value=Decimal(7)
    ),
    smart_contract.early_closure_fee_module.EARLY_CLOSURE_FEE_INCOME_ACCOUNT_PARAM.id: AccountIdParameterValue(  # noqa: E501
        account_id_value=accounts.DUMMY_INTERNAL_ACCOUNT
    ),
}
