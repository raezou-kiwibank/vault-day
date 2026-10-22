# Copyright @ 2026 Thought Machine Group Limited. All rights reserved.
__smart_contract_feature__ = True

# standard libs
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple

from dateutil.relativedelta import relativedelta

# feature library
import feature_library.common.balance_utils as balance_utils
import feature_library.common.date_and_time as date_and_time
import feature_library.common.denomination as denomination_module
import feature_library.common.posting_utils as posting_utils
import feature_library.common.state_utils as state_utils
import feature_library.common.tuples as common_tuples
import feature_library.lending.addresses as lending_addresses

# contracts api
from contracts_api import (
    AccountNotificationDirective,
    Attribute,
    AttributeHookArguments,
    AttributeHookResult,
    AttributeStringType,
    CustomInstruction,
    DefinedDateTime,
    EventTypesFilter,
    ExpectedParameter,
    LastScheduledEventDateTimesObservationFetcher,
    Posting,
    ScheduledEvent,
    ScheduledEventHookArguments,
    ScheduleExpression,
    SmartContractEventType,
    SupervisorScheduledEventHookArguments,
)

CHECK_OVERDUE_EVENT = "CHECK_OVERDUE"
DUE_AMOUNT_CALCULATION_EVENT = "DUE_AMOUNT_CALCULATION"

LAST_DUE_AMOUNT_CALCULATION_SOF_ID = "LAST_DUE_AMOUNT_CALCULATION_SOF"
LAST_DUE_AMOUNT_CALCULATION_SOF = LastScheduledEventDateTimesObservationFetcher(
    fetcher_id=LAST_DUE_AMOUNT_CALCULATION_SOF_ID,
    filter=EventTypesFilter(
        event_types=[DUE_AMOUNT_CALCULATION_EVENT],
    ),
    at=DefinedDateTime.EFFECTIVE_DATETIME,
)

data_fetchers = [LAST_DUE_AMOUNT_CALCULATION_SOF]

PARAM_NEXT_OVERDUE_DATE = "next_overdue_date"

# Notifications
OVERDUE_REPAYMENT_NOTIFICATION_SUFFIX = "_OVERDUE_REPAYMENT"

FUND_MOVEMENT_MAP = {
    lending_addresses.PRINCIPAL_DUE: lending_addresses.PRINCIPAL_OVERDUE,
    lending_addresses.INTEREST_DUE: lending_addresses.INTEREST_OVERDUE,
}

