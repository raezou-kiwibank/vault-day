# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as common_fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.lending.interfaces as lending_interfaces
import feature_library.lending.repayments.overpayment as overpayment
import feature_library.lending.repayments.secondary.horizontal_repayment_hierarchy as horizontal_repayment_hierarchy  # noqa: E501

from contracts_api import (
    CustomInstruction,
    DeactivationHookArguments,
    DeactivationHookResult,
    PostingInstructionsDirective,
    PostPostingHookArguments,
    PostPostingHookResult,
    PrePostingHookArguments,
    PrePostingHookResult,
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
        *overpayment.expected_parameters,
        *denomination_module.expected_parameters,
    ]
)

data_fetchers = common_fetchers.distinct_fetchers(
    [
        overpayment.OVERPAYMENT_PARAMS_POF,
        *denomination_module.data_fetchers,
        common_fetchers.ALL_BALANCES_ET_BOF,
        common_fetchers.ALL_BALANCES_LIVE_BOF,
    ]
)


@fetch_account_data(
    parameters=[
        overpayment.OVERPAYMENT_PARAMS_POF_ID,
        denomination_module.DENOMINATION_ET_POF_ID,
    ],
    balances=[
        common_fetchers.ALL_BALANCES_LIVE_BOF_ID,
    ],
)
def pre_posting_hook(
    vault: SmartContractVault, arguments: PrePostingHookArguments
) -> PrePostingHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=arguments.effective_datetime,
        parameters=denomination_module.get_parameters(vault),
        balances=vault.get_balances_observation(
            fetcher_id=common_fetchers.ALL_BALANCES_LIVE_BOF_ID
        ).balances,
    )

    denomination: str = state.parameters[denomination_module.DENOMINATION_PARAM_ID]

    repayment_hierarchy_config = lending_interfaces.RepaymentHierarchyConfig(
        repayment_hierarchy=horizontal_repayment_hierarchy.HorizontalRepaymentHierarchy,
        fetchers_config=horizontal_repayment_hierarchy.DEFAULT_HORIZONTAL_FETCHERS_CONFIG,
    )

    if arguments.posting_instructions:
        balances = posting_utils.get_posting_instructions_balances(
            posting_instructions=arguments.posting_instructions
        )
        summed_balance = balance_utils.sum_balances(
            balances=balances,
            denomination=denomination,
        )
        repayment_amount = balance_utils.net_credit(bal=summed_balance)

        rejection = overpayment.validate_if_overpayment_is_greater_than_max(
            state=state,
            repayment_amount=repayment_amount,
            repayment_hierarchy_config=repayment_hierarchy_config,
        )
        if rejection:
            return PrePostingHookResult(rejection=rejection)

    return None


@fetch_account_data(
    parameters=[
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
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=arguments.effective_datetime,
        parameters=denomination_module.get_parameters(vault),
        balances=vault.get_balances_observation(
            fetcher_id=common_fetchers.ALL_BALANCES_ET_BOF_ID
        ).balances,
    )

    denomination: str = state.parameters[denomination_module.DENOMINATION_PARAM_ID]

    custom_instructions = []
    if arguments.posting_instructions:
        balances = posting_utils.get_posting_instructions_balances(
            posting_instructions=arguments.posting_instructions
        )
        summed_balance = balance_utils.sum_balances(
            balances=balances,
            denomination=denomination,
        )
        repayment_amount = balance_utils.net_credit(bal=summed_balance)

        # 1. Handle overpayment (rebalancing PRINCIPAL and OVERPAYMENT tracker)
        postings = overpayment.handle_overpayment(
            state=state,
            overpayment_amount=repayment_amount,
        )
        if postings:
            custom_instructions.append(
                CustomInstruction(
                    postings=postings,
                    instruction_details={"description": "Handle overpayment"},
                )
            )

        # 2. Charge fee as penalty (if configured and applicable)
        fee_cis = overpayment.charge_overpayment_fee_as_penalty(
            state=state,
            vault=vault,
            overpayment_amount=repayment_amount,
            precision=2,
        )
        custom_instructions.extend(fee_cis)

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


@fetch_account_data(
    parameters=[
        denomination_module.DENOMINATION_LIVE_POF_ID,
    ],
    balances=[
        common_fetchers.ALL_BALANCES_LIVE_BOF_ID,
    ],
)
def deactivation_hook(
    vault: SmartContractVault, arguments: DeactivationHookArguments
) -> DeactivationHookResult | None:
    balances = vault.get_balances_observation(
        fetcher_id=common_fetchers.ALL_BALANCES_LIVE_BOF_ID
    ).balances

    denomination: str = vault.get_parameters_observation(
        fetcher_id=denomination_module.DENOMINATION_LIVE_POF_ID
    ).parameters[denomination_module.DENOMINATION_PARAM_ID]  # type: ignore

    postings: list[Posting] = overpayment.get_residual_cleanup_postings(
        balances=balances,
        account_id=vault.account_id,
        denomination=denomination,
    )

    if postings:
        return DeactivationHookResult(
            posting_instructions_directives=[
                PostingInstructionsDirective(
                    posting_instructions=[
                        CustomInstruction(
                            postings=postings, instruction_details={"description": "Cleanup"}
                        )
                    ],
                    value_datetime=arguments.effective_datetime,
                )
            ]
        )
    return None
