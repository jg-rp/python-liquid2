"""Liquid template lexical scanner."""

from __future__ import annotations

import re
from itertools import chain
from typing import TYPE_CHECKING
from typing import Callable
from typing import Optional
from typing import Pattern

from typing_extensions import Never

from .exceptions import LiquidSyntaxError
from .token import CommentToken
from .token import ContentToken
from .token import ErrorToken
from .token import LinesToken
from .token import OutputToken
from .token import PathToken
from .token import RangeToken
from .token import RawToken
from .token import TagToken
from .token import Token
from .token import TokenType
from .token import WhitespaceControl
from .token import is_token_type

if TYPE_CHECKING:
    from .token import TokenT

RE_LINE_COMMENT = re.compile(r"\#(.*?)(?=(\n|[\-+~]?%\}))")
RE_OUTPUT_END = re.compile(r"([+\-~]?)\}\}")
RE_TAG_END = re.compile(r"([+\-~]?)%\}")
RE_WHITESPACE_CONTROL = re.compile(r"[+\-~]")

RE_TAG_NAME = re.compile(r"[a-z][a-z_0-9]*\b")

RE_WHITESPACE = re.compile(r"[ \n\r\t]+")
RE_LINE_SPACE = re.compile(r"[ \t]+")
RE_LINE_TERM = re.compile(r"\r?\n")

RE_PROPERTY = re.compile(r"[\u0080-\uFFFFa-zA-Z_][\u0080-\uFFFFa-zA-Z0-9_-]*")
RE_INDEX = re.compile(r"-?[0-9]+")
ESCAPES = frozenset(["b", "f", "n", "r", "t", "u", "/", "\\"])

SYMBOLS: dict[str, str] = {
    "GE": r">=",
    "LE": r"<=",
    "EQ": r"==",
    "NE": r"!=",
    "LG": r"<>",
    "GT": r">",
    "LT": r"<",
    "DOUBLE_DOT": r"\.\.",
    "DOUBLE_PIPE": r"\|\|",
    "ASSIGN": r"=",
    "ROOT": r"\$",
    "LPAREN": r"\(",
    "RPAREN": r"\)",
    "SINGLE_QUOTE_STRING": r"'",
    "DOUBLE_QUOTE_STRING": r"\"",
    "COLON": r":",
    "COMMA": r",",
    "PIPE": r"\|",
    "LBRACKET": r"\[",
}

NUMBERS: dict[str, str] = {
    "FLOAT": r"(:?-?[0-9]+\.[0-9]+(?:[eE][+-]?[0-9]+)?)|(-?[0-9]+[eE]-[0-9]+)",
    "INT": r"-?[0-9]+(?:[eE]\+?[0-9]+)?",
}

WORD: dict[str, str] = {
    "WORD": r"[\u0080-\uFFFFa-zA-Z_][\u0080-\uFFFFa-zA-Z0-9_-]*",
}

KEYWORD_MAP: dict[str, TokenType] = {
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "and": TokenType.AND_WORD,
    "or": TokenType.OR_WORD,
    "in": TokenType.IN,
    "not": TokenType.NOT_WORD,
    "contains": TokenType.CONTAINS,
    "nil": TokenType.NULL,
    "null": TokenType.NULL,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "with": TokenType.WITH,
    "required": TokenType.REQUIRED,
    "as": TokenType.AS,
    "for": TokenType.FOR,
}

TOKEN_MAP: dict[str, TokenType] = {
    **KEYWORD_MAP,
    "FLOAT": TokenType.FLOAT,
    "INT": TokenType.INT,
    "GE": TokenType.GE,
    "LE": TokenType.LE,
    "EQ": TokenType.EQ,
    "NE": TokenType.NE,
    "LG": TokenType.NE,
    "GT": TokenType.GT,
    "LT": TokenType.LT,
    "DOUBLE_DOT": TokenType.DOUBLE_DOT,
    "DOUBLE_PIPE": TokenType.DOUBLE_PIPE,
    "ASSIGN": TokenType.ASSIGN,
    "LPAREN": TokenType.LPAREN,
    "RPAREN": TokenType.RPAREN,
    "COLON": TokenType.COLON,
    "COMMA": TokenType.COMMA,
    "PIPE": TokenType.PIPE,
}

