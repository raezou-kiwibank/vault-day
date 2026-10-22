# standard libs
from decimal import Decimal

# feature library
import feature_library.common.denomination as denomination
import feature_library.deposit.fees.withdrawal.excess_fee as excess_fee

# inception sdk
from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    DecimalParameterValue,
    EnumerationParameterValue,
    ParameterValue,
    StringParameterValue,
)

import tests.deposit.fees.withdrawal.excess_fee.simulation.accounts as accounts
from tests.common.test_denomination import DEFAULT_DENOMINATION

default_parameter_values: dict[str, ParameterValue] = {
    denomination.DENOMINATION_PARAM_ID: StringParameterValue(string_value=DEFAULT_DENOMINATION),
    excess_fee.EXCESS_FEE_PARAM_ID: DecimalParameterValue(decimal_value=Decimal("2.50")),
    excess_fee.PERMITTED_WITHDRAWALS_PARAM_ID: DecimalParameterValue(decimal_value=Decimal("2")),
    excess_fee.EXCESS_FEE_MONITORED_TRANSACTION_TYPE_PARAM_ID: StringParameterValue(
        string_value="ATM"
    ),
    excess_fee.EXCESS_FEE_INCOME_ACCOUNT_PARAM_ID: AccountIdParameterValue(
        account_id_value=accounts.EXCESS_FEE_INCOME_ACCOUNT
    ),
    excess_fee.BLOCK_EXCESS_WITHDRAWALS_PARAM_ID: EnumerationParameterValue(
        enumeration_value="False"
    ),
}
