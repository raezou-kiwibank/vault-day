import feature_library.common.denomination as denomination
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.interest.interest_accrual as interest_accrual
import feature_library.deposit.interest.interest_application as interest_application

from contracts_api import (
    AccountNotificationDirective,
    ActivationHookArguments,
    ActivationHookResult,
    CustomInstruction,
    DefinedDateTime,
    ParametersFilter,
    ParametersObservationFetcher,
    PostingInstructionsDirective,
    ScheduledEventHookArguments,
    ScheduledEventHookResult,
    Tside,
    UpdateAccountEventTypeDirective,
    fetch_account_data,
)

from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

api = "4.0.0"
version = "0.0.1"
display_name = "Liability Account with Interest Application"
summary = "Liability Account with Interest Application"
tside = Tside.LIABILITY

event_types = [
    *interest_application.event_types("interest_application"),
]

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *denomination.expected_parameters,
        *interest_application.expected_parameters,
        interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM,
        interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM,
    ]
)

ACCRUAL_ACCOUNT_PARAMS_POF_ID = "accrual_account_params_pof"
ACCRUAL_ACCOUNT_PARAMS_POF = ParametersObservationFetcher(
    fetcher_id=ACCRUAL_ACCOUNT_PARAMS_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(
        parameter_ids=[
            interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID,
            interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID,
        ]
    ),
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *denomination.data_fetchers,
        ACCRUAL_ACCOUNT_PARAMS_POF,
        *interest_application.data_fetchers,
    ]
)


@fetch_account_data(
    parameters=[
        interest_application.INTEREST_APPLICATION_PARAMS_ET_POF_ID,
        ACCRUAL_ACCOUNT_PARAMS_POF_ID,
        denomination.DENOMINATION_ET_POF_ID,
    ]
)
def activation_hook(
    vault: SmartContractVault, hook_arguments: ActivationHookArguments
) -> ActivationHookResult | None:
    state = state_utils.initialise_state(
        vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters={
            **interest_application.get_parameters(vault),
            **vault.get_parameters_observation(fetcher_id=ACCRUAL_ACCOUNT_PARAMS_POF_ID).parameters,
            **denomination.get_parameters(vault),
        },
    )

    scheduled_events = interest_application.get_scheduled_events(state)

    return ActivationHookResult(
        scheduled_events_return_value=scheduled_events,
    )


@fetch_account_data(
    event_type=interest_application.APPLICATION_EVENT,
    parameters=[
        interest_application.INTEREST_APPLICATION_PARAMS_ET_POF_ID,
        ACCRUAL_ACCOUNT_PARAMS_POF_ID,
        denomination.DENOMINATION_ET_POF_ID,
    ],
    balances=[fetchers.ALL_BALANCES_ET_BOF_ID],
)
def scheduled_event_hook(
    vault: SmartContractVault, hook_arguments: ScheduledEventHookArguments
) -> ScheduledEventHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters={
            **interest_application.get_parameters(vault),
            **vault.get_parameters_observation(fetcher_id=ACCRUAL_ACCOUNT_PARAMS_POF_ID).parameters,
            **denomination.get_parameters(vault),
        },
        balances=vault.get_balances_observation(
            fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID
        ).balances,
    )

    event_type = hook_arguments.event_type

    custom_instructions: list[CustomInstruction] = []
    event_type_directives: list[UpdateAccountEventTypeDirective] = []
    notification_directives: list[AccountNotificationDirective] = []

    if event_type == interest_application.APPLICATION_EVENT:
        # We need to provide a custom fetchers config since the default one uses fetchers
        # that are not defined in this contract
        accrual_fetchers_config = interest_application.AccrualAccountFetchersConfig(
            balance_fetcher_id=None,
            param_fetcher_id=ACCRUAL_ACCOUNT_PARAMS_POF_ID,
            accrued_payable_acc_param_id=interest_accrual.ACCRUED_INTEREST_PAYABLE_ACCOUNT_PARAM_ID,
            accrued_receivable_acc_param_id=interest_accrual.ACCRUED_INTEREST_RECEIVABLE_ACCOUNT_PARAM_ID,
        )

        schedule_logic_result = interest_application.schedule_logic(
            state=state,
            account_type="interest_application",
            accrual_fetchers_config=accrual_fetchers_config,
        )

        custom_instructions.extend(schedule_logic_result.custom_instructions)
        event_type_directives.extend(schedule_logic_result.event_type_directives)
        notification_directives.extend(schedule_logic_result.notification_directives)

    return ScheduledEventHookResult(
        posting_instructions_directives=(
            [
                PostingInstructionsDirective(
                    posting_instructions=custom_instructions,
                    value_datetime=state.effective_datetime,
                )
            ]
            if custom_instructions
            else None
        ),
        update_account_event_type_directives=event_type_directives or None,
        account_notification_directives=notification_directives or None,
    )
