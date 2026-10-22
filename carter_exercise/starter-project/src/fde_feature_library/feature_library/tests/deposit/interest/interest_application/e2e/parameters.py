# standard libs
from decimal import Decimal

# inception sdk
from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    DecimalParameterValue,
    EnumerationParameterValue,
    ParameterValue,
    StringParameterValue,
)

import tests.deposit.interest.interest_application.e2e.accounts as accounts
import tests.deposit.interest.interest_application.smart_contract as smart_contract
from tests.common.test_denomination import DEFAULT_DENOMINATION

default_parameter_values: dict[str, ParameterValue] = {
    smart_contract.denomination.DENOMINATION_PARAM.id: StringParameterValue(
        string_value=DEFAULT_DENOMINATION,
    ),
    smart_contract.interest_application.APPLICATION_PRECISION_PARAM_ID: DecimalParameterValue(
        decimal_value=Decimal(2)
    ),
    smart_contract.interest_application.INTEREST_APPLICATION_FREQUENCY_PARAM_ID: (
        EnumerationParameterValue(enumeration_value="monthly")
    ),
    smart_contract.interest_application.INTEREST_PAID_ACCOUNT_PARAM_ID: AccountIdParameterValue(
        account_id_value=accounts.INTEREST_PAID_ACCOUNT
    ),
    smart_contract.interest_application.INTEREST_RECEIVED_ACCOUNT_PARAM_ID: AccountIdParameterValue(
        account_id_value=accounts.INTEREST_RECEIVED_ACCOUNT
    ),
    smart_contract.interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID: (
        AccountIdParameterValue(account_id_value=accounts.ACCRUED_INTEREST_PAYABLE_ACCOUNT)
    ),
    smart_contract.interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID: (
        AccountIdParameterValue(account_id_value=accounts.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT)
    ),
    smart_contract.interest_application.INTEREST_APPLICATION_DAY_PARAM_ID: DecimalParameterValue(
        decimal_value=Decimal(1)
    ),
    smart_contract.interest_application.INTEREST_APPLICATION_TIME_PARAM_ID: StringParameterValue(
        string_value="00:00:01"
    ),
}
