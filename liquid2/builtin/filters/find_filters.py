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


def _getitem(obj: Any, key: object, default: object = None) -> Any:
    """Helper for the `find` filter.

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

        if value is not None and not is_undefined(value):
            for item in left:
                if _getitem(item, key) == value:
                    return item

        for item in left:
            if item not in (False, None):
                return item

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

        if value is not None and not is_undefined(value):
            for i, item in enumerate(left):
                if _getitem(item, key) == value:
                    return i

        for i, item in enumerate(left):
            if item not in (False, None):
                return i

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

        if value is not None and not is_undefined(value):
            for item in left:
                if _getitem(item, key) == value:
                    return True

        return any(item not in (False, None) for item in left)
