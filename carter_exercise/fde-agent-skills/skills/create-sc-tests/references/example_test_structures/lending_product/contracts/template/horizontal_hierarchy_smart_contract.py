# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination
import feature_library.common.fetchers as common_fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.lending.interfaces as lending_interfaces
import feature_library.lending.repayments.early_repayment as early_repayment
import feature_library.lending.repayments.secondary.horizontal_repayment_hierarchy as horizontal_repayment_hierarchy  # noqa: E501

from contracts_api import (
    ActivationHookArguments,
    ActivationHookResult,
    PostingInstructionsDirective,
    PostPostingHookArguments,
    PostPostingHookResult,
    Tside,
    fetch_account_data,
)

from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

api = "4.0.0"
version = "1.0.0"
tside = Tside.ASSET

# Required for simulation
expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *early_repayment.expected_parameters,
        *denomination.expected_parameters,
    ]
)

data_fetchers = common_fetchers.distinct_fetchers(
    [
        *early_repayment.data_fetchers,
        *denomination.data_fetchers,
        common_fetchers.ALL_BALANCES_ET_BOF,
        common_fetchers.ALL_BALANCES_LIVE_BOF,
    ]
)


def activation_hook(
    vault: SmartContractVault, arguments: ActivationHookArguments
) -> ActivationHookResult | None:
    return ActivationHookResult()


@fetch_account_data(
    parameters=[
        early_repayment.EARLY_REPAYMENT_ET_POF_ID,
        denomination.DENOMINATION_ET_POF_ID,
    ],
    balances=[
        common_fetchers.ALL_BALANCES_ET_BOF_ID,
    ],
)
def post_posting_hook(
    vault: SmartContractVault, arguments: PostPostingHookArguments
) -> PostPostingHookResult | None:
    # Explicitly pass balances to initialise_state as per modernization guidelines
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=arguments.effective_datetime,
        parameters=denomination.get_parameters(vault),
        balances=vault.get_balances_observation(
            fetcher_id=common_fetchers.ALL_BALANCES_ET_BOF_ID
        ).balances,
    )

    denomination_val: str = state.parameters[denomination.DENOMINATION_PARAM_ID]  # type: ignore

    repayment_hierarchy_config = lending_interfaces.RepaymentHierarchyConfig(
        repayment_hierarchy=horizontal_repayment_hierarchy.HorizontalRepaymentHierarchy,
        fetchers_config=horizontal_repayment_hierarchy.DEFAULT_HORIZONTAL_FETCHERS_CONFIG,
    )

    custom_instructions = []
    if arguments.posting_instructions:
        balances = posting_utils.get_posting_instructions_balances(
            posting_instructions=arguments.posting_instructions
        )
        # Sum balances to get a single Balance object for the relevant denomination
        summed_balance = balance_utils.sum_balances(
            balances=balances,
            denomination=denomination_val,
        )
        repayment_amount = balance_utils.net_debit(bal=summed_balance)

        if early_repayment.is_posting_an_early_repayment(
            state=state,
            repayment_amount=repayment_amount,
            repayment_hierarchy_config=repayment_hierarchy_config,
            early_repayment_fees=[early_repayment.EarlyRepaymentPercentageFee],
        ):
            fee_amount = early_repayment.calculate_early_repayment_percentage_fee(state=state)
            custom_instructions.extend(
                early_repayment.charge_early_repayment_fee(
                    state=state,
                    amount_to_charge=fee_amount,
                    fee_name="Early Repayment Percentage Fee",
                )
            )

    return PostPostingHookResult(
        posting_instructions_directives=(
            [
                PostingInstructionsDirective(
                    posting_instructions=custom_instructions,
                    value_datetime=arguments.effective_datetime,
                )
            ]
            if custom_instructions
            else None
        )
    )
