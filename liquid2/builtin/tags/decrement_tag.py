"""The standard _decrement_ tag."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Iterable
from typing import TextIO

from liquid2 import Node
from liquid2 import Tag
from liquid2 import TagToken
from liquid2 import TokenStream
from liquid2.builtin import parse_string_or_identifier
from liquid2.exceptions import LiquidSyntaxError

if TYPE_CHECKING:
    from liquid2 import RenderContext
    from liquid2 import TokenT
    from liquid2.builtin import Identifier


class DecrementNode(Node):
    """The standard _decrement_ tag."""

    __slots__ = ("name", "name")

    def __init__(self, token: TokenT, name: Identifier) -> None:
        super().__init__(token)
        self.name = name
        self.blank = False

    def __str__(self) -> str:
        assert isinstance(self.token, TagToken)
        return f"{{%{self.token.wc[0]} decrement {self.name} {self.token.wc[1]}%}}"

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        return buffer.write(str(context.decrement(self.name)))

    def template_scope(self) -> Iterable[Identifier]:
        """Return variables this node adds to the template local scope."""
        yield self.name


class DecrementTag(Tag):
    """The standard _decrement_ tag."""

    block = False
    node_class = DecrementNode

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
