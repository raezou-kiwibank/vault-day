import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal as maximum_daily_withdrawal  # noqa: E501

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
display_name = "Liability Account with Maximum Daily Withdrawal Limit"
summary = "Liability Account with Maximum Daily Withdrawal Limit"
tside = Tside.LIABILITY

PRODUCT_NAME = "liability_account_max_daily_withdrawal"

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *denomination_module.expected_parameters,
        *maximum_daily_withdrawal.expected_parameters,
    ]
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *denomination_module.data_fetchers,
        *maximum_daily_withdrawal.data_fetchers,
        fetchers.EFFECTIVE_DATE_POSTIF,
        fetchers.ALL_BALANCES_LIVE_BOF,
    ]
)


@fetch_account_data(
    parameters=[
        denomination_module.DENOMINATION_ET_POF_ID,
        maximum_daily_withdrawal.MAX_DAILY_WITHDRAWAL_POF_ID,
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
    # Initialise state
    state: state_utils.SmartContractState = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination_module.get_parameters(vault),
    )

    if rejection := maximum_daily_withdrawal.validate(
        state=state,
        client_transactions=hook_arguments.client_transactions,
    ):
        return PrePostingHookResult(rejection=rejection)

    return None
