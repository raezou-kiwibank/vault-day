import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.fees.unarranged_overdraft_fee as unarranged_overdraft_fee

from contracts_api import (
    ActivationHookArguments,
    ActivationHookResult,
    CustomInstruction,
    EventTypesGroup,
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
display_name = "Liability Account with Unarranged Overdraft Fee"
summary = "Liability Account with Unarranged Overdraft Fee"
tside = Tside.LIABILITY

PRODUCT_NAME = "liability_account_unarranged_overdraft_fee"

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *denomination_module.expected_parameters,
        *unarranged_overdraft_fee.expected_parameters,
    ]
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *denomination_module.data_fetchers,
        *unarranged_overdraft_fee.data_fetchers,
    ]
)

event_types = [
    *unarranged_overdraft_fee.event_types,
]
event_types_groups = [
    EventTypesGroup(
        name="unarranged_overdraft_schedules",
        event_types_order=[
            unarranged_overdraft_fee.ACCRUAL_EVENT,
            unarranged_overdraft_fee.APPLICATION_EVENT,
        ],
    )
]


@fetch_account_data(
    parameters=[
        unarranged_overdraft_fee.UNARRANGED_OVERDRAFT_FEE_POF_ID,
    ]
)
def activation_hook(
    vault: SmartContractVault, hook_arguments: ActivationHookArguments
) -> ActivationHookResult | None:
    state = state_utils.initialise_state(
        vault,
        effective_datetime=hook_arguments.effective_datetime,
    )

    scheduled_events = unarranged_overdraft_fee.get_scheduled_events(state)
    return ActivationHookResult(
        scheduled_events_return_value=scheduled_events,
    )


@fetch_account_data(
    event_type=unarranged_overdraft_fee.ACCRUAL_EVENT,
    parameters=[
        denomination_module.DENOMINATION_ET_POF_ID,
        unarranged_overdraft_fee.UNARRANGED_OVERDRAFT_FEE_POF_ID,
    ],
    balances=[
        fetchers.ALL_BALANCES_ET_BOF_ID,
    ],
)
@fetch_account_data(
    event_type=unarranged_overdraft_fee.APPLICATION_EVENT,
    parameters=[
        denomination_module.DENOMINATION_ET_POF_ID,
        unarranged_overdraft_fee.UNARRANGED_OVERDRAFT_FEE_POF_ID,
    ],
    balances=[
        fetchers.ALL_BALANCES_ET_BOF_ID,
    ],
)
def scheduled_event_hook(
    vault: SmartContractVault, hook_arguments: ScheduledEventHookArguments
) -> ScheduledEventHookResult | None:
    handler_fns = {
        unarranged_overdraft_fee.ACCRUAL_EVENT: _handle_unarranged_overdraft_accrual,
        unarranged_overdraft_fee.APPLICATION_EVENT: _handle_unarranged_overdraft_application,
    }
    instructions = handler_fns[hook_arguments.event_type](vault, hook_arguments)

    return (
        ScheduledEventHookResult(
            posting_instructions_directives=[
                PostingInstructionsDirective(
                    posting_instructions=instructions,
                    value_datetime=hook_arguments.effective_datetime,
                )
            ]
        )
        if instructions
        else None
    )


def _handle_unarranged_overdraft_accrual(
    vault: SmartContractVault,
    hook_arguments: ScheduledEventHookArguments,
) -> list[CustomInstruction]:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination_module.get_parameters(vault),
        balances=vault.get_balances_observation(
            fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID
        ).balances,
    )
    return unarranged_overdraft_fee.accrue_fees(state=state)


def _handle_unarranged_overdraft_application(
    vault: SmartContractVault,
    hook_arguments: ScheduledEventHookArguments,
) -> list[CustomInstruction]:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination_module.get_parameters(vault),
        balances=vault.get_balances_observation(
            fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID
        ).balances,
    )
    return unarranged_overdraft_fee.apply_fees(state=state, account_type=PRODUCT_NAME)
