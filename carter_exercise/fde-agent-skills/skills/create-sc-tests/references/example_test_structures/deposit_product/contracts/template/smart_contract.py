# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
import feature_library.common.denomination as denomination
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.temporal_features.cooling_off_period as cooling_off_period

from contracts_api import (
    AccountNotificationDirective,
    AttributeHookArguments,
    AttributeHookResult,
    PostPostingHookArguments,
    PostPostingHookResult,
    Tside,
    fetch_account_data,
)

from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

api = "4.0.0"
version = "0.0.1"
display_name = "Liability Account with Cooling Off Period"
summary = "Liability Account with Cooling Off Period"
tside = Tside.LIABILITY

PRODUCT_NAME = "cooling_off_period"

# Notification for testing
WITHDRAWAL_SUBJECT_TO_FEES = "WITHDRAWAL_SUBJECT_TO_FEES"

notification_types = [WITHDRAWAL_SUBJECT_TO_FEES]

attributes = [
    *cooling_off_period.attributes,
]

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *denomination.expected_parameters,
        *cooling_off_period.expected_parameters,
    ]
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *denomination.data_fetchers,
        *cooling_off_period.data_fetchers,
        *fetchers.data_fetchers,
    ]
)


@fetch_account_data(
    parameters=[
        denomination.DENOMINATION_ET_POF_ID,
        cooling_off_period.COOLING_OFF_PERIOD_PARAMS_ET_POF_ID,
    ],
    balances=[fetchers.ALL_BALANCES_ET_BOF_ID],
)
def post_posting_hook(
    vault: SmartContractVault, hook_arguments: PostPostingHookArguments
) -> PostPostingHookResult | None:
    state = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination.get_parameters(vault),
        balances=vault.get_balances_observation(
            fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID
        ).balances,
    )

    if cooling_off_period.is_withdrawal_subject_to_fees(
        state=state,
        posting_instructions=hook_arguments.posting_instructions,
    ):
        return PostPostingHookResult(
            account_notification_directives=[
                AccountNotificationDirective(
                    notification_type=WITHDRAWAL_SUBJECT_TO_FEES,
                    notification_details={"account_id": vault.account_id},
                )
            ]
        )

    return PostPostingHookResult()


@fetch_account_data(
    attribute_name=cooling_off_period.COOLING_OFF_PERIOD_END_DATE_ATTR_ID,
    parameters=[
        denomination.DENOMINATION_ET_POF_ID,
        cooling_off_period.COOLING_OFF_PERIOD_PARAMS_ET_POF_ID,
    ],
)
def attribute_hook(
    vault: SmartContractVault, hook_arguments: AttributeHookArguments
) -> AttributeHookResult | None:

    if hook_arguments.attribute_name == cooling_off_period.COOLING_OFF_PERIOD_END_DATE_ATTR_ID:
        return cooling_off_period.cooling_off_period_end_date_attribute_handler(
            vault=vault, hook_arguments=hook_arguments
        )

    return None
