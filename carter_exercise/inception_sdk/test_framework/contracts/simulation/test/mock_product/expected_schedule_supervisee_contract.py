# Copyright @ 2024 Thought Machine Group Limited. All rights reserved.
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
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Contract metadata
api = "4.0.0"
version = "0.0.1"
tside = Tside.ASSET
supported_denominations = ["GBP"]


# Events
EVENT_TO_OVERRIDE = "EVENT_TO_OVERRIDE"
EVENT_TO_LEAVE = "EVENT_TO_LEAVE"
event_types = [
    SmartContractEventType(name=EVENT_TO_OVERRIDE),
    SmartContractEventType(name=EVENT_TO_LEAVE),
]


def activation_hook(
    vault: SmartContractVault, hook_arguments: ActivationHookArguments
) -> ActivationHookResult | None:
    account_creation_datetime = vault.get_account_creation_datetime()

    scheduled_events: dict[str, ScheduledEvent] = {
        EVENT_TO_OVERRIDE: ScheduledEvent(
            start_datetime=account_creation_datetime,
            expression=ScheduleExpression(hour=2, minute=0, second=0),
        ),
        EVENT_TO_LEAVE: ScheduledEvent(
            start_datetime=account_creation_datetime,
            expression=ScheduleExpression(hour=3, minute=0, second=0),
        ),
    }

    return ActivationHookResult(scheduled_events_return_value=scheduled_events)


def scheduled_event_hook(
    vault: SmartContractVault, hook_arguments: ScheduledEventHookArguments
) -> ScheduledEventHookResult | None:
    return None
