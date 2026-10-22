import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.dormancy.dormancy as dormancy

from contracts_api import (
    PrePostingHookArguments,
    PrePostingHookResult,
    Tside,
    fetch_account_data,
)

from inception_sdk.vault.contracts.extensions.contracts_api_extensions.vault_types import (
    SmartContractVault,
)

api = "4.0.0"
version = "0.0.1"
display_name = "Liability Account with Dormancy."
summary = "Liability Account with Dormancy."
tside = Tside.LIABILITY

PRODUCT_NAME = "liability_account_dormancy"

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *dormancy.expected_parameters,
    ]
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *dormancy.data_fetchers,
    ]
)


@fetch_account_data(
    parameters=[
        dormancy.DORMANCY_PARAMS_ET_POF_ID,
    ],
    flags=[
        dormancy.DORMANCY_FOF_ID,
    ],
)
def pre_posting_hook(
    vault: SmartContractVault, hook_arguments: PrePostingHookArguments
) -> PrePostingHookResult | None:
    state = state_utils.initialise_state(
        vault,
        effective_datetime=hook_arguments.effective_datetime,
    )

    rejection = dormancy.validate_account_transaction(state)
    if rejection:
        return PrePostingHookResult(rejection=rejection)

    return None
