from decimal import Decimal

import feature_library.common.denomination as denomination_module
import feature_library.deposit.fees.overdraft_limit as overdraft_limit

from inception_sdk.vault.core_api import (
    DecimalParameterValue,
    ParameterValue,
    StringParameterValue,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION

default_parameter_values: dict[str, ParameterValue] = {
    denomination_module.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    overdraft_limit.ARRANGED_OVERDRAFT_AMOUNT_PARAM.id: DecimalParameterValue(
        decimal_value=Decimal(100)
    ),
    overdraft_limit.UNARRANGED_OVERDRAFT_AMOUNT_PARAM.id: DecimalParameterValue(
        decimal_value=Decimal(50)
    ),
}
