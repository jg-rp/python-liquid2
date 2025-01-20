"""An implementation of the `map` filter that accepts lambda expressions."""

from __future__ import annotations

from operator import getitem
from typing import TYPE_CHECKING
from typing import Any
from typing import Iterable

from liquid2.builtin import LambdaExpression
from liquid2.builtin import Null
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


class _Null:
    """A null without a token for use by the map filter."""

    def __eq__(self, other: object) -> bool:
        return other is None or isinstance(other, (_Null, Null))

    def __str__(self) -> str:  # pragma: no cover
        return ""


_NULL = _Null()


def _getitem(sequence: Any, key: object, default: object = None) -> Any:
    """Helper for the map filter.

    Same as obj[key], but returns a default value if key does not exist
    in obj.
    """
    try:
        return getitem(sequence, key)
    except (KeyError, IndexError):
        return default
    except TypeError:
        if not hasattr(sequence, "__getitem__"):
            raise
        return default


class MapFilter:
    """An implementation of the `map` filter that accepts lambda expressions."""

    with_context = True

    def validate(
        self,
        _env: Environment,
        token: TokenT,
        name: str,
        args: list[KeywordArgument | PositionalArgument],
    ) -> None:
        """Raise a `LiquidSyntaxError` if _args_ are not valid."""
        if len(args) != 1:
            raise LiquidSyntaxError(
                f"{name!r} expects exactly one argument, got {len(args)}",
                token=token,
            )

        if not isinstance(args[0], PositionalArgument):
            raise LiquidSyntaxError(
                f"{name!r} takes no keyword arguments",
                token=token,
            )

        arg = args[0].value

        if isinstance(arg, LambdaExpression) and not isinstance(arg.expression, Path):
            raise LiquidSyntaxError(
                f"{name!r} expects a path to a variable, "
                f"got {arg.expression.__class__.__name__}",
                token=arg.expression.token,
            )

    def __call__(
        self,
        left: Iterable[object],
        first: str | LambdaExpression,
        *,
        context: RenderContext,
    ) -> list[object]:
        """Apply the filter and return the result."""
        left = sequence_arg(left)

        if isinstance(first, LambdaExpression):
            return [
                _NULL if is_undefined(item) else item
                for item in first.map(context, left)
            ]

        try:
            return [_getitem(itm, str(first), default=_NULL) for itm in left]
        except TypeError as err:
            raise LiquidTypeError("can't map sequence", token=None) from err
