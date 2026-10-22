# CBF: CPP-2092
__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

# features
import feature_library.common.addresses as common_addresses
import feature_library.common.balance_utils as balance_utils
import feature_library.common.calendar_utils as calendar_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.fetchers as fetchers
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.common.utils as utils
import feature_library.deposit.interfaces as deposit_interfaces

# contracts api
from contracts_api import (
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    AccountNotificationDirective,
    Attribute,
    AttributeDecimalType,
    AttributeHookArguments,
    AttributeHookResult,
    BalanceCoordinate,
    BalancesFilter,
    BalancesObservationFetcher,
    CalendarEvent,
    CustomInstruction,
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
    Phase,
    Rejection,
    RejectionReason,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Balance addresses
EARLY_WITHDRAWALS_TRACKER_ADDRESS = "EARLY_WITHDRAWALS_TRACKER"


# Fetchers
EARLY_WITHDRAWALS_TRACKER_LIVE_BOF_ID = "EARLY_WITHDRAWALS_TRACKER_LIVE_FETCHER"
EARLY_WITHDRAWALS_TRACKER_LIVE_BOF = BalancesObservationFetcher(
    fetcher_id=EARLY_WITHDRAWALS_TRACKER_LIVE_BOF_ID,
    at=DefinedDateTime.LIVE,
    filter=BalancesFilter(addresses=[EARLY_WITHDRAWALS_TRACKER_ADDRESS]),
)

# Notifications
WITHDRAWAL_FEE_SUFFIX = "_WITHDRAWAL_FEE"

# Parameters
EARLY_WITHDRAWAL_FLAT_FEE_PARAM_ID = "&{early_withdrawal_flat_fee}"
EARLY_WITHDRAWAL_PERCENTAGE_FEE_PARAM_ID = "&{early_withdrawal_percentage_fee}"
MAXIMUM_WITHDRAWAL_PERCENTAGE_LIMIT_PARAM_ID = "&{maximum_withdrawal_percentage_limit}"
FEE_FREE_WITHDRAWAL_PERCENTAGE_LIMIT_PARAM_ID = "&{fee_free_withdrawal_percentage_limit}"

EARLY_WITHDRAWAL_FLAT_FEE_PARAM = ExpectedParameter(
    id=EARLY_WITHDRAWAL_FLAT_FEE_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

EARLY_WITHDRAWAL_PERCENTAGE_FEE_PARAM = ExpectedParameter(
    id=EARLY_WITHDRAWAL_PERCENTAGE_FEE_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

MAXIMUM_WITHDRAWAL_PERCENTAGE_LIMIT_PARAM = ExpectedParameter(
    id=MAXIMUM_WITHDRAWAL_PERCENTAGE_LIMIT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

FEE_FREE_WITHDRAWAL_PERCENTAGE_LIMIT_PARAM = ExpectedParameter(
    id=FEE_FREE_WITHDRAWAL_PERCENTAGE_LIMIT_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    EARLY_WITHDRAWAL_FLAT_FEE_PARAM,
    EARLY_WITHDRAWAL_PERCENTAGE_FEE_PARAM,
    MAXIMUM_WITHDRAWAL_PERCENTAGE_LIMIT_PARAM,
    FEE_FREE_WITHDRAWAL_PERCENTAGE_LIMIT_PARAM,
    denomination_module.DENOMINATION_PARAM,
]

# Attributes
MAXIMUM_WITHDRAWAL_LIMIT_ATTR_ID = "maximum_withdrawal_limit"
MAXIMUM_WITHDRAWAL_LIMIT_ATTRIBUTE = Attribute(
    name=MAXIMUM_WITHDRAWAL_LIMIT_ATTR_ID,
    data_type=AttributeDecimalType(),
)

FEE_FREE_WITHDRAWAL_LIMIT_ATTR_ID = "fee_free_withdrawal_limit"
FEE_FREE_WITHDRAWAL_LIMIT_ATTRIBUTE = Attribute(
    name=FEE_FREE_WITHDRAWAL_LIMIT_ATTR_ID,
    data_type=AttributeDecimalType(),
)

attributes = [
    MAXIMUM_WITHDRAWAL_LIMIT_ATTRIBUTE,
    FEE_FREE_WITHDRAWAL_LIMIT_ATTRIBUTE,
]

# Fetchers
WITHDRAWAL_FEES_POF_ID = "withdrawal_fees_pof"
WITHDRAWAL_FEES_POF = ParametersObservationFetcher(
    fetcher_id=WITHDRAWAL_FEES_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[p.id for p in expected_parameters]),
)
data_fetchers = [fetchers.ALL_BALANCES_LIVE_BOF, WITHDRAWAL_FEES_POF]


HandleWithdrawalsResult = NamedTuple(
    "HandleWithdrawalsResult",
    [
        ("custom_instructions", list[CustomInstruction]),
        ("account_notification_directives", list[AccountNotificationDirective]),
    ],
)

WithdrawalFeeAmounts = NamedTuple(
    "WithdrawalFeeAmounts",
    [
        ("flat_fee", Decimal),
        ("percentage_fee", Decimal),
    ],
)

WithdrawalFeesFetchersConfig = NamedTuple(
    "WithdrawalFeesFetchersConfig",
    [
        ("balance_fetcher_id", str),
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
        ("precision", int),
    ],
)

DEFAULT_WITHDRAWAL_FEES_FETCHERS_CONFIG = WithdrawalFeesFetchersConfig(
    balance_fetcher_id=fetchers.ALL_BALANCES_LIVE_BOF_ID,
    param_fetcher_id=WITHDRAWAL_FEES_POF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM.id,
    precision=2,
)


def notification_type(product_name: str) -> str:
    """Returns a notification type.

    :param product_name: the product name
    :return: notification type.
    """
    return f"{product_name.upper()}{WITHDRAWAL_FEE_SUFFIX}"


def get_notification_types(product_name: str) -> list[str]:
    """Generates all the notification types for this Feature module.

    Args:
        product_name (str): the product represented by the calling Smart Contract.

    Returns:
        list[str]: generates all the notification types for this Feature module, based on the
        product name.
    """
    return [notification_type(product_name)]


def get_parameters(
    vault: SmartContractVault, param_fetcher_id: str = WITHDRAWAL_FEES_POF_ID
) -> dict[str, datetime | Decimal | str | None]:
    """Retrieves configuration parameters for the withdrawal fees feature.

    Args:
        vault: The SmartContractVault instance to query.
        param_fetcher_id: The unique identifier for the parameter fetcher.
            Defaults to `WITHDRAWAL_FEES_POF_ID`.

    Returns:
        Parameters for the withdrawal fees feature.
        (datetime, Decimal, string, or None).
    """
    return vault.get_parameters_observation(fetcher_id=param_fetcher_id).parameters


def _append_to_state(
    state: state_utils.SmartContractState,
    balance_fetcher_id: str = fetchers.ALL_BALANCES_LIVE_BOF_ID,
    param_fetcher_id: str = WITHDRAWAL_FEES_POF_ID,
) -> state_utils.SmartContractState:
    """Extends the Smart Contract state with vault parameters and balance observations.

    This helper function fetches parameter data and live balances from the vault
    associated with the current state and merges them into a new state object.

    Fetchers:
        Balances:
            LIVE_BALANCES_BOF_ID: Used to retrieve current vault balances.
        Parameters:
            WITHDRAWAL_FEES_POF_ID: Used to retrieve vault parameter observations.

    Args:
        state (SmartContractState): The current state object containing the vault reference.
        balance_fetcher_id (str): The ID of the fetcher used to observe balances.
            Defaults to LIVE_BALANCES_BOF_ID.
        param_fetcher_id (str): The ID of the fetcher used to observe parameters.
            Defaults to WITHDRAWAL_FEES_POF_ID.

    Returns:
        SmartContractState: A new state object updated with the fetched parameters
            and balances.
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, param_fetcher_id),
        balances=state.vault.get_balances_observation(fetcher_id=balance_fetcher_id).balances,
    )


# Posting helpers
def validate(
    state: state_utils.SmartContractState,
    posting_instructions: posting_utils.PostingInstructionListAlias,
    balance_adjustments: list[deposit_interfaces.DefaultBalanceAdjustment] | None = None,
    fetchers_config: WithdrawalFeesFetchersConfig = DEFAULT_WITHDRAWAL_FEES_FETCHERS_CONFIG,
) -> Rejection | None:
    """For use in the pre_posting_hook.

    Deposits are accepted with no validation.
    Reject the posting instructions if any of the following conditions are met:
    - The withdrawal amount exceeds the available balance
    - A partial withdrawal causes the total withdrawal amount to exceed the maximum withdrawal limit
    - The withdrawal occurs on a public holiday and the posting does not include
      `"calendar_override": "true"` in the metadata
    - The withdrawal amount is less than the incurred withdrawal fee amount.

    :param state: the SmartContractState containing the vault and balances
    :param posting_instructions: list of posting instructions to validate
    :param balance_adjustments: list of balance adjustments that impact the default balance,
    used when calculating the customer deposited amount. The customer deposited amount is the sum
    of the DEFAULT balance, EARLY_WITHDRAWALS_TRACKER_ADDRESS and the returned amount of each
    adjustment.
    For example, interest application adjustment should be negative, and a fee
    charge adjustment should be positive.
    :param fetchers_config: the balances and parameters fetchers configuration
    :return: rejection if any of the above conditions are met
    """
    state = _append_to_state(
        state, fetchers_config.balance_fetcher_id, fetchers_config.param_fetcher_id
    )
    if rejection := state_utils.check_parameters_exist(
        state, {fetchers_config.denomination_param_id}
    ):
        return rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    withdrawal_amount: Decimal = balance_utils.net_debit(
        balance_utils.get_available_balance(
            balances=posting_utils.get_posting_instructions_balances(
                posting_instructions=posting_instructions
            ),
            denomination=denomination,
        )
    )

    # Deposits skip validation.
    if withdrawal_amount <= Decimal(0):
        return None

    if rejection := _validate_withdrawal_date(
        state=state, posting_instructions=posting_instructions
    ):
        return rejection

    # Check for sufficient funds
    if rejection := _validate_available_balance(
        state=state,
        withdrawal_amount=withdrawal_amount,
        fetchers_config=fetchers_config,
    ):
        return rejection

    # Check if the user has hit their early withdrawal ceiling
    if rejection := _validate_withdrawal_limit(
        state=state,
        withdrawal_amount=withdrawal_amount,
        balance_adjustments=balance_adjustments,
        fetchers_config=fetchers_config,
    ):
        return rejection

    if rejection := _validate_withdrawal_covers_fees(
        state=state,
        withdrawal_amount=withdrawal_amount,
        balance_adjustments=balance_adjustments,
        fetchers_config=fetchers_config,
    ):
        return rejection

    return None


def _validate_withdrawal_date(
    state: state_utils.SmartContractState,
    posting_instructions: posting_utils.PostingInstructionListAlias,
    calendar_fetcher_id: str = calendar_utils.PUBLIC_HOLIDAYS_COF.fetcher_id,
) -> Rejection | None:
    """Checks if a withdrawal falls on a public holiday and validates override permissions.

    :param state: the SmartContractState containing the vault and calendar events
    :param posting_instructions: the posting instructions to check for calendar override
    :param calendar_fetcher_id: the fetcher ID for the calendar events
    :return: rejection if the withdrawal date is a holiday and no override is provided
    """
    # 1. Fetch public holiday schedule
    calendar_events: list[CalendarEvent] = state.vault.get_calendars_observation(
        fetcher_id=calendar_fetcher_id,
    ).calendars["&{PUBLIC_HOLIDAYS}"]

    # 2. Check for the override flag in the instruction details
    is_calendar_override: bool = posting_utils.is_key_in_instruction_details(
        key="calendar_override", posting_instructions=posting_instructions
    )
    if is_calendar_override:
        return None

    # 3. Evaluate restriction logic
    is_holiday: bool = calendar_utils.falls_on_calendar_events(
        effective_datetime=state.effective_datetime, calendar_events=calendar_events
    )

    if is_holiday:
        return Rejection(
            message="Cannot withdraw on public holidays.",
            reason_code=RejectionReason.AGAINST_TNC,
        )

    return None


def _validate_available_balance(
    state: state_utils.SmartContractState,
    withdrawal_amount: Decimal,
    fetchers_config: WithdrawalFeesFetchersConfig = DEFAULT_WITHDRAWAL_FEES_FETCHERS_CONFIG,
) -> Rejection | None:
    """Validates that the account has sufficient funds to cover the withdrawal.

    :param state: the SmartContractState containing the vault and balances
    :param withdrawal_amount: the amount of the withdrawal to validate
    :param fetchers_config: the balances and parameters fetchers configuration
    :return: rejection if the withdrawal exceeds the available balance
    """
    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    # 1. Fetch the actual liquid balance currently in the account
    current_balance: Decimal = balance_utils.net_credit(
        balance_utils.get_current_net_balance(balances=state.balances, denomination=denomination)
    )

    # 2. Compare requested amount against reality
    if withdrawal_amount > current_balance:
        return Rejection(
            message=(
                f"The withdrawal amount of {withdrawal_amount} {denomination} "
                f"exceeds the available balance of {current_balance} {denomination}."
            ),
            reason_code=RejectionReason.INSUFFICIENT_FUNDS,
        )

    return None


def _validate_withdrawal_limit(
    state: state_utils.SmartContractState,
    withdrawal_amount: Decimal,
    balance_adjustments: list[deposit_interfaces.DefaultBalanceAdjustment] | None = None,
    fetchers_config: WithdrawalFeesFetchersConfig = DEFAULT_WITHDRAWAL_FEES_FETCHERS_CONFIG,
) -> Rejection | None:
    """Validates if the current withdrawal exceeds the remaining allowed limit.

    Based on the EARLY_WITHDRAWALS_TRACKER_ADDRESS.

    :param state: the SmartContractState containing the vault and balances
    :param withdrawal_amount: the amount of the withdrawal to validate
    :param balance_adjustments: list of balance adjustments that impact the default balance
    :param fetchers_config: the balances and parameters fetchers configuration
    :return: rejection if the withdrawal exceeds the maximum withdrawal limit
    """
    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    # 1. Determine the absolute ceiling for withdrawals
    maximum_withdrawal_limit = _calculate_maximum_withdrawal_limit(
        state=state,
        balance_adjustments=balance_adjustments,
        fetchers_config=fetchers_config,
    )

    # 2. Fetch the 'used' amount from the specific balance tracker
    used_withdrawals: Decimal = balance_utils.net_credit(
        state.balances[
            BalanceCoordinate(
                EARLY_WITHDRAWALS_TRACKER_ADDRESS, DEFAULT_ASSET, denomination, Phase.COMMITTED
            )
        ]
    )

    # 3. Calculate remaining headroom
    available_withdrawal_limit: Decimal = maximum_withdrawal_limit - used_withdrawals

    # 4. Reject if the request exceeds available capacity
    if withdrawal_amount > available_withdrawal_limit:
        return Rejection(
            message=(
                f"The withdrawal amount of {withdrawal_amount} {denomination} "
                f"would exceed the available withdrawal limit of "
                f"{available_withdrawal_limit} {denomination}."
            ),
            reason_code=RejectionReason.AGAINST_TNC,
        )

    return None


def _validate_withdrawal_covers_fees(
    state: state_utils.SmartContractState,
    withdrawal_amount: Decimal,
    balance_adjustments: list[deposit_interfaces.DefaultBalanceAdjustment] | None = None,
    fetchers_config: WithdrawalFeesFetchersConfig = DEFAULT_WITHDRAWAL_FEES_FETCHERS_CONFIG,
) -> Rejection | None:
    """Validates that the withdrawal amount is sufficient to cover the fees.

    Associated transaction fees are calculated.

    :param state: the SmartContractState containing the vault and balances
    :param withdrawal_amount: the amount of the withdrawal to validate
    :param balance_adjustments: list of balance adjustments that impact the default balance
    :param fetchers_config: the balances and parameters fetchers configuration
    :return: rejection if the withdrawal fees exceed the withdrawal amount
    """
    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    # 1. Calculate the breakdown of fees
    withdrawal_fee_amounts = calculate_withdrawal_fee_amounts(
        state=state,
        withdrawal_amount=withdrawal_amount,
        balance_adjustments=balance_adjustments,
        precision=fetchers_config.precision,
    )

    total_fee_amount = withdrawal_fee_amounts.flat_fee + withdrawal_fee_amounts.percentage_fee

    # 2. Ensure the user isn't withdrawing less than what the fee costs
    if withdrawal_amount < total_fee_amount:
        return Rejection(
            message=(
                f"The withdrawal fees of {total_fee_amount} {denomination} "
                f"are not covered by the withdrawal amount of "
                f"{withdrawal_amount} {denomination}."
            ),
            reason_code=RejectionReason.INSUFFICIENT_FUNDS,
        )

    return None


def handle_withdrawals(
    state: state_utils.SmartContractState,
    posting_instructions: posting_utils.PostingInstructionListAlias,
    product_name: str,
    balance_adjustments: list[deposit_interfaces.DefaultBalanceAdjustment] | None = None,
    fetchers_config: WithdrawalFeesFetchersConfig = DEFAULT_WITHDRAWAL_FEES_FETCHERS_CONFIG,
) -> HandleWithdrawalsResult:
    """For use in the post_posting_hook.

    For a withdrawal:
    - Create instruction to track the withdrawal on the EARLY_WITHDRAWALS_TRACKER_ADDRESS address
    - Generate the withdrawal fee notification to be used by the bank to orchestrate the
      fee charging externally.

    :param state: the SmartContractState containing the vault and balances
    :param posting_instructions: list of posting instructions containing the withdrawal
    :param product_name: the product name
    :param balance_adjustments: list of balance adjustments that impact the default balance,
    used when calculating the customer deposited amount. The customer deposited amount is the sum
    of the DEFAULT balance, EARLY_WITHDRAWALS_TRACKER_ADDRESS and the returned amount of each
    adjustment.
    For example, interest application adjustment should be negative, and a fee
    charge adjustment should be positive.
    :param fetchers_config: the balances and parameters fetchers configuration
    :return: result object containing a rejection if inputs were invalid, otherwise posting
    instructions and notifications.
    """
    state = _append_to_state(
        state, fetchers_config.balance_fetcher_id, fetchers_config.param_fetcher_id
    )
    rejection = state_utils.check_parameters_exist(state, {fetchers_config.denomination_param_id})
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    posting_amount: Decimal = balance_utils.net_debit(
        balance_utils.get_available_balance(
            balances=posting_utils.get_posting_instructions_balances(
                posting_instructions=posting_instructions
            ),
            denomination=denomination,
        )
    )

    # Only withdrawals need to be handled
    is_withdrawal = posting_amount > Decimal(0)
    if not is_withdrawal:
        return HandleWithdrawalsResult(custom_instructions=[], account_notification_directives=[])

    withdrawal_amount = abs(posting_amount)

    withdrawal_tracker_instructions = _update_tracked_withdrawals(
        account_id=state.vault.account_id,
        withdrawal_amount=withdrawal_amount,
        denomination=denomination,
        effective_datetime=state.effective_datetime,
    )

    current_withdrawal_amount_adjustment = get_current_withdrawal_amount_default_balance_adjustment(
        withdrawal_amount=withdrawal_amount,
    )
    balance_adjustments = balance_adjustments.copy() if balance_adjustments else []
    balance_adjustments.append(current_withdrawal_amount_adjustment)

    withdrawal_fee_amounts = calculate_withdrawal_fee_amounts(
        state=state,
        withdrawal_amount=withdrawal_amount,
        balance_adjustments=balance_adjustments,
    )

    withdrawal_fee_notifications = [
        generate_withdrawal_fee_notification(
            account_id=state.vault.account_id,
            denomination=denomination,
            withdrawal_amount=withdrawal_amount,
            flat_fee_amount=withdrawal_fee_amounts.flat_fee,
            percentage_fee_amount=withdrawal_fee_amounts.percentage_fee,
            product_name=product_name,
            client_batch_id=posting_instructions[0].client_batch_id,  # type: ignore
            precision=fetchers_config.precision,
        )
    ]

    return HandleWithdrawalsResult(
        custom_instructions=withdrawal_tracker_instructions,
        account_notification_directives=withdrawal_fee_notifications,
    )


def get_current_withdrawal_amount_default_balance_adjustment(
    withdrawal_amount: Decimal,
) -> deposit_interfaces.DefaultBalanceAdjustment:
    """The customer deposited amount is the sum of the DEFAULT balance.

    EARLY_WITHDRAWALS_TRACKER_ADDRESS and the returned amount of each adjustment. However, in
    post-posting the DEFAULT balance has current withdrawal deducted, and the
    EARLY_WITHDRAWALS_TRACKER_ADDRESS has not yet been updated to reflect the impact of this
    withdrawal.
    When calculating the fee amounts, we take previous withdrawals into consideration, so updating
    the withdrawals tracker to reflect the current withdrawal would incorrectly imply that the
    current withdrawal has already been processed, hence updating the balances with the
    withdrawal_tracker_instructions is not suitable.
    Instead, we provide a Default Balance Adjustment which returns the withdrawal amount, which
    will allow the customer deposited amount to be calculated correctly.

    :param withdrawal_amount: the absolute amount withdrawn from the account in this transaction
    :return: the default balance adjustment which accounts for the current withdrawal amount
    """
    return deposit_interfaces.DefaultBalanceAdjustment(
        calculate_balance_adjustment=lambda **_: withdrawal_amount
    )


# Account Attribute helpers
def maximum_withdrawal_limit_attribute_handler(
    vault: SmartContractVault,
    hook_arguments: AttributeHookArguments,
    fetchers_config: WithdrawalFeesFetchersConfig = DEFAULT_WITHDRAWAL_FEES_FETCHERS_CONFIG,
) -> AttributeHookResult:
    """Get the maximum withdrawal limit for the derived parameter value.

    :param vault: the Vault object for the account
    :param hook_arguments: the attribute hook arguments
    :param fetchers_config: the balances and parameters fetchers configuration
    :return: attribute hook result containing the maximum withdrawal limit
    """
    balance_adjustments: list[deposit_interfaces.DefaultBalanceAdjustment] | None = None

    state: state_utils.SmartContractState = _append_to_state(
        state_utils.initialise_state(
            vault=vault,
            effective_datetime=hook_arguments.effective_datetime,
            parameters=denomination_module.get_parameters(vault),
        ),
        fetchers_config.balance_fetcher_id,
        fetchers_config.param_fetcher_id,
    )

    result = _calculate_maximum_withdrawal_limit(
        state=state,
        balance_adjustments=balance_adjustments,
        fetchers_config=fetchers_config,
    )

    return AttributeHookResult(attribute_value=result)


def fee_free_withdrawal_limit_attribute_handler(
    vault: SmartContractVault,
    hook_arguments: AttributeHookArguments,
    fetchers_config: WithdrawalFeesFetchersConfig = DEFAULT_WITHDRAWAL_FEES_FETCHERS_CONFIG,
) -> AttributeHookResult:
    """Get the fee free withdrawal limit for the derived parameter value.

    :param vault: the Vault object for the account
    :param hook_arguments: the attribute hook arguments
    :param fetchers_config: the balances and parameters fetchers configuration
    :return: attribute hook result containing the fee free withdrawal limit
    """
    balance_adjustments: list[deposit_interfaces.DefaultBalanceAdjustment] | None = None

    state: state_utils.SmartContractState = _append_to_state(
        state_utils.initialise_state(
            vault=vault,
            effective_datetime=hook_arguments.effective_datetime,
            parameters=denomination_module.get_parameters(vault),
        ),
        fetchers_config.balance_fetcher_id,
        fetchers_config.param_fetcher_id,
    )

    result = _calculate_fee_free_withdrawal_limit(
        state=state,
        balance_adjustments=balance_adjustments,
        fetchers_config=fetchers_config,
    )

    return AttributeHookResult(attribute_value=result)


# Withdrawals Tracker helpers
def reset_withdrawals_tracker(
    state: state_utils.SmartContractState,
    balance_fetcher_id: str = EARLY_WITHDRAWALS_TRACKER_LIVE_BOF_ID,
    param_fetcher_id: str = WITHDRAWAL_FEES_POF.fetcher_id,
    denomination_param_id: str = denomination_module.DENOMINATION_PARAM.id,
) -> list[CustomInstruction]:
    """Create postings to net-off the withdrawals tracker balance.

    :param state: the SmartContractState containing the vault and balances
    :param balance_fetcher_id: id of the balance fetcher
    :param param_fetcher_id: id of the parameter fetcher
    :param denomination_param_id: parameter id for the denomination
    :return: list of posting instructions for netting off the withdrawals tracker.
    """
    state = _append_to_state(state, balance_fetcher_id, param_fetcher_id)
    rejection = state_utils.check_parameters_exist(state, {denomination_param_id})
    assert rejection is None, rejection

    denomination: str = state.parameters[denomination_param_id]  # type: ignore
    tracker_balance: Decimal = balance_utils.net_credit(
        state.balances[
            BalanceCoordinate(
                EARLY_WITHDRAWALS_TRACKER_ADDRESS, DEFAULT_ASSET, denomination, Phase.COMMITTED
            )
        ]
    )

    return (
        [
            CustomInstruction(
                postings=posting_utils.create_postings(
                    amount=tracker_balance,
                    debit_account=state.vault.account_id,
                    credit_account=state.vault.account_id,
                    debit_address=EARLY_WITHDRAWALS_TRACKER_ADDRESS,
                    credit_address=common_addresses.INTERNAL_CONTRA,
                    denomination=denomination,
                ),
                value_datetime=state.effective_datetime,
                instruction_details={"description": "Resetting the withdrawals tracker"},
                override_all_restrictions=True,
            )
        ]
        if tracker_balance > Decimal(0)
        else []
    )


def _update_tracked_withdrawals(
    account_id: str, withdrawal_amount: Decimal, denomination: str, effective_datetime: datetime
) -> list[CustomInstruction]:
    """Create posting instructions to update the withdrawals tracker balance.

    :param account_id: id of the customer account
    :param withdrawal_amount: the absolute amount withdrawn from the account in this transaction
    :param denomination: the denomination of the account
    :param effective_datetime: datetime of the withdrawal
    :return: list of custom instructions
    """
    if withdrawal_amount > Decimal(0):
        return [
            CustomInstruction(
                postings=posting_utils.create_postings(
                    amount=withdrawal_amount,
                    debit_account=account_id,
                    credit_account=account_id,
                    debit_address=common_addresses.INTERNAL_CONTRA,
                    credit_address=EARLY_WITHDRAWALS_TRACKER_ADDRESS,
                    denomination=denomination,
                ),
                value_datetime=effective_datetime,
                instruction_details={"description": "Updating the withdrawals tracker balance"},
                override_all_restrictions=True,
            )
        ]

    return []


# Notification helpers
def generate_withdrawal_fee_notification(
    account_id: str,
    denomination: str,
    withdrawal_amount: Decimal,
    flat_fee_amount: Decimal,
    percentage_fee_amount: Decimal,
    product_name: str,
    client_batch_id: str,
    precision: int = 2,
) -> AccountNotificationDirective:
    """Generate the notification containing the respective fee amounts for a withdrawal.

    :param account_id: vault account id for which this notification is sent
    :param denomination: the denomination of the account
    :param withdrawal_amount: the absolute amount withdrawn from the account in this transaction
    :param flat_fee_amount: the flat fee amount chargeable
    :param percentage_fee_amount: the percentage fee amount chargeable
    :param product_name: the product name
    :param client_batch_id: the client_batch_id of the batch containing the withdrawal
    :param precision: the precision used for rounding calculations
    :return: the withdrawal fee account notification directive
    """

    return AccountNotificationDirective(
        notification_type=notification_type(product_name=product_name),
        notification_details={
            "account_id": account_id,
            "denomination": denomination,
            "withdrawal_amount": str(utils.round_decimal(withdrawal_amount, precision)),
            "flat_fee_amount": str(utils.round_decimal(flat_fee_amount, precision)),
            "percentage_fee_amount": str(utils.round_decimal(percentage_fee_amount, precision)),
            "total_fee_amount": str(
                utils.round_decimal(flat_fee_amount + percentage_fee_amount, precision)
            ),
            "client_batch_id": client_batch_id,
        },
    )


# Calculation helpers
def calculate_withdrawal_fee_amounts(
    state: state_utils.SmartContractState,
    withdrawal_amount: Decimal,
    balance_adjustments: list[deposit_interfaces.DefaultBalanceAdjustment] | None = None,
    precision: int = 2,
) -> WithdrawalFeeAmounts:
    """Calculate the flat fee and percentage fee amounts that are chargeable against a withdrawal.

    :param state: the SmartContractState containing the vault and balances
    :param withdrawal_amount: the absolute amount withdrawn from the account in this transaction
    :param balance_adjustments: list of balance adjustments that impact the default balance,
    used when calculating the customer deposited amount. The customer deposited amount is the sum
    of the DEFAULT balance, EARLY_WITHDRAWALS_TRACKER_ADDRESS and the returned amount of each
    adjustment.
    :param precision: the precision used for rounding calculations
    :return: an object containing the flat fee amount and the percentage fee amount.
    """
    amount_subject_to_fee = _calculate_withdrawal_amount_subject_to_fees(
        state=state,
        withdrawal_amount=withdrawal_amount,
        balance_adjustments=balance_adjustments,
    )

    if amount_subject_to_fee == Decimal(0):
        return WithdrawalFeeAmounts(Decimal(0), Decimal(0))

    flat_fee: Decimal = state.parameters[EARLY_WITHDRAWAL_FLAT_FEE_PARAM.id]  # type: ignore
    percentage_fee = utils.round_decimal(
        amount=(amount_subject_to_fee * state.parameters[EARLY_WITHDRAWAL_PERCENTAGE_FEE_PARAM.id]),  # type: ignore
        decimal_places=precision,
    )

    return WithdrawalFeeAmounts(flat_fee, percentage_fee)


def get_customer_deposit_amount(
    state: state_utils.SmartContractState,
    balance_adjustments: list[deposit_interfaces.DefaultBalanceAdjustment] | None = None,
    fetchers_config: WithdrawalFeesFetchersConfig = DEFAULT_WITHDRAWAL_FEES_FETCHERS_CONFIG,
) -> Decimal:
    """Calculate the amount the customer has deposited in the account.

    The customer deposited amount
    is the sum of the DEFAULT balance, EARLY_WITHDRAWALS_TRACKER_ADDRESS and any adjustments to the
    default balance.

    For example, interest application adjustment should be negative, and a fee
    charge adjustment should be positive.

    :param state: the SmartContractState containing the vault and balances
    :param balance_adjustments: list of balance adjustments that impact the default balance,
    used when calculating the customer deposited amount.
    :param fetchers_config: the balances and parameters fetchers configuration
    :return: the amount the customer has deposited in the account.
    """
    state = _append_to_state(
        state, fetchers_config.balance_fetcher_id, fetchers_config.param_fetcher_id
    )
    rejection = state_utils.check_parameters_exist(state, {fetchers_config.denomination_param_id})
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    default_balance: Decimal = balance_utils.net_credit(
        state.balances[
            BalanceCoordinate(DEFAULT_ADDRESS, DEFAULT_ASSET, denomination, Phase.COMMITTED)
        ]
    )
    withdrawals_tracker_balance: Decimal = balance_utils.net_credit(
        state.balances[
            BalanceCoordinate(
                EARLY_WITHDRAWALS_TRACKER_ADDRESS, DEFAULT_ASSET, denomination, Phase.COMMITTED
            )
        ]
    )

    default_balance_adjustment = (
        sum(
            balance_adjustment.calculate_balance_adjustment(
                vault=state.vault,
                balances=state.balances,
                denomination=denomination,
            )
            for balance_adjustment in balance_adjustments
        )
        if balance_adjustments is not None
        else Decimal(0)
    )

    return default_balance + withdrawals_tracker_balance + default_balance_adjustment


def _calculate_withdrawal_amount_subject_to_fees(
    state: state_utils.SmartContractState,
    withdrawal_amount: Decimal,
    balance_adjustments: list[deposit_interfaces.DefaultBalanceAdjustment] | None = None,
    fetchers_config: WithdrawalFeesFetchersConfig = DEFAULT_WITHDRAWAL_FEES_FETCHERS_CONFIG,
) -> Decimal:
    """Calculate the withdrawal amount subject to fee.

    This is the portion of the withdrawal amount
    that exceeds the fee free limit.

    :param state: the SmartContractState containing the vault and balances
    :param withdrawal_amount: the absolute amount withdrawn from the account in this transaction
    :param balance_adjustments: list of balance adjustments that impact the default balance,
    used when calculating the customer deposited amount. The customer deposited amount is the sum
    of the DEFAULT balance, EARLY_WITHDRAWALS_TRACKER_ADDRESS and the returned amount of each
    adjustment.
    :param fetchers_config: the balances and parameters fetchers configuration
    :return: the amount of the withdrawal which is subject to fees.
    """
    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore
    withdrawals_tracker_balance: Decimal = balance_utils.net_credit(
        state.balances[
            BalanceCoordinate(
                EARLY_WITHDRAWALS_TRACKER_ADDRESS, DEFAULT_ASSET, denomination, Phase.COMMITTED
            )
        ]
    )
    fee_free_withdrawal_limit = _calculate_fee_free_withdrawal_limit(
        state=state,
        balance_adjustments=balance_adjustments,
        fetchers_config=fetchers_config,
    )

    # Previous withdrawals reduce the remaining fee free limit
    # If we have exceeded the fee free limit, there is 0 fee free limit remaining
    fee_free_withdrawal_limit_remaining = max(
        fee_free_withdrawal_limit - withdrawals_tracker_balance, Decimal(0)
    )

    # If withdrawal amount is less than the remaining fee free limit, then this withdrawal
    # is not subject to fees
    return max(withdrawal_amount - fee_free_withdrawal_limit_remaining, Decimal(0))


def _calculate_maximum_withdrawal_limit(
    state: state_utils.SmartContractState,
    balance_adjustments: list[deposit_interfaces.DefaultBalanceAdjustment] | None = None,
    fetchers_config: WithdrawalFeesFetchersConfig = DEFAULT_WITHDRAWAL_FEES_FETCHERS_CONFIG,
) -> Decimal:
    """Calculate the maximum withdrawal limit as a percentage of the customer's deposited amount.

    :param state: the SmartContractState containing the vault and balances
    :param balance_adjustments: list of balance adjustments that impact the default balance,
    used when calculating the customer deposited amount. The customer deposited amount is the sum
    of the DEFAULT balance, EARLY_WITHDRAWALS_TRACKER_ADDRESS and the returned amount of each
    adjustment.
    :param fetchers_config: the balances and parameters fetchers configuration
    :return: the maximum withdrawal limit.
    """
    customer_deposit_amount = get_customer_deposit_amount(
        state=state,
        balance_adjustments=balance_adjustments,
        fetchers_config=fetchers_config,
    )

    return utils.round_decimal(
        amount=(
            customer_deposit_amount  # ty: ignore[unsupported-operator]
            * state.parameters[
                MAXIMUM_WITHDRAWAL_PERCENTAGE_LIMIT_PARAM.id
            ]  # ignore[unsupported-operator]
        ),
        decimal_places=fetchers_config.precision,
    )


def _calculate_fee_free_withdrawal_limit(
    state: state_utils.SmartContractState,
    balance_adjustments: list[deposit_interfaces.DefaultBalanceAdjustment] | None = None,
    fetchers_config: WithdrawalFeesFetchersConfig = DEFAULT_WITHDRAWAL_FEES_FETCHERS_CONFIG,
) -> Decimal:
    """Calculate the fee free withdrawal limit as a percentage of the customer's deposited amount.

    :param state: the SmartContractState containing the vault and balances
    :param balance_adjustments: list of balance adjustments that impact the default balance,
    used when calculating the customer deposited amount. The customer deposited amount is the sum
    of the DEFAULT balance, EARLY_WITHDRAWALS_TRACKER_ADDRESS and the returned amount of each
    adjustment.
    :param fetchers_config: the balances and parameters fetchers configuration
    :return: the fee free withdrawal limit.
    """
    customer_deposit_amount = get_customer_deposit_amount(
        state=state, balance_adjustments=balance_adjustments, fetchers_config=fetchers_config
    )

    return utils.round_decimal(
        amount=(
            customer_deposit_amount  # ty: ignore[unsupported-operator]
            * state.parameters[FEE_FREE_WITHDRAWAL_PERCENTAGE_LIMIT_PARAM.id]
        ),
        decimal_places=fetchers_config.precision,
    )
