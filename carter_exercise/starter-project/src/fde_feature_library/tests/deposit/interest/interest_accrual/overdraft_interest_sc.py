import feature_library.common.application_precision as application_precision
import feature_library.common.denomination as denomination
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.interest.interest_accrual as interest_accrual
import feature_library.deposit.interest.secondary.overdraft_interest as overdraft_interest

from contracts_api import (
    ActivationHookArguments,
    ActivationHookResult,
    CustomInstruction,
    PostingInstructionsDirective,
    ScheduledEventHookArguments,
    ScheduledEventHookResult,
    Tside,
    fetch_account_data,
)

from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

api = "4.0.0"
version = "0.0.1"
display_name = "Liability Account with Overdraft Interest Accrual"
summary = "Liability Account with Overdraft Interest Accrual"
tside = Tside.LIABILITY

event_types = [
    *interest_accrual.event_types,
]

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *denomination.expected_parameters,
        *interest_accrual.expected_parameters,
        *overdraft_interest.expected_parameters,
        application_precision.APPLICATION_PRECISION_PARAM,
    ]
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *denomination.data_fetchers,
        *interest_accrual.data_fetchers,
        *overdraft_interest.data_fetchers,
        *fetchers.data_fetchers,
    ]
)


@fetch_account_data(
    parameters=[
        interest_accrual.INTEREST_ACCRUAL_PARAMS_ET_POF_ID,
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
    event_type=interest_accrual.INTEREST_ACCRUAL_EVENT_TYPE,
    parameters=[
        interest_accrual.INTEREST_ACCRUAL_PARAMS_ET_POF_ID,
        overdraft_interest.OVERDRAFT_INTEREST_POF_ID,
        denomination.DENOMINATION_ET_POF_ID,
    ],
    balances=[
        "all_balances_et_bof",
        "one_month_effective_date_fetcher",
    ],
)
def scheduled_event_hook(
    vault: SmartContractVault, hook_arguments: ScheduledEventHookArguments
) -> ScheduledEventHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination.get_parameters(vault),
        balances=vault.get_balances_observation(
            fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID
        ).balances,
    )

    event_type = hook_arguments.event_type

    custom_instructions: list[CustomInstruction] = []

    if event_type == interest_accrual.INTEREST_ACCRUAL_EVENT_TYPE:
        interest_accrual_cis = interest_accrual.schedule_logic(
            state=state,
            interest_types=[
                interest_accrual.InterestTypeConfig(
                    interest_type=overdraft_interest.InterestType,
                    fetchers_config=overdraft_interest.DEFAULT_OVERDRAFT_INTEREST_FETCHERS_CONFIG,
                )
            ],
        )

        custom_instructions.extend(interest_accrual_cis)

    return ScheduledEventHookResult(
        posting_instructions_directives=(
            [
                PostingInstructionsDirective(
                    posting_instructions=custom_instructions,
                    value_datetime=state.effective_datetime,
                )
            ]
            if custom_instructions
            else None
        ),
    )
