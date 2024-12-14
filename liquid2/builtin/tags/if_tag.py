"""The standard _if_ tag."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Iterable
from typing import TextIO

from liquid2 import BlockNode
from liquid2 import ConditionalBlockNode
from liquid2 import Expression
from liquid2 import Node
from liquid2 import Tag
from liquid2 import TagToken
from liquid2 import TokenStream
from liquid2.builtin import BooleanExpression

if TYPE_CHECKING:
    from liquid2 import RenderContext
    from liquid2 import TokenT


class IfNode(Node):
    """The standard _if_ tag."""

    __slots__ = ("condition", "consequence", "alternatives", "default")

    def __init__(
        self,
        token: TokenT,
        condition: BooleanExpression,
        consequence: BlockNode,
        alternatives: list[ConditionalBlockNode],
        default: BlockNode | None,
    ) -> None:
        super().__init__(token)
        self.condition = condition
        self.consequence = consequence
        self.alternatives = alternatives
        self.default = default

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        if self.condition.evaluate(context):
            return self.consequence.render(context, buffer)

        for alternative in self.alternatives:
            if alternative.expression.evaluate(context):
                return alternative.block.render(context, buffer)

        if self.default:
            return self.default.render(context, buffer)

        return 0

    async def render_to_output_async(
        self, context: RenderContext, buffer: TextIO
    ) -> int:
        """Render the node to the output buffer."""
        if await self.condition.evaluate_async(context):
            return await self.consequence.render_async(context, buffer)

        for alternative in self.alternatives:
            if await alternative.expression.evaluate_async(context):
                return await alternative.render_async(context, buffer)

        if self.default:
            return await self.default.render_async(context, buffer)

        return 0

    def children(
        self, _static_context: RenderContext, *, _include_partials: bool = True
    ) -> Iterable[Node]:
        """Return this node's children."""
        yield self.consequence
        yield from self.alternatives
        if self.default:
            yield self.default

    def expressions(self) -> Iterable[Expression]:
        """Return this node's expressions."""
        yield self.condition


class IfTag(Tag):
    """The standard _if_ tag."""

    block = True
    node_class = IfNode
    end_block = frozenset(["endif", "elsif", "else"])

    def parse(self, stream: TokenStream) -> Node:
        """Parse tokens from _stream_ into an AST node."""
        token = stream.next()
        assert isinstance(token, TagToken)

        parse_block = self.env.parser.parse_block
        parse_expression = BooleanExpression.parse

        condition = parse_expression(TokenStream(token.expression))

        block_token = stream.current()
        assert block_token is not None
        consequence = BlockNode(block_token, parse_block(stream, end=self.end_block))

        alternatives: list[ConditionalBlockNode] = []
        alternative: BlockNode | None = None

        while stream.is_tag("elsif"):
            alternative_token = stream.next()
            assert isinstance(alternative_token, TagToken)

            alternative_expression = parse_expression(
                TokenStream(alternative_token.expression)
            )

            alternative_block = BlockNode(
                token=alternative_token, nodes=parse_block(stream, self.end_block)
            )
            alternatives.append(
                ConditionalBlockNode(
                    alternative_token,
                    alternative_block,
                    alternative_expression,
                )
            )

        if stream.is_tag("else"):
            stream.next()
            alternative_token = stream.current()
            assert alternative_token is not None
            alternative = BlockNode(
                alternative_token, parse_block(stream, self.end_block)
            )

        return self.node_class(
            token,
            condition,
            consequence,
            alternatives,
            alternative,
        )
