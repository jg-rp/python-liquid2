"""The standard _case_ tag."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Iterable
from typing import TextIO

from liquid2 import BlockNode
from liquid2 import ContentToken
from liquid2 import Node
from liquid2 import Tag
from liquid2 import TagToken
from liquid2 import TokenType
from liquid2.builtin import parse_primitive
from liquid2.builtin.expressions import _eq
from liquid2.exceptions import LiquidSyntaxError
from liquid2.expression import Expression

if TYPE_CHECKING:
    from liquid2 import RenderContext
    from liquid2 import TokenStream
    from liquid2 import TokenT


class CaseNode(Node):
    """The standard _case_ tag."""

    __slots__ = (
        "expression",
        "whens",
        "default",
        "leading_whitespace",
        "end_tag_token",
    )

    def __init__(
        self,
        token: TokenT,
        expression: Expression,
        whens: list[MultiExpressionBlockNode],
        default: BlockNode | None,
        leading_whitespace: str,
        end_tag_token: TagToken,
    ) -> None:
        super().__init__(token)
        self.expression = expression
        self.whens = whens
        self.default = default
        self.leading_whitespace = leading_whitespace
        self.end_tag_token = end_tag_token

        self.blank = all(node.blank for node in self.whens) and (
            not self.default or self.default.blank
        )

    def __str__(self) -> str:
        assert isinstance(self.token, TagToken)
        default = ""

        if self.default:
            assert isinstance(self.default.token, TagToken)
            default = (
                f"{{%{self.default.token.wc[0]} else {self.default.token.wc[1]}%}}"
                f"{self.default}"
            )

        return (
            f"{{%{self.token.wc[0]} case {self.expression} {self.token.wc[1]}%}}"
            f"{self.leading_whitespace}"
            f"{''.join(str(w) for w in self.whens)}"
            f"{default}"
            f"{{%{self.end_tag_token.wc[0]} endcase {self.end_tag_token.wc[1]}%}}"
        )

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        count = 0
        for when in self.whens:
            count += when.render(context, buffer)

        if not count and self.default is not None:
            count += self.default.render(context, buffer)

        return count

    async def render_to_output_async(
        self, context: RenderContext, buffer: TextIO
    ) -> int:
        """Render the node to the output buffer."""
        count = 0
        for when in self.whens:
            count += await when.render_async(context, buffer)

        if not count and self.default is not None:
            count += await self.default.render_async(context, buffer)

        return count

    def children(
        self,
        static_context: RenderContext,  # noqa: ARG002
        *,
        include_partials: bool = True,  # noqa: ARG002
    ) -> Iterable[Node]:
        """Return this node's children."""
        yield from self.whens

        if self.default:
            yield self.default

    def expressions(self) -> Iterable[Expression]:
        """Return this node's expressions."""
        yield self.expression


class CaseTag(Tag):
    """The standard _case_ tag."""

    block = True
    node_class = CaseNode
    end_block = frozenset(["endcase", "when", "else"])

    def parse(self, stream: TokenStream) -> Node:
        """Parse tokens from _stream_ into an AST node."""
        token = stream.current()
        assert isinstance(token, TagToken)
        expr_stream = stream.into_inner()
        left = parse_primitive(expr_stream.next())
        expr_stream.expect_eos()

        # Check for content or markup between the _case_ tag and the first _when_ or
        # _else_ tag. It is not allowed.
        block_token = stream.current()
        leading_whitespace = ""
        match block_token:
            case TagToken(name=name):
                if name not in self.end_block:
                    raise LiquidSyntaxError(
                        f"expected a 'when' tag, found '{name}'",
                        token=block_token,
                    )
            case ContentToken(text=text):
                if not text.isspace():
                    raise LiquidSyntaxError(
                        "unexpected text after 'case' tag",
                        token=block_token,
                    )
                leading_whitespace = text
                stream.next()
            case _:
                raise LiquidSyntaxError(
                    "unexpected markup after 'case' tag",
                    token=block_token,
                )

        whens: list[MultiExpressionBlockNode] = []
        default: BlockNode | None = None

        parse_block = self.env.parser.parse_block

        while stream.is_tag("when"):
            alternative_token = stream.current()
            assert isinstance(alternative_token, TagToken)

            expressions = self._parse_when_expression(stream.into_inner())
            alternative_block_token = stream.current()
            alternative_block = parse_block(stream, self.end_block)

            whens.append(
                MultiExpressionBlockNode(
                    alternative_token,
                    BlockNode(token=alternative_block_token, nodes=alternative_block),
                    _AnyExpression(alternative_token, left, expressions),
                )
            )

        if stream.is_tag("else"):
            alternative_token = stream.next()
            alternative_block = parse_block(stream, self.end_block)
            default = BlockNode(alternative_token, alternative_block)

        stream.expect_tag("endcase")
        end_block_tag = stream.current()
        assert isinstance(end_block_tag, TagToken)

        return self.node_class(
            token,
            left,
            whens,
            default,
            leading_whitespace,
            end_block_tag,
        )

    def _parse_when_expression(self, stream: TokenStream) -> list[Expression]:
        expressions: list[Expression] = [parse_primitive(stream.next())]
        while stream.current().type_ in (TokenType.COMMA, TokenType.OR_WORD):
            stream.next()
            expressions.append(parse_primitive(stream.next()))
        stream.expect_eos()
        return expressions


class _AnyExpression(Expression):
    __slots__ = (
        "left",
        "expressions",
    )

    def __init__(
        self, token: TokenT, left: Expression, expressions: list[Expression]
    ) -> None:
        super().__init__(token)
        self.left = left
        self.expressions = expressions

    def __str__(self) -> str:
        return ", ".join(str(expr) for expr in self.expressions)

    def evaluate(self, context: RenderContext) -> object:
        left = self.left.evaluate(context)
        return any((_eq(left, right.evaluate(context)) for right in self.expressions))

    async def evaluate_async(self, context: RenderContext) -> object:
        left = await self.left.evaluate_async(context)
        for expr in self.expressions:
            right = await expr.evaluate_async(context)
            if _eq(left, right):
                return True
        return False

    def children(self) -> list[Expression]:
        return self.expressions


class MultiExpressionBlockNode(Node):
    """A node containing a sequence of nodes guarded by a choice of expressions."""

    __slots__ = ("block", "expression")

    def __init__(
        self,
        token: TokenT,
        block: BlockNode,
        expression: _AnyExpression,
    ) -> None:
        super().__init__(token)
        self.block = block
        self.expression = expression
        self.blank = self.block.blank

    def __str__(self) -> str:
        assert isinstance(self.token, TagToken)
        return (
            f"{{%{self.token.wc[0]} when {self.expression} {self.token.wc[1]}%}}"
            f"{self.block}"
        )

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        if self.expression.evaluate(context):
            return self.block.render(context, buffer)
        return 0

    async def render_to_output_async(
        self, context: RenderContext, buffer: TextIO
    ) -> int:
        """Render the node to the output buffer."""
        if await self.expression.evaluate_async(context):
            return await self.block.render_async(context, buffer)
        return 0

    def children(
        self,
        static_context: RenderContext,  # noqa: ARG002
        *,
        include_partials: bool = True,  # noqa: ARG002
    ) -> Iterable[Node]:
        """Return this node's children."""
        yield self.block

    def expressions(self) -> Iterable[Expression]:
        """Return this node's expressions."""
        yield self.expression
