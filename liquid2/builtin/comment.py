"""The built in, standard implementation of the comment node."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from typing import TextIO

from liquid2 import CommentToken
from liquid2 import InlineCommentToken
from liquid2 import Node
from liquid2 import Tag
from liquid2.exceptions import LiquidSyntaxError

if TYPE_CHECKING:
    from liquid2 import RenderContext
    from liquid2 import TokenStream
    from liquid2 import TokenT

# Enforce Shopify-style inline comment tag rules.
RE_INVALID_INLINE_COMMENT = re.compile(r"\n\s*[^#\s]")


class CommentNode(Node):
    """The built in, standard implementation of the comment node."""

    __slots__ = ("text",)

    def __init__(self, token: TokenT, text: str) -> None:
        super().__init__(token)
        self.text = text

    def __str__(self) -> str:
        assert isinstance(self.token, CommentToken)
        return str(self.token)

    def render_to_output(self, _context: RenderContext, _buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        return 0


class Comment(Tag):
    """The built in pseudo tag representing template comments."""

    block = False
    node_class = CommentNode

    def parse(self, stream: TokenStream) -> Node:
        """Parse tokens from _stream_ into an AST node."""
        token = stream.current()
        assert isinstance(token, CommentToken)

        if isinstance(token, InlineCommentToken) and RE_INVALID_INLINE_COMMENT.search(
            token.text
        ):
            raise LiquidSyntaxError(
                "line in inline comment tags must start with a '#'",
                token=token,
            )

        return self.node_class(token, token.text)
