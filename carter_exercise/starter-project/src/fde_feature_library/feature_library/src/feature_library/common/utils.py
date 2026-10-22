# standard libs
from decimal import ROUND_HALF_UP, Decimal

__smart_contract_feature__ = True


def str_to_bool(string: str) -> bool:
    """Convert a string true to bool True, default value of False.

    :param string: case-insensitive, should be "true" or "false".
    :return: boolean true if the string is "true", false otherwise.
    """
    return str(string).lower() == "true"


def round_decimal(
    amount: Decimal,
    decimal_places: int,
    rounding: str = ROUND_HALF_UP,
) -> Decimal:
    """Round to specified number of decimal places.

    :param amount: Decimal, amount to round
    :param decimal_places: int, number of places to round to
    :param rounding: the type of rounding strategy to use
    :return: Decimal, rounded amount
    """
    return amount.quantize(Decimal((0, (1,), -int(decimal_places))), rounding=rounding)


def remove_exponent(d: Decimal) -> Decimal:
    """Safely remove trailing zeros when dealing with exponents.

    This is useful when using a
    decimal value in a string used for informational purposes (e.g. instruction_details or logging).
    E.g: remove_exponent(Decimal("5E+3"))
    Returns: Decimal('5000')
    """
    return d.quantize(Decimal(1)) if d == d.to_integral() else d.normalize()
