from json import dumps

import feature_library.common.denomination as denomination_module
from feature_library.deposit.fees.withdrawal import (
    payment_type_monthly_limit_fee,
)

from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    ParameterValue,
    StringParameterValue,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.deposit.fees.withdrawal.payment_type_monthly_limit_fee.e2e import accounts

default_parameter_values: dict[str, ParameterValue] = {
    denomination_module.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    payment_type_monthly_limit_fee.PAYMENT_TYPE_FEE_INCOME_ACCOUNT_PARAM.id: (
        AccountIdParameterValue(account_id_value=accounts.PAYMENT_TYPE_FEE_INCOME_ACCOUNT)
    ),
    payment_type_monthly_limit_fee.MAXIMUM_MONTHLY_PAYMENT_TYPE_WITHDRAWAL_LIMIT_PARAM.id: (
        StringParameterValue(string_value=dumps({"ATM": {"fee": "0.50", "limit": "2"}}))
    ),
}
