"""Top-level markup and expression tokens produced by the lexer."""

from __future__ import annotations

import re
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from enum import auto
from typing import TypeAlias
from typing import TypeGuard
from typing import Union


class WhitespaceControl(Enum):
    PLUS = auto()
    MINUS = auto()
    TILDE = auto()
    DEFAULT = auto()

    def __str__(self) -> str:
        if self == WhitespaceControl.PLUS:
            return "+"
        if self == WhitespaceControl.MINUS:
            return "-"
        if self == WhitespaceControl.TILDE:
            return "~"
        return ""


class TokenType(Enum):
    EOI = auto()
    ERROR = auto()

    COMMENT = auto()
    CONTENT = auto()
    LINES = auto()
    OUTPUT = auto()
    RAW = auto()
    TAG = auto()

    PATH = auto()
    RANGE = auto()

    AND_WORD = auto()  # and
    AS = auto()
    ASSIGN = auto()  # =
    COLON = auto()
    COMMA = auto()
    CONTAINS = auto()
    DOT = auto()
    DOUBLE_DOT = auto()
    DOUBLE_PIPE = auto()
    DOUBLE_QUOTE_STRING = auto()
    ELSE = auto()
    EQ = auto()
    FALSE = auto()
    FLOAT = auto()
    FOR = auto()
    GE = auto()
    GT = auto()
    IF = auto()
    IN = auto()
    INT = auto()
    LE = auto()
    LPAREN = auto()
    LT = auto()
    NE = auto()
    NOT_WORD = auto()
    NULL = auto()
    OR_WORD = auto()  # or
    PIPE = auto()
    REQUIRED = auto()
    RPAREN = auto()
    SINGLE_QUOTE_STRING = auto()
    TRUE = auto()
    WITH = auto()
    WORD = auto()


@dataclass(kw_only=True, slots=True)
class TokenT:
    type_: TokenType


@dataclass(kw_only=True, slots=True)
class ContentToken(TokenT):
    start: int
    stop: int
    text: str

    def __str__(self) -> str:
        return self.text


@dataclass(kw_only=True, slots=True)
class RawToken(TokenT):
    start: int
    stop: int
    wc: tuple[
        WhitespaceControl,
        WhitespaceControl,
        WhitespaceControl,
        WhitespaceControl,
    ]
    text: str

    def __str__(self) -> str:
        return (
            f"{{%{self.wc[0]} raw {self.wc[1]}%}}"
            f"{self.text}"
            f"{{%{self.wc[2]} endraw {self.wc[3]}%}}"
        )


@dataclass(kw_only=True, slots=True)
class CommentToken(TokenT):
    start: int
    stop: int
    wc: tuple[WhitespaceControl, WhitespaceControl]
    text: str
    hashes: str

    def __str__(self) -> str:
        return f"{{{self.hashes}{self.wc[0]}{self.text}{self.wc[1]}{self.hashes}}}"


@dataclass(kw_only=True, slots=True)
class OutputToken(TokenT):
    start: int
    stop: int
    wc: tuple[WhitespaceControl, WhitespaceControl]
    expression: list[TokenT]

    def __str__(self) -> str:
        return (
            f"{{{{{self.wc[0]} "
            f"{_expression_as_string(self.expression)} "
            f"{self.wc[1]}}}}}"
        )


@dataclass(kw_only=True, slots=True)
class TagToken(TokenT):
    start: int
    stop: int
    wc: tuple[WhitespaceControl, WhitespaceControl]
    name: str
    expression: list[TokenT]

    def __str__(self) -> str:
        if self.expression:
            return (
                f"{{%{self.wc[0]} {self.name} "
                f"{_expression_as_string(self.expression)} "
                f"{self.wc[1]}%}}"
            )
        return f"{{%{self.wc[0]} {self.name} {self.wc[1]}%}}"


