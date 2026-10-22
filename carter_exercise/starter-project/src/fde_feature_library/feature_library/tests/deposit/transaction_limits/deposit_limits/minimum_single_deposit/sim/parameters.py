from decimal import Decimal

import feature_library.common.denomination as denomination_module
import feature_library.deposit.transaction_limits.deposit_limits.minimum_single_deposit as minimum_single_deposit  # noqa: E501

from inception_sdk.vault.core_api import (
    DecimalParameterValue,
    StringParameterValue,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION

default_parameter_values: dict[str, DecimalParameterValue | StringParameterValue] = {
    denomination_module.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=DEFAULT_DENOMINATION
    ),
    minimum_single_deposit.MINIMUM_SINGLE_DEPOSIT_PARAM.id: DecimalParameterValue(
        decimal_value=Decimal(10)
    ),
}
