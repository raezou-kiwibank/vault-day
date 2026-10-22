# Copyright @ 2024 Thought Machine Group Limited. All rights reserved.
# contracts api
from contracts_api import (
    Rejection,
    RejectionReason,
    SmartContractDescriptor,
    SupervisedHooks,
    SupervisionExecutionMode,
    SupervisorPrePostingHookArguments,
    SupervisorPrePostingHookResult,
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
        supervised_hooks=SupervisedHooks(pre_posting_hook=SupervisionExecutionMode.INVOKED),
    ),
]


def pre_posting_hook(
    vault: SupervisorContractVault, hook_arguments: SupervisorPrePostingHookArguments
) -> SupervisorPrePostingHookResult | None:
    # Naive check if force override is set for postings on only one supervisee account here
    if all(
        str(posting_instruction.instruction_details.get("force_override", "false")) == "true"
        for posting_instruction in list(hook_arguments.supervisee_posting_instructions.values())[0]  # type: ignore [attr-defined] # noqa
    ):
        return None

    return SupervisorPrePostingHookResult(
        rejection=Rejection(
            message="supervisor rejection", reason_code=RejectionReason.AGAINST_TNC
        ),
    )
