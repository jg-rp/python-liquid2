"""The standard  _capture_ tag."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import TextIO

from liquid2 import BlockNode
from liquid2 import MetaNode
from liquid2 import Node
from liquid2 import RenderContext
from liquid2 import Tag
from liquid2 import TagToken
from liquid2 import TokenStream
from liquid2.builtin import parse_identifier

if TYPE_CHECKING:
    from liquid2 import RenderContext
    from liquid2 import TokenT
    from liquid2.builtin import Identifier


class CaptureNode(Node):
    """The standard  _capture_ tag."""

    __slots__ = ("name", "block")

    def __init__(self, token: TokenT, *, name: Identifier, block: BlockNode) -> None:
        super().__init__(token)
        self.name = name
        self.block = block

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        buf = context.get_output_buffer(buffer)
        self.block.render(context, buf)
        context.assign(self.name, context.markup(buf.getvalue()))
        return 0

    async def render_to_output_async(
        self, context: RenderContext, buffer: TextIO
    ) -> int:
        """Render the node to the output buffer."""
        buf = context.get_output_buffer(buffer)
        await self.block.render_async(context, buf)
        context.assign(self.name, context.markup(buf.getvalue()))
        return 0

    def children(self) -> list[MetaNode]:
        """Return a list of child nodes and/or expressions associated with this node."""
        return [
            MetaNode(
                token=self.token,
                node=self.block,
                template_scope=[self.name],
            )
        ]


class CaptureTag(Tag):
    """The standard _capture_ tag."""

    block = True
    node_class = CaptureNode
    end_block = frozenset(["endcapture"])

    def parse(self, stream: TokenStream) -> Node:
        """Parse tokens from _stream_ into an AST node."""
        token = next(stream)
        assert isinstance(token, TagToken)

        expr_stream = TokenStream(token.expression)
        name = parse_identifier(expr_stream.next())
        expr_stream.expect_eos()

        block_token = stream.current()
        assert block_token is not None  # XXX: empty block or end of file
        nodes = self.env.parser.parse_block(stream, self.end_block)
        stream.expect_tag("endcapture")

        return self.node_class(
            token,
            name=name,
            block=BlockNode(token=block_token, nodes=nodes),
        )
