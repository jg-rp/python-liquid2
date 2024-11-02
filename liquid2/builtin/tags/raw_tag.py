"""The standard _raw_ tag."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import TextIO

from liquid2 import Node
from liquid2 import RawToken
from liquid2 import Tag

if TYPE_CHECKING:
    from liquid2 import MetaNode
    from liquid2 import RenderContext
    from liquid2 import TokenStream
    from liquid2 import TokenT


class RawNode(Node):
    """The standard _raw_ tag."""

    __slots__ = ("text",)

    def __init__(self, token: TokenT, text: str) -> None:
        super().__init__(token)
        self.text = text

    def render_to_output(self, _context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        return buffer.write(self.text)

    def children(self) -> list[MetaNode]:
        """Return a list of child nodes and/or expressions associated with this node."""
        return []


class RawTag(Tag):
    """The standard _raw_ tag."""

    block = False
    node_class = RawNode

    def parse(self, stream: TokenStream) -> Node:
        """Parse tokens from _stream_ into an AST node."""
        token = stream.current()
        assert isinstance(token, RawToken)
        return self.node_class(token, token.text)
