# standard libs
from datetime import datetime
from decimal import Decimal

# contracts api
from contracts_api import (
    DEFAULT_ASSET,
    CustomInstruction,
    Phase,
    Posting,
    ScheduledEvent,
    ScheduleExpression,
)


def schedules(start_datetime: datetime) -> ScheduledEvent:
    return ScheduledEvent(
        start_datetime=start_datetime,
        expression=ScheduleExpression(hour=0, minute=0, second=0),
    )


def posting_logic(account_id: str, amount: Decimal) -> list[CustomInstruction]:
    return [
        CustomInstruction(
            postings=[
                Posting(
                    credit=True,
                    account_id=account_id,
                    amount=amount,
                    account_address="TEST_ADDRESS_1",
                    asset=DEFAULT_ASSET,
                    denomination="GBP",
                    phase=Phase.COMMITTED,
                ),
                Posting(
                    credit=False,
                    account_id=account_id,
                    amount=amount,
                    account_address="TEST_ADDRESS_2",
                    asset=DEFAULT_ASSET,
                    denomination="GBP",
                    phase=Phase.COMMITTED,
                ),
            ]
        )
    ]
