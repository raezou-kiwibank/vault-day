import feature_library.common.denomination as denomination
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.fees.withdrawal.payment_type_monthly_limit_fee as payment_type_monthly_limit_fee  # noqa: E501

from contracts_api import (
    PostingInstructionsDirective,
    PostPostingHookArguments,
    PostPostingHookResult,
    Tside,
    fetch_account_data,
)

from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

api = "4.0.0"
version = "0.0.1"
tside = Tside.LIABILITY

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *denomination.expected_parameters,
        *payment_type_monthly_limit_fee.expected_parameters,
    ]
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *payment_type_monthly_limit_fee.data_fetchers,
        denomination.DENOMINATION_ET_POF,
    ]
)


@fetch_account_data(
    parameters=[
        denomination.DENOMINATION_ET_POF_ID,
        payment_type_monthly_limit_fee.MONTHLY_LIMIT_FEES_POF_ID,
    ],
    postings=[
        payment_type_monthly_limit_fee.MONTH_TO_EFFECTIVE_POSTIF_ID,
    ],
)
def post_posting_hook(
    vault: SmartContractVault, hook_arguments: PostPostingHookArguments
) -> PostPostingHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination.get_parameters(vault),
    )
    custom_instructions = payment_type_monthly_limit_fee.apply_fees(
        state=state,
        updated_client_transactions=hook_arguments.client_transactions,
        account_type="TEST_ACCOUNT",
    )
    if custom_instructions:
        return PostPostingHookResult(
            posting_instructions_directives=[
                PostingInstructionsDirective(
                    posting_instructions=custom_instructions,
                    value_datetime=hook_arguments.effective_datetime,
                )
            ]
        )
    return None
