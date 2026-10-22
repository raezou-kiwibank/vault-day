# Copyright @ 2023 - 2024 Thought Machine Group Limited. All rights reserved.

# standard libs
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from typing import Optional

# contracts api
from contracts_api import (
    ActivationHookArguments,
    ActivationHookResult,
    ScheduledEvent,
    ScheduledEventHookArguments,
    ScheduledEventHookResult,
    ScheduleExpression,
    SmartContractEventType,
    Tside,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions.vault_types import (
    SmartContractVault,
)

api = "4.0.0"
version = "1.0.0"
supported_denominations = ["GBP"]
tside = Tside.LIABILITY

THRICE_EVENT = "THRICE_EVENT"
event_types = [
    SmartContractEventType(
        name=THRICE_EVENT,
    ),
]


def activation_hook(
    vault: SmartContractVault, hook_arguments: ActivationHookArguments
) -> Optional[ActivationHookResult]:
    schedule_time = hook_arguments.effective_datetime
    return ActivationHookResult(
        scheduled_events_return_value={
            THRICE_EVENT: ScheduledEvent(
                start_datetime=hook_arguments.effective_datetime,
                expression=ScheduleExpression(
                    second="0",
                    minute="0/25",
                    hour=schedule_time.hour,
                    day=schedule_time.day,
                    month=schedule_time.month,
                    year=schedule_time.year,
                ),
            )
        }
    )


def scheduled_event_hook(
    vault: SmartContractVault, hook_arguments: ScheduledEventHookArguments
) -> Optional[ScheduledEventHookResult]:
    return None


# flake8: noqa
