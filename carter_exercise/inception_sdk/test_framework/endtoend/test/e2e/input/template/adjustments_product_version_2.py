# standard libs
from dateutil.relativedelta import relativedelta
from decimal import Decimal

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    AccountConstraint,
    ActivationHookArguments,
    ActivationHookResult,
    AdjustmentStrategy,
    CustomInstruction,
    DefinedDateTime,
    ExpectedParameter,
    ParametersObservationFetcher,
    Phase,
    Posting,
    PostingInstructionsDirective,
    PostPostingAdjustmentHookArguments,
    PostPostingAdjustmentHookResult,
    ScheduledEvent,
    ScheduledEventHookArguments,
    ScheduleExpression,
    SmartContractEventType,
    Tside,
    fetch_account_data,
)

api = "4.0.0"
version = "1.0.1"
tside = Tside.LIABILITY
adjustment_strategy = AdjustmentStrategy.SCHEDULE_TRIGGERED

# Event Types
SCHEDULED_EVENT = "SCHEDULED_EVENT_1"
event_types = [SmartContractEventType(name=SCHEDULED_EVENT, adjustment_point=True)]

# Parameters
PARAM_ADJUSTMENTS_INTERNAL_ACCOUNT = "&{ADJUSTMENTS_INTERNAL_ACCOUNT}"

expected_parameters = [
    ExpectedParameter(
        id=PARAM_ADJUSTMENTS_INTERNAL_ACCOUNT,
        constraint=AccountConstraint(),
    )
]

# Fetchers
EFFECTIVE_PARAMETERS_OF_ID = "EFFECTIVE_PARAMETERS_OF"
EFFECTIVE_PARAMETERS_OF = ParametersObservationFetcher(
    fetcher_id=EFFECTIVE_PARAMETERS_OF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
)

data_fetchers = [
    EFFECTIVE_PARAMETERS_OF,
]


def activation_hook(vault, hook_arguments: ActivationHookArguments) -> ActivationHookResult | None:
    return ActivationHookResult(
        scheduled_events_return_value={
            SCHEDULED_EVENT: ScheduledEvent(
                start_datetime=hook_arguments.effective_datetime + relativedelta(seconds=1),
                expression=ScheduleExpression(hour="*"),
            ),
        }
    )


def scheduled_event_hook(vault, hook_arguments: ScheduledEventHookArguments) -> None:
    return None


@fetch_account_data(
    parameters=[EFFECTIVE_PARAMETERS_OF_ID],
)
def post_posting_hook(vault, hook_arguments):
    return None


def post_posting_adjustment_hook(
    adjusted_vault,
    snapshot_vault,
    hook_arguments: PostPostingAdjustmentHookArguments,
) -> PostPostingAdjustmentHookResult | None:
    parameter_observation = adjusted_vault.get_parameters_observation(
        fetcher_id=EFFECTIVE_PARAMETERS_OF_ID,
    ).parameters
    internal_account_id = str(parameter_observation[PARAM_ADJUSTMENTS_INTERNAL_ACCOUNT])
    return PostPostingAdjustmentHookResult(
        posting_instructions_directives=[
            PostingInstructionsDirective(
                posting_instructions=[
                    CustomInstruction(
                        postings=[
                            Posting(
                                credit=True,
                                amount=Decimal("20"),
                                denomination="GBP",
                                account_id=adjusted_vault.account_id,
                                account_address=DEFAULT_ADDRESS,
                                asset=DEFAULT_ASSET,
                                phase=Phase.COMMITTED,
                            ),
                            Posting(
                                credit=False,
                                amount=Decimal("20"),
                                denomination="GBP",
                                account_id=internal_account_id,
                                account_address=DEFAULT_ADDRESS,
                                asset=DEFAULT_ASSET,
                                phase=Phase.COMMITTED,
                            ),
                        ],
                        instruction_details={"description": "Adjustment Fee: 20 GBP"},
                    )
                ],
                value_datetime=hook_arguments.effective_datetime,
            )
        ]
    )
