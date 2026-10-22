import feature_library.common.denomination as denomination
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.interest.deposit_interest_accrual_utils as deposit_interest_accrual_utils  # noqa: E501
import feature_library.deposit.interest.interest_accrual as interest_accrual
import feature_library.deposit.interest.secondary.flat_interest as flat_interest

from contracts_api import (
    ActivationHookArguments,
    ActivationHookResult,
    CustomInstruction,
    DeactivationHookArguments,
    DeactivationHookResult,
    PostingInstructionsDirective,
    ScheduledEventHookArguments,
    ScheduledEventHookResult,
    Tside,
    fetch_account_data,
)

from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

api = "4.0.0"
version = "0.0.1"
display_name = "Liability Account with Interest Accrual"
summary = "Liability Account with Interest Accrual"
tside = Tside.LIABILITY

event_types = [
    *interest_accrual.event_types,
]

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *denomination.expected_parameters,
        *interest_accrual.expected_parameters,
        *flat_interest.expected_parameters,
    ]
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *denomination.data_fetchers,
        *interest_accrual.data_fetchers,
        *flat_interest.data_fetchers,
        *fetchers.data_fetchers,
    ]
)


@fetch_account_data(
    parameters=[
        interest_accrual.INTEREST_ACCRUAL_PARAMS_ET_POF_ID,
        denomination.DENOMINATION_ET_POF_ID,
    ]
)
def activation_hook(
    vault: SmartContractVault, hook_arguments: ActivationHookArguments
) -> ActivationHookResult | None:
    state = state_utils.initialise_state(
        vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters={
            **vault.get_parameters_observation(
                fetcher_id=interest_accrual.INTEREST_ACCRUAL_PARAMS_ET_POF_ID
            ).parameters,
            **denomination.get_parameters(vault),
        },
    )

    scheduled_events = interest_accrual.get_scheduled_events(state)

    return ActivationHookResult(
        scheduled_events_return_value=scheduled_events,
    )


@fetch_account_data(
    event_type=interest_accrual.INTEREST_ACCRUAL_EVENT_TYPE,
    parameters=[
        interest_accrual.INTEREST_ACCRUAL_PARAMS_ET_POF_ID,
        flat_interest.FIXED_INTEREST_RATE_ET_POF_ID,
        denomination.DENOMINATION_ET_POF_ID,
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
            **vault.get_parameters_observation(
                fetcher_id=interest_accrual.INTEREST_ACCRUAL_PARAMS_ET_POF_ID
            ).parameters,
            **flat_interest.get_parameters(vault),
            **denomination.get_parameters(vault),
        },
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
                    interest_type=flat_interest.InterestType,
                    fetchers_config=None,
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


@fetch_account_data(
    parameters=[
        interest_accrual.INTEREST_ACCRUAL_PARAMS_ET_POF_ID,
        denomination.DENOMINATION_ET_POF_ID,
    ],
    balances=[fetchers.ALL_BALANCES_ET_BOF_ID],
)
def deactivation_hook(
    vault: SmartContractVault, hook_arguments: DeactivationHookArguments
) -> DeactivationHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters={
            **vault.get_parameters_observation(
                fetcher_id=interest_accrual.INTEREST_ACCRUAL_PARAMS_ET_POF_ID
            ).parameters,
            **denomination.get_parameters(vault),
        },
        balances=vault.get_balances_observation(
            fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID
        ).balances,
    )

    reversal_postings = deposit_interest_accrual_utils.get_interest_reversal_postings(
        state=state,
        event_name="DEACTIVATION",
        accrued_payable_account_param_id=interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID,
        accrued_receivable_account_param_id=interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID,
    )

    return DeactivationHookResult(
        posting_instructions_directives=(
            [
                PostingInstructionsDirective(
                    posting_instructions=reversal_postings,
                    value_datetime=state.effective_datetime,
                )
            ]
            if reversal_postings
            else None
        ),
    )
