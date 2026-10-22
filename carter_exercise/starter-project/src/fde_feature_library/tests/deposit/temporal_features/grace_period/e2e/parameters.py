# standard libs
from decimal import Decimal

# features
import feature_library.common.denomination as denomination
import feature_library.deposit.temporal_features.grace_period as grace_period

# inception sdk
from inception_sdk.vault.core_api import (
    DecimalParameterValue,
    ParameterValue,
    StringParameterValue,
)

# tests
import tests.deposit.temporal_features.grace_period.smart_contract as smart_contract

# e2e
from tests.common.test_denomination import DEFAULT_DENOMINATION

parameter_values: dict[str, ParameterValue] = {
    denomination.DENOMINATION_PARAM_ID: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    grace_period.GRACE_PERIOD_PARAM_ID: DecimalParameterValue(
        decimal_value=Decimal("5"),
    ),
    smart_contract.TERM_PARAM_ID: DecimalParameterValue(
        decimal_value=Decimal("12"),
    ),
}
