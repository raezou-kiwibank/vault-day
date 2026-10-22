__smart_contract_feature__ = True
from decimal import Decimal
from typing import NamedTuple

from contracts_api import (
    AccountNotificationDirective,
    CustomInstruction,
    UpdateAccountEventTypeDirective,
)

# Return type for get_interest_rate method defined in interest_type_interface
INTEREST_TYPE_OVERDRAFT = "OVERDRAFT"
INTEREST_TYPE_TIERED = "TIERED"
INTEREST_TYPE_FLAT = "FLAT"
INTEREST_TYPES = {INTEREST_TYPE_OVERDRAFT, INTEREST_TYPE_TIERED, INTEREST_TYPE_FLAT}
InterestRateTuple = NamedTuple(
    "InterestRateTuple",
    [
        ("interest_rate_param_value", Decimal | str | None),
        ("interest_type", str),
    ],
)

# Used for accrual calculations, return type for get accrual amount in interest_type_interface
AccrualDetail = NamedTuple(
    "AccrualDetail",
    [
        ("accrual_amount", Decimal),
        ("description", str),
    ],
)

# Return type for schedule logic functions
ScheduleLogicResult = NamedTuple(
    "ScheduleLogicResult",
    [
        ("custom_instructions", list[CustomInstruction]),
        ("event_type_directives", list[UpdateAccountEventTypeDirective]),
        ("notification_directives", list[AccountNotificationDirective]),
    ],
)
