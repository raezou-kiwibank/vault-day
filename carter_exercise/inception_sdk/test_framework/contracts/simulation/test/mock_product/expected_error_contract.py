# Copyright @ 2024 Thought Machine Group Limited. All rights reserved.
# contracts api
from contracts_api import (
    DeactivationHookArguments,
    DeactivationHookResult,
    Parameter,
    ParameterLevel,
    Rejection,
    RejectionReason,
    StringShape,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Contract Metadata
api = "4.0.0"
version = "0.0.1"

parameters = [
    Parameter(
        name="test_param",
        display_name="test_param",
        shape=StringShape(),
        level=ParameterLevel.INSTANCE,
        default_value="default",
    )
]


def deactivation_hook(
    vault: SmartContractVault, hook_arguments: DeactivationHookArguments
) -> DeactivationHookResult | None:
    return DeactivationHookResult(
        rejection=Rejection(message="always fail", reason_code=RejectionReason.AGAINST_TNC)
    )
