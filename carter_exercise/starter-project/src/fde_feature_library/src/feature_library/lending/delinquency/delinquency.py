# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
__smart_contract_feature__ = True

# standard libs
from datetime import datetime

# feature library
import feature_library.common.balance_utils as balance_utils
import feature_library.common.date_and_time as date_and_time
import feature_library.common.state_utils as state_utils
import feature_library.lending.addresses as lending_addresses

# contracts api
from contracts_api import (
    AccountNotificationDirective,
    ExpectedParameter,
    ScheduledEvent,
    ScheduleExpression,
    SmartContractEventType,
)

# Schedule event names
CHECK_DELINQUENCY_EVENT = "CHECK_DELINQUENCY"

# Prefixes

# Parameter Names
CHECK_DELINQUENCY_TIME_PARAM_ID = "&{check_delinquency_time}"
GRACE_PERIOD_PARAM_ID = "&{grace_period}"

CHECK_DELINQUENCY_TIME_PARAM = ExpectedParameter(
    id=CHECK_DELINQUENCY_TIME_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

GRACE_PERIOD_PARAM = ExpectedParameter(
    id=GRACE_PERIOD_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    CHECK_DELINQUENCY_TIME_PARAM,
    GRACE_PERIOD_PARAM,
]

# Notifications
MARK_DELINQUENT_NOTIFICATION_SUFFIX = "_DELINQUENT_NOTIFICATION"


def get_grace_period_parameter(state: state_utils.SmartContractState) -> int:
    """Retrieve the grace period parameter.

    Args:
        state: The smart contract state.

    Returns:
        The grace period in days.
    """
    return int(state.parameters[GRACE_PERIOD_PARAM_ID])  # type: ignore


def event_types(product_name: str) -> list[SmartContractEventType]:
    """Return the event types for delinquency.

    Args:
        product_name: The name of the product.

    Returns:
        The smart contract event types.
    """
    return [
        SmartContractEventType(
            name=CHECK_DELINQUENCY_EVENT,
            scheduler_tag_ids=[f"{product_name.upper()}_{CHECK_DELINQUENCY_EVENT}_AST"],
        )
    ]


def notification_type(product_name: str) -> str:
    """Create the notification type.

    Args:
        product_name: The product name.

    Returns:
        The notification type.
    """
    return f"{product_name.upper()}{MARK_DELINQUENT_NOTIFICATION_SUFFIX}"


def scheduled_events(
    state: state_utils.SmartContractState,
    start_datetime: datetime,
    is_one_off: bool = False,
    skip: bool = False,
) -> dict[str, ScheduledEvent]:
    """Create a check delinquency schedule starting at the specified date.

    This schedule can either be a monthly recurring schedule or executed once.

    Args:
        state: The smart contract state.
        start_datetime: The date on which the schedule starts. Time components are ignored.
        is_one_off: Whether the schedule is recurring or a one-off.
        skip: If True, schedule will be skipped indefinitely.

    Returns:
        A dictionary containing the check delinquency schedule.
    """
    year = str(start_datetime.year) if is_one_off else None
    month = str(start_datetime.month) if is_one_off else None

    time_str = state.parameters[CHECK_DELINQUENCY_TIME_PARAM_ID]  # type: ignore
    parsed_time = date_and_time.parse_time_str(str(time_str))

    return {
        CHECK_DELINQUENCY_EVENT: ScheduledEvent(
            start_datetime=start_datetime.astimezone(state.vault.events_timezone).replace(
                hour=0, minute=0, second=0
            ),
            expression=ScheduleExpression(
                year=year,
                month=month,
                day=str(start_datetime.day),
                hour=str(parsed_time.hour),
                minute=str(parsed_time.minute),
                second=str(parsed_time.second),
            ),
            skip=skip,
        ),
    }


def schedule_logic(
    state: state_utils.SmartContractState,
    product_name: str,
    denomination: str,
    addresses: list[str] | None = None,
) -> list[AccountNotificationDirective]:
    """Instruct a notification to inform the customer of their account delinquency.

    Args:
        state: The smart contract state.
        product_name: The name of the product.
        denomination: The denomination of the balance addresses.
        addresses: The balance addresses to check for delinquency. Defaults to
            lending_addresses.LATE_REPAYMENT_ADDRESSES.

    Returns:
        A list of AccountNotificationDirective.
    """
    if addresses is None:
        addresses = lending_addresses.LATE_REPAYMENT_ADDRESSES

    total_balance = balance_utils.net_debit(
        balance_utils.sum_balances(
            balances=state.balances,
            addresses=addresses,
            denomination=denomination,
        )
    )

    if total_balance > 0:
        return [
            AccountNotificationDirective(
                notification_type=notification_type(product_name),
                notification_details={"account_id": str(state.vault.account_id)},
            )
        ]
    return []
