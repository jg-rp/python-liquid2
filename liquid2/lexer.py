"""JSONPath expression lexical scanner."""

from __future__ import annotations

import re
from functools import partial
from itertools import chain
from typing import TYPE_CHECKING
from typing import Callable
from typing import Literal
from typing import Optional
from typing import Pattern

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

RE_LINE_COMMENT = re.compile(r"\#.*?(?=(\n|[\-+~]?%\}))")
RE_OUTPUT_END = re.compile(r"([+\-~]?)\}\}")
RE_TAG_END = re.compile(r"([+\-~]?)%\}")
RE_WHITESPACE_CONTROL = re.compile(r"[+\-~]")

RE_TAG_NAME = re.compile(r"[a-z][a-z_0-9]*\b")

RE_WHITESPACE = re.compile(r"[ \n\r\t]+")
RE_LINE_SPACE = re.compile(r"[ \t]+")
RE_LINE_TERM = re.compile(r"\r?\n")

RE_PROPERTY = re.compile(r"[\u0080-\uFFFFa-zA-Z_][\u0080-\uFFFFa-zA-Z0-9_-]*")
RE_INDEX = re.compile(r"[0-9]+")
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
    "SINGLE_QUOTE_STRING": TokenType.SINGLE_QUOTE_STRING,
    "DOUBLE_QUOTE_STRING": TokenType.DOUBLE_QUOTE_STRING,
    "COLON": TokenType.COLON,
    "COMMA": TokenType.COMMA,
    "PIPE": TokenType.PIPE,
}

