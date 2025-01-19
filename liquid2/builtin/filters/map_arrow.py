"""An implementation of a `map` filter that accepts an arrow function."""

from __future__ import annotations

from itertools import zip_longest
from operator import getitem
from typing import TYPE_CHECKING
from typing import Any
from typing import Iterable

from liquid2.builtin import ArrowFunction
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


class MapFilter:
    """An implementation of a `map` filter that accepts an arrow function."""

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

        if isinstance(arg, ArrowFunction) and not isinstance(arg.expression, Path):
            raise LiquidSyntaxError(
                f"{name!r} expects a path to a variable, "
                f"got {arg.expression.__class__.__name__}",
                token=arg.expression.token,
            )

    def __call__(
        self,
        left: Iterable[object],
        arrow: str | ArrowFunction,
        *,
        context: RenderContext,
    ) -> list[object]:
        """Apply the filter and return the result."""
        left = sequence_arg(left)

        if isinstance(arrow, ArrowFunction):
            items: list[object] = []
            scope: dict[str, object] = {}

            if len(arrow.params) == 1:
                param = arrow.params[0]
                with context.extend(scope):
                    for item in left:
                        scope[param] = item
                        items.append(arrow.expression.evaluate(context))
            else:
                name_param, index_param = arrow.params[:2]
                with context.extend(scope):
                    for index, item in enumerate(left):
                        scope[index_param] = index
                        scope[name_param] = item
                        items.append(arrow.expression.evaluate(context))

            return [_NULL if is_undefined(item) else item for item in items]

        try:
            return [_getitem(itm, str(arrow), default=_NULL) for itm in left]
        except TypeError as err:
            raise LiquidTypeError("can't map sequence", token=None) from err
