# Copyright @ 2023 Thought Machine Group Limited. All rights reserved.

# standard libs
from decimal import Decimal
from typing import Optional

# contracts api
from contracts_api import (
    ActivationHookArguments,
    ActivationHookResult,
    PostingInstructionsDirective,
    ScheduledEventHookArguments,
    ScheduledEventHookResult,
    SmartContractEventType,
)

# inception sdk
import inception_sdk.test_framework.endtoend.test.e2e.input.feature as feature
from inception_sdk.vault.contracts.extensions.contracts_api_extensions.vault_types import (
    SmartContractVault,
)

api = "4.0.0"
version = "1.0.0"


event_types = [
    SmartContractEventType(
        name="ACCRUE_OFFSET_INTEREST",
    ),
]


def activation_hook(
    vault: SmartContractVault, hook_arguments: ActivationHookArguments
) -> Optional[ActivationHookResult]:
    return ActivationHookResult(
        scheduled_events_return_value={
            "ACCRUE_OFFSET_INTEREST": feature.schedules(
                start_datetime=hook_arguments.effective_datetime
            ),
        }
    )


def scheduled_event_hook(
    vault: SmartContractVault, hook_arguments: ScheduledEventHookArguments
) -> Optional[ScheduledEventHookResult]:
    # We use a different amount in supervisor to distinguish which has run
    posting_directives = [
        PostingInstructionsDirective(
            posting_instructions=feature.posting_logic(vault.account_id, amount=Decimal("0.1"))
        )
    ]

    return ScheduledEventHookResult(posting_instructions_directives=posting_directives)


# flake8: noqa
