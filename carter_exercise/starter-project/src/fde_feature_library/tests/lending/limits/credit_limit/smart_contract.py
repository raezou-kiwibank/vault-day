import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.lending.limits.credit_limit as credit_limit

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
display_name = "Credit Card with Credit Limit"
summary = "Credit Card with Credit Limit"
tside = Tside.ASSET

PRODUCT_NAME = "credit_card_credit_limit"

expected_parameters = [
    *denomination_module.expected_parameters,
    *credit_limit.expected_parameters,
]

data_fetchers = [
    *denomination_module.data_fetchers,
    *credit_limit.data_fetchers,
    *fetchers.data_fetchers,
]


@fetch_account_data(
    parameters=[
        denomination_module.DENOMINATION_ET_POF_ID,
        credit_limit.CREDIT_LIMIT_POF_ID,
    ],
    balances=[fetchers.ALL_BALANCES_ET_BOF_ID],
)
def pre_posting_hook(
    vault: SmartContractVault, hook_arguments: PrePostingHookArguments
) -> PrePostingHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination_module.get_parameters(vault),
        balances=vault.get_balances_observation(
            fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID
        ).balances,
    )

    # Validate denomination
    denomination_rejection = denomination_module.validate_denomination(
        state, hook_arguments.posting_instructions
    )
    if denomination_rejection:
        return PrePostingHookResult(rejection=denomination_rejection)

    # Skip credit limit check for force overrides
    if posting_utils.is_force_override(hook_arguments.posting_instructions):
        return None

    denomination = str(state.parameters[denomination_module.DENOMINATION_PARAM.id])

    # Calculate posting amount (net debit for asset-side accounts)
    posting_balances = posting_utils.get_posting_instructions_balances(
        hook_arguments.posting_instructions
    )
    from contracts_api import DEFAULT_ADDRESS, DEFAULT_ASSET, Phase

    posting_amount = posting_balances[
        (DEFAULT_ADDRESS, DEFAULT_ASSET, denomination, Phase.COMMITTED)
    ].net

    # Only check credit limit for debits (spending)
    if posting_amount > 0:
        rejection = credit_limit.validate_credit_limit(
            state=state,
            denomination=denomination,
            posting_amount=posting_amount,
        )
        if rejection:
            return PrePostingHookResult(rejection=rejection)

    return None
