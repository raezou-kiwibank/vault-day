# standard libs
from decimal import Decimal
from json import dumps

# inception sdk
from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    DecimalParameterValue,
    EnumerationParameterValue,
    ParameterValue,
    StringParameterValue,
)

import tests.deposit.fees.inactivity.e2e.accounts as accounts
import tests.deposit.fees.inactivity.invalid_smart_contract as smart_contract
from tests.common.test_denomination import DEFAULT_DENOMINATION

default_parameter_values: dict[str, ParameterValue] = {
    smart_contract.denomination_module.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    smart_contract.inactivity_fee.INACTIVITY_FEE_PARAM.id: DecimalParameterValue(
        decimal_value=Decimal(10)
    ),
    smart_contract.inactivity_fee.INACTIVITY_FLAGS_PARAM.id: StringParameterValue(
        string_value=dumps(["ACCOUNT_INACTIVE"])
    ),
    smart_contract.inactivity_fee.INACTIVITY_FEE_INCOME_ACCOUNT_PARAM.id: AccountIdParameterValue(
        account_id_value=accounts.INACTIVITY_FEE_INCOME_ACCOUNT
    ),
    smart_contract.inactivity_fee.INACTIVITY_FEE_APPLICATION_DAY_PARAM.id: DecimalParameterValue(
        decimal_value=Decimal(1)
    ),
    smart_contract.inactivity_fee.INACTIVITY_FEE_APPLICATION_TIME_PARAM.id: StringParameterValue(
        string_value="23:59:59"
    ),
    smart_contract.inactivity_fee.INACTIVITY_FEE_PARTIAL_FEE_ENABLED_PARAM.id: EnumerationParameterValue(  # noqa: E501
        enumeration_value="False"
    ),
}
