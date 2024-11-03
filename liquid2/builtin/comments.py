"""The built in, standard implementation of the comment node."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import TextIO

from liquid2 import CommentToken
from liquid2 import Node
from liquid2 import Tag

if TYPE_CHECKING:
    from liquid2 import MetaNode
    from liquid2 import RenderContext
    from liquid2 import TokenStream
    from liquid2 import TokenT


class CommentNode(Node):
    """The built in, standard implementation of the comment node."""

    __slots__ = ("text",)

    def __init__(self, token: TokenT, text: str) -> None:
        super().__init__(token)
        self.text = text

    def __str__(self) -> str:
        return self.text

    def render_to_output(self, _context: RenderContext, _buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        return 0

    def children(self) -> list[MetaNode]:
        """Return a list of child nodes and/or expressions associated with this node."""
        return []


class Comment(Tag):
    """The built in pseudo tag representing template comments."""

    block = False
    node_class = CommentNode

    def parse(self, stream: TokenStream) -> Node:
        """Parse tokens from _stream_ into an AST node."""
        token = stream.current()
        assert isinstance(token, CommentToken)
        return self.node_class(token, token.text)
