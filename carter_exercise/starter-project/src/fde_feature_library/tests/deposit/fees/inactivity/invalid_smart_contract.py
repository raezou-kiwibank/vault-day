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
        parameters={},
        balances=vault.get_balances_observation(
            fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID
        ).balances,
    )

    if hook_arguments.event_type == inactivity_fee.APPLICATION_EVENT:
        apply_fees_instructions = inactivity_fee.apply_fees(
            state=state,
            account_type=PRODUCT_NAME,
            fetchers_config=inactivity_fee.InactivityFeeFetchersConfig(
                param_fetcher_id=inactivity_fee.INACTIVITY_FEE_POF_ID,
                flags_fetcher_id=inactivity_fee.INACTIVITY_FOF_ID,
                # This parameter id will not be found and will trigger an error.
                denomination_param_id="missing_denomination",
            ),
        )

        if apply_fees_instructions:
            return ScheduledEventHookResult(
                posting_instructions_directives=[
                    PostingInstructionsDirective(
                        posting_instructions=apply_fees_instructions,
                        value_datetime=hook_arguments.effective_datetime,
                    )
                ]
            )

    return None
