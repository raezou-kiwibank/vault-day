from json import dumps

import feature_library.common.denomination as denomination_module
from feature_library.deposit.fees.withdrawal import payment_type_threshold_fee

from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    StringParameterValue,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.deposit.fees.withdrawal.payment_type_threshold_fee.simulation import accounts

default_parameter_values = {
    denomination_module.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=DEFAULT_DENOMINATION
    ),
    payment_type_threshold_fee.PAYMENT_TYPE_FEE_INCOME_ACCOUNT_PARAM.id: AccountIdParameterValue(
        account_id_value=accounts.PAYMENT_TYPE_FEE_INCOME_ACCOUNT,
    ),
    payment_type_threshold_fee.PAYMENT_TYPE_THRESHOLD_FEE_PARAM.id: StringParameterValue(
        string_value=dumps({"ATM": {"fee": "0.15", "threshold": "5000"}})
    ),
}
