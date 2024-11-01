from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .token import TokenT
    from .token import Token


class LiquidSyntaxError(Exception):
    """An exception raised due to a syntax error."""

    def __init__(self, *args: object, token: TokenT | Token) -> None:
        super().__init__(*args)
        self.token = token
