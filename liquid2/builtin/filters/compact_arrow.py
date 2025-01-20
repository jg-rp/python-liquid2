"""An implementation of the `compact` filter that accepts lambda expressions."""

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

        if isinstance(key, LambdaExpression):
            items: list[object] = []
            for item, rv in zip(left, key.map(context, left), strict=True):
                if not is_undefined(rv) and rv is not None:
                    items.append(item)
            return items

        if key is not None:
            try:
                return [itm for itm in left if itm[key] is not None]
            except TypeError as err:
                raise LiquidTypeError(
                    f"can't read property '{key}'", token=None
                ) from err
        return [itm for itm in left if itm is not None]