MARKUP: dict[str, str] = {
    "RAW": (
        r"\{%(?P<RAW_WC0>[\-+~]?)\s*raw\s*(?P<RAW_WC1>[\-+~]?)%\}"
        r"(?P<RAW_TEXT>.*?)"
        r"\{%(?P<RAW_WC2>[\-+~]?)\s*endraw\s*(?P<RAW_WC3>[\-+~]?)%\}"
    ),
    "OUTPUT": r"\{\{(?P<OUT_WC>[\-+~]?)\s*",
    "TAG": r"\{%(?P<TAG_WC>[\-+~]?)\s*(?P<TAG_NAME>[a-z][a-z_0-9]*)",
    "COMMENT": (
        r"\{(?P<HASHES>#+)(?P<COMMENT_WC0>[\-+~]?)"
        r"(?P<COMMENT_TEXT>.*)"
        r"(?P<COMMENT_WC1>[\-+~]?)(?P=HASHES)\}"
    ),
    "CONTENT": r".+?(?=(\{\{|\{%|\{#+|$))",
}

WC_MAP = {
    None: WhitespaceControl.DEFAULT,
    "": WhitespaceControl.DEFAULT,
    "-": WhitespaceControl.MINUS,
    "+": WhitespaceControl.PLUS,
    "~": WhitespaceControl.TILDE,
}

WC_DEFAULT = (WhitespaceControl.DEFAULT, WhitespaceControl.DEFAULT)

StateFn = Callable[["Lexer"], Optional["StateFn"]]


def _compile(*rules: dict[str, str], flags: int = 0) -> Pattern[str]:
    _rules = chain.from_iterable(rule_set.items() for rule_set in rules)
    pattern = "|".join(f"(?P<{name}>{pattern})" for name, pattern in _rules)
    return re.compile(pattern, flags)


MARKUP_RULES = _compile(MARKUP, flags=re.DOTALL)
TOKEN_RULES = _compile(NUMBERS, SYMBOLS, WORD)


