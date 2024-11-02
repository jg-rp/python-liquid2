"""Step through a stream of tokens."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Container
from typing import Iterable
from typing import Type

from more_itertools import peekable

from .exceptions import LiquidSyntaxError
from .token import TagToken
from .token import Token
from .token import TokenType
from .token import WhitespaceControl

if TYPE_CHECKING:
    from .token import TokenT

# TODO: benchmark without peelable and iterable


class TokenStream(peekable):  # type: ignore
    """Step through or iterate a stream of tokens."""

    def __init__(self, iterable: Iterable[TokenT]) -> None:
        super().__init__(iterable)
        self.trim_carry = WhitespaceControl.DEFAULT
        self.eoi = Token(type_=TokenType.EOI, value="", index=-1, source="")

    def __str__(self) -> str:  # pragma: no cover
        token = self.current()
        peeked = self.peek()

        try:
            return (
                f"current: '{token}' at {self._index(token)}, "
                f"next: '{peeked}' at {self._index(peeked)}"
            )
        except StopIteration:
            return "EOI"

    def _index(self, token: TokenT) -> int:
        if hasattr(token, "index"):
            return token.index  # type: ignore
        if hasattr(token, "start"):
            return token.start  # type: ignore
        return -1

    # TODO: always EOI token, never None

    def current(self) -> TokenT:
        """Return the item at self[0] without advancing the iterator."""
        try:
            return self[0]  # type: ignore
        except IndexError:
            return self.eoi

    def next(self) -> TokenT:
        """Return the next token and advance the iterator."""
        return next(self, self.eoi)

    def peek(self) -> TokenT:  # type: ignore
        """Return the item at self[1] without advancing the iterator."""
        try:
            return self[1]  # type: ignore
        except IndexError:
            return self.eoi

    def push(self, token: TokenT) -> None:
        """Push a token back on to the stream."""
        self.prepend(token)

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

    def expect_peek(self, typ: TokenType) -> None:
        """Raise a _LiquidSyntaxError_ if the next token type does not match _typ_."""
        token = self.peek()
        if token.type_ != typ:
            raise LiquidSyntaxError(
                f"expected {typ.name}, found {token.type_.name}",
                token=token,
            )

    def expect_tag(self, tag_name: str) -> None:
        """Raise a syntax error if the current token is not a tag with _tag_name_."""
        token = self.current()
        if not isinstance(token, TagToken):
            raise LiquidSyntaxError(
                f"expected tag '{tag_name}', found {token.__class__.__name__}",
                token=token,
            )

        if token.name != tag_name:
            raise LiquidSyntaxError(
                f"expected tag '{tag_name}', found {token.name}", token=token
            )

    def expect_eos(self) -> None:
        """Raise a syntax error if we're not at the end of the stream."""
        token = self.current()
        if token.type_ != TokenType.EOI:
            raise LiquidSyntaxError(
                f"unexpected {token.__class__.__name__}", token=token
            )

    def is_tag(self, tag_name: str) -> bool:
        """Return _True_ if the current token is a tag named _tag_name_."""
        token = self.current()
        if isinstance(token, TagToken):  # TODO: try without isinstance
            return token.name == tag_name
        return False

    def is_word(self, value: str) -> bool:
        """Return _True_ if the current token is a word with value equal to _value_."""
        token = self.current()
        if isinstance(token, Token) and token.type_ == TokenType.WORD:
            return token.value == value
        return False

    def peek_word(self, value: str) -> bool:
        """Return _True_ if the next token is a word with value equal to _value_."""
        token = self.peek()
        if isinstance(token, Token) and token.type_ == TokenType.WORD:
            return token.value == value
        return False

    def is_one_of(self, tag_names: Container[str]) -> bool:
        """Return _True_ if the current token is a tag with a name in _tag_names_."""
        token = self.current()
        if isinstance(token, TagToken):
            return token.name in tag_names
        return False

    def peek_one_of(self, tag_names: Container[str]) -> bool:
        """Return _True_ if the next token is a tag with a name in _tag_names_."""
        peeked = self.peek()
        if isinstance(peeked, TagToken):
            return peeked.name in tag_names
        return False

    def into_inner(self) -> TokenStream:
        """Return a new stream over the current token's expression, consuming the token.

        Raises:
            LiquidSyntaxError: if the current token is not a tag
        """
        token = self.next()

        if not isinstance(token, TagToken):
            raise LiquidSyntaxError(
                f"expected a tag, found {token.__class__.__name__}", token=token
            )

        if not token.expression:
            raise LiquidSyntaxError("expected a expression", token=token)

        return TokenStream(token.expression)
