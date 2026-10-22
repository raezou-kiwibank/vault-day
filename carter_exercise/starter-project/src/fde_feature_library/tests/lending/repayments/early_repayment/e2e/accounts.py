# inception sdk
import inception_sdk.vault.core_api as core_api

CUSTOMER_ACCOUNT = "CUSTOMER_ACCOUNT"
DEPOSIT_ACCOUNT = "DEPOSIT_ACCOUNT"
EARLY_REPAYMENT_FEE_INCOME_ACCOUNT = "EARLY_REPAYMENT_FEE_INCOME"

internal_accounts_tside = {
    core_api.AccountV2TSide.T_SIDE_ASSET: [
        DEPOSIT_ACCOUNT,
    ],
    core_api.AccountV2TSide.T_SIDE_LIABILITY: [
        EARLY_REPAYMENT_FEE_INCOME_ACCOUNT,
    ],
}
