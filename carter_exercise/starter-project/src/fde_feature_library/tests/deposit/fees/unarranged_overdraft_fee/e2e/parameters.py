from decimal import Decimal

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
    StringParameterValue,
)

import tests.deposit.fees.paper_statement.e2e.invalid_smart_contract as smart_contract
from tests.common.test_denomination import DEFAULT_DENOMINATION
from tests.deposit.fees.unarranged_overdraft_fee.e2e.accounts import (
    INCOME_ACCOUNT,
    RECEIVABLE_ACCOUNT,
)

default_parameter_values = {
    smart_contract.denomination_module.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
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
        decimal_value=Decimal("1")
    ),
    UNARRANGED_OVERDRAFT_FEE_APPLICATION_TIME_PARAM.id: StringParameterValue(
        string_value="00:00:01"
    ),
}
