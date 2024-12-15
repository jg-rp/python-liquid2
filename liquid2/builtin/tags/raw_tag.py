"""The standard _raw_ tag."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import TextIO

from liquid2 import Node
from liquid2 import RawToken
from liquid2 import Tag

if TYPE_CHECKING:
    from liquid2 import RenderContext
    from liquid2 import TokenStream
    from liquid2 import TokenT


class RawNode(Node):
    """The standard _raw_ tag."""

    __slots__ = ("text",)

    def __init__(self, token: TokenT, text: str) -> None:
        super().__init__(token)
        self.text = text

    def __str__(self) -> str:
        assert isinstance(self.token, RawToken)
        return (
            f"{{%{self.token.wc[0]} raw {self.token.wc[1]}%}}"
            f"{self.text}"
            f"{{%{self.token.wc[2]} endraw {self.token.wc[3]}%}}"
        )

    def render_to_output(self, _context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        return buffer.write(self.text)


class RawTag(Tag):
    """The standard _raw_ tag."""

    block = False
    node_class = RawNode
    inner_whitespace_control: bool = True

    def parse(self, stream: TokenStream) -> Node:
        """Parse tokens from _stream_ into an AST node."""
        token = stream.current()
        assert isinstance(token, RawToken)
        return self.node_class(
            token,
            self.env.trim(
                token.text,
                token.wc[1],
                token.wc[2],
            )
            if self.inner_whitespace_control
            else token.text,
        )
