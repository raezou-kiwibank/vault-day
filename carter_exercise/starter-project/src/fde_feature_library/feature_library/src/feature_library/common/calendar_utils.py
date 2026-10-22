__smart_contract_feature__ = True
from datetime import datetime

from contracts_api import (
    CalendarEvent,
    CalendarEvents,
    CalendarsFilter,
    CalendarsObservationFetcher,
    DefinedDateTime,
)

PUBLIC_HOLIDAYS_COF_ID = "public_holidays_cof"
PUBLIC_HOLIDAYS_COF = CalendarsObservationFetcher(
    fetcher_id=PUBLIC_HOLIDAYS_COF_ID,
    filter=CalendarsFilter(calendar_ids=["&{PUBLIC_HOLIDAYS}"]),
    at=DefinedDateTime.EFFECTIVE_DATETIME,
)

data_fetchers = [
    PUBLIC_HOLIDAYS_COF,
]


def falls_on_calendar_events(
    effective_datetime: datetime, calendar_events: CalendarEvents | list[CalendarEvent]
) -> bool:
    """Returns if true if the given date is on or between a calendar event's start and/or end
    timestamp, inclusive.
    """
    return any(
        calendar_event.start_datetime <= effective_datetime < calendar_event.end_datetime
        for calendar_event in calendar_events
    )
