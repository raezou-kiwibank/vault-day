# contracts api
from contracts_api import ConversionHookArguments, ConversionHookResult, Rejection, RejectionReason

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Contract Metadata
api = "4.0.0"
version = "0.0.1"
supported_denominations = ["USD"]


def conversion_hook(
    vault: SmartContractVault, hook_arguments: ConversionHookArguments
) -> ConversionHookResult | None:
    return ConversionHookResult(
        rejection=Rejection(
            message="Account Conversion Failed.", reason_code=RejectionReason.AGAINST_TNC
        )
    )
