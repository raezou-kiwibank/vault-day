import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.transaction_limits.deposit_limits.minimum_initial_deposit as minimum_initial_deposit  # noqa: E501

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
display_name = "Liability Account with Minimum Initial Deposit"
summary = "Liability Account with Minimum Initial Deposit"
tside = Tside.LIABILITY

PRODUCT_NAME = "liability_account_min_initial_deposit"

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *denomination_module.expected_parameters,
        *minimum_initial_deposit.expected_parameters,
    ]
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *denomination_module.data_fetchers,
        *minimum_initial_deposit.data_fetchers,
    ]
)


@fetch_account_data(
    parameters=[
        denomination_module.DENOMINATION_ET_POF_ID,
        minimum_initial_deposit.MIN_INITIAL_DEPOSIT_POF_ID,
    ],
    balances=[
        fetchers.ALL_BALANCES_LIVE_BOF_ID,
    ],
)
def pre_posting_hook(
    vault: SmartContractVault, hook_arguments: PrePostingHookArguments
) -> PrePostingHookResult | None:
    # Initialise state
    state: state_utils.SmartContractState = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination_module.get_parameters(vault),
    )

    if rejection := minimum_initial_deposit.validate(
        state=state, postings=hook_arguments.posting_instructions
    ):
        return PrePostingHookResult(rejection=rejection)

    return None
