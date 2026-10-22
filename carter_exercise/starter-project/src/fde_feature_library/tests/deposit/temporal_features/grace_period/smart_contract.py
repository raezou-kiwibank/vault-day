# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
import feature_library.common.denomination as denomination
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.temporal_features.grace_period as grace_period

from contracts_api import (
    AccountNotificationDirective,
    ActivationHookArguments,
    ActivationHookResult,
    ExpectedParameter,
    PreParameterChangeHookArguments,
    PreParameterChangeHookResult,
    PrePostingHookArguments,
    PrePostingHookResult,
    Rejection,
    RejectionReason,
    ScheduledEventHookArguments,
    ScheduledEventHookResult,
    Tside,
    fetch_account_data,
)

from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

api = "4.0.0"
version = "0.0.1"
display_name = "Liability Account with Grace Period"
summary = "Liability Account with Grace Period"
tside = Tside.LIABILITY

PRODUCT_NAME = "grace_period"

notification_types = [
    grace_period.notification_type(product_name=PRODUCT_NAME),
]
event_types = [
    *grace_period.event_types(product_name=PRODUCT_NAME),
]

TERM_PARAM_ID = "&{term}"
TERM_PARAM = ExpectedParameter(
    id=TERM_PARAM_ID,
    triggers_pre_parameter_change_hook=True,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *denomination.expected_parameters,
        *grace_period.expected_parameters,
        TERM_PARAM,
    ]
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *denomination.data_fetchers,
        *grace_period.data_fetchers,
        *fetchers.data_fetchers,
    ]
)


@fetch_account_data(
    parameters=[
        denomination.DENOMINATION_ET_POF_ID,
        grace_period.GRACE_PERIOD_PARAMS_ET_POF_ID,
    ]
)
def activation_hook(
    vault: SmartContractVault, hook_arguments: ActivationHookArguments
) -> ActivationHookResult | None:
    state = state_utils.initialise_state(
        vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination.get_parameters(vault),
    )

    scheduled_events = grace_period.get_scheduled_events(state=state)

    return ActivationHookResult(
        scheduled_events_return_value=scheduled_events,
    )


@fetch_account_data(
    parameters=[
        denomination.DENOMINATION_ET_POF_ID,
        grace_period.GRACE_PERIOD_PARAMS_ET_POF_ID,
    ],
    balances=[fetchers.ALL_BALANCES_ET_BOF_ID],
)
def pre_posting_hook(
    vault: SmartContractVault, hook_arguments: PrePostingHookArguments
) -> PrePostingHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination.get_parameters(vault),
        balances=vault.get_balances_observation(
            fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID
        ).balances,
    )

    # First validate deposit
    if rejection := grace_period.validate_deposit(
        state=state,
        posting_instructions=hook_arguments.posting_instructions,
    ):
        return PrePostingHookResult(rejection=rejection)

    # Reject withdrawals subject to fees to easily test the boolean return
    if grace_period.is_withdrawal_subject_to_fees(
        state=state,
        posting_instructions=hook_arguments.posting_instructions,
    ):
        return PrePostingHookResult(
            rejection=Rejection(
                message="Withdrawal is subject to fees",
                reason_code=RejectionReason.AGAINST_TNC,
            )
        )

    return PrePostingHookResult()


@fetch_account_data(
    event_type=grace_period.GRACE_PERIOD_END_EVENT,
    parameters=[
        denomination.DENOMINATION_ET_POF_ID,
        grace_period.GRACE_PERIOD_PARAMS_ET_POF_ID,
    ],
    balances=[fetchers.ALL_BALANCES_ET_BOF_ID],
)
def scheduled_event_hook(
    vault: SmartContractVault, hook_arguments: ScheduledEventHookArguments
) -> ScheduledEventHookResult:

    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination.get_parameters(vault),
        balances=vault.get_balances_observation(
            fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID
        ).balances,
    )

    notification_directives: list[AccountNotificationDirective] = []

    event_type = hook_arguments.event_type

    if event_type == grace_period.GRACE_PERIOD_END_EVENT:
        notification_directives.extend(
            grace_period.handle_account_closure_notification(state=state, product_name=PRODUCT_NAME)
        )

    return ScheduledEventHookResult(
        account_notification_directives=notification_directives if notification_directives else None
    )


@fetch_account_data(
    parameters=[
        denomination.DENOMINATION_ET_POF_ID,
        grace_period.GRACE_PERIOD_PARAMS_ET_POF_ID,
    ]
)
def pre_parameter_change_hook(
    vault: SmartContractVault, hook_arguments: PreParameterChangeHookArguments
) -> PreParameterChangeHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination.get_parameters(vault),
    )

    if rejection := grace_period.validate_term_parameter_change(state=state):
        return PreParameterChangeHookResult(rejection=rejection)

    return PreParameterChangeHookResult()
