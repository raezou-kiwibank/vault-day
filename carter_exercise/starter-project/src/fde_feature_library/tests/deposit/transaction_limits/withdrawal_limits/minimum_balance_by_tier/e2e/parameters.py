# ruff: noqa: E501
import json

import feature_library.common.denomination as denomination_module
import feature_library.deposit.common as withdrawal_limits_common
import feature_library.deposit.transaction_limits.withdrawal_limits.minimum_balance_by_tier as minimum_balance_by_tier  # noqa: E501

from inception_sdk.vault.core_api import (
    ParameterValue,
    StringParameterValue,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION

default_parameter_values: dict[str, ParameterValue] = {
    denomination_module.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    minimum_balance_by_tier.TIERED_MIN_BALANCE_THRESHOLD_PARAM.id: StringParameterValue(
        string_value=json.dumps({"UPPER_TIER": "50", "LOWER_TIER": "10"})
    ),
    withdrawal_limits_common.ACCOUNT_TIER_PARAM.id: StringParameterValue(string_value="UPPER_TIER"),
}
