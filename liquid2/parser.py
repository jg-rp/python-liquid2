"""Liquid token parser."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Container
from typing import cast

from liquid2 import TokenStream

from .builtin import Content
from .exceptions import LiquidSyntaxError
from .token import TokenType
from .token import is_comment_token
from .token import is_content_token
from .token import is_lines_token
from .token import is_output_token
from .token import is_raw_token
from .token import is_tag_token

if TYPE_CHECKING:
    from .ast import Node
    from .environment import Environment
    from .token import TokenT


class Parser:
    """Liquid token parser."""

    def __init__(self, env: Environment) -> None:
        self.env = env
        self.tags = env.tags

    def parse(self, tokens: list[TokenT]) -> list[Node]:
        """Parse _tokens_ into an abstract syntax tree."""
        tags = self.tags
        comment = tags["__COMMENT"]
        content = cast(Content, tags["__CONTENT"])
        output = tags["__OUTPUT"]
        raw = tags["__RAW"]
        lines = tags["__LINES"]

        nodes: list[Node] = []
        stream = TokenStream(tokens)

        default_trim = self.env.default_trim
        left_trim = default_trim

        while True:
            token = stream.current()
            if is_content_token(token):
                nodes.append(content.parse(stream, left_trim=left_trim))
                left_trim = default_trim
            elif is_comment_token(token):
                left_trim = token.wc[-1]
                nodes.append(comment.parse(stream))
            elif is_raw_token(token):
                left_trim = token.wc[-1]
                nodes.append(raw.parse(stream))
            elif is_output_token(token):
                left_trim = token.wc[-1]
                nodes.append(output.parse(stream))
            elif is_tag_token(token):
                stream.trim_carry = token.wc[-1]
                try:
                    nodes.append(tags[token.name].parse(stream))
                except KeyError as err:
                    raise LiquidSyntaxError(
                        f"unexpected tag '{token.name}'", token=stream.current()
                    ) from err

                left_trim = stream.trim_carry
            elif is_lines_token(token):
                left_trim = token.wc[-1]
                nodes.append(lines.parse(stream))
            elif token.type_ == TokenType.EOI:
                break
            else:
                raise LiquidSyntaxError(
                    f"unexpected token {token.type_.name}",
                    token=token,
                )

            stream.next()

        return nodes

    def parse_block(self, stream: TokenStream, end: Container[str]) -> list[Node]:
        """Parse markup tokens from _stream_ until wee find a tag in _end_."""
        tags = self.tags
        comment = tags["__COMMENT"]
        content = cast(Content, tags["__CONTENT"])
        output = tags["__OUTPUT"]
        raw = tags["__RAW"]
        lines = tags["__LINES"]

        default_trim = self.env.default_trim
        left_trim = stream.trim_carry

        nodes: list[Node] = []

        while True:
            token = stream.current()
            if is_content_token(token):
                nodes.append(content.parse(stream, left_trim=left_trim))
                left_trim = default_trim
            elif is_comment_token(token):
                left_trim = token.wc[-1]
                nodes.append(comment.parse(stream))
            elif is_raw_token(token):
                left_trim = token.wc[-1]
                nodes.append(raw.parse(stream))
            elif is_output_token(token):
                left_trim = token.wc[-1]
                nodes.append(output.parse(stream))
            elif is_tag_token(token):
                stream.trim_carry = token.wc[-1]

                if token.name in end:
                    break

                try:
                    nodes.append(tags[token.name].parse(stream))
                except KeyError as err:
                    raise LiquidSyntaxError(
                        f"unexpected tag '{token.name}'", token=stream.current()
                    ) from err

                left_trim = stream.trim_carry
            elif is_lines_token(token):
                left_trim = token.wc[-1]
                nodes.append(lines.parse(stream))
            elif token.type_ == TokenType.EOI:
                break
            else:
                raise LiquidSyntaxError(
                    f"unexpected token {token.type_.name}",
                    token=token,
                )

            stream.next()

        return nodes
