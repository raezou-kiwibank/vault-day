from datetime import datetime
from zoneinfo import ZoneInfo

from inception_sdk.test_framework.contracts.simulation.data_objects.data_objects import (
    SimulationEvent,
)

UTC = ZoneInfo("UTC")
SYDNEY_TZ = ZoneInfo("Australia/Sydney")
NYC_TZ = ZoneInfo("America/New_York")

timezones = [UTC, NYC_TZ, SYDNEY_TZ]

DEFAULT_PG = "DEFAULT"


def create_update_pgtz_instruction(
    event_datetime: datetime,
    timezone: ZoneInfo = UTC,
    processing_group: str = DEFAULT_PG,
) -> SimulationEvent:
    """
    Returns a Simulation instruction event to update the Processing Group Time Zone (PGTZ).
    """
    return SimulationEvent(
        time=event_datetime,
        event={
            "update_processing_group": {
                "processing_group": {
                    "id": processing_group,
                    "timezone": str(timezone),
                },
                "update_mask": {"paths": ["timezone"]},
            }
        },
    )


def ctx_id_generator(prefix: str):
    i = 0
    while True:
        yield prefix + str(i)
        i += 1
