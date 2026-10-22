# standard libs
from decimal import Decimal

import feature_library.common.denomination as denomination

# features
import feature_library.lending.repayments.overpayment as overpayment
import feature_library.lending.repayments.overpayment_allowance as overpayment_allowance

# inception sdk
from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    DecimalParameterValue,
    StringParameterValue,
)

# simulation
import tests.lending.repayments.overpayment_allowance.simulation.accounts as accounts
from tests.common.test_denomination import DEFAULT_DENOMINATION

parameter_values = {
    denomination.DENOMINATION_PARAM_ID: StringParameterValue(string_value=DEFAULT_DENOMINATION),
    overpayment_allowance.OVERPAYMENT_ALLOWANCE_PERCENTAGE_PARAM_ID: DecimalParameterValue(
        decimal_value=Decimal("0.10")
    ),
    overpayment_allowance.OVERPAYMENT_ALLOWANCE_FEE_PERCENTAGE_PARAM_ID: DecimalParameterValue(
        decimal_value=Decimal("0.05")
    ),
    overpayment_allowance.OVERPAYMENT_ALLOWANCE_FEE_INCOME_ACCOUNT_PARAM_ID: AccountIdParameterValue(
        account_id_value=accounts.OVERPAYMENT_ALLOWANCE_FEE_INCOME_ACCOUNT
    ),
    overpayment_allowance.CHECK_OVERPAYMENT_ALLOWANCE_TIME_PARAM_ID: StringParameterValue(
        string_value="00:00:00"
    ),
    overpayment.OVERPAYMENT_FEE_RATE_PARAM_ID: DecimalParameterValue(decimal_value=Decimal("0.0")),
    overpayment.OVERPAYMENT_FEE_INCOME_ACCOUNT_PARAM_ID: AccountIdParameterValue(
        account_id_value=accounts.OVERPAYMENT_ALLOWANCE_FEE_INCOME_ACCOUNT
    ),
    overpayment.OVERPAYMENT_IMPACT_PREFERENCE_PARAM_ID: StringParameterValue(
        string_value="reduce_term"
    ),
}
