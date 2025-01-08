"""The built-in implementation of the text content node."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import TextIO

from liquid2 import CommentToken
from liquid2 import ContentToken
from liquid2 import LinesToken
from liquid2 import Node
from liquid2 import OutputToken
from liquid2 import RawToken
from liquid2 import Tag
from liquid2 import TagToken
from liquid2 import WhitespaceControl

if TYPE_CHECKING:
    from liquid2 import RenderContext
    from liquid2 import TokenStream
    from liquid2 import TokenT


class ContentNode(Node):
    """The built-in implementation of the text content node."""

    __slots__ = ("text", "left_trim", "right_trim")

    def __init__(
        self,
        token: TokenT,
        text: str,
        *,
        left_trim: WhitespaceControl,
        right_trim: WhitespaceControl,
    ) -> None:
        super().__init__(token)
        self.text = text
        self.left_trim = left_trim
        self.right_trim = right_trim
        self.blank = not text or text.isspace()

    def __str__(self) -> str:
        return self.text

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        # NOTE: Trimming at render time for the benefit of template serialization.
        return buffer.write(
            context.env.trim(self.text, self.left_trim, self.right_trim)
        )


class Content(Tag):
    """The template text content pseudo tag."""

    block = False
    node_class = ContentNode

    def parse(
        self,
        stream: TokenStream,
        *,
        left_trim: WhitespaceControl = WhitespaceControl.DEFAULT,
    ) -> Node:
        """Parse tokens from _stream_ into an AST node."""
        token = stream.current()
        assert isinstance(token, ContentToken)

        right_trim = WhitespaceControl.DEFAULT

        peeked = stream.peek()
        if isinstance(
            peeked, (TagToken, OutputToken, CommentToken, RawToken, LinesToken)
        ):
            right_trim = peeked.wc[0]

        return self.node_class(
            token,
            token.text,
            left_trim=left_trim,
            right_trim=right_trim,
        )
