from decimal import Decimal

import feature_library.common.denomination as denomination
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.lending.interest.interest_accrual as interest_accrual
import feature_library.lending.interest.interest_application as interest_application

from contracts_api import (
    ActivationHookArguments,
    ActivationHookResult,
    CustomInstruction,
    DefinedDateTime,
    EndOfMonthSchedule,
    EventTypesFilter,
    LastScheduledEventDateTimesObservationFetcher,
    ParametersFilter,
    ParametersObservationFetcher,
    PostingInstructionsDirective,
    PostingInstructionType,
    PostPostingHookArguments,
    PostPostingHookResult,
    ScheduledEvent,
    ScheduledEventHookArguments,
    ScheduledEventHookResult,
    SmartContractEventType,
    Tside,
    fetch_account_data,
)

from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

api = "4.0.0"
version = "1.0.0"
tside = Tside.ASSET

APPLICATION_EVENT = "APPLICATION_EVENT"
OVERPAYMENT = "OVERPAYMENT"

APPLICATION_EVENT_SOF_ID = "application_event_sof"
APPLICATION_EVENT_SOF = LastScheduledEventDateTimesObservationFetcher(
    fetcher_id=APPLICATION_EVENT_SOF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=EventTypesFilter(
        event_types=[APPLICATION_EVENT],
    ),
)

ACCRUED_RECEIVABLE_POF_ID = "accrued_receivable_pof"
ACCRUED_RECEIVABLE_POF = ParametersObservationFetcher(
    fetcher_id=ACCRUED_RECEIVABLE_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(
        parameter_ids=[interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID]
    ),
)

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *interest_application.expected_parameters,
        *denomination.expected_parameters,
        interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM,
    ]
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *interest_application.data_fetchers,
        *denomination.data_fetchers,
        APPLICATION_EVENT_SOF,
        ACCRUED_RECEIVABLE_POF,
    ]
)

event_types = [
    SmartContractEventType(name=APPLICATION_EVENT),
]


def activation_hook(
    vault: SmartContractVault, hook_arguments: ActivationHookArguments
) -> ActivationHookResult | None:
    application_event = ScheduledEvent(
        start_datetime=hook_arguments.effective_datetime,
        schedule_method=EndOfMonthSchedule(
            day=28,
            hour=0,
            minute=0,
            second=0,
        ),
    )

    return ActivationHookResult(
        scheduled_events_return_value={
            APPLICATION_EVENT: application_event,
        },
    )


@fetch_account_data(
    event_type=APPLICATION_EVENT,
    parameters=[
        interest_application.INTEREST_APPLICATION_PARAMS_ET_POF_ID,
        denomination.DENOMINATION_ET_POF_ID,
        ACCRUED_RECEIVABLE_POF_ID,
    ],
    balances=[
        interest_application.ACCRUED_INTEREST_ET_BOF_ID,
        interest_application.ACCRUED_INTEREST_ONE_MONTH_AGO_BOF_ID,
    ],
    last_scheduled_event_datetimes=[APPLICATION_EVENT_SOF_ID],
)
def scheduled_event_hook(
    vault: SmartContractVault, hook_arguments: ScheduledEventHookArguments
) -> ScheduledEventHookResult | None:
    params = (
        denomination.get_parameters(vault=vault)
        | vault.get_parameters_observation(fetcher_id=ACCRUED_RECEIVABLE_POF_ID).parameters
    )

    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=params,
    )

    postings = []
    if hook_arguments.event_type == APPLICATION_EVENT:
        previous_application_datetime = (
            vault.get_last_scheduled_event_datetimes_observation(
                fetcher_id=APPLICATION_EVENT_SOF_ID
            ).last_scheduled_event_datetimes.get(APPLICATION_EVENT)
            or vault.get_account_activation_datetime()
        )

        postings = interest_application.apply_interest(
            state=state,
            previous_application_datetime=previous_application_datetime,
        )

    return ScheduledEventHookResult(
        posting_instructions_directives=(
            [
                PostingInstructionsDirective(
                    posting_instructions=[
                        CustomInstruction(
                            postings=postings,
                            instruction_details={"description": "Application postings"},
                        )
                    ],
                )
            ]
            if postings
            else None
        )
    )


@fetch_account_data(
    parameters=[
        interest_application.INTEREST_APPLICATION_PARAMS_ET_POF_ID,
        denomination.DENOMINATION_ET_POF_ID,
        ACCRUED_RECEIVABLE_POF_ID,
    ],
    balances=[
        interest_application.ACCRUED_INTEREST_ET_BOF_ID,
    ],
)
def post_posting_hook(
    vault: SmartContractVault, hook_arguments: PostPostingHookArguments
) -> PostPostingHookResult | None:
    posting = hook_arguments.posting_instructions[0]

    if (
        posting.type == PostingInstructionType.INBOUND_HARD_SETTLEMENT
        and posting.instruction_details.get("description") == OVERPAYMENT
    ):
        params = (
            denomination.get_parameters(vault=vault)
            | vault.get_parameters_observation(fetcher_id=ACCRUED_RECEIVABLE_POF_ID).parameters
        )

        state = state_utils.initialise_state(
            vault=vault,
            effective_datetime=hook_arguments.effective_datetime,
            parameters=params,
        )

        postings = interest_application.repay_accrued_interest(
            state=state,
            repayment_amount=Decimal(posting.amount),
        )

        if not postings:
            return None

        return PostPostingHookResult(
            posting_instructions_directives=[
                PostingInstructionsDirective(
                    posting_instructions=[
                        CustomInstruction(
                            postings=postings,
                            instruction_details={"description": "Repay accrued interest"},
                        )
                    ],
                )
            ]
        )

    return None
