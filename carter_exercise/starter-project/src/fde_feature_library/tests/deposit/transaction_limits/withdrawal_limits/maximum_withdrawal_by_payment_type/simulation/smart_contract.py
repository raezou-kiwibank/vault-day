import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.transaction_limits.withdrawal_limits.maximum_withdrawal_by_payment_type as maximum_withdrawal_by_payment_type  # noqa: E501

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
display_name = "Liability Account with Maximum Withdrawal By Payment Type Limit"
summary = "Liability Account with Maximum Withdrawal By Payment Type Limit"
tside = Tside.LIABILITY

PRODUCT_NAME = "maximum_withdrawal_by_payment_type"

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *denomination_module.expected_parameters,
        *maximum_withdrawal_by_payment_type.expected_parameters,
    ]
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *denomination_module.data_fetchers,
        *maximum_withdrawal_by_payment_type.data_fetchers,
    ]
)


@fetch_account_data(
    parameters=[
        denomination_module.DENOMINATION_ET_POF_ID,
        maximum_withdrawal_by_payment_type.MAX_WITHDRAWAL_BY_PAYMENT_TYPE_POF_ID,
    ]
)
def pre_posting_hook(
    vault: SmartContractVault, hook_arguments: PrePostingHookArguments
) -> PrePostingHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination_module.get_parameters(vault),
    )

    if rejection := maximum_withdrawal_by_payment_type.validate(
        state=state,
        postings=hook_arguments.posting_instructions,
    ):
        return PrePostingHookResult(rejection=rejection)

    return None
