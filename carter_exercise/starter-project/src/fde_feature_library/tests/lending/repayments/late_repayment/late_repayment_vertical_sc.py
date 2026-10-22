# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as common_fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.lending.interfaces as lending_interfaces
import feature_library.lending.repayments.late_repayment as late_repayment
import feature_library.lending.repayments.secondary.vertical_repayment_hierarchy as vertical_repayment_hierarchy  # noqa: E501

from contracts_api import (
    ActivationHookArguments,
    ActivationHookResult,
    PostingInstructionsDirective,
    ScheduledEventHookArguments,
    ScheduledEventHookResult,
    Tside,
    fetch_account_data,
)

from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

api = "4.0.0"
version = "1.0.0"
tside = Tside.ASSET

PRODUCT_NAME = "LATE_REPAYMENT_VERTICAL"

# Required for simulation
expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *late_repayment.expected_parameters,
        *denomination_module.expected_parameters,
    ]
)

data_fetchers = common_fetchers.distinct_fetchers(
    [
        *late_repayment.data_fetchers,
        *denomination_module.data_fetchers,
        common_fetchers.ALL_BALANCES_ET_BOF,
        common_fetchers.ALL_BALANCES_LIVE_BOF,
    ]
)

event_types = late_repayment.event_types(product_name=PRODUCT_NAME)


@fetch_account_data(
    parameters=[
        late_repayment.LATE_REPAYMENT_POF_ID,
    ],
)
def activation_hook(
    vault: SmartContractVault, arguments: ActivationHookArguments
) -> ActivationHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=arguments.effective_datetime,
    )

    scheduled_events = late_repayment.get_scheduled_events(
        state=state,
        start_datetime=arguments.effective_datetime,
    )

    return ActivationHookResult(scheduled_events_return_value=scheduled_events)


@fetch_account_data(
    event_type=late_repayment.CHECK_LATE_REPAYMENT_EVENT,
    parameters=[
        late_repayment.LATE_REPAYMENT_POF_ID,
        denomination_module.DENOMINATION_ET_POF_ID,
    ],
    balances=[
        common_fetchers.ALL_BALANCES_ET_BOF_ID,
    ],
)
def scheduled_event_hook(
    vault: SmartContractVault, arguments: ScheduledEventHookArguments
) -> ScheduledEventHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=arguments.effective_datetime,
        parameters=denomination_module.get_parameters(vault),
        balances=vault.get_balances_observation(
            fetcher_id=common_fetchers.ALL_BALANCES_ET_BOF_ID
        ).balances,
    )

    custom_instructions = []
    if arguments.event_type == late_repayment.CHECK_LATE_REPAYMENT_EVENT:
        repayment_hierarchy_config = lending_interfaces.RepaymentHierarchyConfig(
            repayment_hierarchy=vertical_repayment_hierarchy.VerticalRepaymentHierarchy,
            fetchers_config=vertical_repayment_hierarchy.DEFAULT_VERTICAL_FETCHERS_CONFIG,
        )

        custom_instructions.extend(
            late_repayment.schedule_logic(
                state=state,
                repayment_hierarchy_config=repayment_hierarchy_config,
            )
        )

    return ScheduledEventHookResult(
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
