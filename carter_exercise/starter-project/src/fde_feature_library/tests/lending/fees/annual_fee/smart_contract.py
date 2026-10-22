# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.

# feature library
import feature_library.lending.fees.annual_fee as annual_fee

# contracts api
from contracts_api import (
    ActivationHookArguments,
    ActivationHookResult,
    DeactivationHookArguments,
    DeactivationHookResult,
    EventTypesGroup,
    PostingInstructionsDirective,
    ScheduledEventHookArguments,
    ScheduledEventHookResult,
    Tside,
    fetch_account_data,
)

# inception sdk

# Contracts API Metadata
api = "4.0.0"
version = "0.0.1"
display_name = "Annual Fee Template"
description = "A template for annual fee"
summary = "Annual Fee"
tside = Tside.ASSET

event_types = [
    *annual_fee.event_types,
]

event_types_groups = [
    EventTypesGroup(
        name="FEES",
        event_types=[
            annual_fee.APPLICATION_EVENT,
        ],
    )
]

# Parameters
expected_parameters = [
    *annual_fee.parameters,
]


@fetch_account_data(
    event_type=annual_fee.APPLICATION_EVENT,
    balances=[annual_fee.interest_application.accrual_module.ACCRUAL_ADDRESS],
)
def scheduled_event_hook(
    vault, hook_arguments: ScheduledEventHookArguments
) -> ScheduledEventHookResult | None:
    event_type = hook_arguments.event_type
    effective_datetime = hook_arguments.effective_datetime

    if event_type == annual_fee.APPLICATION_EVENT:
        apply_fees_instructions = annual_fee.apply_fees(
            vault=vault,
            effective_datetime=effective_datetime,
        )

        if apply_fees_instructions:
            return ScheduledEventHookResult(
                posting_instructions_directives=[
                    PostingInstructionsDirective(
                        posting_instructions=apply_fees_instructions,
                        value_datetime=hook_arguments.effective_datetime,
                    )
                ]
            )

    return None


def activation_hook(vault, hook_arguments: ActivationHookArguments) -> ActivationHookResult | None:
    return None


def deactivation_hook(
    vault, hook_arguments: DeactivationHookArguments
) -> DeactivationHookResult | None:
    return None
