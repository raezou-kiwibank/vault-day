from decimal import Decimal

import feature_library.common.denomination as denomination_module
import feature_library.deposit.fees.withdrawal.excess_fee as excess_fee_module

from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    DecimalParameterValue,
    EnumerationParameterValue,
    ParameterValue,
    StringParameterValue,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.deposit.fees.withdrawal.excess_fee.e2e import accounts

default_parameter_values: dict[str, ParameterValue] = {
    denomination_module.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    excess_fee_module.EXCESS_FEE_PARAM.id: DecimalParameterValue(decimal_value=Decimal("2.50")),
    excess_fee_module.PERMITTED_WITHDRAWALS_PARAM.id: DecimalParameterValue(
        decimal_value=Decimal("2")
    ),
    excess_fee_module.EXCESS_FEE_MONITORED_TRANSACTION_TYPE_PARAM.id: StringParameterValue(
        string_value="ATM"
    ),
    excess_fee_module.EXCESS_FEE_INCOME_ACCOUNT_PARAM.id: AccountIdParameterValue(
        account_id_value=accounts.EXCESS_FEE_INCOME_ACCOUNT
    ),
    excess_fee_module.BLOCK_EXCESS_WITHDRAWALS_PARAM.id: EnumerationParameterValue(
        enumeration_value="False"
    ),
}
