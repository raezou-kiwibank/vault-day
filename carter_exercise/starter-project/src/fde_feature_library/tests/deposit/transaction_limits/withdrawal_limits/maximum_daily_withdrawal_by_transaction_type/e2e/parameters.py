import feature_library.common.denomination as denomination_module
import feature_library.deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal_by_transaction_type as maximum_daily_withdrawal_by_transaction_type  # noqa: E501

from inception_sdk.vault.core_api import (
    ParameterValue,
    StringParameterValue,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION

default_parameter_values: dict[str, ParameterValue] = {
    denomination_module.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    maximum_daily_withdrawal_by_transaction_type.DAILY_WITHDRAWAL_LIMIT_BY_TRANSACTION_TYPE_PARAM.id: StringParameterValue(  # noqa: E501
        string_value='{"ATM": "1000"}'
    ),
    maximum_daily_withdrawal_by_transaction_type.TIERED_DAILY_WITHDRAWAL_LIMIT_PARAM.id: StringParameterValue(  # noqa: E501
        string_value='{"UPPER_TIER": {"ATM": "500"}}'
    ),
    "account_tier": StringParameterValue(string_value="UPPER_TIER"),
}
