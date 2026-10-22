import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.fees.maintenance_fees as maintenance_fees_module

from contracts_api import (
    ActivationHookArguments,
    ActivationHookResult,
    PostingInstructionsDirective,
    ScheduledEventHookArguments,
    ScheduledEventHookResult,
    Tside,
    fetch_account_data,
)

from inception_sdk.vault.contracts.extensions.contracts_api_extensions.vault_types import (
    SmartContractVault,
)

api = "4.0.0"
version = "0.0.1"
display_name = "Liability Account with Maintenance Fees"
summary = "Liability Account with Maintenance Fees"
tside = Tside.LIABILITY

PRODUCT_NAME = "liability_account_maintenance_fees"

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *denomination_module.expected_parameters,
        *maintenance_fees_module.expected_parameters,
    ]
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *denomination_module.data_fetchers,
        *maintenance_fees_module.data_fetchers,
    ]
)

event_types = [
    *maintenance_fees_module.event_types(
        product_name=PRODUCT_NAME, frequency=maintenance_fees_module.MONTHLY
    ),
    *maintenance_fees_module.event_types(
        product_name=PRODUCT_NAME, frequency=maintenance_fees_module.ANNUALLY
    ),
]


@fetch_account_data(
    parameters=[
        maintenance_fees_module.MAINTENANCE_FEES_POF_ID,
    ]
)
def activation_hook(
    vault: SmartContractVault, hook_arguments: ActivationHookArguments
) -> ActivationHookResult | None:
    state = state_utils.initialise_state(
        vault,
        effective_datetime=hook_arguments.effective_datetime,
    )

    scheduled_events_monthly = maintenance_fees_module.get_scheduled_events(
        state=state, frequency=maintenance_fees_module.MONTHLY
    )
    scheduled_events_annual = maintenance_fees_module.get_scheduled_events(
        state=state, frequency=maintenance_fees_module.ANNUALLY
    )

    scheduled_events = {**scheduled_events_monthly, **scheduled_events_annual}

    return ActivationHookResult(
        scheduled_events_return_value=scheduled_events,
    )


@fetch_account_data(
    event_type=maintenance_fees_module.APPLY_MONTHLY_FEE_EVENT,
    parameters=[
        denomination_module.DENOMINATION_ET_POF_ID,
        maintenance_fees_module.MAINTENANCE_FEES_POF_ID,
    ],
    balances=[
        fetchers.ALL_BALANCES_ET_BOF_ID,
    ],
)
@fetch_account_data(
    event_type=maintenance_fees_module.APPLY_ANNUAL_FEE_EVENT,
    parameters=[
        denomination_module.DENOMINATION_ET_POF_ID,
        maintenance_fees_module.MAINTENANCE_FEES_POF_ID,
    ],
    balances=[
        fetchers.ALL_BALANCES_ET_BOF_ID,
    ],
)
def scheduled_event_hook(
    vault: SmartContractVault, hook_arguments: ScheduledEventHookArguments
) -> ScheduledEventHookResult | None:
    state: state_utils.SmartContractState = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination_module.get_parameters(vault),
        balances=vault.get_balances_observation(
            fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID
        ).balances,
    )

    posting_instructions = []
    update_event_directives = []

    if hook_arguments.event_type == maintenance_fees_module.APPLY_MONTHLY_FEE_EVENT:
        posting_instructions.extend(
            maintenance_fees_module.apply_monthly_fee(
                state=state,
                account_type=PRODUCT_NAME,
            )
        )

    if hook_arguments.event_type == maintenance_fees_module.APPLY_ANNUAL_FEE_EVENT:
        posting_instructions.extend(
            maintenance_fees_module.apply_annual_fee(
                state=state,
                account_type=PRODUCT_NAME,
            )
        )
        update_next_annual = maintenance_fees_module.update_next_annual_schedule_execution(
            state=state
        )
        if update_next_annual:
            update_event_directives.append(update_next_annual)

    if posting_instructions or update_event_directives:
        return ScheduledEventHookResult(
            posting_instructions_directives=[
                PostingInstructionsDirective(
                    posting_instructions=posting_instructions,
                    value_datetime=hook_arguments.effective_datetime,
                )
            ]
            if posting_instructions
            else [],
            update_account_event_type_directives=update_event_directives,
        )

    return None
