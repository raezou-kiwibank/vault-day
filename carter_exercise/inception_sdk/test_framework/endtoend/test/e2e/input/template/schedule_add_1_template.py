# Copyright @ 2023 - 2024 Thought Machine Group Limited. All rights reserved.

# standard libs
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from typing import Optional

# contracts api
from contracts_api import (
    ActivationHookArguments,
    ActivationHookResult,
    BalanceCoordinate,
    BalanceDefaultDict,
    BalancesObservationFetcher,
    CustomInstruction,
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    DefinedDateTime,
    Phase,
    Posting,
    PostingInstructionsDirective,
    ScheduledEvent,
    ScheduledEventHookArguments,
    ScheduledEventHookResult,
    ScheduleExpression,
    SmartContractEventType,
    Tside,
    fetch_account_data,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions.vault_types import (
    SmartContractVault,
)

api = "4.0.0"
version = "1.0.0"
supported_denominations = ["GBP"]
tside = Tside.LIABILITY


EFFECTIVE_OBSERVATION_FETCHER_ID = "EFFECTIVE_FETCHER"
EFFECTIVE_OBSERVATION_FETCHER = BalancesObservationFetcher(
    fetcher_id=EFFECTIVE_OBSERVATION_FETCHER_ID, at=DefinedDateTime.EFFECTIVE_DATETIME
)
data_fetchers = [
    EFFECTIVE_OBSERVATION_FETCHER,
]

ONCE_ONLY_EVENT = "ONCE_ONLY_SCHEDULE"
event_types = [
    SmartContractEventType(
        name=ONCE_ONLY_EVENT,
    ),
]

DENOMINATION = "GBP"
INTERNAL_CONTRA = "INTERNAL_CONTRA"

SCHEDULE_DELTA = relativedelta(minutes=10)


def activation_hook(
    vault: SmartContractVault, hook_arguments: ActivationHookArguments
) -> Optional[ActivationHookResult]:
    schedule_time = hook_arguments.effective_datetime + SCHEDULE_DELTA
    return ActivationHookResult(
        scheduled_events_return_value={
            ONCE_ONLY_EVENT: ScheduledEvent(
                start_datetime=hook_arguments.effective_datetime,
                expression=ScheduleExpression(
                    second=schedule_time.second,
                    minute=schedule_time.minute,
                    hour=schedule_time.hour,
                    day=schedule_time.day,
                    month=schedule_time.month,
                    year=schedule_time.year,
                ),
            )
        }
    )


@fetch_account_data(
    event_type=ONCE_ONLY_EVENT,
    balances=[EFFECTIVE_OBSERVATION_FETCHER_ID],
)
def scheduled_event_hook(
    vault: SmartContractVault, hook_arguments: ScheduledEventHookArguments
) -> Optional[ScheduledEventHookResult]:
    balances: BalanceDefaultDict = vault.get_balances_observation(
        fetcher_id=EFFECTIVE_OBSERVATION_FETCHER_ID
    ).balances
    default_bal = balances[
        BalanceCoordinate(DEFAULT_ADDRESS, DEFAULT_ASSET, DENOMINATION, Phase.COMMITTED)
    ].net
    amount = 2 * default_bal + Decimal(1)
    posting_directives = [
        PostingInstructionsDirective(
            posting_instructions=[
                CustomInstruction(
                    instruction_details={
                        "event": ONCE_ONLY_EVENT,
                        "description": "Add 2x DEFAULT + £1 to DEFAULT balance.",
                    },
                    postings=[
                        Posting(
                            account_address=INTERNAL_CONTRA,
                            account_id=vault.account_id,
                            amount=amount,
                            asset=DEFAULT_ASSET,
                            credit=False,
                            denomination=DENOMINATION,
                            phase=Phase.COMMITTED,
                        ),
                        Posting(
                            account_address=DEFAULT_ADDRESS,
                            account_id=vault.account_id,
                            amount=amount,
                            asset=DEFAULT_ASSET,
                            credit=True,
                            denomination=DENOMINATION,
                            phase=Phase.COMMITTED,
                        ),
                    ],
                )
            ]
        )
    ]

    return ScheduledEventHookResult(posting_instructions_directives=posting_directives)


# flake8: noqa
