# standard libs
from decimal import Decimal

# inception sdk
from inception_sdk.vault.core_api import (
    DecimalParameterValue,
    ParameterValue,
    StringParameterValue,
)

# library
import tests.deposit.transaction_limits.deposit_limits.minimum_initial_deposit.smart_contract as smart_contract  # noqa: E501
from tests.common.test_denomination import DEFAULT_DENOMINATION

# Accounts V2 endpoint requires parameters to be uploaded using the ParameterValue syntax,
# including instance parameters
default_parameter_values: dict[str, ParameterValue] = {
    smart_contract.denomination_module.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    smart_contract.minimum_initial_deposit.MIN_INITIAL_DEPOSIT_PARAM.id: DecimalParameterValue(
        decimal_value=Decimal(20)
    ),
}
