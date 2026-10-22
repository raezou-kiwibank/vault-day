# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta

import feature_library.common.date_and_time as date_and_time
import feature_library.common.state_utils as state_utils

# feature library
# contracts api
from contracts_api import (
    AccountNotificationDirective,
    ExpectedParameter,
    ScheduledEvent,
    ScheduleExpression,
    SmartContractEventType,
)

# Schedule event names
NOTIFY_DUE_AMOUNT_EVENT = "NOTIFY_DUE_AMOUNT"

# Prefixes

# Parameter Names
NOTIFICATION_PERIOD_PARAM_ID = "&{notification_period}"
NOTIFICATION_PERIOD_PARAM = ExpectedParameter(
    id=NOTIFICATION_PERIOD_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

DUE_NOTIFICATION_TIME_PARAM_ID = "&{due_amount_notification_time}"
DUE_NOTIFICATION_TIME_PARAM = ExpectedParameter(
    id=DUE_NOTIFICATION_TIME_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    NOTIFICATION_PERIOD_PARAM,
    DUE_NOTIFICATION_TIME_PARAM,
]

# Notifications
REPAYMENT_NOTIFICATION_SUFFIX = "_REPAYMENT"


def get_notification_period_parameter(state: state_utils.SmartContractState) -> int:
    """Retrieve the notification period parameter.

    Args:
        state: The smart contract state.

    Returns:
        The notification period in days.
    """
    return int(state.parameters[NOTIFICATION_PERIOD_PARAM_ID])  # type: ignore


def _get_schedule_time_from_parameters(
    state: state_utils.SmartContractState,
) -> date_and_time.Time:
    """Retrieve the hour, minute, and second for the due amount notification schedule.

    Args:
        state: The smart contract state.

    Returns:
        A tuple containing (hour, minute, second).
    """
    time_str = state.parameters[DUE_NOTIFICATION_TIME_PARAM_ID]  # type: ignore
    return date_and_time.parse_time_str(str(time_str))


def event_types(product_name: str) -> list[SmartContractEventType]:
    """Create event_types metadata for NOTIFY_DUE_AMOUNT schedule.

    Args:
        product_name: The name of the product.

    Returns:
        List of SmartContractEventType.
    """
    return [
        SmartContractEventType(
            name=NOTIFY_DUE_AMOUNT_EVENT,
            scheduler_tag_ids=[f"{product_name.upper()}_{NOTIFY_DUE_AMOUNT_EVENT}_AST"],
        )
    ]


def notification_type(product_name: str) -> str:
    """Create the notification type.

    Args:
        product_name: The product name.

    Returns:
        The notification type.
    """
    return f"{product_name.upper()}{REPAYMENT_NOTIFICATION_SUFFIX}"


def get_next_due_amount_notification_schedule(
    state: state_utils.SmartContractState, next_due_amount_calc_datetime: datetime
) -> datetime:
    """Determine the next notification datetime based on schedule parameters.

    Args:
        state: The smart contract state.
        next_due_amount_calc_datetime: The date of the next due amount calculation.

    Returns:
        The scheduled datetime for the notification.
    """
    notification_period = get_notification_period_parameter(state)
    schedule_time = _get_schedule_time_from_parameters(state)

    return next_due_amount_calc_datetime - relativedelta(
        days=notification_period,
        hour=schedule_time.hour,
        minute=schedule_time.minute,
        second=schedule_time.second,
    )


def get_next_due_amount_notification_datetime(
    state: state_utils.SmartContractState,
    current_due_amount_notification_datetime: datetime,
    repayment_frequency_delta: relativedelta,
) -> datetime:
    """Return the next due amount notification datetime given the current one.

    Args:
        state: The smart contract state.
        current_due_amount_notification_datetime: The current due amount notification date.
        repayment_frequency_delta: The relative delta for the repayment frequency.

    Returns:
        The next due amount notification datetime.
    """
    notification_period = get_notification_period_parameter(state)
    # get the due_amount_calc for previous date.
    current_due_amount_calc_date_time = current_due_amount_notification_datetime + relativedelta(
        days=notification_period
    )
    # get next_due_amount_calc
    next_due_amount_calc_datetime = current_due_amount_calc_date_time + repayment_frequency_delta

    next_due_amount_notification_datetime = get_next_due_amount_notification_schedule(
        state=state, next_due_amount_calc_datetime=next_due_amount_calc_datetime
    )
    return next_due_amount_notification_datetime


def scheduled_events(
    state: state_utils.SmartContractState, next_due_amount_calc_datetime: datetime
) -> dict[str, ScheduledEvent]:
    """Create execution schedule for NOTIFY_DUE_AMOUNT.

    Runs `notification_period` days before the first due amount calculation date.

    Args:
        state: The smart contract state.
        next_due_amount_calc_datetime: Date when the next due_amount_calc_datetime will happen.

    Returns:
        Dictionary of ScheduledEvent.
    """
    notification_datetime = get_next_due_amount_notification_schedule(
        state=state, next_due_amount_calc_datetime=next_due_amount_calc_datetime
    )
    return {
        NOTIFY_DUE_AMOUNT_EVENT: ScheduledEvent(
            start_datetime=notification_datetime - relativedelta(seconds=1),
            expression=ScheduleExpression(
                year=str(notification_datetime.year),
                month=str(notification_datetime.month),
                day=str(notification_datetime.day),
                hour=str(notification_datetime.hour),
                minute=str(notification_datetime.minute),
                second=str(notification_datetime.second),
            ),
        )
    }


# Scheduled hook helpers
def schedule_logic(
    state: state_utils.SmartContractState,
    product_name: str,
    overdue_datetime: datetime,
    due_interest: Decimal = Decimal("0"),
    due_principal: Decimal = Decimal("0"),
) -> list[AccountNotificationDirective]:
    """Send notification prior to a payment becoming due.

    Args:
        state: The smart contract state.
        product_name: The product name.
        overdue_datetime: The date that the repayment amount will become overdue.
        due_interest: The due_interest.
        due_principal: The due_principal.

    Returns:
        List of AccountNotificationDirective.
    """
    if due_principal + due_interest > 0:
        return [
            send_due_amount_notification(
                account_id=state.vault.account_id,
                due_principal=due_principal,
                due_interest=due_interest,
                overdue_datetime=overdue_datetime,
                product_name=product_name,
            )
        ]
    return []


# notification helpers
def send_due_amount_notification(
    account_id: str,
    due_principal: Decimal,
    due_interest: Decimal,
    overdue_datetime: datetime,
    product_name: str,
) -> AccountNotificationDirective:
    """Instruct a notification.

    Args:
        account_id: Vault account id.
        due_principal: Calculated due principal.
        due_interest: Calculated due interest.
        overdue_datetime: The date that the repayment amount will become overdue.
        product_name: The name of the product for the notification prefix.

    Returns:
        The account notification directive.
    """
    return AccountNotificationDirective(
        notification_type=notification_type(product_name),
        notification_details={
            "account_id": account_id,
            "principal_due": str(due_principal),
            "interest_due": str(due_interest),
            "overdue_date": str(overdue_datetime.date()),
        },
    )
