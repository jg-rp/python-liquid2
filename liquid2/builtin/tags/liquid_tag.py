"""The standard _liquid_ tag."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Iterable
from typing import TextIO

from liquid2 import BlockNode
from liquid2 import LinesToken
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
        self.blank = block.blank

    def __str__(self) -> str:
        assert isinstance(self.token, LinesToken)
        # NOTE: We're using a string representation of the token, not the node.
        # Which might cause issues later.
        return str(self.token)

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        return self.block.render(context, buffer)

    async def render_to_output_async(
        self, context: RenderContext, buffer: TextIO
    ) -> int:
        """Render the node to the output buffer."""
        return await self.block.render_async(context, buffer)

    def children(
        self,
        static_context: RenderContext,  # noqa: ARG002
        *,
        include_partials: bool = True,  # noqa: ARG002
    ) -> Iterable[Node]:
        """Return this node's children."""
        yield self.block


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
