# Copyright @ 2025 Thought Machine Group Limited. All rights reserved.

# standard libs
from dateutil.relativedelta import relativedelta

# contracts api
from contracts_api import (
    ActivationHookResult,
    AdjustmentStrategy,
    ScheduledEvent,
    ScheduledEventHookArguments,
    ScheduleExpression,
    SmartContractEventType,
    Tside,
)

api = "4.0.0"
version = "1.0.0"
tside = Tside.LIABILITY
adjustment_strategy = AdjustmentStrategy.SCHEDULE_TRIGGERED

# Constants
DENOMINATION = "GBP"
INTERNAL_CONTRA = "INTERNAL_CONTRA"
SCHEDULED_EVENT = "SCHEDULED_EVENT"

event_types = [
    SmartContractEventType(
        name=SCHEDULED_EVENT,
        adjustment_point=True,
    ),
]


def activation_hook(vault, hook_arguments):
    effective_datetime = hook_arguments.effective_datetime

    return ActivationHookResult(
        scheduled_events_return_value={
            SCHEDULED_EVENT: ScheduledEvent(
                start_datetime=effective_datetime,
                end_datetime=effective_datetime + relativedelta(minutes=3),
                expression=ScheduleExpression(minute="*"),
            ),
        },
    )


def scheduled_event_hook(vault, hook_arguments: ScheduledEventHookArguments):
    pass
