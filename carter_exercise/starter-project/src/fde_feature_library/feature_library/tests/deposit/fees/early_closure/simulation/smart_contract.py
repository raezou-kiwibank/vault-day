import feature_library.common.balance_utils as balance_utils
import feature_library.common.calendar_utils as calendar_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.fees.early_closure_fee as early_closure_fee_module

from contracts_api import (
    DeactivationHookArguments,
    DeactivationHookResult,
    PostingInstructionsDirective,
    Tside,
    fetch_account_data,
)

from inception_sdk.vault.contracts.extensions.contracts_api_extensions.vault_types import (
    SmartContractVault,
)

api = "4.0.0"
version = "0.0.1"
display_name = "Liability Account with Early Closure Fee."
summary = "Liability Account with Early Closure Fee."
tside = Tside.LIABILITY

PRODUCT_NAME = "liability_account_withdrawal_fees"

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *denomination_module.expected_parameters,
        *early_closure_fee_module.expected_parameters,
    ]
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *calendar_utils.data_fetchers,
        *denomination_module.data_fetchers,
        *early_closure_fee_module.data_fetchers,
    ]
)


@fetch_account_data(
    parameters=[
        denomination_module.DENOMINATION_ET_POF_ID,
        early_closure_fee_module.EARLY_CLOSURE_FEES_POF_ID,
    ],
    balances=[
        fetchers.ALL_BALANCES_ET_BOF_ID,
    ],
)
def deactivation_hook(
    vault: SmartContractVault, hook_arguments: DeactivationHookArguments
) -> DeactivationHookResult | None:
    closure_posting_directives: list[PostingInstructionsDirective] = []
    # Initialise state
    state: state_utils.SmartContractState = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination_module.get_parameters(vault),
        balances=vault.get_balances_observation(
            fetcher_id=fetchers.ALL_BALANCES_ET_BOF.fetcher_id
        ).balances,
    )
    apply_fees_result: early_closure_fee_module.ApplyFeesResult = (
        early_closure_fee_module.apply_fees(
            state=state,
            account_type=PRODUCT_NAME,
        )
    )
    if apply_fees_result.rejection:
        return DeactivationHookResult(rejection=apply_fees_result.rejection)

    if apply_fees_result.custom_instructions:
        closure_posting_directives.append(
            PostingInstructionsDirective(
                posting_instructions=apply_fees_result.custom_instructions,
                client_batch_id=f"{vault.get_hook_execution_id()}",
                value_datetime=hook_arguments.effective_datetime,
            )
        )
        state = state_utils.append_to_state(
            state=state,
            balances=balance_utils.update_inflight_balances(
                account_id=vault.account_id,
                tside=tside,
                current_balances=state.balances,
                posting_instructions=apply_fees_result.custom_instructions,  # type: ignore
            ),
        )

    if rejection := balance_utils.validate_ready_for_closure(state.balances):
        return DeactivationHookResult(rejection=rejection)

    if closure_posting_directives:
        return DeactivationHookResult(
            posting_instructions_directives=closure_posting_directives,
        )
    return None
