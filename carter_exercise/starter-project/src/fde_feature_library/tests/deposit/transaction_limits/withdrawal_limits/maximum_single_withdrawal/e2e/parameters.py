from decimal import Decimal

import feature_library.common.denomination as denomination_module
import feature_library.deposit.transaction_limits.withdrawal_limits.maximum_single_withdrawal as maximum_single_withdrawal  # noqa: E501

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
    maximum_single_withdrawal.MAX_WITHDRAWAL_PARAM.id: DecimalParameterValue(
        decimal_value=Decimal(100)
    ),
}
