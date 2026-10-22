# Copyright @ 2024 Thought Machine Group Limited. All rights reserved.
# contracts api
from contracts_api import (
    PrePostingHookArguments,
    PrePostingHookResult,
    Rejection,
    RejectionReason,
    Tside,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Contract metadata
api = "4.0.0"
version = "0.0.1"
tside = Tside.ASSET
supported_denominations = ["GBP"]


def pre_posting_hook(
    vault: SmartContractVault, hook_arguments: PrePostingHookArguments
) -> PrePostingHookResult | None:
    if all(
        str(posting_instruction.instruction_details.get("force_override", "false")) == "true"
        for posting_instruction in hook_arguments.posting_instructions
    ):
        return None

    return PrePostingHookResult(
        rejection=Rejection(
            message="supervisee rejection", reason_code=RejectionReason.AGAINST_TNC
        ),
    )
