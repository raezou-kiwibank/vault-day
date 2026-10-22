# standard libs
from json import dumps

import feature_library.common.denomination as denomination_module
import feature_library.deposit.fees.withdrawal.payment_type_flat_fee as payment_type_flat_fee

# inception sdk
from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    ParameterValue,
    StringParameterValue,
)

import tests.deposit.fees.withdrawal.payment_type_flat_fee.e2e.accounts as accounts
from tests.common.test_denomination import DEFAULT_DENOMINATION

default_parameter_values: dict[str, ParameterValue] = {
    denomination_module.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=DEFAULT_DENOMINATION
    ),
    payment_type_flat_fee.PAYMENT_TYPE_FEE_INCOME_ACCOUNT_PARAM.id: AccountIdParameterValue(
        account_id_value=accounts.PAYMENT_TYPE_FEE_INCOME_ACCOUNT
    ),
    payment_type_flat_fee.PAYMENT_TYPE_FLAT_FEE_PARAM.id: StringParameterValue(
        string_value=dumps({"ATM": "1", "POS": "0.5"})
    ),
}
