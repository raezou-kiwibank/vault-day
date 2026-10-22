# Copyright @ 2024 Thought Machine Group Limited. All rights reserved.
"""
This is a contract for testing vault caller and the Simulation API.
"""
# third party
from contract_modules import simple_module  # type: ignore

# contracts api
from contracts_api import (
    AccountNotificationDirective,
    ActivationHookArguments,
    ActivationHookResult,
    Tside,
)

api = "4.0.0"
version = "1.0.0"
display_name = "Simple Supervised Asset Account with a Contract Module."
summary = "A simple supervised asset account with a contract module."
tside = Tside.ASSET

ACTIVATION_NOTIFICATION = "activation_notification"
notification_types = [ACTIVATION_NOTIFICATION]


def activation_hook(
    vault, activation_hook_arguments: ActivationHookArguments
) -> ActivationHookResult:
    return ActivationHookResult(
        account_notification_directives=[
            AccountNotificationDirective(
                notification_type=ACTIVATION_NOTIFICATION,
                notification_details={
                    "msg": f"Contract module value is '{simple_module.simple_value}'."
                },
            )
        ]
    )
