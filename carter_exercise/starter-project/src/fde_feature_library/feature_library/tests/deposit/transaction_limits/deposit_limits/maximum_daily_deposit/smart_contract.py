import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.transaction_limits.deposit_limits.maximum_daily_deposit as maximum_daily_deposit  # noqa: E501

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
display_name = "maximum_daily_deposit"
summary = "maximum_daily_deposit"
tside = Tside.LIABILITY

PRODUCT_NAME = "maximum_daily_deposit"

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *denomination_module.expected_parameters,
        *maximum_daily_deposit.expected_parameters,
    ]
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *denomination_module.data_fetchers,
        *maximum_daily_deposit.data_fetchers,
        fetchers.ALL_BALANCES_LIVE_BOF,
    ]
)


@fetch_account_data(
    parameters=[
        denomination_module.DENOMINATION_ET_POF_ID,
        maximum_daily_deposit.MAX_DAILY_DEPOSIT_POF_ID,
    ],
    balances=[
        fetchers.ALL_BALANCES_LIVE_BOF_ID,
    ],
    postings=[
        fetchers.EFFECTIVE_DATE_POSTIF_ID,
    ],
)
def pre_posting_hook(
    vault: SmartContractVault, hook_arguments: PrePostingHookArguments
) -> PrePostingHookResult | None:
    state: state_utils.SmartContractState = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination_module.get_parameters(vault),
    )

    rejection = maximum_daily_deposit.validate(
        state=state, client_transactions=hook_arguments.client_transactions
    )

    if rejection:
        return PrePostingHookResult(rejection=rejection)

    return None
