import feature_library.common.denomination as denomination
import feature_library.common.fetchers as fetchers
import feature_library.common.state_utils as state_utils
import feature_library.deposit.temporal_features.deposit_period as deposit_period

from contracts_api import (
    ActivationHookArguments,
    ActivationHookResult,
    PrePostingHookArguments,
    PrePostingHookResult,
    ScheduledEventHookArguments,
    ScheduledEventHookResult,
    Tside,
    fetch_account_data,
)

from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

api = "4.0.0"
version = "0.0.1"
display_name = "Liability Account with Deposit Period"
summary = "Liability Account with Deposit Period"
tside = Tside.LIABILITY

PRODUCT_NAME = "deposit_period"

notification_types = [
    deposit_period.notification_type(
        product_name=PRODUCT_NAME,
    )
]
event_types = [
    *deposit_period.event_types(product_name=PRODUCT_NAME),
]

expected_parameters = [
    *denomination.expected_parameters,
    *deposit_period.expected_parameters,
]

data_fetchers = [
    *denomination.data_fetchers,
    *deposit_period.data_fetchers,
    *fetchers.data_fetchers,
]


@fetch_account_data(
    parameters=[
        denomination.DENOMINATION_ET_POF_ID,
        deposit_period.DEPOSIT_PERIOD_PARAMS_ET_POF_ID,
    ]
)
def activation_hook(
    vault: SmartContractVault, hook_arguments: ActivationHookArguments
) -> ActivationHookResult | None:
    state = state_utils.initialise_state(
        vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters={
            **denomination.get_parameters(vault),
        },
    )

    scheduled_events = deposit_period.get_scheduled_events(state=state)

    return ActivationHookResult(
        scheduled_events_return_value=scheduled_events,
    )


@fetch_account_data(
    parameters=[
        denomination.DENOMINATION_ET_POF_ID,
        deposit_period.DEPOSIT_PERIOD_PARAMS_ET_POF_ID,
    ],
    balances=[fetchers.ALL_BALANCES_ET_BOF_ID],
)
def pre_posting_hook(
    vault: SmartContractVault, hook_arguments: PrePostingHookArguments
) -> PrePostingHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters={
            **denomination.get_parameters(vault),
        },
        balances=vault.get_balances_observation(
            fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID
        ).balances,
    )

    if rejection := deposit_period.validate(
        state=state, posting_instructions=hook_arguments.posting_instructions
    ):
        return PrePostingHookResult(rejection=rejection)

    return PrePostingHookResult()


@fetch_account_data(
    event_type=deposit_period.DEPOSIT_PERIOD_END_EVENT,
    parameters=[
        denomination.DENOMINATION_ET_POF_ID,
        deposit_period.DEPOSIT_PERIOD_PARAMS_ET_POF_ID,
    ],
    balances=[fetchers.ALL_BALANCES_ET_BOF_ID],
)
def scheduled_event_hook(
    vault: SmartContractVault, hook_arguments: ScheduledEventHookArguments
) -> ScheduledEventHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters={
            **denomination.get_parameters(vault),
            **deposit_period.get_parameters(vault),
        },
        balances=vault.get_balances_observation(
            fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID
        ).balances,
    )

    event_type = hook_arguments.event_type

    if event_type == deposit_period.DEPOSIT_PERIOD_END_EVENT:
        notification_directives = deposit_period.schedule_logic(
            state=state, product_name=PRODUCT_NAME
        )

        return ScheduledEventHookResult(
            account_notification_directives=(
                notification_directives if notification_directives else None
            )
        )

    return None
