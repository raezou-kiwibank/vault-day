# standard libs
from decimal import Decimal

# contracts api
from contracts_api import ActivationHookArguments, ActivationHookResult

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Contract Metadata
api = "4.0.0"
version = "0.0.1"
supported_denominations = ["USD"]


def activation_hook(
    vault: SmartContractVault, hook_arguments: ActivationHookArguments
) -> ActivationHookResult | None:
    Decimal("s")
    return None
