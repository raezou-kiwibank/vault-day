import inception_sdk.vault.core_api as core_api

CUSTOMER_ACCOUNT = "CUSTOMER_ACCOUNT"
DUMMY_INTERNAL_ACCOUNT = "1"

internal_accounts_tside = {
    core_api.AccountV2TSide.T_SIDE_ASSET: [DUMMY_INTERNAL_ACCOUNT],
    core_api.AccountV2TSide.T_SIDE_LIABILITY: [],
}
