# standard libs
from decimal import Decimal

# features
import feature_library.common.denomination as denomination_module

# inception sdk
from feature_library.deposit.fees.overdraft_limit import (
    ARRANGED_OVERDRAFT_AMOUNT_PARAM,
    UNARRANGED_OVERDRAFT_AMOUNT_PARAM,
)
from feature_library.deposit.fees.unarranged_overdraft_fee import (
    UNARRANGED_OVERDRAFT_FEE_ACCRUAL_TIME_PARAM,
    UNARRANGED_OVERDRAFT_FEE_APPLICATION_DAY_PARAM,
    UNARRANGED_OVERDRAFT_FEE_APPLICATION_TIME_PARAM,
    UNARRANGED_OVERDRAFT_FEE_CAP_PARAM,
    UNARRANGED_OVERDRAFT_FEE_INCOME_ACCOUNT_PARAM,
    UNARRANGED_OVERDRAFT_FEE_PARAM,
    UNARRANGED_OVERDRAFT_FEE_RECEIVABLE_ACCOUNT_PARAM,
)

from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    DecimalParameterValue,
    ParameterValue,
    StringParameterValue,
)

from tests.common.test_denomination import DEFAULT_DENOMINATION

INCOME_ACCOUNT = "UNARRANGED_OVERDRAFT_FEE_INCM_ACCT"
RECEIVABLE_ACCOUNT = "UNARRANGED_OVERDRAFT_FEE_RCVBL_ACCT"

default_parameter_values: dict[str, ParameterValue] = {
    denomination_module.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=DEFAULT_DENOMINATION
    ),
    UNARRANGED_OVERDRAFT_FEE_PARAM.id: DecimalParameterValue(decimal_value=Decimal("5.00")),
    UNARRANGED_OVERDRAFT_FEE_CAP_PARAM.id: DecimalParameterValue(decimal_value=Decimal("30.00")),
    UNARRANGED_OVERDRAFT_FEE_INCOME_ACCOUNT_PARAM.id: AccountIdParameterValue(
        account_id_value=INCOME_ACCOUNT
    ),
    UNARRANGED_OVERDRAFT_FEE_RECEIVABLE_ACCOUNT_PARAM.id: AccountIdParameterValue(
        account_id_value=RECEIVABLE_ACCOUNT
    ),
    ARRANGED_OVERDRAFT_AMOUNT_PARAM.id: DecimalParameterValue(decimal_value=Decimal("100.00")),
    UNARRANGED_OVERDRAFT_AMOUNT_PARAM.id: DecimalParameterValue(decimal_value=Decimal("300.00")),
    UNARRANGED_OVERDRAFT_FEE_ACCRUAL_TIME_PARAM.id: StringParameterValue(string_value="00:00:01"),
    UNARRANGED_OVERDRAFT_FEE_APPLICATION_DAY_PARAM.id: DecimalParameterValue(
        decimal_value=Decimal(1)
    ),
    UNARRANGED_OVERDRAFT_FEE_APPLICATION_TIME_PARAM.id: StringParameterValue(
        string_value="00:00:01"
    ),
}
