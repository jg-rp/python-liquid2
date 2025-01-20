"""Implementations of `sort` and `sort_natural` filters accepting lambda expressions."""

from __future__ import annotations

from functools import partial
from operator import getitem
from operator import itemgetter
from typing import TYPE_CHECKING
from typing import Any

from liquid2.builtin import LambdaExpression
from liquid2.builtin import Path
from liquid2.builtin import PositionalArgument
from liquid2.exceptions import LiquidSyntaxError
from liquid2.exceptions import LiquidTypeError
from liquid2.filter import sequence_arg
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
        """Raise a `LiquidSyntaxError` if _args_ are not valid."""
        if len(args) > 1:
            raise LiquidSyntaxError(
                f"{name!r} expects at most one argument, got {len(args)}",
                token=token,
            )

        if len(args) == 1:
            arg = args[0].value
            if isinstance(arg, LambdaExpression) and not isinstance(
                arg.expression, Path
            ):
                raise LiquidSyntaxError(
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
            scope: dict[str, object] = {}

            if len(key.params) == 1:
                param = key.params[0]
                with context.extend(scope):
                    for item in left:
                        scope[param] = item
                        rv = key.expression.evaluate(context)
                        items.append((item, _MAX_CH if is_undefined(rv) else rv))
            else:
                name_param, index_param = key.params[:2]
                with context.extend(scope):
                    for index, item in enumerate(left):
                        scope[index_param] = index
                        scope[name_param] = item
                        rv = key.expression.evaluate(context)
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
            scope: dict[str, object] = {}

            if len(key.params) == 1:
                param = key.params[0]
                with context.extend(scope):
                    for item in left:
                        scope[param] = item
                        rv = key.expression.evaluate(context)
                        items.append(
                            (item, _MAX_CH if is_undefined(rv) else str(rv).lower())
                        )
            else:
                name_param, index_param = key.params[:2]
                with context.extend(scope):
                    for index, item in enumerate(left):
                        scope[index_param] = index
                        scope[name_param] = item
                        rv = key.expression.evaluate(context)
                        items.append(
                            (item, _MAX_CH if is_undefined(rv) else str(rv).lower())
                        )

            return [item[0] for item in sorted(items, key=itemgetter(1))]

        if key:
            item_getter = partial(_getitem, key=str(key), default=_MAX_CH)
            return sorted(left, key=lambda obj: _lower(item_getter(obj)))

        return sorted(left, key=_lower)


# TODO: class SortNumericFilter(SortFilter):
