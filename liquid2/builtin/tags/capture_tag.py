"""The standard  _capture_ tag."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Iterable
from typing import TextIO

from liquid2 import BlockNode
from liquid2 import Node
from liquid2 import RenderContext
from liquid2 import Tag
from liquid2 import TagToken
from liquid2 import TokenStream
from liquid2.builtin import parse_identifier
from liquid2.exceptions import LiquidSyntaxError

if TYPE_CHECKING:
    from liquid2 import RenderContext
    from liquid2 import TokenT
    from liquid2.builtin import Identifier


class CaptureNode(Node):
    """The standard  _capture_ tag."""

    __slots__ = ("name", "block", "end_tag_token")

    def __init__(
        self,
        token: TokenT,
        *,
        name: Identifier,
        block: BlockNode,
        end_tag_token: TagToken,
    ) -> None:
        super().__init__(token)
        self.name = name
        self.block = block
        self.end_tag_token = end_tag_token

    def __str__(self) -> str:
        assert isinstance(self.token, TagToken)
        return (
            f"{{%{self.token.wc[0]} capture {self.name} {self.token.wc[1]}%}}"
            f"{self.block}"
            f"{{%{self.end_tag_token.wc[0]} endcapture {self.end_tag_token.wc[1]}%}}"
        )

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

    def children(
        self,
        static_context: RenderContext,  # noqa: ARG002
        *,
        include_partials: bool = True,  # noqa: ARG002
    ) -> Iterable[Node]:
        """Return this node's children."""
        yield self.block

    def template_scope(self) -> Iterable[Identifier]:
        """Return variables this node adds to the template local scope."""
        yield self.name


class CaptureTag(Tag):
    """The standard _capture_ tag."""

    block = True
    node_class = CaptureNode
    end_block = frozenset(["endcapture"])

    def parse(self, stream: TokenStream) -> Node:
        """Parse tokens from _stream_ into an AST node."""
        token = stream.next()
        assert isinstance(token, TagToken)

        if not token.expression:
            raise LiquidSyntaxError("missing identifier", token=token)

        expr_stream = TokenStream(token.expression)
        name = parse_identifier(expr_stream.next())
        expr_stream.expect_eos()

        block_token = stream.current()
        nodes = self.env.parser.parse_block(stream, self.end_block)
        stream.expect_tag("endcapture")
        end_tag_token = stream.current()
        assert isinstance(end_tag_token, TagToken)

        return self.node_class(
            token,
            name=name,
            block=BlockNode(token=block_token, nodes=nodes),
            end_tag_token=end_tag_token,
        )
