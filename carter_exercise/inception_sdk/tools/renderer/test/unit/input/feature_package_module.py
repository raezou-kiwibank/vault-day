__smart_contract_feature__ = True
# standard libs
from decimal import Decimal
from typing import NamedTuple

api = "4.0.0"

AccrualDetail = NamedTuple(
    "AccrualDetail",
    [
        ("amount", Decimal),
        ("description", str),
    ],
)
