from json import dumps

import feature_library.deposit.dormancy.dormancy as dormancy

from inception_sdk.vault.core_api import ParameterValue, StringParameterValue

parameter_values: dict[str, ParameterValue] = {
    dormancy.DORMANCY_FLAGS_PARAM_ID: StringParameterValue(string_value=dumps(["ACCOUNT_DORMANT"])),
}