REPAYMENT_PERIOD_PARAM_ID = "&{repayment_period}"
REPAYMENT_PERIOD_PARAM = ExpectedParameter(
    id=REPAYMENT_PERIOD_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

CHECK_OVERDUE_TIME_PARAM_ID = "&{check_overdue_time}"
CHECK_OVERDUE_TIME_PARAM = ExpectedParameter(
    id=CHECK_OVERDUE_TIME_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

expected_parameters = [
    REPAYMENT_PERIOD_PARAM,
    CHECK_OVERDUE_TIME_PARAM,
]


OverdueScheduledEventsFetchersConfig = NamedTuple(
    "OverdueScheduledEventsFetchersConfig",
    [
        ("check_overdue_time_param_id", str),
        ("repayment_period_param_id", str),
        ("last_due_amount_calculation_sof_id", str),
    ],
)


DEFAULT_OVERDUE_SCHEDULED_EVENTS_FETCHERS_CONFIG = OverdueScheduledEventsFetchersConfig(
    check_overdue_time_param_id=CHECK_OVERDUE_TIME_PARAM_ID,
    repayment_period_param_id=REPAYMENT_PERIOD_PARAM_ID,
    last_due_amount_calculation_sof_id=LAST_DUE_AMOUNT_CALCULATION_SOF_ID,
)


OverdueScheduleLogicFetchersConfig = NamedTuple(
    "OverdueScheduleLogicFetchersConfig",
    [
        ("denomination_param_id", str),
    ],
)

DEFAULT_OVERDUE_SCHEDULE_LOGIC_FETCHERS_CONFIG = OverdueScheduleLogicFetchersConfig(
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
)

next_overdue_attribute = Attribute(
    name=PARAM_NEXT_OVERDUE_DATE,
    data_type=AttributeStringType(),
)


def get_repayment_period_parameter(
    state: state_utils.SmartContractState, param_id: str = REPAYMENT_PERIOD_PARAM_ID
) -> int:
    """Retrieve the repayment period parameter.

    Args:
        state: The smart contract state.
        param_id: The repayment period parameter ID.

    Returns:
        The repayment period in days.
    """
    return int(state.parameters[param_id])  # type: ignore


def next_overdue_attribute_handler(
    state: state_utils.SmartContractState,
    hook_arguments: AttributeHookArguments,
    fetchers_config: OverdueScheduledEventsFetchersConfig = DEFAULT_OVERDUE_SCHEDULED_EVENTS_FETCHERS_CONFIG,  # noqa: E501
) -> AttributeHookResult:
    """Calculate the next overdue attribute.

    Args:
        state: The smart contract state.
        hook_arguments: The hook arguments as received from the contract.
        fetchers_config: The fetchers configuration.

    Returns:
        The attribute hook result.
    """
    previous_due_amount_calculation_datetime = (
        state.vault.get_last_scheduled_event_datetimes_observation(
            fetcher_id=fetchers_config.last_due_amount_calculation_sof_id
        ).last_scheduled_event_datetimes.get(DUE_AMOUNT_CALCULATION_EVENT)
    )

    if previous_due_amount_calculation_datetime is None:
        return AttributeHookResult(attribute_value=datetime.min.isoformat())

    return AttributeHookResult(
        attribute_value=(
            previous_due_amount_calculation_datetime
            + relativedelta(days=get_repayment_period_parameter(state=state))
        ).isoformat()
    )


def event_types(product_name: str) -> list[SmartContractEventType]:
    """Return the event types for checking overdue amounts.

    Args:
        product_name: The product name.

    Returns:
        The smart contract event types list.
    """
    return [
        SmartContractEventType(
            name=CHECK_OVERDUE_EVENT,
            scheduler_tag_ids=[f"{product_name.upper()}_{CHECK_OVERDUE_EVENT}_AST"],
        )
    ]


def notification_type(product_name: str) -> str:
    """Create the notification type.

    Args:
        product_name: The product name.

    Returns:
        The notification type.
    """
    return f"{product_name.upper()}{OVERDUE_REPAYMENT_NOTIFICATION_SUFFIX}"


def scheduled_events(
    state: state_utils.SmartContractState,
    first_due_amount_calculation_datetime: datetime,
    is_one_off: bool = False,
    skip: bool = False,
    fetchers_config: OverdueScheduledEventsFetchersConfig = DEFAULT_OVERDUE_SCHEDULED_EVENTS_FETCHERS_CONFIG,  # noqa: E501
) -> dict[str, ScheduledEvent]:
    """Create a check overdue schedule.

    Calculates the date on which the schedule will run from the first due amount calculation
    date and the repayment period. The time component is determined by the `check_overdue_time`
    schedule time parameter.

    Args:
        state: The smart contract state.
        first_due_amount_calculation_datetime: The datetime on which the first due amount is
            calculated, used to determine the next overdue check date ignoring the time component.
        is_one_off: Whether the schedule is recurring or a one-off schedule.
        skip: If True, schedule will be skipped indefinitely until this field is updated,
            defaults to False.
        fetchers_config: The fetchers configuration.

    Returns:
        A dictionary containing the check overdue schedule.
    """
    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.check_overdue_time_param_id,
            fetchers_config.repayment_period_param_id,
        },
    )
    assert rejection is None, rejection

    repayment_period = get_repayment_period_parameter(
        state=state, param_id=fetchers_config.repayment_period_param_id
    )
    next_overdue_check_datetime = first_due_amount_calculation_datetime + relativedelta(
        days=repayment_period
    )

    time_str = state.parameters[fetchers_config.check_overdue_time_param_id]  # type: ignore
    parsed_time = date_and_time.parse_time_str(str(time_str))

    year = str(next_overdue_check_datetime.year) if is_one_off else None
    month = str(next_overdue_check_datetime.month) if is_one_off else None

    schedule_datetime = next_overdue_check_datetime.astimezone(state.vault.events_timezone).replace(
        hour=parsed_time.hour, minute=parsed_time.minute, second=parsed_time.second
    )

    return {
        CHECK_OVERDUE_EVENT: ScheduledEvent(
            start_datetime=next_overdue_check_datetime.astimezone(
                state.vault.events_timezone
            ).replace(hour=0, minute=0, second=0),
            expression=ScheduleExpression(
                year=year,
                month=month,
                day=str(schedule_datetime.day),
                hour=str(schedule_datetime.hour),
                minute=str(schedule_datetime.minute),
                second=str(schedule_datetime.second),
            ),
            skip=skip,
        )
    }


