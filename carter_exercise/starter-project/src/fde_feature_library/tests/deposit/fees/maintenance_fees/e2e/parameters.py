import json
from decimal import Decimal

import feature_library.common.denomination as denomination_module
import feature_library.deposit.common as common
import feature_library.deposit.fees.maintenance_fees as maintenance_fees_module

from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    DecimalParameterValue,
    EnumerationParameterValue,
    ParameterValue,
    StringParameterValue,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.deposit.fees.maintenance_fees.e2e.accounts import (
    INCOME_ACCOUNT,
)

default_parameter_values: dict[str, ParameterValue] = {
    maintenance_fees_module.MAINTENANCE_FEE_APPLICATION_DAY_PARAM.id: DecimalParameterValue(
        decimal_value=Decimal("1")
    ),
    maintenance_fees_module.MAINTENANCE_FEE_APPLICATION_TIME_PARAM.id: StringParameterValue(
        string_value="00:00:00"
    ),
    maintenance_fees_module.MONTHLY_MAINTENANCE_FEE_BY_TIER_PARAM.id: StringParameterValue(
        string_value=json.dumps(
            {
                "UPPER_TIER": "20",
                "MIDDLE_TIER": "10",
                "LOWER_TIER": "5",
            }
        )
    ),
    maintenance_fees_module.MONTHLY_MAINTENANCE_FEE_INCOME_ACCOUNT_PARAM.id: AccountIdParameterValue(  # noqa: E501
        account_id_value=INCOME_ACCOUNT
    ),
    maintenance_fees_module.MONTHLY_MAINTENANCE_FEE_PARTIAL_FEE_ENABLED_PARAM.id: EnumerationParameterValue(  # noqa: E501
        enumeration_value="False"
    ),
    maintenance_fees_module.ANNUAL_MAINTENANCE_FEE_BY_TIER_PARAM.id: StringParameterValue(
        string_value=json.dumps(
            {
                "UPPER_TIER": "200",
                "MIDDLE_TIER": "100",
                "LOWER_TIER": "50",
            }
        )
    ),
    maintenance_fees_module.ANNUAL_MAINTENANCE_FEE_INCOME_ACCOUNT_PARAM.id: AccountIdParameterValue(
        account_id_value=INCOME_ACCOUNT
    ),
    common.ACCOUNT_TIER_PARAM.id: StringParameterValue(string_value="LOWER_TIER"),
    denomination_module.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=DEFAULT_DENOMINATION
    ),
}
