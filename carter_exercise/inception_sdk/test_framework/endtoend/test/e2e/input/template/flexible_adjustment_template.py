# Copyright @ 2025 Thought Machine Group Limited. All rights reserved.

# standard libs
from dateutil.relativedelta import relativedelta
from decimal import Decimal

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    ActivationHookResult,
    AdjustmentCorrectionPoint,
    AdjustmentStrategy,
    BalanceCoordinate,
    BalancesObservationFetcher,
    CustomInstruction,
    DefinedDateTime,
    EventTypesGroup,
    Override,
    Phase,
    Posting,
    PostingInstructionsDirective,
    RelativeDateTime,
    ScheduledEvent,
    ScheduledEventHookArguments,
    ScheduledEventHookResult,
    ScheduleExpression,
    Shift,
    SmartContractAdjustmentEventType,
    SmartContractEventType,
    Tside,
    fetch_account_data,
)

api = "4.0.0"
version = "1.0.0"
tside = Tside.LIABILITY
adjustment_strategy = AdjustmentStrategy.SCHEDULE_TRIGGERED

# Constants
DENOMINATION = "GBP"
ACCRUED_INTEREST_ACCOUNT = "&{ACCRUED_INTEREST_ACCOUNT}"
SCHEDULED_EVENT = "SCHEDULED_EVENT"
ADJUSTMENT_EVENT = "ADJUSTMENT_EVENT"
ACCRUED_INTEREST_PAYABLE_ADDRESS = "ACCRUED_INTEREST_PAYABLE"

event_types = [
    SmartContractAdjustmentEventType(
        name=ADJUSTMENT_EVENT,
        correction_point=AdjustmentCorrectionPoint(
            value_datetime=RelativeDateTime(
                origin=DefinedDateTime.EFFECTIVE_DATETIME,
                find=Override(hour=23, minute=59, second=59),
                shift=Shift(days=-1),
            ),
            booking_datetime=RelativeDateTime(
                origin=DefinedDateTime.ADJUSTMENT_EFFECTIVE_DATETIME,
                find=Override(hour=23, minute=59, second=59),
                shift=Shift(days=-1),
            ),
        ),
    ),
    SmartContractEventType(
        name=SCHEDULED_EVENT,
    ),
]
event_types_groups = [
    EventTypesGroup(
        name="EOD_GROUP",
        event_types_order=[ADJUSTMENT_EVENT, SCHEDULED_EVENT],
    )
]

# Fetchers
BALANCES_OBSERVATION_FETCHER_ID = "BALANCES_OBSERVATION_FETCHER_ID"
BALANCES_OBSERVATION_FETCHER = BalancesObservationFetcher(
    fetcher_id=BALANCES_OBSERVATION_FETCHER_ID,
    at=RelativeDateTime(
        origin=DefinedDateTime.EFFECTIVE_DATETIME,
        find=Override(hour=23, minute=59, second=59),
        shift=Shift(days=-1),
    ),
)
data_fetchers = [
    BALANCES_OBSERVATION_FETCHER,
]


def activation_hook(vault, hook_arguments):
    effective_datetime = hook_arguments.effective_datetime

    return ActivationHookResult(
        scheduled_events_return_value={
            ADJUSTMENT_EVENT: ScheduledEvent(
                start_datetime=effective_datetime + relativedelta(seconds=1),
                expression=ScheduleExpression(hour="1", minute="0", second="0"),
            ),
            SCHEDULED_EVENT: ScheduledEvent(
                start_datetime=effective_datetime + relativedelta(seconds=1),
                expression=ScheduleExpression(hour="2", minute="0", second="0"),
            ),
        },
    )


@fetch_account_data(
    event_type=SCHEDULED_EVENT,
    balances=[BALANCES_OBSERVATION_FETCHER_ID],
)
def scheduled_event_hook(
    vault, hook_arguments: ScheduledEventHookArguments
) -> ScheduledEventHookResult | None:
    balances = vault.get_balances_observation(fetcher_id=BALANCES_OBSERVATION_FETCHER_ID).balances

    balance_coordinate = BalanceCoordinate(
        account_address=DEFAULT_ADDRESS,
        asset=DEFAULT_ASSET,
        denomination=DENOMINATION,
        phase=Phase.COMMITTED,
    )
    net_balance = balances[balance_coordinate].net
    amount = abs(net_balance) * Decimal("0.01")

    if amount > Decimal("0"):
        return ScheduledEventHookResult(
            posting_instructions_directives=[
                PostingInstructionsDirective(
                    posting_instructions=[
                        CustomInstruction(
                            postings=[
                                Posting(
                                    credit=True,
                                    amount=amount,
                                    denomination=DENOMINATION,
                                    account_id=vault.account_id,
                                    account_address=ACCRUED_INTEREST_PAYABLE_ADDRESS,
                                    asset=DEFAULT_ASSET,
                                    phase=Phase.COMMITTED,
                                ),
                                Posting(
                                    credit=False,
                                    amount=amount,
                                    denomination=DENOMINATION,
                                    account_id=ACCRUED_INTEREST_ACCOUNT,
                                    account_address=DEFAULT_ADDRESS,
                                    asset=DEFAULT_ASSET,
                                    phase=Phase.COMMITTED,
                                ),
                            ],
                        )
                    ],
                    value_datetime=hook_arguments.effective_datetime.replace(
                        hour=23, minute=59, second=59, microsecond=0
                    )
                    - relativedelta(days=1),
                    booking_datetime=hook_arguments.effective_datetime.replace(
                        hour=23, minute=59, second=59, microsecond=0
                    )
                    - relativedelta(days=1),
                )
            ]
        )
    return None
