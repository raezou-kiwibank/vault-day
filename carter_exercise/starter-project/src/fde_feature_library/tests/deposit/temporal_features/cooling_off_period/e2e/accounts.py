# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
# inception sdk
import inception_sdk.vault.core_api as core_api

INTERNAL_ACCOUNT = "INTERNAL_ACCOUNT"

internal_accounts_tside = {
    core_api.AccountV2TSide.T_SIDE_ASSET: [
        INTERNAL_ACCOUNT,
    ],
}
