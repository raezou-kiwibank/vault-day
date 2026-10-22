import feature_library.common.denomination as denomination
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.lending.fetchers as lending_fetchers
import feature_library.lending.interest.interest_accrual as interest_accrual
import feature_library.lending.interest.secondary.variable_rate as variable_rate

from contracts_api import (
    ActivationHookArguments,
    ActivationHookResult,
    PostingInstructionsDirective,
    ScheduledEventHookArguments,
    ScheduledEventHookResult,
    SmartContractEventType,
    Tside,
    fetch_account_data,
)

from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

api = "4.0.0"
version = "1.0.0"
display_name = "Variable Rate Interest Accrual Simulation Contract"
summary = "Simulation contract for testing variable rate interest accrual"
tside = Tside.ASSET

# Required for simulation
expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *interest_accrual.expected_parameters,
        *variable_rate.expected_parameters,
        *denomination.expected_parameters,
    ]
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *interest_accrual.data_fetchers,
        *variable_rate.data_fetchers,
        *denomination.data_fetchers,
        *lending_fetchers.data_fetchers,
    ]
)

event_types = [
    SmartContractEventType(name=interest_accrual.ACCRUAL_EVENT),
]


@fetch_account_data(
    parameters=[
        interest_accrual.PARAM_ET_POF_ID,
    ]
)
def activation_hook(
    vault: SmartContractVault, hook_arguments: ActivationHookArguments
) -> ActivationHookResult | None:
    state = state_utils.initialise_state(vault, hook_arguments.effective_datetime)

    scheduled_events = interest_accrual.get_scheduled_events(state)
    return ActivationHookResult(scheduled_events_return_value=scheduled_events)


@fetch_account_data(
    event_type=interest_accrual.ACCRUAL_EVENT,
    parameters=[
        interest_accrual.PARAM_ET_POF_ID,
        variable_rate.VARIABLE_RATE_ET_POF_ID,
        denomination.DENOMINATION_ET_POF_ID,
    ],
    balances=[lending_fetchers.PRINCIPAL_ET_BOF_ID],
)
def scheduled_event_hook(
    vault: SmartContractVault, hook_arguments: ScheduledEventHookArguments
) -> ScheduledEventHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination.get_parameters(vault),
    )

    custom_instructions = []
    if hook_arguments.event_type == interest_accrual.ACCRUAL_EVENT:

        def _get_annual_interest_rate(
            state, fetchers_config=variable_rate.DEFAULT_VARIABLE_RATE_FETCHERS_CONFIG
        ):
            return variable_rate.get_annual_interest_rate(
                state=state, fetchers_config=fetchers_config
            )

        custom_instructions = interest_accrual.schedule_logic(
            state=state, get_annual_interest_rate=_get_annual_interest_rate, account_type="LOAN"
        )

    return ScheduledEventHookResult(
        posting_instructions_directives=(
            [
                PostingInstructionsDirective(
                    posting_instructions=custom_instructions,
                    value_datetime=hook_arguments.effective_datetime,
                )
            ]
            if custom_instructions
            else None
        )
    )
