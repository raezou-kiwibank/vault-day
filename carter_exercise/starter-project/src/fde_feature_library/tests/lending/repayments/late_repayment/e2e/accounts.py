# inception sdk
import inception_sdk.vault.core_api as core_api

CUSTOMER_ACCOUNT = "CUSTOMER_ACCOUNT"
DEPOSIT_ACCOUNT = "DEPOSIT_ACCOUNT"
LATE_REPAYMENT_FEE_INCOME = "LATE_REPAYMENT_FEE_INCOME"

internal_accounts_tside = {
    core_api.AccountV2TSide.T_SIDE_ASSET: [
        DEPOSIT_ACCOUNT,
    ],
    core_api.AccountV2TSide.T_SIDE_LIABILITY: [
        LATE_REPAYMENT_FEE_INCOME,
    ],
}
