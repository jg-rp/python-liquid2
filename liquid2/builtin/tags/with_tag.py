"""The built-in `with` tag."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Iterable
from typing import TextIO

from liquid2 import BlockNode
from liquid2 import Node
from liquid2 import Tag
from liquid2 import TagToken
from liquid2 import TokenStream
from liquid2.builtin import Identifier
from liquid2.builtin import parse_keyword_arguments

if TYPE_CHECKING:
    from liquid2 import Expression
    from liquid2 import RenderContext
    from liquid2 import TokenT
    from liquid2.builtin import KeywordArgument


class WithNode(Node):
    """The built-in `with` tag."""

    __slots__ = ("args", "block", "end_tag_token")

    def __init__(
        self,
        token: TokenT,
        args: list[KeywordArgument],
        block: BlockNode,
        end_tag_token: TagToken,
    ):
        super().__init__(token)
        self.args = args
        self.block = block
        self.end_tag_token = end_tag_token
        self.blank = self.block.blank

    def __str__(self) -> str:
        assert isinstance(self.token, TagToken)
        args = " " + ", ".join(str(p) for p in self.args) if self.args else ""
        return (
            f"{{%{self.token.wc[0]} with{args} {self.token.wc[1]}%}}"
            f"{self.block}"
            f"{{%{self.end_tag_token.wc[0]} endwith {self.end_tag_token.wc[1]}%}}"
        )

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        namespace = dict(arg.evaluate(context) for arg in self.args)
        with context.extend(namespace):
            return self.block.render(context, buffer)

    async def render_to_output_async(
        self, context: RenderContext, buffer: TextIO
    ) -> int:
        """Render the node to the output buffer."""
        namespace = dict([await arg.evaluate_async(context) for arg in self.args])
        with context.extend(namespace):
            return await self.block.render_async(context, buffer)

    def expressions(self) -> Iterable[Expression]:
        """Return this node's expressions."""
        yield from (arg.value for arg in self.args)

    def children(
        self,
        static_context: RenderContext,  # noqa: ARG002
        *,
        include_partials: bool = True,  # noqa: ARG002
    ) -> Iterable[Node]:
        """Return this node's children."""
        yield self.block

    def block_scope(self) -> Iterable[Identifier]:
        """Return variables this node adds to the node's block scope."""
        yield from (Identifier(p.name, token=p.token) for p in self.args)


class WithTag(Tag):
    """The built-in `with` tag."""

    node_class = WithNode

    def parse(self, stream: TokenStream) -> Node:
        """Parse tokens from _stream_ into a node for the abstract syntax tree.."""
        token = stream.next()
        assert isinstance(token, TagToken)

        tokens = TokenStream(token.expression)
        args = parse_keyword_arguments(tokens)
        block = BlockNode(
            stream.current(), self.env.parser.parse_block(stream, ("endwith",))
        )

        stream.expect_tag("endwith")
        end_tag_token = stream.current()
        assert isinstance(end_tag_token, TagToken)

        return self.node_class(token, args, block, end_tag_token)
