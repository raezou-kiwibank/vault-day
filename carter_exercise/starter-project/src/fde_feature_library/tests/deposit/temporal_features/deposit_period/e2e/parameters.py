# standard libs
from decimal import Decimal

import feature_library.common.denomination as denomination
import feature_library.deposit.temporal_features.deposit_period as deposit_period

# inception sdk
from inception_sdk.vault.core_api import (
    DecimalParameterValue,
    EnumerationParameterValue,
    ParameterValue,
    StringParameterValue,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION

default_parameter_values: dict[str, ParameterValue] = {
    denomination.DENOMINATION_PARAM_ID: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    deposit_period.DEPOSIT_PERIOD_PARAM_ID: DecimalParameterValue(decimal_value=Decimal(7)),
    deposit_period.NUMBER_OF_PERMITTED_DEPOSITS_PARAM_ID: EnumerationParameterValue(
        enumeration_value=deposit_period.UNLIMITED
    ),
}
