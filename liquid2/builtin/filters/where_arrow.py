"""An implementation of the `where` filter that accepts lambda expressions."""

from __future__ import annotations

from operator import getitem
from typing import TYPE_CHECKING
from typing import Any
from typing import Iterable

from liquid2.builtin import LambdaExpression
from liquid2.builtin import PositionalArgument
from liquid2.builtin.expressions import is_truthy
from liquid2.exceptions import LiquidSyntaxError
from liquid2.filter import sequence_arg
from liquid2.undefined import is_undefined

if TYPE_CHECKING:
    from liquid2 import Environment
    from liquid2 import RenderContext
    from liquid2 import TokenT
    from liquid2.builtin import KeywordArgument


def _getitem(sequence: Any, key: object, default: object = None) -> Any:
    """Helper for the where filter.

    Same as sequence[key], but returns a default value if key does not exist
    in sequence.
    """
    try:
        return getitem(sequence, key)
    except (KeyError, IndexError):
        return default
    except TypeError:
        if not hasattr(sequence, "__getitem__"):
            raise
        return default


class WhereFilter:
    """An implementation of the `where` filter that accepts lambda expressions."""

    with_context = True

    def validate(
        self,
        _env: Environment,
        token: TokenT,
        name: str,
        args: list[KeywordArgument | PositionalArgument],
    ) -> None:
        """Raise a `LiquidSyntaxError` if _args_ are not valid."""
        if len(args) not in (1, 2):
            raise LiquidSyntaxError(
                f"{name!r} expects one or two arguments, got {len(args)}",
                token=token,
            )

        arg = args[0].value

        if isinstance(arg, LambdaExpression) and len(args) != 1:
            raise LiquidSyntaxError(
                f"{name!r} expects one argument when given a lambda expressions",
                token=args[1].token,
            )

    def __call__(
        self,
        left: Iterable[object],
        first: str | LambdaExpression,
        value: object = None,
        *,
        context: RenderContext,
    ) -> list[object]:
        """Apply the filter and return the result."""
        left = sequence_arg(left)

        if isinstance(first, LambdaExpression):
            items: list[object] = []
            scope: dict[str, object] = {}

            if len(first.params) == 1:
                param = first.params[0]
                with context.extend(scope):
                    for item in left:
                        scope[param] = item
                        rv = first.expression.evaluate(context)
                        if not is_undefined(rv) and is_truthy(rv):
                            items.append(item)
            else:
                name_param, index_param = first.params[:2]
                with context.extend(scope):
                    for index, item in enumerate(left):
                        scope[index_param] = index
                        scope[name_param] = item
                        rv = first.expression.evaluate(context)
                        if not is_undefined(rv) and is_truthy(rv):
                            items.append(item)

            return items

        if value is not None and not is_undefined(value):
            return [itm for itm in left if _getitem(itm, first) == value]
        return [itm for itm in left if _getitem(itm, first) not in (False, None)]
