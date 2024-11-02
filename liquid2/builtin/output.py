"""The standard output statement."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import TextIO

from liquid2 import MetaNode
from liquid2 import Node
from liquid2 import OutputToken
from liquid2 import Tag
from liquid2 import TokenStream
from liquid2.builtin import FilteredExpression
from liquid2.stringify import to_liquid_string

if TYPE_CHECKING:
    from liquid2 import RenderContext
    from liquid2 import TokenT
    from liquid2.expression import Expression


class OutputNode(Node):
    """The standard output statement."""

    __slots__ = ("expression",)

    def __init__(self, token: TokenT, expression: Expression) -> None:
        super().__init__(token)
        self.expression = expression

    def __str__(self) -> str:
        return f"`{self.expression}`"

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        return buffer.write(
            to_liquid_string(
                self.expression.evaluate(context),
                auto_escape=context.auto_escape,
            )
        )

    async def render_to_output_async(
        self, context: RenderContext, buffer: TextIO
    ) -> int:
        """Render the node to the output buffer."""
        return buffer.write(
            to_liquid_string(
                await self.expression.evaluate_async(context),
                auto_escape=context.auto_escape,
            )
        )

    def children(self) -> list[MetaNode]:
        """Return a list of child nodes and/or expressions associated with this node."""
        return [MetaNode(token=self.token, expression=self.expression)]


class Output(Tag):
    """The built in pseudo tag for output statements."""

    block = False
    node_class = OutputNode

    def parse(self, stream: TokenStream) -> Node:
        """Parse tokens from _stream_ into an AST node."""
        token = stream.current()
        assert isinstance(token, OutputToken)
        return self.node_class(
            token, FilteredExpression.parse(TokenStream(token.expression))
        )
