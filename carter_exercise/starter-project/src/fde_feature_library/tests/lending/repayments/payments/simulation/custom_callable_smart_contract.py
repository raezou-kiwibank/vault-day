# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as common_fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.lending.interfaces as lending_interfaces
import feature_library.lending.repayments.early_repayment as early_repayment
import feature_library.lending.repayments.overpayment as overpayment
import feature_library.lending.repayments.payments as payments
import feature_library.lending.repayments.secondary.vertical_repayment_hierarchy as vertical_repayment_hierarchy  # noqa: E501

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
tside = Tside.ASSET

# Required for simulation
expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *early_repayment.expected_parameters,
        *overpayment.expected_parameters,
        *denomination_module.expected_parameters,
    ]
)

data_fetchers = common_fetchers.distinct_fetchers(
    [
        *early_repayment.data_fetchers,
        overpayment.OVERPAYMENT_PARAMS_POF,
        *denomination_module.data_fetchers,
        common_fetchers.ALL_BALANCES_ET_BOF,
        common_fetchers.ALL_BALANCES_LIVE_BOF,
    ]
)


@fetch_account_data(
    parameters=[
        early_repayment.EARLY_REPAYMENT_ET_POF_ID,
        overpayment.OVERPAYMENT_PARAMS_POF_ID,
        denomination_module.DENOMINATION_ET_POF_ID,
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
        parameters=denomination_module.get_parameters(vault),
        balances=vault.get_balances_observation(
            fetcher_id=common_fetchers.ALL_BALANCES_ET_BOF_ID
        ).balances,
    )

    repayment_hierarchy_config = lending_interfaces.RepaymentHierarchyConfig(
        repayment_hierarchy=vertical_repayment_hierarchy.VerticalRepaymentHierarchy,
        fetchers_config=vertical_repayment_hierarchy.DEFAULT_VERTICAL_FETCHERS_CONFIG,
    )

    custom_instructions = []
    if arguments.posting_instructions:

        def custom_is_early_repayment_callable(
            state, repayment_amount, repayment_hierarchy_config, early_repayment_fees
        ):
            return early_repayment.is_posting_an_early_repayment(
                state=state,
                repayment_amount=repayment_amount,
                repayment_hierarchy_config=repayment_hierarchy_config,
                early_repayment_fees=early_repayment_fees,
                precision=4,  # Custom configuration explicitly passed
            )

        custom_instructions = payments.generate_repayment_postings(
            state=state,
            hook_arguments=arguments,
            repayment_hierarchy_config=repayment_hierarchy_config,
            is_posting_early_repayment_callable=custom_is_early_repayment_callable,
            handle_penalties_pending_capitalisation_callable=lambda state: [],  # Mock this out for tests
            overpayment_features=[overpayment.OverpaymentFeature],
            early_repayment_fees=[early_repayment.EarlyRepaymentFlatFee],
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
