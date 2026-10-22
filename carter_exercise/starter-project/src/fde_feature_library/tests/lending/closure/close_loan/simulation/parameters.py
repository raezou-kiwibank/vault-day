# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
import feature_library.common.denomination as denomination_module

from inception_sdk.vault.core_api import StringParameterValue

from tests.common.test_denomination import DEFAULT_DENOMINATION

parameter_values = {
    denomination_module.DENOMINATION_PARAM_ID: StringParameterValue(
        string_value=DEFAULT_DENOMINATION
    ),
}
