"""Markup and expression tokens produced by the lexer."""

from __future__ import annotations

import re
from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from enum import auto
from typing import TypeAlias
from typing import TypeGuard
from typing import Union


@dataclass(kw_only=True, slots=True)
class TokenT(ABC):
    """The base class for all tokens."""

    type_: TokenType
    source: str

    @property
    @abstractmethod
    def stop(self) -> int:
        """The end position of this token."""

    @property
    @abstractmethod
    def start(self) -> int:
        """The start position of this token."""


Markup: TypeAlias = Union[
    "RawToken",
    "CommentToken",
    "OutputToken",
    "TagToken",
    "LinesToken",
]


@dataclass(kw_only=True, slots=True)
class ContentToken(TokenT):
    """A token representing template text content that is not markup."""

    start: int
    stop: int
    text: str

    def __str__(self) -> str:
        return self.text


@dataclass(kw_only=True, slots=True)
class RawToken(TokenT):
    """A token representing raw content that should be treated as plain text."""

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
    """A token representing a comment."""

    start: int
    stop: int
    wc: tuple[WhitespaceControl, WhitespaceControl]
    text: str
    hashes: str

    def __str__(self) -> str:
        return f"{{{self.hashes}{self.wc[0]}{self.text}{self.wc[1]}{self.hashes}}}"


@dataclass(kw_only=True, slots=True)
class BlockCommentToken(CommentToken):
    """A token representing a block comment.

    That's one with a start and end tag.
    """

    def __str__(self) -> str:
        return f"{{%{self.wc[0]} comment %}}{self.text}{{% endcomment {self.wc[1]}%}}"


@dataclass(kw_only=True, slots=True)
class InlineCommentToken(CommentToken):
    """A token representing an inline comment tag.

    That's one with `#` as the tag name. Like `{% # some comment %}`.
    """

    def __str__(self) -> str:
        return f"{{%{self.wc[0]} #{self.text}{self.wc[1]}%}}"


@dataclass(kw_only=True, slots=True)
class OutputToken(TokenT):
    """A token representing an output statement."""

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
    """A token representing a tag.

    This could be an inline tag, or the start or end of a block tag.
    """

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
    """A token representing line statements, where each line is a tag expression.

    The built-in `{% liquid %}` tag is an example of a tag that uses line statements.
    """

    start: int
    stop: int
    wc: tuple[WhitespaceControl, WhitespaceControl]
    name: str
    statements: list[TagToken | CommentToken]
    whitespace: list[str]

    def __str__(self) -> str:
        assert len(self.whitespace) >= len(self.statements)
        if self.statements:
            lines = "\n".join(
                whitespace + _tag_as_line_statement(line)
                for line, whitespace in zip(
                    self.statements, self.whitespace, strict=False
                )
            )
            return f"{{%{self.wc[0]} liquid{lines} {self.wc[1]}%}}"
        return f"{{%{self.wc[0]} liquid {self.wc[1]}%}}"


def _expression_as_string(expression: list[TokenT]) -> str:
    buf: list[str] = []

    for token in expression:
        if isinstance(token, Token):
            if token.type_ == TokenType.SINGLE_QUOTE_STRING:
                buf.append(f" '{token.value}'")
            elif token.type_ == TokenType.DOUBLE_QUOTE_STRING:
                buf.append(f' "{token.value}"')
            elif token.type_ == TokenType.COMMA:
                buf.append(",")  # no leading space
            else:
                buf.append(f" {token.value}")
        else:
            buf.append(f" {token}")

    return "".join(buf).strip()


def _tag_as_line_statement(markup: TagToken | CommentToken) -> str:
    if isinstance(markup, TagToken):
        if markup.expression:
            return f"{markup.name} {_expression_as_string(markup.expression)}"
        return markup.name
    if isinstance(markup, BlockCommentToken):
        return f"comment\n{markup.text}endcomment"
    return f"#{markup.text}"


@dataclass(kw_only=True, slots=True)
class Token(TokenT):
    """A liquid expression token."""

    value: str
    index: int
    source: str = field(repr=False)

    @property
    def start(self) -> int:
        """Return the start position of this token."""
        return self.index

    @property
    def stop(self) -> int:
        """Return the end position of this token."""
        return self.index + len(self.value)


PathT: TypeAlias = list[Union[int, str, "PathToken"]]

