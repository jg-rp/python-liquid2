"""Implementations of `find`, `find_index` and `has` accepting lambda expressions."""

from __future__ import annotations

from operator import getitem
from typing import TYPE_CHECKING
from typing import Any
from typing import Iterable

from liquid2.builtin import LambdaExpression
from liquid2.builtin import PositionalArgument
from liquid2.builtin.expressions import is_truthy
from liquid2.exceptions import LiquidTypeError
from liquid2.filter import sequence_arg
from liquid2.undefined import is_undefined

if TYPE_CHECKING:
    from liquid2 import Environment
    from liquid2 import RenderContext
    from liquid2 import TokenT
    from liquid2.builtin import KeywordArgument


def _getitem(sequence: Any, key: object, default: object = None) -> Any:
    """Helper for the `find` filter.

    Same as sequence[key], but returns a default value if key does not exist
    in sequence, and handles some corner cases so as to mimic Shopify/Liquid
    behavior.
    """
    try:
        return getitem(sequence, key)
    except (KeyError, IndexError):
        return default
    except TypeError:
        if isinstance(sequence, str) and isinstance(key, str) and key in sequence:
            return key
        if isinstance(sequence, int) and isinstance(key, int):
            return sequence == key
        return default


class FindFilter:
    """An implementation of the `find` filter that accepts lambda expressions."""

    with_context = True

    def validate(
        self,
        _env: Environment,
        token: TokenT,
        name: str,
        args: list[KeywordArgument | PositionalArgument],
    ) -> None:
        """Raise a `LiquidTypeError` if _args_ are not valid."""
        if len(args) not in (1, 2):
            raise LiquidTypeError(
                f"{name!r} expects one or two arguments, got {len(args)}",
                token=token,
            )

        arg = args[0].value

        if isinstance(arg, LambdaExpression) and len(args) != 1:
            raise LiquidTypeError(
                f"{name!r} expects one argument when given a lambda expressions",
                token=args[1].token,
            )

    def __call__(
        self,
        left: Iterable[object],
        key: str | LambdaExpression,
        value: object = None,
        *,
        context: RenderContext,
    ) -> object:
        """Apply the filter and return the result."""
        left = sequence_arg(left)

        if isinstance(key, LambdaExpression):
            for item, rv in zip(left, key.map(context, left), strict=True):
                if not is_undefined(rv) and is_truthy(rv):
                    return item

        elif value is not None and not is_undefined(value):
            return next((itm for itm in left if _getitem(itm, key) == value), None)

        else:
            return next(
                (itm for itm in left if _getitem(itm, key) not in (False, None)),
                None,
            )

        return None


class FindIndexFilter(FindFilter):
    """An implementation of the `find_index` filter that accepts lambda expressions."""

    def __call__(
        self,
        left: Iterable[object],
        key: str | LambdaExpression,
        value: object = None,
        *,
        context: RenderContext,
    ) -> object:
        """Apply the filter and return the result."""
        left = sequence_arg(left)

        if isinstance(key, LambdaExpression):
            for i, pair in enumerate(zip(left, key.map(context, left), strict=True)):
                item, rv = pair
                if not is_undefined(rv) and is_truthy(rv):
                    return i

        elif value is not None and not is_undefined(value):
            return next(
                (i for i, itm in enumerate(left) if _getitem(itm, key) == value),
                None,
            )

        else:
            return next(
                (
                    i
                    for i, itm in enumerate(left)
                    if _getitem(itm, key) not in (False, None)
                ),
                None,
            )

        return None


class HasFilter(FindFilter):
    """An implementation of the `has` filter that accepts lambda expressions."""

    def __call__(
        self,
        left: Iterable[object],
        key: str | LambdaExpression,
        value: object = None,
        *,
        context: RenderContext,
    ) -> bool:
        """Apply the filter and return the result."""
        left = sequence_arg(left)

        if isinstance(key, LambdaExpression):
            for rv in key.map(context, left):
                if not is_undefined(rv) and is_truthy(rv):
                    return True

        elif value is not None and not is_undefined(value):
            return any(
                (itm for itm in left if _getitem(itm, key) == value),
            )

        else:
            return any(
                (itm for itm in left if _getitem(itm, key) not in (False, None)),
            )

        return False
