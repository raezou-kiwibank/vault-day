# standard libs
from decimal import Decimal

import feature_library.common.denomination as denomination

# features
import feature_library.lending.repayments.late_repayment as late_repayment

# inception sdk
from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    DecimalParameterValue,
    ParameterValue,
    StringParameterValue,
)

# simulation
import tests.lending.repayments.late_repayment.simulation.accounts as accounts
from tests.common.test_denomination import DEFAULT_DENOMINATION

parameter_values: dict[str, ParameterValue] = {
    denomination.DENOMINATION_PARAM_ID: StringParameterValue(string_value=DEFAULT_DENOMINATION),
    late_repayment.LATE_REPAYMENT_FEE_INCOME_ACCOUNT_PARAM_ID: AccountIdParameterValue(
        account_id_value=accounts.LATE_REPAYMENT_FEE_INCOME_ACCOUNT
    ),
    late_repayment.LATE_REPAYMENT_FEE_PARAM_ID: DecimalParameterValue(
        decimal_value=Decimal("25.00")
    ),
    late_repayment.CHECK_LATE_REPAYMENT_TIME_PARAM_ID: StringParameterValue(
        string_value="00:00:00"
    ),
}
