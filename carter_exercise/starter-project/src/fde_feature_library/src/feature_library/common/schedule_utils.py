__smart_contract_feature__ = True

# standard libs
from datetime import datetime

from dateutil.relativedelta import relativedelta

# contracts api
from contracts_api import EndOfMonthSchedule, ScheduledEvent, ScheduleExpression, ScheduleFailover

# inception sdk
from inception_sdk.vault.contracts.extensions.contracts_api_extensions import SmartContractVault

MONTHLY = "monthly"
QUARTERLY = "quarterly"
ANNUALLY = "annually"


def one_off_schedule_expression(schedule_datetime: datetime) -> ScheduleExpression:
    """Creates a ScheduleExpression for a one-off event.
    :param schedule_datetime: the datetime for the one-off event
    :return: the ScheduleExpression
    """
    return ScheduleExpression(
        year=str(schedule_datetime.year),
        month=str(schedule_datetime.month),
        day=str(schedule_datetime.day),
        hour=str(schedule_datetime.hour),
        minute=str(schedule_datetime.minute),
        second=str(schedule_datetime.second),
    )


def get_schedule_expression_from_parameters(
    *,
    time: str,
    day: int | str | None = None,
    month: int | str | None = None,
    year: int | str | None = None,
    day_of_week: int | str | None = None,
) -> ScheduleExpression:
    hour, minute, second = map(int, time.split(":"))

    return ScheduleExpression(
        hour=hour,
        minute=minute,
        second=second,
        day=None if not day else str(day),
        month=None if not month else str(month),
        year=None if not year else str(year),
        day_of_week=None if not day_of_week else str(day_of_week),
    )


def monthly_scheduled_event(
    vault: SmartContractVault,
    start_datetime: datetime,
    time: str,
    day: int,
    failover: ScheduleFailover = ScheduleFailover.FIRST_VALID_DAY_BEFORE,
) -> ScheduledEvent:
    """Creates a monthly scheduled event, using values provided from relevant day and time parameters.
    :param vault: the vault object holding the parameters
    :param start_datetime: when the schedule should start from (inclusive)
    :param parameter_prefix: the prefix for the parameter names
    :param failover: the desired behaviour if the day does not exist in a given month
    :param day: the desired day of the month to create the schedule
    :return: the desired scheduled event
    """

    account_activation_datetime = vault.get_account_activation_datetime()
    # Schedule DSL expressions (e.g. EndOfMonthSchedule) are exclusive of start_datetime, but
    # inclusive for non DSL.
    start_datetime = start_datetime - relativedelta(seconds=1)
    if start_datetime < account_activation_datetime:
        start_datetime = account_activation_datetime

    hour, minute, second = map(int, time.split(":"))

    return ScheduledEvent(
        start_datetime=start_datetime,
        schedule_method=EndOfMonthSchedule(
            day=day,
            hour=hour,
            minute=minute,
            second=second,
            failover=failover,
        ),
    )


def get_next_schedule_date(
    start_date: datetime, schedule_frequency: str, intended_day: int
) -> datetime:
    """Calculate next valid date for schedule based on required frequency and day of month.
    Falls to last valid day of month if intended day is not in calculated month

    :param start_date: datetime, from which schedule frequency is calculated from
    :param schedule_frequency: str, either 'monthly', 'quarterly' or 'annually'
    :param intended_day: int, day of month the scheduled date should fall on
    :return: datetime, next occurrence of schedule
    """
    frequency_map = {MONTHLY: 1, QUARTERLY: 3, ANNUALLY: 12}

    number_of_months = frequency_map[schedule_frequency]

    if schedule_frequency == MONTHLY and start_date + relativedelta(day=intended_day) > start_date:
        return start_date + relativedelta(day=intended_day)
    else:
        return start_date + relativedelta(months=number_of_months, day=intended_day)
