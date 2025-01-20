"""Implementations of `sort` and `sort_natural` filters accepting lambda expressions."""

from __future__ import annotations

import math
import re
from decimal import Decimal
from functools import partial
from operator import getitem
from operator import itemgetter
from typing import TYPE_CHECKING
from typing import Any

from liquid2.builtin import LambdaExpression
from liquid2.builtin import Path
from liquid2.builtin import PositionalArgument
from liquid2.exceptions import LiquidTypeError
from liquid2.filter import sequence_arg
from liquid2.limits import to_int
from liquid2.undefined import is_undefined

if TYPE_CHECKING:
    from liquid2 import Environment
    from liquid2 import RenderContext
    from liquid2 import TokenT
    from liquid2.builtin import KeywordArgument

# Send objects with missing keys to the end when sorting a list.
_MAX_CH = chr(0x10FFFF)


def _getitem(obj: Any, key: object, default: object = None) -> Any:
    """Helper for the sort filter.

    Same as obj[key], but returns a default value if key does not exist
    in obj.
    """
    try:
        return getitem(obj, key)
    except (KeyError, IndexError):
        return default
    except TypeError:
        if not hasattr(obj, "__getitem__"):
            raise
        return default


def _lower(obj: Any) -> str:
    """Helper for the sort filter."""
    try:
        return str(obj).lower()
    except AttributeError:
        return ""


class SortFilter:
    """An implementation of the `sort` filter that accepts lambda expressions."""

    with_context = True

    def validate(
        self,
        _env: Environment,
        token: TokenT,
        name: str,
        args: list[KeywordArgument | PositionalArgument],
    ) -> None:
        """Raise a `LiquidTypeError` if _args_ are not valid."""
        if len(args) > 1:
            raise LiquidTypeError(
                f"{name!r} expects at most one argument, got {len(args)}",
                token=token,
            )

        if len(args) == 1:
            arg = args[0].value
            if isinstance(arg, LambdaExpression) and not isinstance(
                arg.expression, Path
            ):
                raise LiquidTypeError(
                    f"{name!r} expects a path to a variable, "
                    f"got {arg.expression.__class__.__name__}",
                    token=arg.expression.token,
                )

    def __call__(
        self,
        left: object,
        key: str | LambdaExpression | None = None,
        *,
        context: RenderContext,
    ) -> list[object]:
        """Apply the filter and return the result."""
        left = sequence_arg(left)

        if isinstance(key, LambdaExpression):
            items: list[tuple[object, object]] = []
            for item, rv in zip(left, key.map(context, left), strict=True):
                items.append((item, _MAX_CH if is_undefined(rv) else rv))
            return [item[0] for item in sorted(items, key=itemgetter(1))]

        if key:
            key_func = partial(_getitem, key=str(key), default=_MAX_CH)
            return sorted(left, key=key_func)

        try:
            return sorted(left)
        except TypeError as err:
            raise LiquidTypeError("can't sort sequence", token=None) from err


class SortNaturalFilter(SortFilter):
    """An implementation of the `sort` filter that accepts a lambda expression."""

    def __call__(
        self,
        left: object,
        key: str | LambdaExpression | None = None,
        *,
        context: RenderContext,
    ) -> list[object]:
        """Apply the filter and return the result."""
        left = sequence_arg(left)

        if isinstance(key, LambdaExpression):
            items: list[tuple[object, object]] = []
            for item, rv in zip(left, key.map(context, left), strict=True):
                items.append((item, _MAX_CH if is_undefined(rv) else str(rv).lower()))
            return [item[0] for item in sorted(items, key=itemgetter(1))]

        if key:
            item_getter = partial(_getitem, key=str(key), default=_MAX_CH)
            return sorted(left, key=lambda obj: _lower(item_getter(obj)))

        return sorted(left, key=_lower)


RE_NUMERIC = re.compile(r"-?\d+")


class SortNumericFilter(SortFilter):
    """An implementation `sort_numeric` that accepts a lambda expression."""

    def __call__(
        self,
        left: object,
        key: str | LambdaExpression | None = None,
        *,
        context: RenderContext,
    ) -> list[object]:
        """Apply the filter and return the result."""
        left = sequence_arg(left)

        if isinstance(key, LambdaExpression):
            items: list[tuple[object, object]] = []
            for item, rv in zip(left, key.map(context, left), strict=True):
                items.append((item, _MAX_CH if is_undefined(rv) else rv))
            return [item[0] for item in sorted(items, key=lambda i: _ints(i[1]))]

        if key:
            _key = str(key)
            return sorted(left, key=lambda item: _ints(_get_numeric_item(item, _key)))
        return sorted(left, key=_ints)


def _get_numeric_item(sequence: Any, key: object, default: object = None) -> Any:
    """Item getter for the `sort_numeric` filter."""
    try:
        return getitem(sequence, key)
    except (KeyError, IndexError, TypeError):
        return default


def _ints(obj: object) -> tuple[int | float | Decimal, ...]:
    """Key function for the `sort_numeric` filter."""
    if isinstance(obj, bool):
        # isinstance(False, int) == True
        return (math.inf,)
    if isinstance(obj, (int, float, Decimal)):
        return (obj,)

    ints = tuple(to_int(n) for n in RE_NUMERIC.findall(str(obj)))

    if not ints:
        return (math.inf,)
    return ints
