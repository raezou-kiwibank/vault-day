import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.fees.paper_statement_fee as paper_statement_fee

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
display_name = "Liability Account with Paper Statement Fee."
summary = "Liability Account with Paper Statement Fee."
tside = Tside.LIABILITY

PRODUCT_NAME = "liability_account_paper_statement_fees"

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *denomination_module.expected_parameters,
        *paper_statement_fee.expected_parameters,
    ]
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *denomination_module.data_fetchers,
        *paper_statement_fee.data_fetchers,
    ]
)

event_types = [
    *paper_statement_fee.event_types,
]


@fetch_account_data(
    parameters=[
        paper_statement_fee.PAPER_STATEMENT_FEE_POF_ID,
    ]
)
def activation_hook(
    vault: SmartContractVault, hook_arguments: ActivationHookArguments
) -> ActivationHookResult | None:
    state = state_utils.initialise_state(
        vault,
        effective_datetime=hook_arguments.effective_datetime,
    )

    scheduled_events = paper_statement_fee.get_scheduled_events(state)
    return ActivationHookResult(
        scheduled_events_return_value=scheduled_events,
    )


@fetch_account_data(
    event_type=paper_statement_fee.APPLICATION_EVENT,
    parameters=[
        denomination_module.DENOMINATION_ET_POF_ID,
        paper_statement_fee.PAPER_STATEMENT_FEE_POF_ID,
    ],
    balances=[fetchers.ALL_BALANCES_ET_BOF_ID],
)
def scheduled_event_hook(
    vault: SmartContractVault, hook_arguments: ScheduledEventHookArguments
) -> ScheduledEventHookResult | None:
    state: state_utils.SmartContractState = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters={},  # missing denomination parameter here should trigger assertion failure in
        # apply_fees.
        balances=vault.get_balances_observation(
            fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID
        ).balances,
    )

    if hook_arguments.event_type == paper_statement_fee.APPLICATION_EVENT:
        apply_fees_instructions = paper_statement_fee.apply_fees(
            state=state,
            account_type=PRODUCT_NAME,
            fetchers_config=paper_statement_fee.PaperStatementFeeFetchersConfig(
                param_fetcher_id=paper_statement_fee.PAPER_STATEMENT_FEE_POF_ID,
                denomination_param_id="missing_denomination",
            ),
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
