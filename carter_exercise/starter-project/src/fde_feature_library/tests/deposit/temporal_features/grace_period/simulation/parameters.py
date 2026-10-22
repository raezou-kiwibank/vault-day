# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
from decimal import Decimal

import feature_library.common.denomination as denomination_module
import feature_library.deposit.temporal_features.grace_period as grace_period

from inception_sdk.vault.core_api import DecimalParameterValue, ParameterValue, StringParameterValue

import tests.deposit.temporal_features.grace_period.smart_contract as smart_contract
from tests.common.test_denomination import DEFAULT_DENOMINATION

parameter_values: dict[str, ParameterValue] = {
    denomination_module.DENOMINATION_PARAM_ID: StringParameterValue(
        string_value=DEFAULT_DENOMINATION
    ),
    grace_period.GRACE_PERIOD_PARAM_ID: DecimalParameterValue(decimal_value=Decimal("5")),
    smart_contract.TERM_PARAM_ID: DecimalParameterValue(decimal_value=Decimal(12)),
}
