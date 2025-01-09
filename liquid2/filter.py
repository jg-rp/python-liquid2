"""Filter function helpers."""

from __future__ import annotations

from decimal import Decimal
from functools import wraps
from typing import Any
from typing import Callable
from typing import Iterable
from typing import Iterator
from typing import Mapping
from typing import Sequence

from .exceptions import LiquidTypeError
from .limits import to_int
from .stringify import to_liquid_string
from .undefined import is_undefined


def bool_arg(value: object) -> bool:
    """Return _True_ if _value_ is liquid truthy, or _False_ otherwise."""
    return value is None or value is False or (is_undefined(value) and value.poke())


def mapping_arg(value: object) -> Mapping[Any, Any]:
    """Make sure _value_ is a mapping type.

    Raises:
        LiquidTypeError: If _value_ can't be coerced to a mapping.
    """
    if is_undefined(value):
        value.poke()
        return {}

    if not isinstance(value, Mapping):
        raise LiquidTypeError(
            f"expected a mapping, found {value.__class__.__name__}", token=None
        )

    return value


def int_arg(val: Any, default: int | None = None) -> int:
    """Return _val_ as an int, or _default_ if _val_ can't be cast to an int."""
    try:
        return to_int(val)
    except ValueError as err:
        if default is not None:
            return default
        raise LiquidTypeError(
            f"expected an int or string, found {type(val).__name__}",
            token=None,
        ) from err


def num_arg(val: Any, default: float | int | None = None) -> float | int:
    """Return _val_ as an int or float, or _default_ if casting fails."""
    if isinstance(val, (int, float)):
        return val

    if isinstance(val, str):
        try:
            return to_int(val)
        except ValueError:
            pass

        try:
            return float(val)
        except ValueError as err:
            if default is not None:
                return default
            raise LiquidTypeError(
                f"could not cast string '{val}' to a number",
                token=None,
            ) from err

    elif default is not None:
        return default

    raise LiquidTypeError(
        f"expected an int, float or string, found {type(val).__name__}",
        token=None,
    )


def decimal_arg(val: Any, default: int | Decimal | None = None) -> int | Decimal:
    """Return _val_ as an int or decimal, or _default_ is casting fails."""
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return Decimal(str(val))

    if isinstance(val, str):
        try:
            return to_int(val)
        except ValueError:
            pass

        try:
            return Decimal(val)
        except ValueError as err:
            if default is not None:
                return default
            raise LiquidTypeError(
                f"could not cast string '{val}' to a number",
                token=None,
            ) from err

    elif default is not None:
        return default

    raise LiquidTypeError(
        f"expected an int, float or string, found {type(val).__name__}",
        token=None,
    )


def with_context(_filter: Callable[..., Any]) -> Callable[..., Any]:
    """Ensure the wrapped callable is passed a `context` keyword argument."""
    _filter.with_context = True  # type: ignore
    return _filter


def with_environment(_filter: Callable[..., Any]) -> Callable[..., Any]:
    """Ensure the wrapped callable is passed an `environment` keyword argument."""
    _filter.with_environment = True  # type: ignore
    return _filter


def string_filter(_filter: Callable[..., Any]) -> Callable[..., Any]:
    """A filter function decorator that converts the first argument to a string."""

    @wraps(_filter)
    def wrapper(val: object, *args: Any, **kwargs: Any) -> Any:
        return _filter(to_liquid_string(val, auto_escape=False), *args, **kwargs)

    return wrapper


def sequence_filter(_filter: Callable[..., Any]) -> Callable[..., Any]:
    """Coerce the left value to sequence.

    This is intended to mimic the semantics of the reference implementation's
    `InputIterator` class.
    """

    @wraps(_filter)
    def wrapper(val: object, *args: Any, **kwargs: Any) -> Any:
        if is_undefined(val):
            val.poke()
            val = []
        elif isinstance(val, str):
            val = list(val)
        elif isinstance(val, Sequence):
            val = _flatten(val)
        elif isinstance(val, Mapping) or not isinstance(val, Iterable):
            val = [val]
        return _filter(val, *args, **kwargs)

    return wrapper


def math_filter(_filter: Callable[..., Any]) -> Callable[..., Any]:
    """Raise a `LiquidTypeError` if the filter value can not be cast to a number."""

    @wraps(_filter)
    def wrapper(val: object, *args: Any, **kwargs: Any) -> Any:
        val = num_arg(val, default=0)
        return _filter(val, *args, **kwargs)

    return wrapper


def _flatten(it: Iterable[Any], level: int = 5) -> list[object]:
    """Flatten nested "liquid arrays" into a list."""

    def flatten(it: Iterable[Any], level: int = 5) -> Iterator[object]:
        for obj in it:
            if not level or not isinstance(obj, (list, tuple)):
                yield obj
            else:
                yield from flatten(obj, level=level - 1)

    return list(flatten(it, level))
