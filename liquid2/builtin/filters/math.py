"""Maths related filter functions."""

import decimal
import math

from liquid2.exceptions import LiquidTypeError
from liquid2.filter import math_filter
from liquid2.filter import num_arg
from liquid2.undefined import is_undefined


@math_filter
def abs_(left: float | int) -> float | int:
    """Return the absolute value of number _num_."""
    return abs(left)


@math_filter
def at_most(left: float | int, arg: float | int) -> float | int:
    """Return _val_ or _other_, whichever is smaller."""
    return min(left, num_arg(arg, default=0))


@math_filter
def at_least(left: float | int, arg: float | int) -> float | int:
    """Return _val_ or _other_, whichever is greater."""
    return max(left, num_arg(arg, default=0))


@math_filter
def ceil(left: float | int) -> float | int:
    """Return _num_ rounded up to the next integer."""
    return math.ceil(left)


@math_filter
def divided_by(left: float | int, right: object) -> float | int:
    """Return the result of dividing _num_ by _other_.

    If both _num_ and _other_ are integers, integer division is performed.
    """
    right = num_arg(right, default=0)

    try:
        if isinstance(right, int) and isinstance(left, int):
            return left // right
        return left / right
    except ZeroDivisionError as err:
        raise LiquidTypeError(f"can't divide by {right}", token=None) from err


@math_filter
def floor(left: float | int) -> float | int:
    """Return _num_ rounded down to the next integer."""
    return math.floor(left)


@math_filter
def minus(left: float | int, right: float | int) -> float | int:
    """Return the result of subtracting _other_ from _num_."""
    right = num_arg(right, default=0)

    if isinstance(left, int) and isinstance(right, int):
        return left - right
    return float(decimal.Decimal(str(left)) - decimal.Decimal(str(right)))


@math_filter
def plus(left: float | int, right: float | int) -> float | int:
    """Return the result of adding _other_ to _num_."""
    right = num_arg(right, default=0)

    if isinstance(left, int) and isinstance(right, int):
        return left + right
    return float(decimal.Decimal(str(left)) + decimal.Decimal(str(right)))


@math_filter
def round_(left: float | int, digits: int | None = None) -> float | int:
    """Returns the result of rounding _num_ to _digits_ decimal digits."""
    if digits is None or is_undefined(digits):
        return round(left)

    try:
        _digits = num_arg(digits)
    except LiquidTypeError:
        # Probably a string that can't be cast to an int or float
        return round(left)

    if isinstance(_digits, float):
        _digits = int(_digits)

    if _digits < 0:
        return 0
    if _digits == 0:
        return round(left)

    return round(left, _digits)


@math_filter
def times(left: float | int, right: float | int) -> float | int:
    """Return the result of multiplying _num_ by _other_."""
    right = num_arg(right, default=0)

    if isinstance(left, int) and isinstance(right, int):
        return left * right
    return float(decimal.Decimal(str(left)) * decimal.Decimal(str(right)))


@math_filter
def modulo(left: float | int, right: float | int) -> float | int:
    """Return the remainder of dividing _num_ by _other_."""
    right = num_arg(right, default=0)

    try:
        if isinstance(left, int) and isinstance(right, int):
            return left % right
        return float(decimal.Decimal(str(left)) % decimal.Decimal(str(right)))
    except ZeroDivisionError as err:
        raise LiquidTypeError(
            f"can't divide by {right}",
            token=None,
        ) from err
