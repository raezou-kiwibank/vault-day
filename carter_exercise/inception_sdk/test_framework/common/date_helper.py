# standard libs
from datetime import datetime
from dateutil import parser
from typing import overload


@overload
def isoformat(dt: datetime | str) -> str: ...


@overload
def isoformat(dt: None) -> None:
    # this is a convenience to avoid having to check for None before passing in
    ...


def isoformat(dt: datetime | str | None = None) -> str | None:
    """Assumes that if dt is a string then it is already formatted in ISO format."""
    return dt.isoformat() if isinstance(dt, datetime) else dt


@overload
def isoparse(dt: str) -> datetime: ...


@overload
def isoparse(dt: None) -> None:
    # this is a convenience to avoid having to check for None before passing in
    ...


def isoparse(dt: str | None = None) -> datetime | None:
    """This is a wrapper for the dateutils isoparse function so that it can handle null values."""
    if dt is None:
        return dt
    return parser.isoparse(dt)
