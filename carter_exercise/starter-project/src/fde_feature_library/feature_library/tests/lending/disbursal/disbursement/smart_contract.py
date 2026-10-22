# feature library
import feature_library.common.denomination as denomination
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.lending.disbursal.disbursement as disbursement

# contracts api
from contracts_api import (
    ActivationHookArguments,
    ActivationHookResult,
    PostingInstructionsDirective,
    Tside,
    fetch_account_data,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

api = "4.0.0"
version = "1.0.0"
tside = Tside.ASSET

# Parameters
expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *denomination.expected_parameters,
        *disbursement.expected_parameters,
    ]
)

# Data Fetchers
data_fetchers = fetchers.distinct_fetchers(
    [
        *denomination.data_fetchers,
        *disbursement.data_fetchers,
    ]
)


@fetch_account_data(
    parameters=[
        denomination.DENOMINATION_ET_POF_ID,
        disbursement.DISBURSEMENT_PARAMS_ET_POF_ID,
    ]
)
def activation_hook(
    vault: SmartContractVault,
    arguments: ActivationHookArguments,
) -> ActivationHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=arguments.effective_datetime,
        parameters={
            **denomination.get_parameters(vault),
            **disbursement.get_parameters(vault),
        },
    )

    custom_instructions = disbursement.get_disbursement_custom_instruction(
        state=state,
    )

    return ActivationHookResult(
        posting_instructions_directives=[
            PostingInstructionsDirective(
                posting_instructions=custom_instructions,
                value_datetime=arguments.effective_datetime,
            )
        ]
    )
