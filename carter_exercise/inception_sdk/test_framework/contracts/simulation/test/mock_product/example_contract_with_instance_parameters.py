# fmt: off
# Copyright @ 2021 Thought Machine Group Limited. All rights reserved.
"""
An example that shows required Calendars being declared in a Smart Contract
"""
# standard libs
from decimal import Decimal

# contracts api
from contracts_api import (
    ActivationHookArguments,
    ActivationHookResult,
    DenominationShape,
    NumberShape,
    Parameter,
    ParameterLevel,
    PrePostingHookArguments,
    PrePostingHookResult,
    ScheduledEvent,
    ScheduledEventHookArguments,
    ScheduledEventHookResult,
    ScheduleExpression,
    SmartContractEventType,
    ParameterUpdatePermission,
    requires,
)

display_name = "Contract with Instance Parameters"
api = "4.0.0"
version = "1.0.0"
summary = "Contract with Instance Parameters"
parameters = [
    Parameter(
        name="denomination",  # noqa: CTR007
        shape=DenominationShape(),
        level=ParameterLevel.INSTANCE,
        description="Default denomination for the contract.",
        display_name="Default Denomination.",
        update_permission=ParameterUpdatePermission.USER_EDITABLE,
        default_value="GBP",
    ),
    Parameter(
        name="interest_rate",  # noqa: CTR007
        shape=NumberShape(min_value=0, max_value=1, step=Decimal("0.01")),
        level=ParameterLevel.INSTANCE,
        description="Rate paid on positive balances",
        display_name="Gross Interest Rate",
        update_permission=ParameterUpdatePermission.USER_EDITABLE,
        default_value=Decimal("0"),
    ),
]

# supported_denominations = ["GBP"]

pnl_account = "1"
EVENT_WITH_SINGLE_TAG = "EVENT_WITH_SINGLE_TAG"
event_types = [
    SmartContractEventType(
        name=EVENT_WITH_SINGLE_TAG, scheduler_tag_ids=["AST_1"],
    ),
]


def activation_hook(vault, hook_arguments: ActivationHookArguments) -> ActivationHookResult | None:
    return ActivationHookResult(
        scheduled_events_return_value={
            "EVENT_WITH_SINGLE_TAG": ScheduledEvent(
                start_datetime=hook_arguments.effective_datetime,
                expression=ScheduleExpression(hour=0, minute=0, second=0)
            ),
        }
    )


@requires(
    event_type="EVENT_WITH_SINGLE_TAG",
    parameters=True,
    flags=True,
)
def scheduled_event_hook(
    vault,
    hook_arguments: ScheduledEventHookArguments
) -> ScheduledEventHookResult | None:

    if hook_arguments.event_type == "EVENT_WITH_SINGLE_TAG":
        pass

    return None

@requires(parameters=True)
def pre_posting_hook(vault, hook_arguments: PrePostingHookArguments) -> PrePostingHookResult | None:
    return None

# fmt: on
