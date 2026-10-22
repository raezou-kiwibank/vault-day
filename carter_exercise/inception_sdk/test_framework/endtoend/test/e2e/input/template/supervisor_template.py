# Copyright @ 2023 Thought Machine Group Limited. All rights reserved.

# standard libs
from decimal import Decimal
from typing import Optional

# contracts api
from contracts_api import (
    PostingInstructionsDirective,
    SupervisorActivationHookArguments,
    SupervisorActivationHookResult,
    SupervisorContractEventType,
    SupervisorScheduledEventHookArguments,
    SupervisorScheduledEventHookResult,
    fetch_account_data,
)

# inception sdk
import inception_sdk.test_framework.endtoend.test.e2e.input.feature as feature
from inception_sdk.vault.contracts.extensions.contracts_api_extensions.vault_types import (
    SupervisorContractVault,
)

api = "4.0.0"
version = "1.0.0"


event_types = [
    SupervisorContractEventType(
        name="ACCRUE_OFFSET_INTEREST",
    ),
    SupervisorContractEventType(name="ACCRUE_FEES", scheduler_tag_ids=["ACCRUE_FEES_AST"]),
]


def activation_hook(
    vault: SupervisorContractVault, hook_arguments: SupervisorActivationHookArguments
) -> Optional[SupervisorActivationHookResult]:
    return SupervisorActivationHookResult(
        scheduled_events_return_value={
            "ACCRUE_OFFSET_INTEREST": feature.schedules(
                start_datetime=hook_arguments.effective_datetime
            ),
            "ACCRUE_FEES": feature.schedules(start_datetime=hook_arguments.effective_datetime),
        }
    )


# @fetch_account_data(event)
def scheduled_event_hook(
    vault: SupervisorContractVault, hook_arguments: SupervisorScheduledEventHookArguments
) -> Optional[SupervisorScheduledEventHookResult]:
    posting_directives = {
        account_id: [
            PostingInstructionsDirective(
                posting_instructions=feature.posting_logic(
                    supervisee_vault.account_id, amount=Decimal("2")
                )
            )
        ]
        for account_id, supervisee_vault in vault.supervisees.items()
    }

    return SupervisorScheduledEventHookResult(
        supervisee_posting_instructions_directives=posting_directives
    )


# flake8: noqa