class Lexer:
    """Liquid template lexical scanner."""

    __slots__ = (
        "in_range",
        "line_start",
        "line_statements",
        "line_space",
        "markup",
        "markup_start",
        "pos",
        "source",
        "start",
        "tag_name",
        "expression",
        "wc",
        "path_stack",
    )

    def __init__(self, source: str) -> None:
        self.markup: list[TokenT] = []
        """Markup resulting from scanning a Liquid template."""

        self.expression: list[TokenT] = []
        """Tokens from the current expression."""

        self.line_statements: list[TagToken | CommentToken] = []
        """Markup resulting from scanning a sequence of line statements."""

        self.line_space: list[str] = []
        """Whitespace preceding line statements."""

        self.path_stack: list[PathToken] = []
        """Current path/query/variable, possibly with nested paths."""

        self.start = 0
        """Pointer to the start of the current token."""

        self.pos = 0
        """Pointer to the current character."""

        self.markup_start = -1
        """Pointer to the start of the current expression."""

        self.line_start = -1
        """Pointer to the start of the current line statement."""

        self.wc: list[WhitespaceControl] = []
        """Whitespace control for the current tag or output statement."""

        self.tag_name = ""
        """The name of the current tag."""

        self.in_range: bool = False
        """Indicates if we're currently parsing a range literal."""

        self.source = source
        """The template source text being scanned."""

    def run(self) -> None:
        """Populate _self.tokens_."""
        state: Optional[StateFn] = lex_markup
        while state is not None:
            state = state(self)

    def next(self) -> str:
        """Return the next character, or the empty string if no more characters."""
        try:
            c = self.source[self.pos]
            self.pos += 1
            return c
        except IndexError:
            return ""

    def ignore(self) -> None:
        """Ignore characters up to the pointer."""
        self.start = self.pos

    skip = ignore
    """Alias for `ignore()`."""

    def backup(self) -> None:
        """Move the pointer back one character."""
        if self.pos <= self.start:
            # Cant backup beyond start.
            raise LiquidSyntaxError("unexpected end of expression", token=None)
        self.pos -= 1

    def peek(self) -> str:
        """Return the next character without advancing the pointer."""
        try:
            return self.source[self.pos]
        except IndexError:
            return ""

    def accept(self, pattern: Pattern[str]) -> bool:
        """Match _pattern_ starting from the current position."""
        match = pattern.match(self.source, self.pos)
        if match:
            self.pos += match.end() - match.start()
            return True
        return False

    def accept_path(self, *, carry: bool = False) -> None:
        self.path_stack.append(
            PathToken(
                type_=TokenType.PATH,
                path=[],
                start=self.start,
                stop=-1,
                source=self.source,
            )
        )

        if carry:
            self.path_stack[-1].path.append(self.source[self.start : self.pos])
            self.start = self.pos

        while True:
            c = self.next()

            if c == "":
                self.error("unexpected end of path")

            if c == ".":
                self.ignore()
                self.ignore_whitespace()
                if match := RE_PROPERTY.match(self.source, self.pos):
                    self.path_stack[-1].path.append(match.group())
                    self.pos += match.end() - match.start()
                    self.start = self.pos
                    self.path_stack[-1].stop = self.pos

            elif c == "]":  # TODO: handle empty brackets
                if len(self.path_stack) == 1:
                    self.ignore()
                    self.path_stack[0].stop = self.start
                else:
                    path = self.path_stack.pop()
                    path.stop = self.start
                    self.ignore()
                    self.path_stack[-1].path.append(
                        path
                    )  # TODO: handle unbalanced brackets
                    self.path_stack[-1].stop = self.pos

            elif c == "[":
                self.ignore()
                self.ignore_whitespace()

                if self.peek() in ("'", '"'):
                    quote = self.next()
                    self.ignore()
                    self.accept_string(quote=quote)
                    self.path_stack[-1].path.append(self.source[self.start : self.pos])
                    self.next()
                    self.ignore()  # skip closing quote

                elif match := RE_INDEX.match(self.source, self.pos):
                    self.path_stack[-1].path.append(int(match.group()))
                    self.pos += match.end() - match.start()
                    self.start = self.pos

                elif match := RE_PROPERTY.match(self.source, self.pos):
                    # A nested path
                    self.path_stack.append(
                        PathToken(
                            type_=TokenType.PATH,
                            path=[match.group()],
                            start=self.start,
                            stop=-1,
                            source=self.source,
                        )
                    )
                    self.pos += match.end() - match.start()
                    self.start = self.pos
            else:
                self.backup()
                return

    def accept_string(self, *, quote: str) -> None:
        # Assumes the opening quote has been consumed.
        if self.peek() == quote:
            # an empty string
            # leave the closing quote for the caller
            return

        while True:
            c = self.next()

            if c == "\\":
                peeked = self.peek()
                if peeked in ESCAPES or peeked == quote:
                    self.next()
                else:
                    raise LiquidSyntaxError(
                        "invalid escape sequence",
                        token=ErrorToken(
                            type_=TokenType.ERROR,
                            index=self.pos,
                            value=peeked,
                            markup_start=self.markup_start,
                            markup_stop=self.pos,
                            source=self.source,
                            message="invalid escape sequence",
                        ),
                    )

            if c == quote:
                self.backup()
                return

            if not c:
                raise LiquidSyntaxError(
                    "unclosed string literal",
                    token=ErrorToken(
                        type_=TokenType.ERROR,
                        index=self.start,
                        value=self.source[self.start],
                        markup_start=self.markup_start,
                        markup_stop=self.pos,
                        source=self.source,
                        message="unclosed string literal",
                    ),
                )

    def accept_range(self) -> None:
        rparen = self.expression.pop()
        assert is_token_type(rparen, TokenType.RPAREN)

        range_stop_token = self.expression.pop()
        if range_stop_token.type_ not in (
            TokenType.INT,
            TokenType.SINGLE_QUOTE_STRING,
            TokenType.DOUBLE_QUOTE_STRING,
            TokenType.PATH,
            TokenType.WORD,
        ):
            self.raise_for_token(
                "expected an integer or variable to stop a range expression, "
                f"found {range_stop_token.type_.name}",
                range_stop_token,
            )

        double_dot = self.expression.pop()
        if not is_token_type(double_dot, TokenType.DOUBLE_DOT):
            self.raise_for_token("malformed range expression", double_dot)

        range_start_token = self.expression.pop()
        if range_start_token.type_ not in (
            TokenType.INT,
            TokenType.SINGLE_QUOTE_STRING,
            TokenType.DOUBLE_QUOTE_STRING,
            TokenType.PATH,
        ):
            self.raise_for_token(
                "expected an integer or variable to start a range expression, "
                f"found {range_start_token.type_.name}",
                range_start_token,
            )

        lparen = self.expression.pop()
        if not is_token_type(lparen, TokenType.LPAREN):
            self.raise_for_token(
                "range expressions must be surrounded by parentheses", lparen
            )

        self.expression.append(
            RangeToken(
                type_=TokenType.RANGE,
                range_start=range_start_token,
                range_stop=range_stop_token,
                start=lparen.index,
                stop=rparen.index + 1,
                source=self.source,
            )
        )

    def accept_token(self) -> bool:
        match = TOKEN_RULES.match(self.source, pos=self.pos)

        if not match:
            return False

        kind = match.lastgroup
        assert kind is not None

        value = match.group()
        self.pos += len(value)

        if kind == "SINGLE_QUOTE_STRING":
            self.ignore()
            self.accept_string(quote="'")
            self.expression.append(
                Token(
                    type_=TokenType.SINGLE_QUOTE_STRING,
                    value=self.source[self.start : self.pos],
                    index=self.start,
                    source=self.source,
                )
            )
            self.start = self.pos
            assert self.next() == "'"
            self.ignore()

        elif kind == "DOUBLE_QUOTE_STRING":
            self.ignore()
            self.accept_string(quote='"')
            self.expression.append(
                Token(
                    type_=TokenType.DOUBLE_QUOTE_STRING,
                    value=self.source[self.start : self.pos],
                    index=self.start,
                    source=self.source,
                )
            )
            self.start = self.pos
            assert self.next() == '"'
            self.ignore()

        elif kind == "LBRACKET":
            self.backup()
            self.accept_path()
            self.expression.append(self.path_stack.pop())

        elif kind == "WORD":
            if self.peek() in (".", "["):
                self.accept_path(carry=True)
                self.expression.append(self.path_stack.pop())

            elif token_type := KEYWORD_MAP.get(value):
                self.expression.append(
                    Token(
                        type_=token_type,
                        value=value,
                        index=self.start,
                        source=self.source,
                    )
                )
            else:
                self.expression.append(
                    Token(
                        type_=TokenType.WORD,
                        value=value,
                        index=self.start,
                        source=self.source,
                    )
                )

            self.start = self.pos

        elif token_type := TOKEN_MAP.get(kind):
            self.expression.append(
                Token(
                    type_=token_type,
                    value=value,
                    index=self.start,
                    source=self.source,
                )
            )
            self.start = self.pos

            # Special case for detecting range expressions
            if kind == "DOUBLE_DOT":
                self.in_range = True

            if kind == "RPAREN" and self.in_range:
                self.accept_range()
                self.in_range = False
        else:
            msg = f"unknown token {self.source[self.start:self.pos]!r}"
            raise LiquidSyntaxError(
                msg,
                token=ErrorToken(
                    type_=TokenType.ERROR,
                    index=self.start,
                    value=self.source[self.start : self.pos],
                    markup_start=self.markup_start,
                    markup_stop=self.pos,
                    source=self.source,
                    message=msg,
                ),
            )

        return True

    def ignore_whitespace(self) -> bool:
        """Move the pointer past any whitespace."""
        if self.pos != self.start:
            msg = (
                "must emit or ignore before consuming whitespace "
                f"({self.source[self.start: self.pos]!r}:{self.pos})"
            )
            raise Exception(msg)

        match = RE_WHITESPACE.match(self.source, self.pos)
        if match:
            self.pos += match.end() - match.start()
            self.start = self.pos
            return True
        return False

    def consume_whitespace(self) -> str:
        """Consume and return whitespace."""
        if self.pos != self.start:
            msg = (
                "must emit or ignore before consuming whitespace "
                f"({self.source[self.start: self.pos]!r}:{self.pos})"
            )
            raise Exception(msg)

        match = RE_WHITESPACE.match(self.source, self.pos)
        if match:
            whitespace = match.group()
            self.pos += len(whitespace)
            self.start = self.pos
            return whitespace
        return ""

    def ignore_line_space(self) -> str:
        """Move the pointer past any allowed whitespace inside line statements."""
        if self.pos != self.start:
            msg = (
                "must emit or ignore before consuming whitespace "
                f"({self.source[self.start: self.pos]!r}:{self.pos})"
            )
            raise Exception(msg)

        match = RE_LINE_SPACE.match(self.source, self.pos)
        if match:
            whitespace = match.group()
            self.pos += len(whitespace)
            self.start = self.pos
            return whitespace
        return ""

    def error(self, msg: str) -> Never:
        """Emit an error token."""
        # TODO: better error messages.
        raise LiquidSyntaxError(
            msg,
            token=ErrorToken(
                type_=TokenType.ERROR,
                index=self.pos,
                value=self.source[self.start : self.pos],
                markup_start=self.markup_start,
                markup_stop=self.pos,
                source=self.source,
                message=msg,
            ),
        )

    def raise_for_token(self, msg: str, token: TokenT) -> Never:
        raise LiquidSyntaxError(
            msg,
            token=ErrorToken(
                type_=TokenType.ERROR,
                index=token.start,
                value=self.source[token.start : token.stop],
                markup_start=self.markup_start,
                markup_stop=self.pos,
                source=self.source,
                message=msg,
            ),
        )


