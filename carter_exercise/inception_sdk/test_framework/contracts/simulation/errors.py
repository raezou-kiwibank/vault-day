# third party
from typing_extensions import deprecated

# inception sdk
from inception_sdk.test_framework.contracts.simulation.vault_caller import VaultException


class DeactivationFailure(VaultException):
    def __init__(self, account_id: str, reason_suffix: str):
        super().__init__(
            vault_error_code="014.005.000",
            message=f'failed to run deactivation hook for account "{account_id}":'
            f" {reason_suffix}",
        )


class MissingInstanceParameterValue(VaultException):
    def __init__(self, param: str):
        super().__init__(
            vault_error_code="014.005.000",
            message=f"value was not provided for non-derived, non-optional instance "
            f'parameter with name "{param}"',
        )


class AccountCreatedWithNonExistentInstanceParameter(VaultException):
    """
    Raised if an account is created with a value for an instance parameter that doesn't
    exist
    """

    def __init__(self, param: str):
        super().__init__(
            vault_error_code="014.005.000",
            message=f'non-derived instance parameter with name "{param}" does not exist'
            f" - cannot set value",
        )


class UpdateToNonExistentInstanceParameter(VaultException):
    """
    Raised if an account update includes a value for an instance parameter that doesn't exist
    """

    def __init__(self, param: str):
        super().__init__(
            vault_error_code="000.000.000",
            message=f'parameter "{param}" does not exist',
        )


@deprecated("Use MissingParameterValue directly")
def missing_parameter(missing_param: str) -> MissingInstanceParameterValue:
    return MissingInstanceParameterValue(missing_param)


@deprecated(
    "Use AccountCreatedWithNonExistentInstanceParameter directly. reason_suffix parameter is "
    "ignored but left for backwards compatibility"
)
def param_not_exist(
    param: str, reason_suffix: str | None = ""
) -> AccountCreatedWithNonExistentInstanceParameter:
    return AccountCreatedWithNonExistentInstanceParameter(param)
