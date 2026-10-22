import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.transaction_limits.withdrawal_limits.maximum_daily_withdrawal_by_transaction_type as maximum_daily_withdrawal_by_transaction_type  # noqa: E501

from contracts_api import (
    PreParameterChangeHookArguments,
    PreParameterChangeHookResult,
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
display_name = "Liability Account with Maximum Daily Withdrawal By Transaction Type"
summary = "Liability Account with Maximum Daily Withdrawal By Transaction Type"
tside = Tside.LIABILITY

PRODUCT_NAME = "maximum_daily_withdrawal_by_transaction_type"

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *denomination_module.expected_parameters,
        *maximum_daily_withdrawal_by_transaction_type.expected_parameters,
    ]
)

# Parameter customisations.
maximum_daily_withdrawal_by_transaction_type.DAILY_WITHDRAWAL_LIMIT_BY_TRANSACTION_TYPE_PARAM.triggers_pre_parameter_change_hook = True  # noqa: E501

data_fetchers = fetchers.distinct_fetchers(
    [
        *denomination_module.data_fetchers,
        *maximum_daily_withdrawal_by_transaction_type.data_fetchers,
        fetchers.ALL_BALANCES_ET_BOF,
        fetchers.EFFECTIVE_DATE_POSTIF,
    ]
)


@fetch_account_data(
    parameters=[
        denomination_module.DENOMINATION_ET_POF_ID,
        maximum_daily_withdrawal_by_transaction_type.MAX_DAILY_WITHDRAWAL_BY_TRANSACTION_TYPE_POF_ID,  # noqa: E501
    ],
    balances=[
        fetchers.ALL_BALANCES_ET_BOF_ID,
    ],
    postings=[fetchers.EFFECTIVE_DATE_POSTIF_ID],
)
def pre_posting_hook(
    vault: SmartContractVault, hook_arguments: PrePostingHookArguments
) -> PrePostingHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination_module.get_parameters(vault),
    )

    if rejection := maximum_daily_withdrawal_by_transaction_type.validate(
        state=state,
        client_transactions=hook_arguments.client_transactions,
    ):
        return PrePostingHookResult(rejection=rejection)

    return None


@fetch_account_data(
    parameters=[
        denomination_module.DENOMINATION_ET_POF_ID,
        maximum_daily_withdrawal_by_transaction_type.MAX_DAILY_WITHDRAWAL_BY_TRANSACTION_TYPE_POF_ID,  # noqa: E501
    ],
    balances=[
        fetchers.ALL_BALANCES_ET_BOF_ID,
    ],
    postings=[fetchers.EFFECTIVE_DATE_POSTIF_ID],
)
def pre_parameter_change_hook(
    vault: SmartContractVault, hook_arguments: PreParameterChangeHookArguments
) -> PreParameterChangeHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination_module.get_parameters(vault),
    )
    if param_value := hook_arguments.updated_parameter_values.get(
        maximum_daily_withdrawal_by_transaction_type.DAILY_WITHDRAWAL_LIMIT_BY_TRANSACTION_TYPE_PARAM.id  # noqa: E501
    ):
        if daily_withdrawal_limit_rejection := (
            maximum_daily_withdrawal_by_transaction_type.validate_parameter_change(
                state=state,
                proposed_parameter_value=str(param_value),
            )
        ):
            return PreParameterChangeHookResult(rejection=daily_withdrawal_limit_rejection)

    return None