def lex_markup(l: Lexer) -> StateFn | None:
    while True:
        match = MARKUP_RULES.match(l.source, pos=l.pos)

        if not match:
            assert l.pos == len(l.source), f"{l.pos}:{l.source[l.pos: 10]!r}.."
            return None

        kind = match.lastgroup
        value = match.group()
        l.pos += len(value)

        if kind == "CONTENT":
            l.markup.append(
                ContentToken(
                    type_=TokenType.CONTENT,
                    start=l.start,
                    stop=l.pos,
                    text=value,
                    source=l.source,
                )
            )
            l.start = l.pos
            continue

        if kind == "OUTPUT":
            l.markup_start = l.start
            l.wc.append(WC_MAP[match.group("OUT_WC")])
            l.ignore()
            return lex_inside_output_statement

        if kind == "TAG":
            l.markup_start = l.start
            l.wc.append(WC_MAP[match.group("TAG_WC")])
            tag_name = match.group("TAG_NAME")
            l.tag_name = tag_name
            l.ignore()
            return lex_inside_liquid_tag if tag_name == "liquid" else lex_inside_tag

        if kind == "COMMENT":
            l.markup.append(
                CommentToken(
                    type_=TokenType.COMMENT,
                    start=l.start,
                    stop=l.pos,
                    wc=(
                        WC_MAP[match.group("COMMENT_WC0")],
                        WC_MAP[match.group("COMMENT_WC1")],
                    ),
                    text=match.group("COMMENT_TEXT"),
                    hashes=match.group("HASHES"),
                    source=l.source,
                )
            )
            continue

        if kind == "RAW":
            l.markup.append(
                RawToken(
                    type_=TokenType.RAW,
                    start=l.start,
                    stop=l.pos,
                    wc=(
                        WC_MAP[match.group("RAW_WC0")],
                        WC_MAP[match.group("RAW_WC1")],
                        WC_MAP[match.group("RAW_WC2")],
                        WC_MAP[match.group("RAW_WC3")],
                    ),
                    text=match.group("RAW_TEXT"),
                    source=l.source,
                )
            )
            l.start = l.pos
            continue

        l.error("unreachable")