@dataclass(kw_only=True, slots=True)
class LinesToken(TokenT):
    start: int
    stop: int
    wc: tuple[WhitespaceControl, WhitespaceControl]
    name: str
    statements: list[TagToken | CommentToken]

    def __str__(self) -> str:
        if self.statements:
            lines = "\n".join(_tag_as_line_statement(line) for line in self.statements)
            return f"{{%{self.wc[0]} liquid {lines} {self.wc[1]}%}}"
        return f"{{%{self.wc[0]} liquid {self.wc[1]}%}}"


def _expression_as_string(expression: list[TokenT]) -> str:
    def _as_string(token: TokenT) -> str:
        if isinstance(token, Token):
            if token.type_ == TokenType.SINGLE_QUOTE_STRING:
                return f"'{token.value}'"
            if token.type_ == TokenType.DOUBLE_QUOTE_STRING:
                return f'"{token.value}"'
            return token.value
        return str(token)

    return " ".join(_as_string(token) for token in expression)


def _tag_as_line_statement(markup: TagToken | CommentToken) -> str:
    if isinstance(markup, TagToken):
        if markup.expression:
            return f"{markup.name} {_expression_as_string(markup.expression)}"
        return markup.name
    return f"# {markup.text}"


@dataclass(kw_only=True, slots=True)
class Token(TokenT):
    value: str
    index: int
    source: str = field(repr=False)


PathT: TypeAlias = list[Union[int, str, "PathToken"]]

RE_PROPERTY = re.compile(r"[\u0080-\uFFFFa-zA-Z_][\u0080-\uFFFFa-zA-Z0-9_-]*")


@dataclass(kw_only=True, slots=True)
class PathToken(TokenT):
    path: PathT
    start: int
    stop: int
    source: str = field(repr=False)

    def __str__(self) -> str:
        it = iter(self.path)
        buf = [str(next(it))]
        for segment in it:
            if isinstance(segment, PathToken):
                buf.append(f"[{segment}]")
            elif isinstance(segment, str):
                if RE_PROPERTY.fullmatch(segment):
                    buf.append(f".{segment}")
                else:
                    buf.append(f"[{segment!r}]")
            else:
                buf.append(f"[{segment}]")
        return "".join(buf)


@dataclass(kw_only=True, slots=True)
class RangeToken(TokenT):
    start: TokenT
    stop: TokenT
    index: int
    source: str = field(repr=False)


@dataclass(kw_only=True, slots=True)
class ErrorToken(TokenT):
    index: int
    value: str
    source: str = field(repr=False)
    message: str

    def __str__(self) -> str:
        return self.message


def is_content_token(token: TokenT) -> TypeGuard[ContentToken]:
    """A _ContentToken_ type guard."""
    return token.type_ == TokenType.CONTENT


def is_comment_token(token: TokenT) -> TypeGuard[CommentToken]:
    """A _CommentToken_ type guard."""
    return token.type_ == TokenType.COMMENT


def is_tag_token(token: TokenT) -> TypeGuard[TagToken]:
    """A _TagToken_ type guard."""
    return token.type_ == TokenType.TAG


def is_output_token(token: TokenT) -> TypeGuard[OutputToken]:
    """An _OutputToken_ type guard."""
    return token.type_ == TokenType.OUTPUT


def is_raw_token(token: TokenT) -> TypeGuard[RawToken]:
    """A _RawToken_ type guard."""
    return token.type_ == TokenType.RAW


def is_lines_token(token: TokenT) -> TypeGuard[LinesToken]:
    """A _LinesToken_ type guard."""
    return token.type_ == TokenType.LINES


def is_path_token(token: TokenT) -> TypeGuard[PathToken]:
    """A _PathToken_ type guard."""
    return token.type_ == TokenType.PATH


def is_range_token(token: TokenT) -> TypeGuard[RangeToken]:
    """A _RangeToken_ type guard."""
    return token.type_ == TokenType.RANGE


def is_token_type(token: TokenT, t: TokenType) -> TypeGuard[Token]:
    """A _Token_ type guard."""
    return token.type_ == t
