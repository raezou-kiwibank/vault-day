# standard libs
from decimal import Decimal

import feature_library.common.denomination as denomination

# features
import feature_library.lending.repayments.early_repayment as early_repayment

# inception sdk
from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    DecimalParameterValue,
    StringParameterValue,
)

# simulation
import tests.lending.repayments.early_repayment.simulation.accounts as accounts
from tests.common.test_denomination import DEFAULT_DENOMINATION

vertical_hierarchy_parameter_values = {
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
}

horizontal_hierarchy_parameter_values = {
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
}
