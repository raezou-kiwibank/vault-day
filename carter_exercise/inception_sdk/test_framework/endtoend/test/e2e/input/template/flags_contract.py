# Copyright @ 2024 Thought Machine Group Limited. All rights reserved.

# standard libs
from typing import Any, Optional

# contracts api
from contracts_api import (
    AccountNotificationDirective,
    ActivationHookArguments,
    ActivationHookResult,
    DefinedDateTime,
    FlagsObservation,
    FlagsObservationFetcher,
    PostPostingHookArguments,
    PostPostingHookResult,
    fetch_account_data,
    requires,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions.vault_types import (
    SmartContractVault,
)

api = "4.0.0"
version = "1.0.0"

DO_SOMETHING_FLAG = "&{DO_SOMETHING_FLAG}"
FLAGS_FETCHER_ID = "flag_effective_datetime_obs_fetcher"
flags_fetcher = FlagsObservationFetcher(
    fetcher_id=FLAGS_FETCHER_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
)

data_fetchers: list[Any] = [
    flags_fetcher,
]

SOME_NOTIFICATION = "some_notification"
notification_types = [SOME_NOTIFICATION]


def activation_hook(
    vault: SmartContractVault, hook_arguments: ActivationHookArguments
) -> Optional[ActivationHookResult]:
    return ActivationHookResult()


@fetch_account_data(flags=[FLAGS_FETCHER_ID])
@requires(parameters=True)
def post_posting_hook(
    vault: SmartContractVault,
    hook_arguments: PostPostingHookArguments,
) -> Optional[PostPostingHookResult]:
    flags_obs: FlagsObservation = vault.get_flags_observation(fetcher_id=flags_fetcher.fetcher_id)
    flags: dict[str, bool] = flags_obs.flags
    return PostPostingHookResult(
        account_notification_directives=[
            AccountNotificationDirective(
                notification_type=SOME_NOTIFICATION,
                notification_details={
                    "DO_SOMETHING_FLAG": str(flags.get(DO_SOMETHING_FLAG, "undefined")),
                },
            )
        ]
    )
