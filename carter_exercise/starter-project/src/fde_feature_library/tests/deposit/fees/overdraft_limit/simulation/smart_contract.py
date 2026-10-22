import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.fees.overdraft_limit as overdraft_limit

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
display_name = "Liability Account with Overdraft Limit"
summary = "Liability Account with Overdraft Limit"
tside = Tside.LIABILITY

PRODUCT_NAME = "liability_account_overdraft_limit"

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *denomination_module.expected_parameters,
        *overdraft_limit.expected_parameters,
    ]
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *denomination_module.data_fetchers,
        *overdraft_limit.data_fetchers,
    ]
)


@fetch_account_data(
    parameters=[
        denomination_module.DENOMINATION_ET_POF_ID,
        overdraft_limit.OVERDRAFT_LIMIT_POF_ID,
    ],
    balances=[
        fetchers.ALL_BALANCES_LIVE_BOF_ID,
    ],
)
def pre_posting_hook(
    vault: SmartContractVault, hook_arguments: PrePostingHookArguments
) -> PrePostingHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination_module.get_parameters(vault),
    )

    if rejection := overdraft_limit.validate(
        state=state,
        postings=hook_arguments.posting_instructions,
    ):
        return PrePostingHookResult(rejection=rejection)

    return None
