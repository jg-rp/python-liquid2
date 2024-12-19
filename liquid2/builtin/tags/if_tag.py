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
from liquid2.exceptions import LiquidSyntaxError

if TYPE_CHECKING:
    from liquid2 import RenderContext
    from liquid2 import TokenT


class IfNode(Node):
    """The standard _if_ tag."""

    __slots__ = ("condition", "consequence", "alternatives", "default", "end_tag_token")

    def __init__(
        self,
        token: TokenT,
        condition: BooleanExpression,
        consequence: BlockNode,
        alternatives: list[ConditionalBlockNode],
        default: BlockNode | None,
        end_tag_token: TagToken,
    ) -> None:
        super().__init__(token)
        self.condition = condition
        self.consequence = consequence
        self.alternatives = alternatives
        self.default = default
        self.end_tag_token = end_tag_token

        self.blank = (
            consequence.blank
            and all(node.blank for node in alternatives)
            and (not default or default.blank)
        )

    def __str__(self) -> str:
        assert isinstance(self.token, TagToken)
        alts = "".join(str(alt) for alt in self.alternatives)
        default = ""

        if self.default:
            assert isinstance(self.default.token, TagToken)
            default = (
                f"{{%{self.default.token.wc[0]} else {self.default.token.wc[1]}%}}"
                f"{self.default}"
            )

        return (
            f"{{%{self.token.wc[0]} if {self.condition} {self.token.wc[1]}%}}"
            f"{self.consequence}"
            f"{alts}"
            f"{default}"
            f"{{%{self.end_tag_token.wc[0]} endif {self.end_tag_token.wc[1]}%}}"
        )

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
        self,
        static_context: RenderContext,  # noqa: ARG002
        *,
        include_partials: bool = True,  # noqa: ARG002
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

        if not token.expression:
            raise LiquidSyntaxError("missing expression", token=token)

        condition = parse_expression(TokenStream(token.expression))

        block_token = stream.current()
        assert block_token is not None
        consequence = BlockNode(block_token, parse_block(stream, end=self.end_block))

        alternatives: list[ConditionalBlockNode] = []
        alternative: BlockNode | None = None

        while stream.is_tag("elsif"):
            alternative_token = stream.next()
            assert isinstance(alternative_token, TagToken)

            if not alternative_token.expression:
                raise LiquidSyntaxError("missing expression", token=alternative_token)

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
            alternative_token = stream.next()
            alternative = BlockNode(
                alternative_token, parse_block(stream, self.end_block)
            )

        stream.expect_tag("endif")
        end_tag_token = stream.current()
        assert isinstance(end_tag_token, TagToken)

        return self.node_class(
            token,
            condition,
            consequence,
            alternatives,
            alternative,
            end_tag_token,
        )
