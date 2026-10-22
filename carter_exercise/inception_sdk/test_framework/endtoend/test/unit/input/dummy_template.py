# Copyright @ 2021 Thought Machine Group Limited. All rights reserved.

# contracts api
from contracts_api import EventTypesGroup

# inception sdk
from inception_sdk.test_framework.endtoend.test.unit.input import dummy_feature

display_name = "Contract for event type replacement tests"
api = "4.0.0"
version = "1.0.0"
summary = "Contract for event type replacement tests"

event_types = dummy_feature.get_event_types("DUMMY")
event_types_groups = [
    EventTypesGroup(name="group", event_types_order=[event_type for event_type in event_types])
]
