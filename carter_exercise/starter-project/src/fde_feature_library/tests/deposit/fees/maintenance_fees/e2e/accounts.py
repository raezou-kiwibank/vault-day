# inception sdk
import inception_sdk.vault.core_api as core_api

CUSTOMER_ACCOUNT = "CUSTOMER_ACCOUNT"
DUMMY_INTERNAL_ACCOUNT = "1"
INCOME_ACCOUNT = "INCOME_ACCOUNT"

internal_accounts_tside = {
    core_api.AccountV2TSide.T_SIDE_ASSET: [],
    core_api.AccountV2TSide.T_SIDE_LIABILITY: [
        DUMMY_INTERNAL_ACCOUNT,
        INCOME_ACCOUNT,
    ],
}
