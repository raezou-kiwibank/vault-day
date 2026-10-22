# feature library
import feature_library.common.denomination as denomination
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.lending.principal.minimum_loan_principal as minimum_loan_principal

# contracts api
from contracts_api import (
    PrePostingHookArguments,
    PrePostingHookResult,
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
        *minimum_loan_principal.expected_parameters,
    ]
)

# Data Fetchers
data_fetchers = fetchers.distinct_fetchers(
    [
        *denomination.data_fetchers,
        *minimum_loan_principal.data_fetchers,
    ]
)


@fetch_account_data(
    parameters=[
        denomination.DENOMINATION_ET_POF_ID,
        minimum_loan_principal.MINIMUM_LOAN_PRINCIPAL_ET_POF_ID,
    ]
)
def pre_posting_hook(
    vault: SmartContractVault,
    arguments: PrePostingHookArguments,
) -> PrePostingHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=arguments.effective_datetime,
        parameters={
            **denomination.get_parameters(vault),
        },
    )

    rejection = minimum_loan_principal.validate(
        state=state,
        postings=arguments.posting_instructions,
    )

    if rejection:
        return PrePostingHookResult(rejection=rejection)

    return None
