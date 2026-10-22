# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
from decimal import Decimal

import feature_library.common.addresses as common_addresses
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.fees as fee_utils
import feature_library.common.fetchers as common_fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.lending.addresses as lending_addresses
import feature_library.lending.repayments.overpayment as overpayment
import feature_library.lending.repayments.overpayment_allowance as overpayment_allowance

from contracts_api import (
    ActivationHookArguments,
    ActivationHookResult,
    AttributeHookArguments,
    AttributeHookResult,
    ConversionHookArguments,
    ConversionHookResult,
    CustomInstruction,
    DeactivationHookArguments,
    DeactivationHookResult,
    Posting,
    PostingInstructionsDirective,
    PostPostingHookArguments,
    PostPostingHookResult,
    ScheduledEventHookArguments,
    ScheduledEventHookResult,
    Tside,
    fetch_account_data,
)

from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

api = "4.0.0"
version = "1.0.0"
display_name = "Overpayment Allowance Test Contract"
summary = "Overpayment Allowance Test Contract"
tside = Tside.ASSET

PRODUCT_NAME = "overpayment_allowance_sim_acc"

# Required for simulation
expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *overpayment_allowance.expected_parameters,
        *overpayment.expected_parameters,
        *denomination_module.expected_parameters,
    ]
)

event_types = [
    *overpayment_allowance.event_types(account_type=PRODUCT_NAME),
]

attributes = [
    *overpayment_allowance.attributes,
]

data_fetchers = common_fetchers.distinct_fetchers(
    [
        *overpayment_allowance.data_fetchers,
        overpayment.OVERPAYMENT_PARAMS_POF,
        *denomination_module.data_fetchers,
        common_fetchers.ALL_BALANCES_ET_BOF,
        common_fetchers.ALL_BALANCES_LIVE_BOF,
    ]
)


@fetch_account_data(
    parameters=[
        overpayment_allowance.OVERPAYMENT_ALLOWANCE_PARAM_POF_ID,
        denomination_module.DENOMINATION_ET_POF_ID,
        overpayment.OVERPAYMENT_PARAMS_POF_ID,
    ],
)
def activation_hook(
    vault: SmartContractVault, arguments: ActivationHookArguments
) -> ActivationHookResult | None:
    effective_datetime = arguments.effective_datetime
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=effective_datetime,
        parameters=denomination_module.get_parameters(vault),
    )

    denomination: str = state.parameters[denomination_module.DENOMINATION_PARAM_ID]

    # Initialise allowance from a fixed initial principal of 1000 for simulation
    initial_principal = Decimal("1000")
    custom_instructions = (
        overpayment_allowance.initialise_overpayment_allowance_from_principal_amount(
            state=state,
            principal=initial_principal,
        )
    )

    # Disburse principal manually for simulation
    disbursal_postings = posting_utils.create_postings(
        amount=initial_principal,
        debit_account=vault.account_id,
        debit_address=lending_addresses.PRINCIPAL,
        credit_account="INTERNAL_ACCOUNT",
        denomination=denomination,
    )
    custom_instructions.append(
        CustomInstruction(
            postings=disbursal_postings,
            instruction_details={"description": "Disburse"},
        )
    )

    # Also need the schedule
    scheduled_events = overpayment_allowance.scheduled_events(
        state=state,
        allowance_period_start_datetime=effective_datetime,
    )

    return ActivationHookResult(
        posting_instructions_directives=(
            [
                PostingInstructionsDirective(
                    posting_instructions=custom_instructions,
                    value_datetime=effective_datetime,
                )
            ]
            if custom_instructions
            else []
        ),
        scheduled_events_return_value=scheduled_events,
    )


@fetch_account_data(
    event_type=overpayment_allowance.CHECK_OVERPAYMENT_ALLOWANCE_EVENT,
    parameters=[
        overpayment_allowance.OVERPAYMENT_ALLOWANCE_PARAM_POF_ID,
        denomination_module.DENOMINATION_ET_POF_ID,
        overpayment.OVERPAYMENT_PARAMS_POF_ID,
    ],
    balances=[
        overpayment_allowance.EOD_OVERPAYMENT_ALLOWANCE_BOF_ID,
        overpayment_allowance.ONE_YEAR_OVERPAYMENT_ALLOWANCE_BOF_ID,
    ],
)
def scheduled_event_hook(
    vault: SmartContractVault, arguments: ScheduledEventHookArguments
) -> ScheduledEventHookResult | None:
    event_type = arguments.event_type
    effective_datetime = arguments.effective_datetime
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=effective_datetime,
        parameters=denomination_module.get_parameters(vault),
    )

    custom_instructions = []
    if event_type == overpayment_allowance.CHECK_OVERPAYMENT_ALLOWANCE_EVENT:
        custom_instructions = overpayment_allowance.handle_allowance_usage(
            state=state,
            account_type=PRODUCT_NAME,
        )

    return ScheduledEventHookResult(
        posting_instructions_directives=(
            [
                PostingInstructionsDirective(
                    posting_instructions=custom_instructions,
                    value_datetime=effective_datetime,
                )
            ]
            if custom_instructions
            else []
        )
    )


