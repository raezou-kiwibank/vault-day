import inception_sdk.vault.core_api as core_api

CUSTOMER_ACCOUNT = "CUSTOMER_ACCOUNT"
PAYMENT_TYPE_FEE_INCOME_ACCOUNT = "PAY_TYPE_FEE_INCOME_ACC"

internal_accounts_tside = {
    core_api.AccountV2TSide.T_SIDE_ASSET: [],
    core_api.AccountV2TSide.T_SIDE_LIABILITY: [PAYMENT_TYPE_FEE_INCOME_ACCOUNT],
}
