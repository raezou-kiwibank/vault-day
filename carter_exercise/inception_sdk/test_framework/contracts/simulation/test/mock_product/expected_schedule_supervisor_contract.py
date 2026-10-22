# Copyright @ 2024 Thought Machine Group Limited. All rights reserved.
# contracts api
from contracts_api import (
    ScheduledEvent,
    ScheduleExpression,
    SmartContractDescriptor,
    SupervisorActivationHookArguments,
    SupervisorActivationHookResult,
    SupervisorContractEventType,
    SupervisorScheduledEventHookArguments,
    SupervisorScheduledEventHookResult,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import (
    SupervisorContractVault,
)

# Supervisor metadata
api = "4.0.0"
version = "0.0.1"


# Supervisees
supervised_smart_contracts = [
    SmartContractDescriptor(
        alias="supervisee",
        smart_contract_version_id="&{supervisee}",
        supervise_post_posting_hook=False,
    ),
]

# Events
OVERRIDING_EVENT = "OVERRIDING_EVENT"
NON_OVERRIDING_EVENT = "NON_OVERRIDING_EVENT"
event_types = [
    SupervisorContractEventType(
        name=OVERRIDING_EVENT,
        overrides_event_types=[
            ("supervisee", "EVENT_TO_OVERRIDE"),
        ],
    ),
    SupervisorContractEventType(name=NON_OVERRIDING_EVENT),
]


def activation_hook(
    vault: SupervisorContractVault, hook_arguments: SupervisorActivationHookArguments
) -> SupervisorActivationHookResult | None:
    plan_opening_datetime = vault.get_plan_opening_datetime()

    scheduled_events: dict[str, ScheduledEvent] = {
        OVERRIDING_EVENT: ScheduledEvent(
            start_datetime=plan_opening_datetime,
            expression=ScheduleExpression(hour=0, minute=0, second=0),
        ),
        NON_OVERRIDING_EVENT: ScheduledEvent(
            start_datetime=plan_opening_datetime,
            expression=ScheduleExpression(hour=1, minute=0, second=0),
        ),
    }

    return SupervisorActivationHookResult(scheduled_events_return_value=scheduled_events)


def scheduled_event_hook(
    vault: SupervisorContractVault, hook_arguments: SupervisorScheduledEventHookArguments
) -> SupervisorScheduledEventHookResult | None:
    return None