@fetch_account_data(
    parameters=[
        overpayment_allowance.OVERPAYMENT_ALLOWANCE_PARAM_POF_ID,
        denomination_module.DENOMINATION_ET_POF_ID,
        overpayment.OVERPAYMENT_PARAMS_POF_ID,
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
        repayment_amount = balance_utils.net_debit(bal=summed_balance)
        overpayment_amount = abs(repayment_amount)

        is_early_repayment = False
        for pi in arguments.posting_instructions:
            if pi.instruction_details.get("type") == "EARLY_REPAYMENT":
                is_early_repayment = True
                break

        if is_early_repayment:
            fee = overpayment_allowance.get_overpayment_allowance_fee_for_early_repayment(
                state=state
            )
            if fee > 0:
                custom_instructions.extend(
                    fee_utils.fee_custom_instruction(
                        customer_account_id=vault.account_id,
                        denomination=denomination,
                        amount=fee,
                        internal_account="FEE_INCOME",
                        customer_account_address=common_addresses.PENALTIES,
                        instruction_details={"description": "Early repayment allowance fee"},
                    )
                )
        else:
            # Standard overpayment
            # 1. Rebalance from DEFAULT to PRINCIPAL and update OVERPAYMENT address
            rebalance_postings = overpayment.handle_overpayment(
                state=state,
                overpayment_amount=overpayment_amount,
            )
            # 2. Reduce allowance tracker
            allowance_postings = overpayment_allowance.reduce_overpayment_allowance(
                state=state,
                overpayment_amount=overpayment_amount,
            )

            all_postings = rebalance_postings + allowance_postings
            if all_postings:
                custom_instructions.append(
                    CustomInstruction(
                        postings=all_postings,
                        instruction_details={
                            "description": "Handle overpayment and reduce allowance"
                        },
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


@fetch_account_data(
    attribute_name=overpayment_allowance.OVERPAYMENT_ALLOWANCE_REMAINING_ATTR_ID,
    parameters=[
        overpayment_allowance.OVERPAYMENT_ALLOWANCE_PARAM_POF_ID,
        overpayment_allowance.ONE_YEAR_ALLOWANCE_PARAM_PIF_ID,
        denomination_module.DENOMINATION_ET_POF_ID,
        overpayment.OVERPAYMENT_PARAMS_POF_ID,
    ],
    balances=[
        overpayment_allowance.ONE_YEAR_OVERPAYMENT_ALLOWANCE_BIF_ID,
    ],
    last_scheduled_event_datetimes=[
        overpayment_allowance.OVERPAYMENT_ALLOWANCE_LAST_EXECUTION_SOF_ID,
    ],
)
@fetch_account_data(
    attribute_name=overpayment_allowance.OVERPAYMENT_ALLOWANCE_USED_ATTR_ID,
    parameters=[
        overpayment_allowance.OVERPAYMENT_ALLOWANCE_PARAM_POF_ID,
        overpayment_allowance.ONE_YEAR_ALLOWANCE_PARAM_PIF_ID,
        denomination_module.DENOMINATION_ET_POF_ID,
        overpayment.OVERPAYMENT_PARAMS_POF_ID,
    ],
    balances=[
        overpayment_allowance.ONE_YEAR_OVERPAYMENT_ALLOWANCE_BIF_ID,
    ],
    last_scheduled_event_datetimes=[
        overpayment_allowance.OVERPAYMENT_ALLOWANCE_LAST_EXECUTION_SOF_ID,
    ],
)
@fetch_account_data(
    attribute_name=overpayment_allowance.OVERPAYMENT_ALLOWANCE_FEE_ATTR_ID,
    parameters=[
        overpayment_allowance.OVERPAYMENT_ALLOWANCE_PARAM_POF_ID,
        overpayment_allowance.ONE_YEAR_ALLOWANCE_PARAM_PIF_ID,
        denomination_module.DENOMINATION_ET_POF_ID,
        overpayment.OVERPAYMENT_PARAMS_POF_ID,
    ],
    balances=[
        overpayment_allowance.ONE_YEAR_OVERPAYMENT_ALLOWANCE_BIF_ID,
    ],
    last_scheduled_event_datetimes=[
        overpayment_allowance.OVERPAYMENT_ALLOWANCE_LAST_EXECUTION_SOF_ID,
    ],
)
def attribute_hook(
    vault: SmartContractVault, arguments: AttributeHookArguments
) -> AttributeHookResult | None:
    effective_datetime = arguments.effective_datetime

    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=effective_datetime,
        parameters=denomination_module.get_parameters(vault),
    )

    status = overpayment_allowance.get_overpayment_allowance_status(
        state=state,
        effective_datetime=effective_datetime,
    )

    if arguments.attribute_name == overpayment_allowance.OVERPAYMENT_ALLOWANCE_REMAINING_ATTR_ID:
        return AttributeHookResult(
            attribute_value=status.overpayment_allowance - status.overpayment_allowance_used,
        )

    elif arguments.attribute_name == overpayment_allowance.OVERPAYMENT_ALLOWANCE_USED_ATTR_ID:
        return AttributeHookResult(attribute_value=status.overpayment_allowance_used)

    elif arguments.attribute_name == overpayment_allowance.OVERPAYMENT_ALLOWANCE_FEE_ATTR_ID:
        return AttributeHookResult(
            attribute_value=overpayment_allowance.get_allowance_usage_fee(
                allowance=status.overpayment_allowance,
                used_allowance=status.overpayment_allowance_used,
                overpayment_allowance_fee_percentage=state.parameters[
                    overpayment_allowance.OVERPAYMENT_ALLOWANCE_FEE_PERCENTAGE_PARAM_ID
                ],  # type: ignore
            )
        )

    return None


@fetch_account_data(
    balances=[
        common_fetchers.ALL_BALANCES_LIVE_BOF_ID,
    ],
    parameters=[
        denomination_module.DENOMINATION_LIVE_POF_ID,
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

    postings: list[Posting] = []

    postings.extend(
        overpayment_allowance.get_residual_cleanup_postings(
            balances=balances,
            account_id=vault.account_id,
            denomination=denomination,
        )
    )

    postings.extend(
        overpayment.get_residual_cleanup_postings(
            balances=balances,
            account_id=vault.account_id,
            denomination=denomination,
        )
    )

    return DeactivationHookResult(
        posting_instructions_directives=(
            [
                PostingInstructionsDirective(
                    posting_instructions=[
                        CustomInstruction(
                            postings=postings, instruction_details={"description": "Cleanup"}
                        )
                    ],
                    value_datetime=arguments.effective_datetime,
                )
            ]
            if postings
            else []
        )
    )


@fetch_account_data(
    parameters=[
        overpayment_allowance.OVERPAYMENT_ALLOWANCE_PARAM_POF_ID,
        denomination_module.DENOMINATION_ET_POF_ID,
        overpayment.OVERPAYMENT_PARAMS_POF_ID,
    ],
    balances=[
        overpayment_allowance.ONE_YEAR_OVERPAYMENT_ALLOWANCE_BIF_ID,
    ],
    last_scheduled_event_datetimes=[
        overpayment_allowance.OVERPAYMENT_ALLOWANCE_LAST_EXECUTION_SOF_ID,
    ],
)
def conversion_hook(
    vault: SmartContractVault, arguments: ConversionHookArguments
) -> ConversionHookResult | None:
    effective_datetime = arguments.effective_datetime
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=effective_datetime,
        parameters=denomination_module.get_parameters(vault),
    )

    scheduled_events = overpayment_allowance.update_scheduled_event(
        state=state,
        effective_datetime=effective_datetime,
    )

    custom_instructions = overpayment_allowance.handle_allowance_usage_adhoc(
        state=state,
        account_type=PRODUCT_NAME,
        effective_datetime=effective_datetime,
    )

    return ConversionHookResult(
        scheduled_events_return_value=scheduled_events,
        posting_instructions_directives=(
            [
                PostingInstructionsDirective(
                    posting_instructions=custom_instructions,
                    value_datetime=effective_datetime,
                )
            ]
            if custom_instructions
            else []
        ),
    )