MARKUP: dict[str, str] = {
    "RAW": (
        r"\{%(?P<RAW_WC0>[\-+~]?)\s*raw\s(?P<RAW_WC1>[\-+~]?)%\}"
        r"(?P<RAW_TEXT>.*)"
        r"\{%(?P<RAW_WC2>[\-+~]?)\s*endraw\s(?P<RAW_WC3>[\-+~]?)%\}"
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
        "markup",
        "markup_start",
        "pos",
        "source",
        "start",
        "tag_name",
        "expression",
        "wc",
        "accept_output_token",
        "accept_tag_token",
        "accept_lines_token",
        "path",
        "path_stack",
    )

    def __init__(self, source: str) -> None:
        self.markup: list[TokenT] = []
        """Markup resulting from scanning a Liquid template."""

        self.expression: list[TokenT] = []
        """Tokens from the current expression."""

        self.line_statements: list[TagToken | CommentToken] = []
        """Markup resulting from scanning a sequence of line statements."""

        self.path_stack: list[PathToken] = []
        """Current path, possibly with nested paths."""

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

        self.accept_output_token = partial(
            self.accept_token,
            next_state=lex_inside_output_statement,
            range_state=lex_range_inside_output_statement,
        )

        self.accept_tag_token = partial(
            self.accept_token,
            next_state=lex_inside_tag,
            range_state=lex_range_inside_tag_expression,
        )

        self.accept_lines_token = partial(
            self.accept_token,
            next_state=lex_inside_line_statement,
            range_state=lex_range_inside_line_statement,
        )

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
        """Move the current position back one."""
        if self.pos <= self.start:
            # Cant backup beyond start.
            msg = "unexpected end of expression"
            raise LiquidSyntaxError(
                msg,
                token=Token(
                    type_=TokenType.ERROR,
                    value=msg,
                    index=self.pos,
                    source=self.source,
                ),
            )
        self.pos -= 1

    def peek(self) -> str:
        """Return the next character without advancing the pointer."""
        try:
            return self.source[self.pos]
        except IndexError:
            return ""

    def accept(self, s: str) -> bool:
        """Increment the pointer if the current position starts with _s_."""
        if self.source.startswith(s, self.pos):
            self.pos += len(s)
            return True
        return False

    def accept_match(self, pattern: Pattern[str]) -> bool:
        """Match _pattern_ starting from the pointer."""
        match = pattern.match(self.source, self.pos)
        if match:
            self.pos += len(match.group())
            return True
        return False

    def accept_end_output_statement(self) -> bool:
        """Accepts the output end sequence, possibly preceded by whitespace control."""
        if match := RE_OUTPUT_END.match(self.source, self.pos):
            wc_group = match.group(1)
            if wc_group:
                self.wc.append(WC_MAP[wc_group])
            else:
                self.wc.append(WhitespaceControl.DEFAULT)

            self.pos += len(match.group())
            return True
        return False

    def accept_end_tag(self) -> bool:
        """Accepts the tag end sequence, possibly preceded by whitespace control."""
        if match := RE_TAG_END.match(self.source, self.pos):
            wc_group = match.group(1)
            if wc_group:
                self.pos += 1
                self.wc.append(WC_MAP[wc_group])
            else:
                self.wc.append(WhitespaceControl.DEFAULT)

            self.pos += 2
            return True
        return False

    def ignore_whitespace(self) -> bool:
        """Move the pointer past any whitespace."""
        if self.pos != self.start:
            msg = (
                "must emit or ignore before consuming whitespace "
                f"({self.source[self.start: self.pos]!r}:{self.pos})"
            )
            raise Exception(msg)

        if self.accept_match(RE_WHITESPACE):
            self.ignore()
            return True
        return False

    def ignore_line_space(self) -> bool:
        """Move the pointer past any allowed whitespace inside line statements."""
        if self.accept_match(RE_LINE_SPACE):
            self.ignore()
            return True
        return False

    def error(self, msg: str) -> None:
        """Emit an error token."""
        # better error messages.
        self.markup.append(
            ErrorToken(
                type_=TokenType.ERROR,
                index=self.pos,
                value=self.source[self.start : self.pos],
                source=self.source,
                message=msg,
            )
        )

    def accept_token(  # noqa: PLR0911
        self,
        *,
        next_state: StateFn,
        range_state: StateFn,
    ) -> StateFn | None | Literal[False]:
        match = TOKEN_RULES.match(self.source, pos=self.pos)

        if not match:
            return False

        kind = match.lastgroup
        assert kind is not None

        value = match.group()
        self.pos += len(value)

        if kind == "SINGLE_QUOTE_STRING":
            self.ignore()
            accept_string(self, quote="'")
            self.expression.append(
                Token(
                    type_=TokenType.SINGLE_QUOTE_STRING,
                    value=self.source[self.start : self.pos],
                    index=self.start,
                    source=self.source,
                )
            )
            self.start = self.pos

        elif kind == "DOUBLE_QUOTE_STRING":
            self.ignore()
            accept_string(self, quote='"')
            self.expression.append(
                Token(
                    type_=TokenType.DOUBLE_QUOTE_STRING,
                    value=self.source[self.start : self.pos],
                    index=self.start,
                    source=self.source,
                )
            )
            self.start = self.pos

        elif kind == "LBRACKET":
            self.backup()
            accept_path(self)
            self.expression.append(self.path_stack.pop())

        if kind == "WORD":
            if self.peek() in (".", "["):
                accept_path(self, carry=True)
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
            return next_state

        if token_type := TOKEN_MAP.get(kind):
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
                return range_state

            return next_state

        self.error(f"unknown token {self.source[self.start:self.pos]!r}")
        return None


def lex_markup(l: Lexer) -> StateFn | None:
    while True:
        assert not l.expression  # current expression should be empty
        assert not l.tag_name  # current tag name should be empty

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
                )
            )
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
                )
            )
            continue

        l.error("unreachable")
        return None


def lex_inside_output_statement(
    l: Lexer,
) -> StateFn | None:  # noqa: PLR0911, PLR0912, PLR0915
    while True:
        l.ignore_whitespace()
        next_state = l.accept_output_token()

        if next_state is False:
            if l.accept_end_output_statement():
                l.markup.append(
                    OutputToken(
                        type_=TokenType.OUTPUT,
                        start=l.markup_start,
                        stop=l.pos,
                        wc=(l.wc[0], l.wc[1]),
                        expression=l.expression,
                    )
                )
                l.wc.clear()
                l.expression = []
                l.ignore()
                return lex_markup

            l.error(f"unknown symbol '{l.next()}'")
            return None

        return next_state


