"""The standard _assign_ tag."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Iterable
from typing import TextIO

from liquid2 import Node
from liquid2 import RenderContext
from liquid2 import Tag
from liquid2 import TagToken
from liquid2 import TokenStream
from liquid2 import TokenType
from liquid2.builtin import FilteredExpression
from liquid2.builtin import Identifier
from liquid2.builtin import parse_identifier
from liquid2.exceptions import LiquidSyntaxError

if TYPE_CHECKING:
    from liquid2 import RenderContext
    from liquid2 import TokenT
    from liquid2.expression import Expression


class AssignNode(Node):
    """The standard _assign_ tag."""

    __slots__ = ("name", "expression")

    def __init__(
        self, token: TokenT, *, name: Identifier, expression: Expression
    ) -> None:
        super().__init__(token)
        self.name = name
        self.expression = expression

    def __str__(self) -> str:
        assert isinstance(self.token, TagToken)
        return (
            f"{{%{self.token.wc[0]} "
            f"assign {self.name} = {self.expression}"
            f" {self.token.wc[1]}%}}"
        )

    def render_to_output(self, context: RenderContext, _buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        context.assign(self.name, self.expression.evaluate(context))
        return 0

    async def render_to_output_async(
        self, context: RenderContext, _buffer: TextIO
    ) -> int:
        """Render the node to the output buffer."""
        context.assign(self.name, await self.expression.evaluate_async(context))
        return 0

    def expressions(self) -> Iterable[Expression]:
        """Return this node's expressions."""
        yield self.expression

    def template_scope(self) -> Iterable[Identifier]:
        """Return variables this node adds to the template local scope."""
        yield self.name


class AssignTag(Tag):
    """The standard _assign_ tag."""

    block = False
    node_class = AssignNode

    def parse(self, stream: TokenStream) -> Node:
        """Parse tokens from _stream_ into an AST node."""
        token = stream.current()
        assert isinstance(token, TagToken)

        if not token.expression:
            raise LiquidSyntaxError("missing expression", token=token)

        expr_stream = TokenStream(token.expression)
        name = parse_identifier(expr_stream.next())
        expr_stream.expect(TokenType.ASSIGN)
        expr_stream.next()

        return self.node_class(
            token,
            name=name,
            expression=FilteredExpression.parse(expr_stream),
        )
