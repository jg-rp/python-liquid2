"""Implementations of `where`, `reject` and `compact` that accept lambda expressions."""

from __future__ import annotations

from operator import getitem
from typing import TYPE_CHECKING
from typing import Any
from typing import Iterable

from liquid2.builtin import LambdaExpression
from liquid2.builtin import Path
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
    """Helper for the where filter.

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


class _FilterFilter:
    """Base class for filters that filter array-like objects."""

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


class WhereFilter(_FilterFilter):
    """An implementation of the `where` filter that accepts lambda expressions."""

    def __call__(
        self,
        left: Iterable[object],
        key: str | LambdaExpression,
        value: object = None,
        *,
        context: RenderContext,
    ) -> list[object]:
        """Apply the filter and return the result."""
        left = sequence_arg(left)

        if isinstance(key, LambdaExpression):
            return [
                i
                for i, r in zip(left, key.map(context, left), strict=True)
                if not is_undefined(r) and is_truthy(r)
            ]

        if value is not None and not is_undefined(value):
            return [itm for itm in left if _getitem(itm, key) == value]

        return [itm for itm in left if _getitem(itm, key) not in (False, None)]


class RejectFilter(_FilterFilter):
    """An implementation of the `reject` filter that accepts lambda expressions."""

    def __call__(
        self,
        left: Iterable[object],
        key: str | LambdaExpression,
        value: object = None,
        *,
        context: RenderContext,
    ) -> list[object]:
        """Apply the filter and return the result."""
        left = sequence_arg(left)

        if isinstance(key, LambdaExpression):
            return [
                i
                for i, r in zip(left, key.map(context, left), strict=True)
                if is_undefined(r) or not is_truthy(r)
            ]

        if value is not None and not is_undefined(value):
            return [itm for itm in left if _getitem(itm, key) != value]

        return [itm for itm in left if _getitem(itm, key) in (False, None)]


class CompactFilter:
    """An implementation of the `compact` filter that accepts lambda expressions."""

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
        left: Iterable[object],
        key: str | LambdaExpression | None = None,
        *,
        context: RenderContext,
    ) -> list[object]:
        """Apply the filter and return the result."""
        left = sequence_arg(left)

        if isinstance(key, LambdaExpression):
            return [
                i
                for i, r in zip(left, key.map(context, left), strict=True)
                if not is_undefined(r) and r is not None
            ]

        if key is not None:
            try:
                return [itm for itm in left if itm[key] is not None]
            except TypeError as err:
                raise LiquidTypeError(
                    f"can't read property '{key}'", token=None
                ) from err

        return [itm for itm in left if itm is not None]
