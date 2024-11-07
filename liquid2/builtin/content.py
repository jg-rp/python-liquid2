"""The built in, standard implementation of the text content node."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import TextIO

from liquid2 import CommentToken
from liquid2 import ContentToken
from liquid2 import LinesToken
from liquid2 import Node
from liquid2 import OutputToken
from liquid2 import RawToken
from liquid2 import Tag
from liquid2 import TagToken
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

        right_trim = self.env.default_trim

        if peeked := stream.peek():  # noqa: SIM102
            if isinstance(
                peeked, (TagToken, OutputToken, CommentToken, RawToken, LinesToken)
            ):
                right_trim = peeked.wc[0]

        return self.node_class(token, self.env.trim(token.text, left_trim, right_trim))
