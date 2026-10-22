__smart_contract_feature__ = True

from typing import NamedTuple

from contracts_api import Rejection, RejectionReason

# Used primarily when retrieving schedule times from parameters
Time = NamedTuple(
    "Time",
    [
        ("hour", int),
        ("minute", int),
        ("second", int),
    ],
)


def validate_time_format(time_str: str) -> Rejection | None:
    """Validates that a string matches the HH:MM:SS format.

    Args:
        time_str: the string to validate.

    Returns:
        A Rejection if the format is invalid, otherwise None.
    """
    # Check total length (HH:MM:SS is exactly 8 characters)
    if len(time_str) != 8:
        return Rejection(
            message=f"Invalid time format: '{time_str}'. Expected 8 characters (HH:MM:SS).",
            reason_code=RejectionReason.AGAINST_TNC,
        )

    # Check positions of colons
    if time_str[2] != ":" or time_str[5] != ":":
        return Rejection(
            message=f"Invalid time format: '{time_str}'. Expected colons at positions 2 and 5.",
            reason_code=RejectionReason.AGAINST_TNC,
        )

    # Strip the colons and check that the rest is numeric.
    numeric_part = time_str.replace(":", "")
    if not numeric_part.isdigit():
        return Rejection(
            message=f"Invalid time format: '{time_str}'. Time segments must be numeric.",
            reason_code=RejectionReason.AGAINST_TNC,
        )

    return None


def parse_time_str(time_str: str) -> Time:
    """Parses a time string in HH:MM:SS format into a Time named tuple.

    Raises assertion error if the input string is in an invalid format.

    Args:
        time_str: the string to parse.

    Returns:
        The parsed Time named tuple.
    """
    rejection = validate_time_format(time_str)
    assert rejection is None, rejection

    hour, minute, second = map(int, time_str.split(":"))
    return Time(
        hour=hour,
        minute=minute,
        second=second,
    )
