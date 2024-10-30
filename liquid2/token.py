"""Markup and expression tokens produced by the lexer."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from enum import auto
from typing import TypeAlias
from typing import Union


class WhitespaceControl(Enum):
    PLUS = auto()
    MINUS = auto()
    TILDE = auto()
    DEFAULT = auto()


Markup: TypeAlias = Union[
    "Comment",
    "Content",
    "EOI",
    "Error",
    "Lines",
    "Output",
    "Raw",
    "Tag",
]


@dataclass(frozen=True, slots=True)
class EOI:
    start: int
    stop: int
    source: str


@dataclass(frozen=True, slots=True)
class Error:
    start: int
    stop: int
    text: str
    source: str
    message: str | None = field(default=None)


@dataclass(frozen=True, slots=True)
class Content:
    start: int
    stop: int
    text: str
    source: str


@dataclass(frozen=True, slots=True)
class Raw:
    start: int
    stop: int
    wc: tuple[
        WhitespaceControl,
        WhitespaceControl,
        WhitespaceControl,
        WhitespaceControl,
    ]
    text: str
    source: str


@dataclass(frozen=True, slots=True)
class Comment:
    start: int
    stop: int
    wc: tuple[WhitespaceControl, WhitespaceControl]
    text: str
    hashes: str
    source: str


@dataclass(frozen=True, slots=True)
class Output:
    start: int
    stop: int
    wc: tuple[WhitespaceControl, WhitespaceControl]
    expression: list[Token]
    source: str


@dataclass(frozen=True, slots=True)
class Tag:
    start: int
    stop: int
    wc: tuple[WhitespaceControl, WhitespaceControl]
    name: str
    expression: list[Token]
    source: str


@dataclass(frozen=True, slots=True)
class Lines:
    start: int
    stop: int
    wc: tuple[WhitespaceControl, WhitespaceControl]
    name: str
    statements: list[Tag | Comment | Error]
    source: str


class TokenType(Enum):
    """JSONPath expression token types."""

    EOI = auto()
    ERROR = auto()

    AND = auto()  # &&
    AND_WORD = auto()  # and
    AS = auto()
    ASSIGN = auto()  # =
    COLON = auto()
    COMMA = auto()
    CONTAINS = auto()
    CURRENT = auto()  # @
    DOT = auto()
    DOUBLE_DOT = auto()
    DOUBLE_PIPE = auto()
    DOUBLE_QUOTE_STRING = auto()
    ELSE = auto()
    EQ = auto()
    FALSE = auto()
    FLOAT = auto()
    FOR = auto()
    FUNCTION = auto()
    GE = auto()
    GT = auto()
    IF = auto()
    IN = auto()
    INDEX = auto()
    INT = auto()
    LBRACKET = auto()
    LE = auto()
    LPAREN = auto()
    LT = auto()
    MINUS = auto()  # Whitespace control
    NE = auto()
    NOT = auto()
    NOT_WORD = auto()
    NULL = auto()
    OP = auto()
    OR = auto()  # ||
    OR_WORD = auto()  # or
    PIPE = auto()
    PLUS = auto()  # Whitespace control
    PROPERTY = auto()
    FILTER = auto()  # ? (start of a JSONPath filter selector)
    RBRACKET = auto()
    REQUIRED = auto()
    ROOT = auto()
    RPAREN = auto()
    SINGLE_QUOTE_STRING = auto()
    TILDE = auto()  # Whitespace control
    TRUE = auto()
    WILD = auto()
    WITH = auto()
    WORD = auto()


@dataclass(frozen=True, slots=True)
class Token:
    type_: TokenType
    value: str
    index: int
    query: str
    message: str | None = field(default=None)
