# Copyright @ 2024 Thought Machine Group Limited. All rights reserved.
# contracts api
from contracts_api import (
    Parameter,
    ParameterLevel,
    ParameterUpdatePermission,
    PreParameterChangeHookArguments,
    PreParameterChangeHookResult,
    Rejection,
    RejectionReason,
    StringShape,
    Tside,
    requires,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Contract Metadata
api = "4.0.0"
version = "0.0.1"
tside = Tside.LIABILITY
supported_denominations = ["GBP"]

# Parameters
PARAM_REJECTED = "rejected_param"
PARAM_ACCEPTED = "accepted_param"

parameters = [
    # Instance Parameters
    Parameter(
        name=PARAM_REJECTED,
        shape=StringShape(),
        level=ParameterLevel.INSTANCE,
        description="A parameter to reject updates in test.",
        display_name="Rejected Parameter",
        default_value="rejected",
        update_permission=ParameterUpdatePermission.OPS_EDITABLE,
    ),
    Parameter(
        name=PARAM_ACCEPTED,
        shape=StringShape(),
        level=ParameterLevel.INSTANCE,
        description="A parameter to accept updates in test.",
        display_name="Accepted Parameter",
        default_value="accepted",
        update_permission=ParameterUpdatePermission.OPS_EDITABLE,
    ),
]


@requires(parameters=True)
def pre_parameter_change_hook(
    vault: SmartContractVault, hook_arguments: PreParameterChangeHookArguments
) -> PreParameterChangeHookResult | None:
    updated_parameter_values = hook_arguments.updated_parameter_values
    if PARAM_REJECTED in updated_parameter_values:
        return PreParameterChangeHookResult(
            rejection=Rejection(
                message=(f"Changes to {PARAM_REJECTED} are not allowed."),
                reason_code=RejectionReason.AGAINST_TNC,
            )
        )

    return None
