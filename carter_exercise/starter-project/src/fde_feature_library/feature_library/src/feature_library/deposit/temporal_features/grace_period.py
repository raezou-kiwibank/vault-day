# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import Any, NamedTuple
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta

# features
import feature_library.common.balance_utils as balance_utils
import feature_library.common.denomination as denomination_module
import feature_library.common.posting_utils as posting_utils
import feature_library.common.schedule_utils as schedule_utils
import feature_library.common.state_utils as state_utils

# contracts api
from contracts_api import (
    AccountNotificationDirective,
    Attribute,
    AttributeDateTimeType,
    Balance,
    DefinedDateTime,
    ExpectedParameter,
    ParametersFilter,
    ParametersObservationFetcher,
    Rejection,
    RejectionReason,
    ScheduledEvent,
    SmartContractEventType,
)

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

# Constants
UTC = ZoneInfo("UTC")

# Notifications
GRACE_PERIOD_END_SUFFIX = "_GRACE_PERIOD_END"
# Schedule event names
GRACE_PERIOD_END_EVENT = "GRACE_PERIOD_END"

# Parameters
GRACE_PERIOD_PARAM_ID = "&{grace_period}"
GRACE_PERIOD_PARAM = ExpectedParameter(
    id=GRACE_PERIOD_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

# Attributes
GRACE_PERIOD_END_DATE_ATTR_ID = "grace_period_end_date"
GRACE_PERIOD_END_DATE_ATTRIBUTE = Attribute(
    name=GRACE_PERIOD_END_DATE_ATTR_ID,
    data_type=AttributeDateTimeType(),
)

# Fetchers
GRACE_PERIOD_PARAMS_ET_POF_ID = "grace_period_params_et_pof"
GRACE_PERIOD_PARAMS_ET_POF = ParametersObservationFetcher(
    fetcher_id=GRACE_PERIOD_PARAMS_ET_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(parameter_ids=[GRACE_PERIOD_PARAM_ID]),
)

expected_parameters = [GRACE_PERIOD_PARAM, denomination_module.DENOMINATION_PARAM]
data_fetchers = [GRACE_PERIOD_PARAMS_ET_POF]


FetchersConfig = NamedTuple(
    "FetchersConfig",
    [
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
        ("grace_period_param_id", str),
    ],
)

DEFAULT_FETCHERS_CONFIG = FetchersConfig(
    param_fetcher_id=GRACE_PERIOD_PARAMS_ET_POF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
    grace_period_param_id=GRACE_PERIOD_PARAM_ID,
)


def get_parameters(
    vault: SmartContractVault, fetcher_id: str = GRACE_PERIOD_PARAMS_ET_POF_ID
) -> dict[str, Any]:
    """Retrieves feature-specific parameters from the vault.

    Args:
        vault: The vault object to query for observations.
        fetcher_id: The ID of the parameter observation fetcher.

    Returns:
        The dictionary of parameter values.
    """
    return vault.get_parameters_observation(fetcher_id=fetcher_id).parameters


def _append_to_state(
    *,
    state: state_utils.SmartContractState,
    fetchers_config: FetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> state_utils.SmartContractState:
    """Consolidates feature-specific parameters into the SmartContractState.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers.

    Returns:
        The updated state object.
    """
    return state_utils.append_to_state(
        state=state,
        parameters=get_parameters(state.vault, fetchers_config.param_fetcher_id),
    )


def notification_type(*, product_name: str) -> str:
    """Returns a notification type.

    Args:
        product_name: The product name.

    Returns:
        The notification type.
    """
    return f"{product_name.upper()}{GRACE_PERIOD_END_SUFFIX}"


def event_types(*, product_name: str) -> list[SmartContractEventType]:
    """Returns a list of event types.

    Args:
        product_name: Name of the product.

    Returns:
        A list of SmartContractEventType objects.
    """
    return [
        SmartContractEventType(
            name=GRACE_PERIOD_END_EVENT,
            scheduler_tag_ids=[f"{product_name.upper()}_{GRACE_PERIOD_END_EVENT}_AST"],
        )
    ]


def get_scheduled_events(
    *,
    state: state_utils.SmartContractState,
    fetchers_config: FetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> dict[str, ScheduledEvent]:
    """Creates one off scheduled event for grace period end balance check.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers.

    Returns:
        A dictionary of grace period end scheduled event.
    """
    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    grace_period_end_datetime = get_grace_period_end_datetime(
        state=state, fetchers_config=fetchers_config
    )
    scheduled_event = ScheduledEvent(
        start_datetime=grace_period_end_datetime - relativedelta(seconds=1),
        expression=schedule_utils.one_off_schedule_expression(
            schedule_datetime=grace_period_end_datetime
        ),
        end_datetime=grace_period_end_datetime,
    )
    return {GRACE_PERIOD_END_EVENT: scheduled_event}


def get_grace_period_end_datetime(
    *,
    state: state_utils.SmartContractState,
    fetchers_config: FetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> datetime:
    """Calculates and returns the grace period end datetime.

    This date will represent the midnight of the account creation datetime plus the number of days
    in the grace period, inclusive of the account creation datetime.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers.

    Returns:
        The datetime when the grace period ends.
    """

    rejection = state_utils.check_parameters_exist(
        state=state, param_ids={fetchers_config.grace_period_param_id}
    )

    assert rejection is None, rejection

    grace_period = int(state.parameters[fetchers_config.grace_period_param_id])  # type: ignore

    account_activation_datetime = state.vault.get_account_activation_datetime()

    grace_period_end = account_activation_datetime.astimezone(state.vault.events_timezone).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) + relativedelta(days=grace_period)

    return grace_period_end


def is_within_grace_period(
    *,
    state: state_utils.SmartContractState,
    fetchers_config: FetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> bool:
    """Determines whether the effective datetime is within the grace period of an account.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers.

    Returns:
        True if the effective datetime is less than the grace period end datetime.
    """
    return state.effective_datetime < get_grace_period_end_datetime(
        state=state, fetchers_config=fetchers_config
    )


def validate_deposit(
    *,
    state: state_utils.SmartContractState,
    posting_instructions: posting_utils.PostingInstructionListAlias,
    fetchers_config: FetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> Rejection | None:
    """Reject the posting instructions if deposits are sent after the end of grace period.

    Accept deposits within the grace period.

    Args:
        state: The current state of the smart contract.
        posting_instructions: List of posting instructions to validate.
        fetchers_config: Configuration for the fetchers.

    Returns:
        A rejection if deposits are sent after the end of grace period.
    """
    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    rejection = state_utils.check_parameters_exist(
        state=state, param_ids={fetchers_config.denomination_param_id}
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    is_deposit = balance_utils.net_credit(
        bal=balance_utils.sum_balances(
            balances=posting_utils.get_posting_instructions_balances(
                posting_instructions=posting_instructions
            ),
            denomination=denomination,
        )
    ) > Decimal("0")

    return (
        Rejection(
            message="No deposits are allowed after the grace period end",
            reason_code=RejectionReason.AGAINST_TNC,
        )
        if is_deposit and not is_within_grace_period(state=state, fetchers_config=fetchers_config)
        else None
    )


def is_withdrawal_subject_to_fees(
    *,
    state: state_utils.SmartContractState,
    posting_instructions: posting_utils.PostingInstructionListAlias,
    fetchers_config: FetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> bool:
    """Determines if a withdrawal is subject to fees.

    Args:
        state: The current state of the smart contract.
        posting_instructions: List of posting instructions.
        fetchers_config: Configuration for the fetchers.

    Returns:
        True if withdrawal is subject to fees, False otherwise.
    """
    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    rejection = state_utils.check_parameters_exist(
        state=state, param_ids={fetchers_config.denomination_param_id}
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    is_withdrawal = balance_utils.net_debit(
        bal=balance_utils.sum_balances(
            balances=posting_utils.get_posting_instructions_balances(
                posting_instructions=posting_instructions
            ),
            denomination=denomination,
        )
    ) > Decimal("0")

    return is_withdrawal and not is_within_grace_period(
        state=state, fetchers_config=fetchers_config
    )


def validate_term_parameter_change(
    *,
    state: state_utils.SmartContractState,
    fetchers_config: FetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> Rejection | None:
    """Allow term parameter change within grace period, reject change outside it.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers.

    Returns:
        A rejection if parameter changed outside the grace period.
    """
    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    return (
        Rejection(
            message="Term length cannot be changed outside the grace period",
            reason_code=RejectionReason.AGAINST_TNC,
        )
        if not is_within_grace_period(state=state, fetchers_config=fetchers_config)
        else None
    )


def handle_account_closure_notification(
    *,
    state: state_utils.SmartContractState,
    product_name: str,
    fetchers_config: FetchersConfig = DEFAULT_FETCHERS_CONFIG,
) -> list[AccountNotificationDirective]:
    """Send account closure notification when no funds are present at the end of grace period.

    Args:
        state: The current state of the smart contract.
        product_name: The name of the product for notification type.
        fetchers_config: Configuration for the fetchers.

    Returns:
        A list of account closure notification directives.
    """
    state = _append_to_state(state=state, fetchers_config=fetchers_config)

    rejection = state_utils.check_parameters_exist(
        state=state, param_ids={fetchers_config.denomination_param_id}
    )
    assert rejection is None, rejection

    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    net_balance: Balance = balance_utils.get_current_net_balance(
        balances=state.balances, denomination=denomination
    )

    return (
        [
            AccountNotificationDirective(
                notification_type=notification_type(product_name=product_name),
                notification_details={
                    "account_id": state.vault.account_id,
                    "grace_period_end_datetime": str(state.effective_datetime),
                    "reason": "Close account due to lack of funds at the end of grace period",
                },
            )
        ]
        if net_balance.net == Decimal(0)  # no funds in the the account
        else []
    )
