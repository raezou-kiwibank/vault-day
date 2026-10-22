# contracts api
from contracts_api import PrePostingHookArguments, PrePostingHookResult

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions.vault_types import (
    SmartContractVault,
)

api = "4.0.0"


def pre_posting_hook(
    vault: SmartContractVault, hook_arguments: PrePostingHookArguments
) -> PrePostingHookResult | None:
    return None
