import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.state_utils as state_utils
import feature_library.lending.interest.credit_card_interest_accrual as interest_accrual

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
display_name = "Credit Card with Interest Accrual"
summary = "Credit Card with Interest Accrual"
tside = Tside.ASSET

PRODUCT_NAME = "credit_card_interest_accrual"

expected_parameters = [
    *denomination_module.expected_parameters,
    *interest_accrual.expected_parameters,
]

data_fetchers = [
    *denomination_module.data_fetchers,
    *interest_accrual.data_fetchers,
]

event_types = [
    *interest_accrual.event_types,
]


@fetch_account_data(
    parameters=[
        interest_accrual.INTEREST_ACCRUAL_POF_ID,
    ]
)
def activation_hook(
    vault: SmartContractVault, hook_arguments: ActivationHookArguments
) -> ActivationHookResult | None:
    state = state_utils.initialise_state(
        vault,
        effective_datetime=hook_arguments.effective_datetime,
    )

    scheduled_events = interest_accrual.get_scheduled_events(state)
    return ActivationHookResult(
        scheduled_events_return_value=scheduled_events,
    )


@fetch_account_data(
    event_type=interest_accrual.ACCRUAL_EVENT,
    parameters=[
        denomination_module.DENOMINATION_ET_POF_ID,
        interest_accrual.INTEREST_ACCRUAL_POF_ID,
    ],
    balances=[fetchers.EFFECTIVE_DATE_BOF_ID],
)
def scheduled_event_hook(
    vault: SmartContractVault, hook_arguments: ScheduledEventHookArguments
) -> ScheduledEventHookResult | None:
    state: state_utils.SmartContractState = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination_module.get_parameters(vault),
        balances=vault.get_balances_observation(fetcher_id=fetchers.EFFECTIVE_DATE_BOF_ID).balances,
    )

    if hook_arguments.event_type == interest_accrual.ACCRUAL_EVENT:
        accrual_instructions = interest_accrual.schedule_logic(
            state=state,
            account_type=PRODUCT_NAME,
        )

        if accrual_instructions:
            return ScheduledEventHookResult(
                posting_instructions_directives=[
                    PostingInstructionsDirective(
                        posting_instructions=accrual_instructions,
                        value_datetime=hook_arguments.effective_datetime,
                    )
                ]
            )

    return None
