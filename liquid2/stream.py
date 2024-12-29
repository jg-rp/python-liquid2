"""Step through a stream of tokens."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Sequence

from .exceptions import LiquidSyntaxError
from .token import TagToken
from .token import Token
from .token import TokenType
from .token import WhitespaceControl
from .token import is_tag_token
from .token import is_token_type

if TYPE_CHECKING:
    from .token import TokenT


class TokenStream:
    """Step through a stream of tokens."""

    def __init__(self, tokens: Sequence[TokenT]) -> None:
        self.tokens = tokens
        self.pos = 0
        self.trim_carry = WhitespaceControl.DEFAULT
        self.eoi = Token(type_=TokenType.EOI, value="", index=-1, source="")

    def current(self) -> TokenT:
        """Return the item at self[0] without advancing the iterator."""
        try:
            return self.tokens[self.pos]
        except IndexError:
            return self.eoi

    def next(self) -> TokenT:
        """Return the next token and advance the iterator."""
        try:
            token = self.tokens[self.pos]
            self.pos += 1
            return token
        except IndexError:
            return self.eoi

    def peek(self) -> TokenT:
        """Return the item at self[1] without advancing the iterator."""
        try:
            return self.tokens[self.pos + 1]
        except IndexError:
            return self.eoi

    def expect(self, typ: TokenType) -> None:
        """Raise a _LiquidSyntaxError_ if the current token type doesn't match _typ_."""
        token = self.current()
        if token.type_ != typ:
            raise LiquidSyntaxError(
                f"expected {typ.name}, found {token.type_.name}",
                token=token,
            )

    def expect_one_of(self, *types: TokenType) -> None:
        """Raise a _LiquidSyntaxError_ if the current token type is not in _types_."""
        token = self.current()
        if token.type_ not in types:
            type_string = " or ".join([t.name for t in types])
            raise LiquidSyntaxError(
                f"expected {type_string}, found {token.type_.name}",
                token=token,
            )

    def expect_tag(self, tag_name: str) -> None:
        """Raise a syntax error if the current token is not a tag with _tag_name_."""
        token = self.current()
        if not isinstance(token, TagToken):
            raise LiquidSyntaxError(
                f"expected tag '{tag_name}', found {token.type_.name}",
                token=token,
            )

        if token.name != tag_name:
            raise LiquidSyntaxError(
                f"expected tag {tag_name!r}, found {token.name!r}", token=token
            )

    def expect_eos(self) -> None:
        """Raise a syntax error if we're not at the end of the stream."""
        token = self.current()
        if token.type_ != TokenType.EOI:
            if is_token_type(token, TokenType.WORD):
                name = repr(token.value)
            else:
                name = token.type_.name
            raise LiquidSyntaxError(f"unexpected token {name}", token=token)

    def is_tag(self, tag_name: str) -> bool:
        """Return _True_ if the current token is a tag named _tag_name_."""
        token = self.current()
        if is_tag_token(token):
            return token.name == tag_name
        return False

    def into_inner(self) -> TokenStream:
        """Return a new stream over the current token's expression, consuming the token.

        Raises:
            LiquidSyntaxError: if the current token is not a tag
        """
        token = self.next()

        if not isinstance(token, TagToken):
            raise LiquidSyntaxError(
                f"expected a tag, found {token.type_.name}", token=token
            )

        if not token.expression:
            raise LiquidSyntaxError("expected a expression", token=token)

        return TokenStream(token.expression)