def schedule_logic(
    state: state_utils.SmartContractState,
    hook_arguments: (ScheduledEventHookArguments | SupervisorScheduledEventHookArguments),
    account_type: str = "",
    late_repayment_fee: Decimal = Decimal("0"),
    fetchers_config: OverdueScheduleLogicFetchersConfig = DEFAULT_OVERDUE_SCHEDULE_LOGIC_FETCHERS_CONFIG,  # noqa: E501
) -> common_tuples.ScheduleLogicResult:
    """Create postings to credit principal or interest due amounts and debit overdue.

    Executes at the end of the repayment period.

    Args:
        state: The smart contract state.
        hook_arguments: The hook arguments as received from the contract.
        account_type: The account type as to be noted in custom instruction detail.
        late_repayment_fee: Fee to apply due to late repayment.
        fetchers_config: The fetchers configuration.

    Returns:
        ScheduleLogicResult containing custom instructions and overdue repayment notifications.
    """
    rejection = state_utils.check_parameters_exist(
        state=state,
        param_ids={
            fetchers_config.denomination_param_id,
        },
    )
    assert rejection is None, rejection

    postings: list[Posting] = []
    denomination: str = state.parameters[fetchers_config.denomination_param_id]  # type: ignore

    account_id = state.vault.account_id
    due_amounts = {}
    for due_address, overdue_address in FUND_MOVEMENT_MAP.items():
        due_amounts[due_address] = balance_utils.balance_at_coordinates(
            balances=state.balances,
            address=due_address,
            denomination=denomination,
        )
        postings += posting_utils.create_postings(
            amount=due_amounts[due_address],
            debit_account=account_id,
            credit_account=account_id,
            debit_address=overdue_address,
            credit_address=due_address,
            denomination=denomination,
        )

    if not postings:
        return common_tuples.ScheduleLogicResult(
            custom_instructions=[],
            event_type_directives=[],
            notification_directives=[],
        )

    custom_instructions = [
        CustomInstruction(
            postings=postings,
            override_all_restrictions=True,
            instruction_details={
                "description": "Move outstanding due debt into overdue debt.",
                "event_type": hook_arguments.event_type,
                "gl_impacted": "False",
                "account_type": account_type,
            },
        )
    ]

    notifications: list[AccountNotificationDirective] = []
    # getting the due amounts since they will become overdue
    notifications.extend(
        get_overdue_repayment_notification(
            account_id=account_id,
            product_name=account_type,
            effective_datetime=hook_arguments.effective_datetime,
            overdue_principal_amount=due_amounts[lending_addresses.PRINCIPAL_DUE],
            overdue_interest_amount=due_amounts[lending_addresses.INTEREST_DUE],
            late_repayment_fee=late_repayment_fee,
        )
    )

    return common_tuples.ScheduleLogicResult(
        custom_instructions=custom_instructions,
        event_type_directives=[],
        notification_directives=notifications,
    )


def get_overdue_repayment_notification(
    account_id: str,
    product_name: str,
    effective_datetime: datetime,
    overdue_principal_amount: Decimal,
    overdue_interest_amount: Decimal,
    late_repayment_fee: Decimal = Decimal("0"),
) -> list[AccountNotificationDirective]:
    """Instruct overdue repayment notification.

    Args:
        account_id: Vault account_id.
        product_name: The name of the product for the workflow prefix.
        effective_datetime: Datetime, the effective date overdue schedule executes.
        overdue_principal_amount: The amount from PRINCIPAL_DUE that will become overdue.
        overdue_interest_amount: The amount from INTEREST_DUE that will become overdue.
        late_repayment_fee: Fee to apply due to late repayment.

    Returns:
        List containing the account notification directive, if applicable.
    """
    if overdue_principal_amount + overdue_interest_amount > 0:
        return [
            AccountNotificationDirective(
                notification_type=notification_type(product_name),
                notification_details={
                    "account_id": account_id,
                    "overdue_principal": str(overdue_principal_amount),
                    "overdue_interest": str(overdue_interest_amount),
                    "late_repayment_fee": str(late_repayment_fee),
                    "overdue_date": str(effective_datetime.date()),
                },
            )
        ]
    return []


def get_overdue_datetime(
    due_amount_notification_datetime: datetime,
    repayment_period: int,
    notification_period: int,
) -> datetime:
    """Return the overdue datetime given the due amount notification date.

    Hour, minute and second are not considered.

    Args:
        due_amount_notification_datetime: The date when the due amount notification takes place.
        repayment_period: The number of days after which due amounts are made overdue.
        notification_period: The number of days prior to a payment becoming due,
            send a due notification reminder to the user.

    Returns:
        The overdue datetime.
    """
    return due_amount_notification_datetime + relativedelta(
        days=int(notification_period + repayment_period)
    )
