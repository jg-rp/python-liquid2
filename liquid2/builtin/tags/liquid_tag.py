"""The standard _liquid_ tag."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import TextIO

from liquid2 import BlockNode
from liquid2 import LinesToken
from liquid2 import MetaNode
from liquid2 import Node
from liquid2 import Tag
from liquid2 import TokenStream

if TYPE_CHECKING:
    from liquid2 import RenderContext
    from liquid2 import TokenT


class LiquidNode(Node):
    """The standard _liquid_ tag."""

    __slots__ = ("block",)

    def __init__(
        self,
        token: TokenT,
        block: BlockNode,
    ) -> None:
        super().__init__(token)
        self.block = block

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        return self.block.render(context, buffer)

    async def render_to_output_async(
        self, context: RenderContext, buffer: TextIO
    ) -> int:
        """Render the node to the output buffer."""
        return await self.block.render_async(context, buffer)

    def children(self) -> list[MetaNode]:
        """Return a list of child nodes and/or expressions associated with this node."""
        return self.block.children()


class LiquidTag(Tag):
    """The standard _liquid_ tag."""

    block = False
    node_class = LiquidNode

    def parse(self, stream: TokenStream) -> Node:
        """Parse tokens from _stream_ into an AST node."""
        token = stream.current()
        assert isinstance(token, LinesToken)
        block = self.env.parser.parse_block(TokenStream(token.statements), end=())
        return self.node_class(token, BlockNode(token, block))
