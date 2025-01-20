"""An implementation of the `sum` filter that accepts lambda expressions."""

from __future__ import annotations

from decimal import Decimal
from operator import getitem
from typing import TYPE_CHECKING
from typing import Any
from typing import Iterable

from liquid2.builtin import LambdaExpression
from liquid2.builtin import Path
from liquid2.builtin import PositionalArgument
from liquid2.exceptions import LiquidSyntaxError
from liquid2.filter import decimal_arg
from liquid2.filter import sequence_arg
from liquid2.undefined import is_undefined

if TYPE_CHECKING:
    from liquid2 import Environment
    from liquid2 import RenderContext
    from liquid2 import TokenT
    from liquid2.builtin import KeywordArgument


def _getitem(sequence: Any, key: object, default: object = None) -> Any:
    """Helper for the sum filter.

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


class SumFilter:
    """An implementation of the `sum` filter that accepts lambda expressions."""

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
        left: Iterable[object],
        key: str | LambdaExpression | None = None,
        *,
        context: RenderContext,
    ) -> float | int:
        """Apply the filter and return the result."""
        left = sequence_arg(left)

        if isinstance(key, LambdaExpression):
            rv = sum(
                decimal_arg(item, 0)
                for item in key.map(context, left)
                if not is_undefined(item)
            )
        elif key is not None and not is_undefined(key):
            rv = sum(decimal_arg(_getitem(elem, key, 0), 0) for elem in left)
        else:
            rv = sum(decimal_arg(elem, 0) for elem in left)

        if isinstance(rv, Decimal):
            return float(rv)
        return rv
