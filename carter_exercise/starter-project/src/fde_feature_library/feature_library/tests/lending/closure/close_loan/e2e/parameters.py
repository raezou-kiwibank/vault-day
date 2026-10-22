# inception sdk
# features
import feature_library.common.denomination as denomination

from inception_sdk.vault.core_api import (
    ParameterValue,
    StringParameterValue,
)

# e2e
from tests.common.test_denomination import DEFAULT_DENOMINATION

parameter_values: dict[str, ParameterValue] = {
    denomination.DENOMINATION_PARAM_ID: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
}
