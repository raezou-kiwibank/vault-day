from decimal import Decimal

import feature_library.common.denomination as denomination_module
import feature_library.deposit.transaction_limits.deposit_limits.maximum_single_deposit as maximum_single_deposit  # noqa: E501

from inception_sdk.vault.core_api import (
    DecimalParameterValue,
    StringParameterValue,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION

default_parameter_values: dict[str, DecimalParameterValue | StringParameterValue] = {
    denomination_module.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=DEFAULT_DENOMINATION
    ),
    maximum_single_deposit.MAXIMUM_SINGLE_DEPOSIT_PARAM.id: DecimalParameterValue(
        decimal_value=Decimal(50)
    ),
}
