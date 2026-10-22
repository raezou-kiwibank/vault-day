# standard libs
from decimal import Decimal

import feature_library.common.denomination as denomination

# features
import feature_library.lending.repayments.early_repayment as early_repayment
import feature_library.lending.repayments.overpayment as overpayment

# inception sdk
from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    DecimalParameterValue,
    StringParameterValue,
)

# simulation
import tests.lending.repayments.payments.simulation.accounts as accounts
from tests.common.test_denomination import DEFAULT_DENOMINATION

parameter_values = {
    denomination.DENOMINATION_PARAM_ID: StringParameterValue(string_value=DEFAULT_DENOMINATION),
    early_repayment.EARLY_REPAYMENT_FEE_INCOME_ACCOUNT_PARAM_ID: AccountIdParameterValue(
        account_id_value=accounts.EARLY_REPAYMENT_FEE_INCOME_ACCOUNT
    ),
    early_repayment.EARLY_REPAYMENT_FLAT_FEE_PARAM_ID: DecimalParameterValue(
        decimal_value=Decimal("10.00")
    ),
    early_repayment.EARLY_REPAYMENT_FEE_RATE_PARAM_ID: DecimalParameterValue(
        decimal_value=Decimal("0.05")
    ),
    overpayment.OVERPAYMENT_FEE_INCOME_ACCOUNT_PARAM_ID: AccountIdParameterValue(
        account_id_value=accounts.OVERPAYMENT_FEE_INCOME_ACCOUNT
    ),
    overpayment.OVERPAYMENT_FEE_RATE_PARAM_ID: DecimalParameterValue(decimal_value=Decimal("0.05")),
    overpayment.OVERPAYMENT_IMPACT_PREFERENCE_PARAM_ID: StringParameterValue(
        string_value="reduce_term"
    ),
}
