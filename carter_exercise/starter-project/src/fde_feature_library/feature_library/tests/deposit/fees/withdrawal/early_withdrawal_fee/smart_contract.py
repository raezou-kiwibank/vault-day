import feature_library.common.calendar_utils as calendar_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.parameter_utils as parameter_utils
import feature_library.common.state_utils as state_utils
import feature_library.deposit.fees.withdrawal.early_withdrawal_fees as early_withdrawal_fees  # noqa: E501

from contracts_api import (
    AttributeHookArguments,
    AttributeHookResult,
    PostingInstructionsDirective,
    PostPostingHookArguments,
    PostPostingHookResult,
    PrePostingHookArguments,
    PrePostingHookResult,
    Tside,
    fetch_account_data,
)

from inception_sdk.vault.contracts.extensions.contracts_api_extensions.vault_types import (
    SmartContractVault,
)

api = "4.0.0"
version = "0.0.1"
display_name = "Liability Account with Withdrawal Fees."
summary = "Liability Account with Withdrawal Fees"
tside = Tside.LIABILITY

PRODUCT_NAME = "liability_account_early_withdrawal_fees"

attributes = [
    *early_withdrawal_fees.attributes,
]

expected_parameters = parameter_utils.distinct_expected_parameters(
    [
        *denomination_module.expected_parameters,
        *early_withdrawal_fees.expected_parameters,
    ]
)

data_fetchers = fetchers.distinct_fetchers(
    [
        *calendar_utils.data_fetchers,
        *denomination_module.data_fetchers,
        *early_withdrawal_fees.data_fetchers,
    ]
)

notification_types = [*early_withdrawal_fees.get_notification_types(PRODUCT_NAME)]


@fetch_account_data(
    parameters=[
        denomination_module.DENOMINATION_ET_POF_ID,
        early_withdrawal_fees.WITHDRAWAL_FEES_POF_ID,
    ],
    balances=[
        fetchers.ALL_BALANCES_LIVE_BOF_ID,
    ],
    calendars=[
        calendar_utils.PUBLIC_HOLIDAYS_COF_ID,
    ],
)
def pre_posting_hook(
    vault: SmartContractVault, hook_arguments: PrePostingHookArguments
) -> PrePostingHookResult | None:
    # Initialise state
    state: state_utils.SmartContractState = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination_module.get_parameters(vault),
    )

    if rejection := early_withdrawal_fees.validate(
        state=state, posting_instructions=hook_arguments.posting_instructions
    ):
        return PrePostingHookResult(rejection=rejection)

    return None


@fetch_account_data(
    parameters=[
        denomination_module.DENOMINATION_ET_POF_ID,
        early_withdrawal_fees.WITHDRAWAL_FEES_POF_ID,
    ],
    balances=[
        fetchers.ALL_BALANCES_LIVE_BOF_ID,
    ],
    calendars=[calendar_utils.PUBLIC_HOLIDAYS_COF_ID],
)
def post_posting_hook(
    vault: SmartContractVault, hook_arguments: PostPostingHookArguments
) -> PostPostingHookResult | None:
    # Initialise state
    state: state_utils.SmartContractState = state_utils.initialise_state(
        vault=vault,
        effective_datetime=hook_arguments.effective_datetime,
        parameters=denomination_module.get_parameters(vault),
    )
    result = early_withdrawal_fees.handle_withdrawals(
        state=state,
        posting_instructions=hook_arguments.posting_instructions,
        product_name=PRODUCT_NAME,
    )

    if result.custom_instructions:
        return PostPostingHookResult(
            account_notification_directives=result.account_notification_directives,
            posting_instructions_directives=[
                PostingInstructionsDirective(
                    posting_instructions=result.custom_instructions,
                    value_datetime=hook_arguments.effective_datetime,
                )
            ],
        )

    return None


@fetch_account_data(
    attribute_name=early_withdrawal_fees.FEE_FREE_WITHDRAWAL_LIMIT_ATTR_ID,
    balances=[fetchers.ALL_BALANCES_LIVE_BOF_ID],
    parameters=[
        denomination_module.DENOMINATION_ET_POF_ID,
        early_withdrawal_fees.WITHDRAWAL_FEES_POF_ID,
    ],
)
@fetch_account_data(
    attribute_name=early_withdrawal_fees.MAXIMUM_WITHDRAWAL_LIMIT_ATTR_ID,
    balances=[fetchers.ALL_BALANCES_LIVE_BOF_ID],
    parameters=[
        denomination_module.DENOMINATION_ET_POF_ID,
        early_withdrawal_fees.WITHDRAWAL_FEES_POF_ID,
    ],
)
def attribute_hook(
    vault: SmartContractVault, hook_arguments: AttributeHookArguments
) -> AttributeHookResult:
    attribute_handlers = {
        early_withdrawal_fees.FEE_FREE_WITHDRAWAL_LIMIT_ATTRIBUTE.name: early_withdrawal_fees.fee_free_withdrawal_limit_attribute_handler,  # noqa: E501
        early_withdrawal_fees.MAXIMUM_WITHDRAWAL_LIMIT_ATTRIBUTE.name: early_withdrawal_fees.maximum_withdrawal_limit_attribute_handler,  # noqa: E501
    }

    return attribute_handlers[hook_arguments.attribute_name](vault, hook_arguments)
