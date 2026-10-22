import json
from decimal import Decimal

import feature_library.common.denomination as denomination_module
import feature_library.deposit.common as common
import feature_library.deposit.fees.minimum_monthly_balance as minimum_monthly_balance

from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    DecimalParameterValue,
    EnumerationParameterValue,
    ParameterValue,
    StringParameterValue,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.deposit.fees.minimum_monthly_balance.simulation.accounts import (
    INCOME_ACCOUNT,
)

default_parameter_values: dict[str, ParameterValue] = {
    minimum_monthly_balance.MINIMUM_BALANCE_FEE_PARAM.id: DecimalParameterValue(
        decimal_value=Decimal("5.00")
    ),
    minimum_monthly_balance.MINIMUM_BALANCE_THRESHOLD_BY_TIER_PARAM.id: StringParameterValue(
        string_value=json.dumps(
            {
                "UPPER_TIER": "25",
                "MIDDLE_TIER": "75",
                "LOWER_TIER": "100",
            }
        )
    ),
    minimum_monthly_balance.MINIMUM_BALANCE_FEE_INCOME_ACCOUNT_PARAM.id: AccountIdParameterValue(
        account_id_value=INCOME_ACCOUNT
    ),
    minimum_monthly_balance.MINIMUM_BALANCE_FEE_APPLICATION_DAY_PARAM.id: DecimalParameterValue(
        decimal_value=Decimal("1")
    ),
    minimum_monthly_balance.MINIMUM_BALANCE_FEE_APPLICATION_TIME_PARAM.id: StringParameterValue(
        string_value="00:00:00"
    ),
    minimum_monthly_balance.MINIMUM_BALANCE_PARTIAL_FEE_ENABLED_PARAM.id: EnumerationParameterValue(
        enumeration_value="False"
    ),
    common.ACCOUNT_TIER_PARAM.id: StringParameterValue(string_value="UPPER_TIER"),
    denomination_module.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=DEFAULT_DENOMINATION
    ),
}
