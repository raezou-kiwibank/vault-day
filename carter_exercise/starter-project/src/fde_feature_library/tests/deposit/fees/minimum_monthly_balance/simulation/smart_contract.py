import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.fees.minimum_monthly_balance as minimum_monthly_balance

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
display_name = "Liability Account with Minimum Monthly Balance Fee"
summary = "Liability Account with Minimum Monthly Balance Fee"
tside = Tside.LIABILITY

PRODUCT_NAME = "liability_account_minimum_monthly_balance_fee"

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *denomination_module.expected_parameters,
        *minimum_monthly_balance.expected_parameters,
    ]
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *denomination_module.data_fetchers,
        *minimum_monthly_balance.data_fetchers,
    ]
)

event_types = [
    *minimum_monthly_balance.event_types,
]


@fetch_account_data(
    parameters=[
        minimum_monthly_balance.MINIMUM_BALANCE_FEE_POF_ID,
    ]
)
def activation_hook(
    vault: SmartContractVault, hook_arguments: ActivationHookArguments
) -> ActivationHookResult | None:
    state = state_utils.initialise_state(
        vault,
        effective_datetime=hook_arguments.effective_datetime,
    )

    scheduled_events = minimum_monthly_balance.get_scheduled_events(state)
    return ActivationHookResult(
        scheduled_events_return_value=scheduled_events,
    )


@fetch_account_data(
    event_type=minimum_monthly_balance.APPLY_MINIMUM_MONTHLY_BALANCE_EVENT,
    parameters=[
        denomination_module.DENOMINATION_ET_POF_ID,
        minimum_monthly_balance.MINIMUM_BALANCE_FEE_POF_ID,
    ],
    balances=[
        fetchers.ALL_BALANCES_ET_BOF_ID,
        fetchers.ONE_MONTH_EFFECTIVE_DATE_BDIF_ID,
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

    if hook_arguments.event_type == minimum_monthly_balance.APPLY_MINIMUM_MONTHLY_BALANCE_EVENT:
        apply_fees_instructions = minimum_monthly_balance.apply_fees(
            state=state,
            account_type=PRODUCT_NAME,
        )

        if apply_fees_instructions:
            return ScheduledEventHookResult(
                posting_instructions_directives=[
                    PostingInstructionsDirective(
                        posting_instructions=apply_fees_instructions,
                        value_datetime=hook_arguments.effective_datetime,
                    )
                ]
            )

    return None
