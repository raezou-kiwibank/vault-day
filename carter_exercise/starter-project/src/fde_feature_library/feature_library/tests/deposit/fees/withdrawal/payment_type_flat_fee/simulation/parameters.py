from json import dumps

import feature_library.common.denomination as denomination_module
import feature_library.deposit.fees.withdrawal.payment_type_flat_fee as payment_type_flat_fee

from inception_sdk.vault.core_api import AccountIdParameterValue, StringParameterValue

from tests.deposit.fees.withdrawal.payment_type_flat_fee.simulation import accounts, dimensions

default_parameter_values = {
    denomination_module.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=dimensions.DEFAULT_DENOMINATION
    ),
    payment_type_flat_fee.PAYMENT_TYPE_FEE_INCOME_ACCOUNT_PARAM.id: AccountIdParameterValue(
        account_id_value=accounts.PAYMENT_TYPE_FEE_INCOME_ACCOUNT
    ),
    payment_type_flat_fee.PAYMENT_TYPE_FLAT_FEE_PARAM.id: StringParameterValue(
        string_value=dumps({"ATM": "1", "POS": "0.5"})
    ),
}
