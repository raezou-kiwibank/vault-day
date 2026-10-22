# inception sdk
import inception_sdk.tools.renderer.test.feature.test_resources.test_import_api_extensions.module_1 as module_1  # noqa: E501
from inception_sdk.vault.contracts.extensions.contracts_api_extensions.vault_types import (  # noqa: E501
    SmartContractVault,
)

api = "4.0.0"

test = module_1.my_helper


def my_helper(
    my_arg: str | None,
    vaults: list[SmartContractVault],
    vault_mapping: dict[str, SmartContractVault],
) -> SmartContractVault: ...


# mypy: ignore-errors
