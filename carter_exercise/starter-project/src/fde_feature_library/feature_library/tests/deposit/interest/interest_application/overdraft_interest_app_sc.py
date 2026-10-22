import feature_library.common.application_precision as application_precision
import feature_library.common.denomination as denomination
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.interest.interest_accrual as interest_accrual
import feature_library.deposit.interest.interest_application as interest_application
import feature_library.deposit.interest.secondary.overdraft_interest as overdraft_interest

from contracts_api import (
    AccountNotificationDirective,
    ActivationHookArguments,
    ActivationHookResult,
    CustomInstruction,
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
display_name = "Liability Account with Overdraft Interest Application"
summary = "Liability Account with Overdraft Interest Application"
tside = Tside.LIABILITY

event_types = [
    *interest_application.event_types("interest_application"),
]

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *denomination.expected_parameters,
        *interest_application.expected_parameters,
        *interest_accrual.expected_parameters,
        *overdraft_interest.expected_parameters,
        application_precision.APPLICATION_PRECISION_PARAM,
    ]
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *denomination.data_fetchers,
        *interest_application.data_fetchers,
        *interest_accrual.data_fetchers,
        *overdraft_interest.data_fetchers,
    ]
)


@fetch_account_data(
    parameters=[
        interest_application.INTEREST_APPLICATION_PARAMS_ET_POF_ID,
        overdraft_interest.OVERDRAFT_INTEREST_POF_ID,
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
            **overdraft_interest.get_parameters(vault),
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
        interest_accrual.INTEREST_ACCRUAL_PARAMS_ET_POF_ID,
        overdraft_interest.OVERDRAFT_INTEREST_POF_ID,
        denomination.DENOMINATION_ET_POF_ID,
    ],
    balances=["all_balances_et_bof"],
)
def scheduled_event_hook(
    vault: SmartContractVault, hook_arguments: ScheduledEventHookArguments
) -> ScheduledEventHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters={
            **interest_application.get_parameters(vault),
            **overdraft_interest.get_parameters(vault),
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
        schedule_logic_result = interest_application.schedule_logic(
            state=state,
            account_type="interest_application",
            interest_types=[
                interest_accrual.InterestTypeConfig(
                    interest_type=overdraft_interest.InterestType,
                    fetchers_config=overdraft_interest.DEFAULT_OVERDRAFT_INTEREST_FETCHERS_CONFIG,
                )
            ],
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
