"""Liquid token parser."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Container
from typing import cast

from liquid2 import TokenStream

from .builtin import Content
from .exceptions import LiquidSyntaxError
from .token import CommentToken
from .token import ContentToken
from .token import LinesToken
from .token import OutputToken
from .token import RawToken
from .token import TagToken

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

        default_trim = self.env.trim
        left_trim = stream.trim_carry
        stream.trim_carry = default_trim

        # TODO: benchmark match vs type_ == vs isinstance
        # TODO: benchmark positional vs keyword match args

        while True:
            match stream.current():
                case ContentToken():
                    nodes.append(content.parse(stream, left_trim=left_trim))
                    left_trim = default_trim
                case CommentToken(wc=wc):
                    left_trim = wc[-1]
                    nodes.append(comment.parse(stream))
                case RawToken(wc=wc):
                    left_trim = wc[-1]
                    nodes.append(raw.parse(stream))
                case OutputToken(wc=wc):
                    left_trim = wc[-1]
                    nodes.append(output.parse(stream))
                case TagToken(wc=wc, name=name):
                    left_trim = wc[-1]
                    stream.trim_carry = left_trim
                    try:
                        nodes.append(tags[name].parse(stream))
                    except KeyError as err:
                        # TODO: change error message if name is "liquid"
                        raise LiquidSyntaxError(
                            f"unknown tag '{name}'", token=stream.current()
                        ) from err
                case LinesToken(wc=wc):
                    left_trim = wc[-1]
                    nodes.append(lines.parse(stream))
                case stream.eoi:
                    break
                case _token:
                    raise LiquidSyntaxError(
                        "unexpected token '{_token.__class__.__name__}'",
                        token=_token,
                    )

            next(stream, None)

        return nodes

    def parse_block(self, stream: TokenStream, end: Container[str]) -> list[Node]:
        """Parse markup tokens from _stream_ until wee find a tag in _end_."""
        tags = self.tags
        comment = tags["__COMMENT"]
        content = cast(Content, tags["__CONTENT"])
        output = tags["__OUTPUT"]
        raw = tags["__RAW"]
        lines = tags["__LINES"]

        default_trim = self.env.trim
        left_trim = stream.trim_carry
        stream.trim_carry = default_trim

        nodes: list[Node] = []

        while True:
            match stream.current():
                case ContentToken():
                    nodes.append(content.parse(stream, left_trim=left_trim))
                    left_trim = default_trim
                case CommentToken(wc=wc):
                    left_trim = wc[-1]
                    nodes.append(comment.parse(stream))
                case RawToken(wc=wc):
                    left_trim = wc[-1]
                    nodes.append(raw.parse(stream))
                case OutputToken(wc=wc):
                    left_trim = wc[-1]
                    nodes.append(output.parse(stream))
                case TagToken(wc=wc, name=name):
                    left_trim = wc[-1]

                    if name in end:
                        stream.trim_carry = left_trim
                        break

                    try:
                        nodes.append(tags[name].parse(stream))
                    except KeyError as err:
                        # TODO: change error message if name is "liquid"
                        raise LiquidSyntaxError(
                            f"unknown tag {name}", token=stream.current()
                        ) from err
                case LinesToken(wc=wc):
                    left_trim = wc[-1]
                    nodes.append(lines.parse(stream))
                case stream.eoi:
                    break

            next(stream, None)

        return nodes


def skip_block(stream: TokenStream, end: Container[str]) -> None:
    """Advance the stream until we find a tag with a name in _end_."""
    while not stream.is_one_of(end):
        next(stream)
