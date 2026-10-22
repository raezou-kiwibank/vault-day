# inception sdk
import inception_sdk.vault.core_api as core_api

CUSTOMER_ACCOUNT = "CUSTOMER_ACCOUNT"
LOAN_DISBURSEMENT_INTERNAL_ACCOUNT = "LOAN_DISBURSEMENT"

internal_accounts_tside = {
    core_api.AccountV2TSide.T_SIDE_ASSET: [
        LOAN_DISBURSEMENT_INTERNAL_ACCOUNT,
    ],
}
