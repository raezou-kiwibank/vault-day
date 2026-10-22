# contracts api
from contracts_api import (
    DeactivationHookArguments,
    DeactivationHookResult,
    Rejection,
    RejectionReason,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Contract Metadata
api = "4.0.0"
version = "0.0.1"
supported_denominations = ["USD"]


def deactivation_hook(
    vault: SmartContractVault, hook_arguments: DeactivationHookArguments
) -> DeactivationHookResult | None:
    return DeactivationHookResult(
        rejection=Rejection(
            message="Account Deactivation Failed.", reason_code=RejectionReason.AGAINST_TNC
        )
    )
