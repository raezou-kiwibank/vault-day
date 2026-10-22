import feature_library.common.denomination as denomination_module
import feature_library.deposit.transaction_limits.withdrawal_limits.maximum_withdrawal_by_payment_type as maximum_withdrawal_by_payment_type  # noqa: E501

from inception_sdk.vault.core_api import (
    ParameterValue,
    StringParameterValue,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION

default_parameter_values: dict[str, ParameterValue] = {
    denomination_module.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    maximum_withdrawal_by_payment_type.MAX_WITHDRAWAL_BY_PAYMENT_TYPE_PARAM.id: StringParameterValue(  # noqa: E501
        string_value='{"ATM": "500"}'
    ),
}