def lex_inside_tag(l: Lexer) -> StateFn | None:
    while True:
        l.ignore_whitespace()
        next_state = l.accept_tag_token()

        if next_state is False:
            if l.accept_end_tag():
                l.markup.append(
                    TagToken(
                        type_=TokenType.TAG,
                        start=l.markup_start,
                        stop=l.pos,
                        wc=(l.wc[0], l.wc[1]),
                        name=l.tag_name,
                        expression=l.expression,
                    )
                )
                l.wc.clear()
                l.tag_name = ""
                l.expression = []
                l.ignore()
                return lex_markup

            l.error(f"unknown symbol '{l.next()}'")
            return None

        return next_state


def lex_inside_liquid_tag(l: Lexer) -> StateFn | None:
    l.ignore_whitespace()

    if l.accept_end_tag():
        l.markup.append(
            LinesToken(
                type_=TokenType.LINES,
                start=l.markup_start,
                stop=l.pos,
                wc=(l.wc[0], l.wc[1]),
                name="liquid",
                statements=l.line_statements,
            )
        )

        l.wc.clear()
        l.tag_name = ""
        l.line_statements = []
        l.expression = []
        l.ignore()
        return lex_markup

    if l.accept_match(RE_TAG_NAME):
        l.tag_name = l.source[l.start : l.pos]
        l.line_start = l.start
        l.ignore()
        return lex_inside_line_statement

    if l.accept_match(RE_LINE_COMMENT):
        l.line_statements.append(
            CommentToken(
                type_=TokenType.COMMENT,
                start=l.start,
                stop=l.pos,
                wc=WC_DEFAULT,
                text=l.source[l.start : l.pos],
                hashes="#",
            )
        )
        l.start = l.pos
        return lex_inside_liquid_tag

    l.next()
    l.error("expected a tag name")
    return None


def lex_inside_line_statement(l: Lexer) -> StateFn | None:
    while True:
        l.ignore_line_space()

        if l.accept_match(RE_LINE_TERM):
            l.ignore()
            l.line_statements.append(
                TagToken(
                    type_=TokenType.TAG,
                    start=l.line_start,
                    stop=l.pos,
                    wc=WC_DEFAULT,
                    name=l.tag_name,
                    expression=l.expression,
                )
            )
            l.tag_name = ""
            l.expression = []
            return lex_inside_liquid_tag

        next_state = l.accept_lines_token()

        if next_state is False:
            if l.accept_end_tag():
                l.ignore()
                l.line_statements.append(
                    TagToken(
                        type_=TokenType.TAG,
                        start=l.line_start,
                        stop=l.pos,
                        wc=WC_DEFAULT,
                        name=l.tag_name,
                        expression=l.expression,
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
                    )
                )

                l.wc = []
                l.tag_name = ""
                l.line_statements = []
                l.expression = []
                l.ignore()
                return lex_markup

            l.error(f"unknown symbol '{l.next()}'")
            return None

        return next_state


# TODO: move to method of lexer
def accept_path(l: Lexer, *, carry: bool = False) -> None:
    l.path_stack.append(
        PathToken(
            type_=TokenType.PATH,
            path=[],
            start=l.start,
            stop=-1,
            source=l.source,
        )
    )

    if carry:
        l.path_stack[-1].path.append(l.source[l.start : l.pos])
        l.start = l.pos

    while True:
        c = l.next()

        if c == "":
            l.error("unexpected end of path")
            return

        if c == ".":
            l.ignore()
            l.ignore_whitespace()
            if match := RE_PROPERTY.match(l.source, l.pos):
                l.path_stack[-1].path.append(match.group())
                l.pos += len(match.group())
                l.start = l.pos
                l.path_stack[-1].stop = l.pos

        elif c == "]":  # TODO: handle empty brackets
            if len(l.path_stack) == 1:
                l.ignore()
                l.path_stack[0].stop = l.start
                return

            path = l.path_stack.pop()
            path.stop = l.start
            l.ignore()
            l.path_stack[-1].path.append(path)  # TODO: handle unbalanced brackets
            l.path_stack[-1].stop = l.pos

        elif c == "[":
            l.ignore()
            l.ignore_whitespace()

            if l.peek() in ("'", '"'):
                quote = l.next()
                l.ignore()
                accept_string(l, quote=quote)
                l.path_stack[-1].path.append(l.source[l.start : l.pos])
                l.next()
                l.ignore()  # skip closing quote

            elif match := RE_INDEX.match(l.source, l.pos):
                l.path_stack[-1].path.append(int(match.group()))
                l.pos += len(match.group())
                l.start = l.pos

            elif match := RE_PROPERTY.match(l.source, l.pos):
                # A nested path
                l.path_stack.append(
                    PathToken(
                        type_=TokenType.PATH,
                        path=[match.group()],
                        start=l.start,
                        stop=-1,  # TODO: fix span
                        source=l.source,
                    )
                )
                l.pos += len(match.group())
                l.start = l.pos
        else:
            l.backup()
            return


