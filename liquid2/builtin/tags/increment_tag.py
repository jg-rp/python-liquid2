"""The standard _increment_ tag."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import TextIO

from liquid2 import MetaNode
from liquid2 import Node
from liquid2 import Tag
from liquid2 import TagToken
from liquid2 import TokenStream
from liquid2.builtin import parse_string_or_identifier
from liquid2.exceptions import LiquidSyntaxError

if TYPE_CHECKING:
    from liquid2 import TokenT
    from liquid2.builtin import Identifier
    from liquid2.context import RenderContext


class IncrementNode(Node):
    """The standard _increment_ tag."""

    __slots__ = ("name", "name")

    def __init__(self, token: TokenT, name: Identifier) -> None:
        super().__init__(token)
        self.name = name

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        return buffer.write(str(context.increment(self.name)))

    def children(self) -> list[MetaNode]:
        """Return a list of child nodes and/or expressions associated with this node."""
        return [MetaNode(token=self.token, template_scope=[self.name])]


class IncrementTag(Tag):
    """The standard _increment_ tag."""

    block = False
    node_class = IncrementNode

    def parse(self, stream: TokenStream) -> Node:
        """Parse tokens from _stream_ into an AST node."""
        token = stream.current()
        assert isinstance(token, TagToken)

        if not token.expression:
            raise LiquidSyntaxError("expected an identifier", token=token)

        expr_stream = TokenStream(token.expression)
        name = parse_string_or_identifier(expr_stream.next())
        expr_stream.expect_eos()
        return self.node_class(token, name)
