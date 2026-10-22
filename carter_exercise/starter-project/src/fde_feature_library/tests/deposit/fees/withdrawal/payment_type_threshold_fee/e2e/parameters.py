from json import dumps

from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    ParameterValue,
    StringParameterValue,
)

import tests.deposit.fees.withdrawal.payment_type_threshold_fee.smart_contract as smart_contract
from tests.common.test_denomination import DEFAULT_DENOMINATION

default_parameter_values: dict[str, ParameterValue] = {
    smart_contract.denomination.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    smart_contract.payment_type_threshold_fee.PAYMENT_TYPE_FEE_INCOME_ACCOUNT_PARAM.id: (
        AccountIdParameterValue(account_id_value="PAY_TYPE_FEE_INCOME_ACC")
    ),
    smart_contract.payment_type_threshold_fee.PAYMENT_TYPE_THRESHOLD_FEE_PARAM.id: (
        StringParameterValue(string_value=dumps({"ATM": {"fee": "0.15", "threshold": "5000"}}))
    ),
}