# TODO: move to method of Lexer
def accept_string(l: Lexer, *, quote: str) -> None:
    # Assumes the opening quote has been consumed.
    if l.peek() == quote:
        # an empty string
        # leave the closing quote for the caller
        return

    while True:
        c = l.next()

        if c == "\\":
            peeked = l.peek()
            if peeked in ESCAPES or peeked == quote:
                l.next()
            else:
                raise LiquidSyntaxError(
                    "invalid escape sequence",
                    token=ErrorToken(
                        type_=TokenType.ERROR,
                        index=l.pos,
                        value=peeked,
                        source=l.source,
                        message="invalid escape sequence",
                    ),
                )

        if c == quote:
            l.backup()
            return

        if not c:
            raise LiquidSyntaxError(
                "unclosed string literal",
                token=ErrorToken(
                    type_=TokenType.ERROR,
                    index=l.start,
                    value=l.source[l.start],
                    source=l.source,
                    message="unclosed string literal",
                ),
            )


def lex_range_factory(next_state: StateFn) -> StateFn:
    def _lex_range(l: Lexer) -> StateFn | None:
        # TODO: handle IndexError from pop
        rparen = l.expression.pop()
        assert is_token_type(rparen, TokenType.RPAREN)

        range_stop_token = l.expression.pop()
        if range_stop_token.type_ not in (
            TokenType.INT,
            TokenType.SINGLE_QUOTE_STRING,
            TokenType.DOUBLE_QUOTE_STRING,
            TokenType.PATH,
        ):
            # TODO: fix error index
            l.error(
                "expected an integer or variable to stop a range expression, "
                f"found {range_stop_token.type_.name}"
            )
            return None

        double_dot = l.expression.pop()
        if not is_token_type(double_dot, TokenType.DOUBLE_DOT):
            # TODO: fix error index
            l.error("malformed range expression")
            return None

        range_start_token = l.expression.pop()
        if range_start_token.type_ not in (
            TokenType.INT,
            TokenType.SINGLE_QUOTE_STRING,
            TokenType.DOUBLE_QUOTE_STRING,
            TokenType.PATH,
        ):
            # TODO: fix error index
            l.error(
                "expected an integer or variable to start a range expression, "
                f"found {range_start_token.type_.name}"
            )
            return None

        lparen = l.expression.pop()
        if not is_token_type(lparen, TokenType.LPAREN):
            # TODO: fix error index
            l.error("range expressions must be surrounded by parentheses")
            return None

        l.expression.append(
            RangeToken(
                type_=TokenType.RANGE,
                start=range_start_token,
                stop=range_stop_token,
                index=lparen.index,
                source=l.source,
            )
        )

        l.in_range = False
        return next_state

    return _lex_range


lex_range_inside_output_statement = lex_range_factory(lex_inside_output_statement)
lex_range_inside_tag_expression = lex_range_factory(lex_inside_tag)
lex_range_inside_line_statement = lex_range_factory(lex_inside_line_statement)


def tokenize(source: str) -> list[TokenT]:
    """Scan Liquid template _source_ and return a list of Markup objects."""
    lexer = Lexer(source)
    lexer.run()

    if lexer.markup:
        last_token = lexer.markup[-1]
        if isinstance(last_token, ErrorToken):
            raise LiquidSyntaxError(last_token.message, token=last_token)

    return lexer.markup
