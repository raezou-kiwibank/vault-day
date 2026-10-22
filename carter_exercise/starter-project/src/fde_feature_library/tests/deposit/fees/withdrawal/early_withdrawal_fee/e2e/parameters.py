# standard libs
from decimal import Decimal

# inception sdk
from inception_sdk.vault.core_api import (
    DecimalParameterValue,
    ParameterValue,
    StringParameterValue,
)

import tests.deposit.fees.withdrawal.early_withdrawal_fee.smart_contract as smart_contract
from tests.common.test_denomination import DEFAULT_DENOMINATION

default_parameter_values: dict[str, ParameterValue] = {
    smart_contract.denomination_module.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    smart_contract.early_withdrawal_fees.EARLY_WITHDRAWAL_FLAT_FEE_PARAM.id: DecimalParameterValue(
        decimal_value=Decimal(5)
    ),
    smart_contract.early_withdrawal_fees.EARLY_WITHDRAWAL_PERCENTAGE_FEE_PARAM.id: (
        DecimalParameterValue(decimal_value=Decimal("0.1"))
    ),
    smart_contract.early_withdrawal_fees.MAXIMUM_WITHDRAWAL_PERCENTAGE_LIMIT_PARAM.id: DecimalParameterValue(  # noqa: E501
        decimal_value=Decimal(1)
    ),
    smart_contract.early_withdrawal_fees.FEE_FREE_WITHDRAWAL_PERCENTAGE_LIMIT_PARAM.id: DecimalParameterValue(  # noqa: E501
        decimal_value=Decimal(0)
    ),
}
