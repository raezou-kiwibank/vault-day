# standard libs

# feature library
import feature_library.common.denomination as denomination
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.fees.withdrawal.excess_fee as excess_fee

# contracts api
from contracts_api import (
    PostingInstructionsDirective,
    PostPostingHookArguments,
    PostPostingHookResult,
    PrePostingHookArguments,
    PrePostingHookResult,
    fetch_account_data,
)

from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

api = "4.0.0"
version = "0.0.1"

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        denomination.DENOMINATION_PARAM,
        *excess_fee.expected_parameters,
    ]
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *excess_fee.data_fetchers,
        denomination.DENOMINATION_ET_POF,
    ]
)


@fetch_account_data(
    parameters=[
        excess_fee.EXCESS_FEE_PARAMS_ET_POF_ID,
        denomination.DENOMINATION_ET_POF_ID,
    ],
    postings=[
        excess_fee.EXCESS_FEE_POSTIF_ID,
    ],
)
def pre_posting_hook(
    vault: SmartContractVault, hook_arguments: PrePostingHookArguments
) -> PrePostingHookResult | None:
    state = state_utils.initialise_state(
        vault, hook_arguments.effective_datetime, parameters=denomination.get_parameters(vault)
    )

    if rejection := excess_fee.validate(
        state=state,
        proposed_client_transactions=hook_arguments.client_transactions,
    ):
        return PrePostingHookResult(rejection=rejection)

    return None


@fetch_account_data(
    parameters=[
        excess_fee.EXCESS_FEE_PARAMS_ET_POF_ID,
        denomination.DENOMINATION_ET_POF_ID,
    ],
    postings=[
        excess_fee.EXCESS_FEE_POSTIF_ID,
    ],
)
def post_posting_hook(
    vault: SmartContractVault, hook_arguments: PostPostingHookArguments
) -> PostPostingHookResult | None:
    state = state_utils.initialise_state(
        vault, hook_arguments.effective_datetime, parameters=denomination.get_parameters(vault)
    )

    withdrawals_handling_instructions = excess_fee.handle_withdrawals(
        state=state,
        proposed_client_transactions=hook_arguments.client_transactions,
    )

    if withdrawals_handling_instructions:
        return PostPostingHookResult(
            posting_instructions_directives=[
                PostingInstructionsDirective(
                    posting_instructions=withdrawals_handling_instructions,
                    value_datetime=hook_arguments.effective_datetime,
                )
            ]
        )
    return None
