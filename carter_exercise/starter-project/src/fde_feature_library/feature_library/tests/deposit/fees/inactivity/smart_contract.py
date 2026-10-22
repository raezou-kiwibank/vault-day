import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.fees.inactivity_fee as inactivity_fee

from contracts_api import (
    ActivationHookArguments,
    ActivationHookResult,
    PostingInstructionsDirective,
    ScheduledEventHookArguments,
    ScheduledEventHookResult,
    Tside,
    fetch_account_data,
)

from inception_sdk.vault.contracts.extensions.contracts_api_extensions.vault_types import (
    SmartContractVault,
)

api = "4.0.0"
version = "0.0.1"
display_name = "Liability Account with Inactivity Fee."
summary = "Liability Account with Inactivity Fee."
tside = Tside.LIABILITY

PRODUCT_NAME = "liability_account_inactivity_fees"

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *denomination_module.expected_parameters,
        *inactivity_fee.expected_parameters,
    ]
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *denomination_module.data_fetchers,
        *inactivity_fee.data_fetchers,
    ]
)

event_types = [
    *inactivity_fee.event_types,
]


@fetch_account_data(
    parameters=[
        inactivity_fee.INACTIVITY_FEE_POF_ID,
    ]
)
def activation_hook(
    vault: SmartContractVault, hook_arguments: ActivationHookArguments
) -> ActivationHookResult | None:
    state = state_utils.initialise_state(
        vault,
        effective_datetime=hook_arguments.effective_datetime,
    )

    scheduled_events = inactivity_fee.get_scheduled_events(state)
    return ActivationHookResult(
        scheduled_events_return_value=scheduled_events,
    )


@fetch_account_data(
    event_type=inactivity_fee.APPLICATION_EVENT,
    parameters=[
        denomination_module.DENOMINATION_ET_POF_ID,
        inactivity_fee.INACTIVITY_FEE_POF_ID,
    ],
    flags=[inactivity_fee.INACTIVITY_FOF_ID],
    balances=[fetchers.ALL_BALANCES_ET_BOF_ID],
)
def scheduled_event_hook(
    vault: SmartContractVault, hook_arguments: ScheduledEventHookArguments
) -> ScheduledEventHookResult | None:
    state: state_utils.SmartContractState = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination_module.get_parameters(vault),
        balances=vault.get_balances_observation(
            fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID
        ).balances,
    )

    if hook_arguments.event_type == inactivity_fee.APPLICATION_EVENT:
        schedule_logic_result = inactivity_fee.schedule_logic(
            state=state,
            account_type=PRODUCT_NAME,
        )

        posting_instructions_directives = []
        if schedule_logic_result.custom_instructions:
            posting_instructions_directives.append(
                PostingInstructionsDirective(
                    posting_instructions=schedule_logic_result.custom_instructions,
                    value_datetime=hook_arguments.effective_datetime,
                )
            )

        return ScheduledEventHookResult(
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=schedule_logic_result.event_type_directives,
        )

    return None