RE_PROPERTY = re.compile(r"[\u0080-\uFFFFa-zA-Z_][\u0080-\uFFFFa-zA-Z0-9_-]*")


@dataclass(kw_only=True, slots=True)
class PathToken(TokenT):
    """A token representing the path to a variable."""

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
class TemplateStringToken(TokenT):
    """A token representing a string with interpolated expressions."""

    template: list[Token | OutputToken]
    start: int
    stop: int
    source: str = field(repr=False)

    def __str__(self) -> str:
        quote = "'" if self.type_ == TokenType.SINGLE_QUOTE_TEMPLATE_STRING else '"'
        buf: list[str] = []
        for token in self.template:
            if is_token_type(token, TokenType.SINGLE_QUOTE_STRING) or is_token_type(
                token, TokenType.DOUBLE_QUOTE_STRING
            ):
                buf.append(token.value)
            elif is_output_token(token):
                buf.append(f"${{{_expression_as_string(token.expression)}}}")
            else:
                buf.append(str(token))

        return f"{quote}{''.join(buf)}{quote}"


@dataclass(kw_only=True, slots=True)
class RangeToken(TokenT):
    """A token representing a range expression.

    For example, `(1..3)`.
    """

    range_start: TokenT
    range_stop: TokenT
    start: int
    stop: int
    source: str = field(repr=False)


@dataclass(kw_only=True, slots=True)
class ErrorToken(TokenT):
    """A token representing a syntax error found by the lexer."""

    index: int
    value: str
    markup_start: int
    markup_stop: int
    source: str = field(repr=False)
    message: str

    def __str__(self) -> str:
        return self.message

    @property
    def start(self) -> int:
        """Return the start position of this token."""
        return self.index

    @property
    def stop(self) -> int:
        """Return the end position of this token."""
        return self.index + len(self.value)


def is_content_token(token: TokenT) -> TypeGuard[ContentToken]:
    """A [ContentToken][liquid2.token.ContentToken] type guard."""
    return token.type_ == TokenType.CONTENT


def is_comment_token(token: TokenT) -> TypeGuard[CommentToken]:
    """A [CommentToken][liquid2.token.CommentToken] type guard."""
    return token.type_ == TokenType.COMMENT


def is_tag_token(token: TokenT) -> TypeGuard[TagToken]:
    """A [TagToken][liquid2.token.TagToken] type guard."""
    return token.type_ == TokenType.TAG


def is_output_token(token: TokenT) -> TypeGuard[OutputToken]:
    """An [OutputToken][liquid2.token.OutputToken] type guard."""
    return token.type_ == TokenType.OUTPUT


def is_raw_token(token: TokenT) -> TypeGuard[RawToken]:
    """A [RawToken][liquid2.token.RawToken] type guard."""
    return token.type_ == TokenType.RAW


def is_lines_token(token: TokenT) -> TypeGuard[LinesToken]:
    """A [LinesToken][liquid2.token.LinesToken] type guard."""
    return token.type_ == TokenType.LINES


def is_path_token(token: TokenT) -> TypeGuard[PathToken]:
    """A [PathToken][liquid2.token.PathToken] type guard."""
    return token.type_ == TokenType.PATH


def is_template_string_token(token: TokenT) -> TypeGuard[TemplateStringToken]:
    """A [TemplateStringToken][liquid2.token.TemplateStringToken] type guard."""
    return token.type_ in (
        TokenType.SINGLE_QUOTE_TEMPLATE_STRING,
        TokenType.DOUBLE_QUOTE_TEMPLATE_STRING,
    )


def is_range_token(token: TokenT) -> TypeGuard[RangeToken]:
    """A [RangeToken][liquid2.token.RangeToken] type guard."""
    return token.type_ == TokenType.RANGE


def is_token_type(token: TokenT, t: TokenType) -> TypeGuard[Token]:
    """A [Token][liquid2.token.Token] type guard."""
    return token.type_ == t


class WhitespaceControl(Enum):
    PLUS = auto()
    """Preserve all whitespace."""

    MINUS = auto()
    """Trim all whitespace."""

    TILDE = auto()
    """Trim immediate carriage return and newline characters only."""

    DEFAULT = auto()
    """Use the environment's `default_trim` setting."""

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
    DOUBLE_QUOTE_TEMPLATE_STRING = auto()
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
    SINGLE_QUOTE_TEMPLATE_STRING = auto()
    TRUE = auto()
    WITH = auto()
    WORD = auto()
