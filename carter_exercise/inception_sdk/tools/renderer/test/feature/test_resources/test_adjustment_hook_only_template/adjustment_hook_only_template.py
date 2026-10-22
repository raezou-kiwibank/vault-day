# contracts api
from contracts_api import (
    AdjustmentStrategy,
    PostPostingAdjustmentHookArguments,
    PostPostingAdjustmentHookResult,
    PostPostingHookArguments,
    PostPostingHookResult,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions.vault_types import (
    SmartContractVault,
)

api = "4.0.0"
adjustment_strategy = AdjustmentStrategy.SCHEDULE_TRIGGERED


def post_posting_hook(
    vault: SmartContractVault, hook_arguments: PostPostingHookArguments
) -> PostPostingHookResult | None:
    return None


def post_posting_adjustment_hook(
    snapshot_vault: SmartContractVault,
    adjusted_vault: SmartContractVault,
    hook_arguments: PostPostingAdjustmentHookArguments,
) -> PostPostingAdjustmentHookResult | None:
    return None