def lex_inside_output_statement(
    l: Lexer,
) -> StateFn | None:  # noqa: PLR0911, PLR0912, PLR0915
    while True:
        l.ignore_whitespace()
        if not l.accept_token():
            if match := RE_OUTPUT_END.match(l.source, l.pos):
                l.wc.append(WC_MAP[match.group(1)])
                l.pos += match.end() - match.start()

                l.markup.append(
                    OutputToken(
                        type_=TokenType.OUTPUT,
                        start=l.markup_start,
                        stop=l.pos,
                        wc=(l.wc[0], l.wc[1]),
                        expression=l.expression,
                        source=l.source,
                    )
                )

                l.wc.clear()
                l.expression = []
                l.ignore()
                return lex_markup

            l.error(f"unexpected {l.next()!r}")


def lex_inside_tag(l: Lexer) -> StateFn | None:
    while True:
        l.ignore_whitespace()
        if not l.accept_token():
            if match := RE_TAG_END.match(l.source, l.pos):
                l.wc.append(WC_MAP[match.group(1)])
                l.pos += match.end() - match.start()
                l.markup.append(
                    TagToken(
                        type_=TokenType.TAG,
                        start=l.markup_start,
                        stop=l.pos,
                        wc=(l.wc[0], l.wc[1]),
                        name=l.tag_name,
                        expression=l.expression,
                        source=l.source,
                    )
                )
                l.wc.clear()
                l.tag_name = ""
                l.expression = []
                l.ignore()
                return lex_markup

            l.error(f"unexpected {l.next()!r}")


