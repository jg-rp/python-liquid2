"""An implementation of the `uniq` filter that accepts lambda expressions."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Iterable

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

MISSING = object()


class UniqFilter:
    """An implementation of the `uniq` filter that accepts lambda expressions."""

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
    ) -> list[object]:
        """Apply the filter and return the result."""
        left = sequence_arg(left)

        # Note that we're not using a dict or set for deduplication because we need
        # to handle sequences containing unhashable objects, like dictionaries and
        # lists. This is probably quite slow.

        if isinstance(key, LambdaExpression):
            keys: list[object] = []
            items: list[object] = []

            for item, rv in zip(left, key.map(context, left), strict=True):
                current_key = MISSING if is_undefined(rv) else rv
                if current_key not in keys:
                    keys.append(current_key)
                    items.append(item)

            return items

        if key is not None:
            keys = []
            result = []
            for obj in left:
                try:
                    item = obj[key]
                except KeyError:
                    item = MISSING
                except TypeError as err:
                    raise LiquidTypeError(
                        f"can't read property '{key}' of {obj}",
                        token=None,
                    ) from err

                if item not in keys:
                    keys.append(item)
                    result.append(obj)

            return result

        return [obj for i, obj in enumerate(left) if left.index(obj) == i]
