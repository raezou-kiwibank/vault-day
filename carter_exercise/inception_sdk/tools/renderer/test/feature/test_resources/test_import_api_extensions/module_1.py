# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions.vault_types import (
    SuperviseeContractVault,
    SupervisorContractVault,
)


def my_helper(
    vault: SupervisorContractVault,
    vaults: list[SuperviseeContractVault],
    vault_mapping: dict[str, SuperviseeContractVault],
) -> SupervisorContractVault: ...


# mypy: ignore-errors