def lex_inside_liquid_tag(l: Lexer) -> StateFn | None:
    l.line_space.append(l.consume_whitespace())

    if match := RE_TAG_END.match(l.source, l.pos):
        l.wc.append(WC_MAP[match.group(1)])
        l.pos += match.end() - match.start()
        l.markup.append(
            LinesToken(
                type_=TokenType.LINES,
                start=l.markup_start,
                stop=l.pos,
                wc=(l.wc[0], l.wc[1]),
                name="liquid",
                statements=l.line_statements,
                whitespace=l.line_space,
                source=l.source,
            )
        )

        l.wc.clear()
        l.tag_name = ""
        l.line_statements = []
        l.line_space = []
        l.expression = []
        l.ignore()
        return lex_markup

    if l.accept(RE_TAG_NAME):
        l.tag_name = l.source[l.start : l.pos]
        l.line_start = l.start
        l.ignore()
        return lex_inside_line_statement

    if match := RE_LINE_COMMENT.match(l.source, l.pos):
        l.pos += match.end() - match.start()
        l.line_statements.append(
            CommentToken(
                type_=TokenType.COMMENT,
                start=l.start,
                stop=l.pos,
                wc=WC_DEFAULT,
                text=match.group(1),
                hashes="#",
                source=l.source,
            )
        )
        l.start = l.pos
        # Line comments don't consume their trailing newline, but
        # lex_inside_line_statement does.
        if l.peek() == "\n":
            l.next()
            l.ignore()
        return lex_inside_liquid_tag

    l.next()
    return l.error("expected a tag name")


def lex_inside_line_statement(l: Lexer) -> StateFn | None:
    while True:
        l.ignore_line_space()

        if l.accept(RE_LINE_TERM):
            l.line_statements.append(
                TagToken(
                    type_=TokenType.TAG,
                    start=l.line_start,
                    stop=l.start,
                    wc=WC_DEFAULT,
                    name=l.tag_name,
                    expression=l.expression,
                    source=l.source,
                )
            )
            l.ignore()
            l.tag_name = ""
            l.expression = []
            return lex_inside_liquid_tag

        if not l.accept_token():
            if match := RE_TAG_END.match(l.source, l.pos):
                l.wc.append(WC_MAP[match.group(1)])
                l.pos += match.end() - match.start()
                l.ignore()
                l.line_statements.append(
                    TagToken(
                        type_=TokenType.TAG,
                        start=l.line_start,
                        stop=l.pos,
                        wc=WC_DEFAULT,
                        name=l.tag_name,
                        expression=l.expression,
                        source=l.source,
                    )
                )

                l.markup.append(
                    LinesToken(
                        type_=TokenType.LINES,
                        start=l.markup_start,
                        stop=l.pos,
                        wc=(l.wc[0], l.wc[1]),
                        name="liquid",
                        statements=l.line_statements,
                        whitespace=l.line_space,
                        source=l.source,
                    )
                )

                l.wc = []
                l.tag_name = ""
                l.line_statements = []
                l.line_space = []
                l.expression = []
                l.ignore()
                return lex_markup

            l.error(f"unknown symbol '{l.next()}'")


def tokenize(source: str) -> list[TokenT]:
    """Scan Liquid template _source_ and return a list of Markup objects."""
    lexer = Lexer(source)
    lexer.run()
    return lexer.markup
