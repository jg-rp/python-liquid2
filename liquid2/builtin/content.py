"""The built in, standard implementation of the text content node."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import TextIO

from liquid2 import ContentToken
from liquid2 import Node
from liquid2 import Tag
from liquid2 import WhitespaceControl

if TYPE_CHECKING:
    from liquid2 import MetaNode
    from liquid2 import RenderContext
    from liquid2 import TokenStream
    from liquid2 import TokenT


class ContentNode(Node):
    """The built in, standard implementation of the text content node."""

    __slots__ = ("text",)

    def __init__(self, token: TokenT, text: str) -> None:
        super().__init__(token)
        self.text = text

    def __str__(self) -> str:
        return self.text

    def render_to_output(self, _context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        return buffer.write(self.text)

    def children(self) -> list[MetaNode]:
        """Return a list of child nodes and/or expressions associated with this node."""
        return []


class Content(Tag):
    """The template text content pseudo tag."""

    block = False
    node_class = ContentNode

    def parse(
        self,
        stream: TokenStream,
        *,
        left_trim: WhitespaceControl = WhitespaceControl.DEFAULT,
    ) -> Node:
        """Parse tokens from _stream_ into an AST node."""
        token = stream.current()
        assert isinstance(token, ContentToken)

        peeked = stream.peek()

        right_trim = (
            peeked.wc[0]  # type: ignore
            if peeked is not None
            else self.env.trim
        )

        return self.node_class(token, self.trim(token.text, left_trim, right_trim))

    def trim(  # noqa: PLR0911
        self,
        text: str,
        left_trim: WhitespaceControl,
        right_trim: WhitespaceControl,
    ) -> str:
        """Return text after applying whitespace control."""
        match (left_trim, right_trim):
            case (WhitespaceControl.DEFAULT, WhitespaceControl.DEFAULT):
                return self.trim(text, self.env.trim, self.env.trim)
            case (WhitespaceControl.DEFAULT, _):
                return self.trim(text, self.env.trim, right_trim)
            case (_, WhitespaceControl.DEFAULT):
                return self.trim(text, left_trim, self.env.trim)

            case (WhitespaceControl.MINUS, WhitespaceControl.MINUS):
                return text.strip()
            case (WhitespaceControl.MINUS, WhitespaceControl.PLUS):
                return text.lstrip()
            case (WhitespaceControl.PLUS, WhitespaceControl.MINUS):
                return text.rstrip()
            case (WhitespaceControl.PLUS, WhitespaceControl.PLUS):
                return text

            case (WhitespaceControl.TILDE, WhitespaceControl.TILDE):
                return text.strip("\r\n")
            case (WhitespaceControl.TILDE, right):
                return self.trim(text.lstrip("\r\n"), WhitespaceControl.PLUS, right)
            case (left, WhitespaceControl.TILDE):
                return self.trim(text.rstrip("\r\n"), left, WhitespaceControl.PLUS)
            case _:
                return text
