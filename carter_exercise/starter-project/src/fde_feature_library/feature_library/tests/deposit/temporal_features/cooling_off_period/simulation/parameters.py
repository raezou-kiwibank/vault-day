# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
from decimal import Decimal

import feature_library.common.denomination as denomination_module
import feature_library.deposit.temporal_features.cooling_off_period as cooling_off_period

from inception_sdk.vault.core_api import DecimalParameterValue, ParameterValue, StringParameterValue

from tests.common.test_denomination import DEFAULT_DENOMINATION

parameter_values: dict[str, ParameterValue] = {
    denomination_module.DENOMINATION_PARAM_ID: StringParameterValue(
        string_value=DEFAULT_DENOMINATION
    ),
    cooling_off_period.COOLING_OFF_PERIOD_PARAM_ID: DecimalParameterValue(
        decimal_value=Decimal("5")
    ),
}
