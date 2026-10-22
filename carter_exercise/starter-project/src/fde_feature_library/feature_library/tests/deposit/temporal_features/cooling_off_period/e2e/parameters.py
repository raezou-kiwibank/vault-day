# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# standard libs
from decimal import Decimal

# features
import feature_library.deposit.temporal_features.cooling_off_period as cooling_off_period

# inception sdk
from inception_sdk.vault.core_api import DecimalParameterValue, ParameterValue, StringParameterValue

# tests
from tests.common.test_denomination import DEFAULT_DENOMINATION

parameter_values: dict[str, ParameterValue] = {
    cooling_off_period.denomination_module.DENOMINATION_PARAM_ID: StringParameterValue(
        string_value=DEFAULT_DENOMINATION
    ),
    cooling_off_period.COOLING_OFF_PERIOD_PARAM_ID: DecimalParameterValue(
        decimal_value=Decimal("5")
    ),
}
