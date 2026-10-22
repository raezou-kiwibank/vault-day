"""
Simulation smart contract for testing the Payment Type Threshold Fee feature.
"""

import feature_library.common.denomination as denomination
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.fees.withdrawal.payment_type_threshold_fee as payment_type_threshold_fee  # noqa: E501

from contracts_api import (
    PostingInstructionsDirective,
    PostPostingHookArguments,
    PostPostingHookResult,
    Tside,
    fetch_account_data,
)

from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

api = "4.0.0"
version = "1.0.0"
tside = Tside.LIABILITY

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *denomination.expected_parameters,
        *payment_type_threshold_fee.expected_parameters,
    ]
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *payment_type_threshold_fee.data_fetchers,
        denomination.DENOMINATION_ET_POF,
    ]
)


@fetch_account_data(
    parameters=[
        denomination.DENOMINATION_ET_POF_ID,
        payment_type_threshold_fee.PAYMENT_TYPE_THRESHOLD_FEE_POF_ID,
    ],
    balances=[fetchers.ALL_BALANCES_ET_BOF_ID],
)
def post_posting_hook(
    vault: SmartContractVault, hook_arguments: PostPostingHookArguments
) -> PostPostingHookResult | None:
    """
    Applies payment type threshold fees in the post-posting hook.

    Args:
        vault: The SmartContractVault instance to query.
        hook_arguments: The post-posting hook arguments.

    Returns:
        The post-posting hook result containing any fee instructions, or None.
    """
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination.get_parameters(vault),
        balances=vault.get_balances_observation(
            fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID
        ).balances,
    )
    custom_instructions = payment_type_threshold_fee.apply_fees(
        state=state,
        posting_instructions=hook_arguments.posting_instructions,
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
