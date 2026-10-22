# contracts api
from contracts_api import AdjustmentStrategy, ScheduledEventHookArguments, SmartContractEventType

api = "4.0.0"
version = "1.0.1"

adjustment_strategy = AdjustmentStrategy.SCHEDULE_TRIGGERED
event_types = [SmartContractEventType(name="event_noop", adjustment_point=True)]


def scheduled_event_hook(vault, hook_arguments: ScheduledEventHookArguments) -> None:
    return None
