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
from .query import parse_query
from .token import CommentToken
from .token import ContentToken
from .token import ErrorToken
from .token import LinesToken
from .token import OutputToken
from .token import QueryToken
from .token import RangeToken
from .token import RawToken
from .token import TagToken
from .token import Token
from .token import TokenType
from .token import WhitespaceControl
from .token import is_token_type

if TYPE_CHECKING:
    from .token import TokenT


RE_CONTENT = re.compile(r".+?(?=(\{\{|\{%|\{#+|$))", re.DOTALL)

RE_COMMENT = re.compile(
    r"\{(?P<hashes>#+)([\-+~]?)(.*)([\-+~]?)(?P=hashes)\}", re.DOTALL
)

RE_LINE_COMMENT = re.compile(r"\#.*?(?=(\n|[\-+~]?%\}))")

RE_RAW = re.compile(
    r"\{%([\-+~]?)\s*raw\s([\-+~]?)%\}(.*)\{%([\-+~]?)\s*endraw\s([\-+~]?)%\}",
    re.DOTALL,
)

RE_OUTPUT_END = re.compile(r"([+\-~]?)\}\}")
RE_TAG_END = re.compile(r"([+\-~]?)%\}")
RE_WHITESPACE_CONTROL = re.compile(r"[+\-~]")

RE_TAG_NAME = re.compile(r"[a-z][a-z_0-9]*\b")

RE_WHITESPACE = re.compile(r"[ \n\r\t]+")
RE_LINE_SPACE = re.compile(r"[ \t]+")
RE_LINE_TERM = re.compile(r"\r?\n")

RE_PROPERTY = re.compile(r"[\u0080-\uFFFFa-zA-Z_][\u0080-\uFFFFa-zA-Z0-9_-]*")
RE_INDEX = re.compile(r"-?[0-9]+")
RE_INT = re.compile(r"-?[0-9]+(?:[eE]\+?[0-9]+)?")
# RE_FLOAT includes numbers with a negative exponent and no decimal point.
RE_FLOAT = re.compile(r"(:?-?[0-9]+\.[0-9]+(?:[eE][+-]?[0-9]+)?)|(-?[0-9]+[eE]-[0-9]+)")
RE_FUNCTION_NAME = re.compile(r"[a-z][a-z_0-9]*")
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
    "RBRACKET": r"\]",
    # "NEWLINE": r"\r?\n",
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
    "ROOT": TokenType.ROOT,
    "LPAREN": TokenType.LPAREN,
    "RPAREN": TokenType.RPAREN,
    "SINGLE_QUOTE_STRING": TokenType.SINGLE_QUOTE_STRING,
    "DOUBLE_QUOTE_STRING": TokenType.DOUBLE_QUOTE_STRING,
    "COLON": TokenType.COLON,
    "COMMA": TokenType.COMMA,
    "PIPE": TokenType.PIPE,
    "LBRACKET": TokenType.LBRACKET,
    "RBRACKET": TokenType.RBRACKET,
    # "NEWLINE": TokenType.NEWLINE,
}

WC_MAP = {
    "": WhitespaceControl.DEFAULT,
    "-": WhitespaceControl.MINUS,
    "+": WhitespaceControl.PLUS,
    "~": WhitespaceControl.TILDE,
}

WC_DEFAULT = (WhitespaceControl.DEFAULT, WhitespaceControl.DEFAULT)

StateFn = Callable[["Lexer"], Optional["StateFn"]]


def _compile(*rules: dict[str, str]) -> Pattern[str]:
    _rules = chain.from_iterable(rule_set.items() for rule_set in rules)
    pattern = "|".join(f"(?P<{name}>{pattern})" for name, pattern in _rules)
    return re.compile(pattern)


RULES = _compile(NUMBERS, SYMBOLS, WORD)


class Lexer:
    """Liquid template lexical scanner."""

    __slots__ = (
        "query_tokens",
        "filter_depth",
        "in_range",
        "line_start",
        "line_statements",
        "markup",
        "markup_start",
        "paren_stack",
        "pos",
        "singular_query_depth",
        "source",
        "start",
        "tag_name",
        "tokens",
        "wc",
        "accept_output_token",
        "accept_tag_token",
        "accept_lines_token",
    )

    def __init__(self, source: str) -> None:
        self.filter_depth = 0
        """Filter nesting level."""

        self.singular_query_depth = 0
        """Singular query selector nesting level."""

        self.paren_stack: list[int] = []
        """A running count of parentheses for each, possibly nested, function call.
        
        If the stack is empty, we are not in a function call. Remember that
        function arguments can be arbitrarily nested in parentheses.
        """

        self.markup: list[TokenT] = []
        """Markup resulting from scanning a Liquid template."""

        self.tokens: list[TokenT] = []
        """Tokens from the current expression."""

        self.line_statements: list[TagToken | CommentToken] = []
        """Markup resulting from scanning a sequence of line statements."""

        self.query_tokens: list[Token] = []
        """Tokens from the current query."""

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
            single_quote_state=lex_single_quoted_string_inside_output_statement,
            double_quote_state=lex_double_quoted_string_inside_output_statement,
            range_state=lex_range_inside_output_statement,
            query_state=lex_query_inside_output_statement,
        )

        self.accept_tag_token = partial(
            self.accept_token,
            next_state=lex_inside_tag,
            single_quote_state=lex_single_quoted_string_inside_tag_expression,
            double_quote_state=lex_double_quoted_string_inside_tag_expression,
            range_state=lex_range_inside_tag_expression,
            query_state=lex_query_inside_tag_expression,
        )

        self.accept_lines_token = partial(
            self.accept_token,
            next_state=lex_inside_line_statement,
            single_quote_state=lex_single_quoted_string_inside_line_statement,
            double_quote_state=lex_double_quoted_string_inside_line_statement,
            range_state=lex_range_inside_line_statement,
            query_state=lex_query_inside_line_statement,
        )

    def run(self) -> None:
        """Populate _self.tokens_."""
        state: Optional[StateFn] = lex_markup
        while state is not None:
            state = state(self)

    def emit_token(self, t: TokenType) -> None:
        """Append a token of type _t_ to the output tokens list."""
        self.tokens.append(
            Token(
                type_=t,
                value=self.source[self.start : self.pos],
                index=self.start,
                source=self.source,
            )
        )
        self.start = self.pos

    def emit_query_token(self, t: TokenType) -> None:
        """Append a token of type _t_ to the output tokens list."""
        self.query_tokens.append(
            Token(
                type_=t,
                value=self.source[self.start : self.pos],
                index=self.start,
                source=self.source,
            )
        )
        self.start = self.pos

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

    def accept_and_emit_content(self) -> bool:
        match = RE_CONTENT.match(self.source, self.pos)
        if match:
            self.pos += len(match.group(0))
            self.markup.append(
                ContentToken(
                    type_=TokenType.CONTENT,
                    start=self.start,
                    stop=self.pos,
                    text=match.group(0),
                )
            )
            self.start = self.pos
            return True
        return False

    def accept_and_emit_raw(self) -> bool:
        match = RE_RAW.match(self.source, self.pos)
        if match:
            self.pos += len(match.group(0))
            self.markup.append(
                RawToken(
                    type_=TokenType.RAW,
                    start=self.start,
                    stop=self.pos,
                    wc=(
                        WC_MAP[match.group(1)],
                        WC_MAP[match.group(2)],
                        WC_MAP[match.group(4)],
                        WC_MAP[match.group(5)],
                    ),
                    text=match.group(3),
                )
            )
            self.start = self.pos
            return True
        return False

    def accept_and_emit_comment(self) -> bool:
        match = RE_COMMENT.match(self.source, self.pos)
        if match:
            self.pos += len(match.group(0))
            self.markup.append(
                CommentToken(
                    type_=TokenType.COMMENT,
                    start=self.start,
                    stop=self.pos,
                    wc=(
                        WC_MAP[match.group(2)],
                        WC_MAP[match.group(4)],
                    ),
                    text=match.group(3),
                    hashes=match.group(1),
                )
            )
            self.start = self.pos
            return True
        return False

    def accept_end_output_statement(self) -> bool:
        """Accepts the output end sequence, possibly preceded by whitespace control."""
        match = RE_OUTPUT_END.match(self.source, self.pos)
        if match:
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
        match = RE_TAG_END.match(self.source, self.pos)
        if match:
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
        single_quote_state: StateFn,
        double_quote_state: StateFn,
        range_state: StateFn,
        query_state: StateFn,
    ) -> StateFn | None | Literal[False]:
        match = RULES.match(self.source, pos=self.pos)

        if not match:
            return False

        kind = match.lastgroup
        assert kind is not None

        value = match.group()
        self.pos += len(value)

        if kind == "SINGLE_QUOTE_STRING":
            return single_quote_state

        if kind == "DOUBLE_QUOTE_STRING":
            return double_quote_state

        if kind == "ROOT":
            self.ignore()
            return query_state

        if kind == "LBRACKET":
            self.backup()
            return query_state

        if kind == "WORD":
            if self.peek() in (".", "["):
                self.query_tokens.append(
                    Token(
                        type_=TokenType.PROPERTY,
                        value=value,
                        index=self.start,
                        source=self.source,
                    )
                )
                self.start = self.pos
                return query_state

            if token_type := KEYWORD_MAP.get(value):
                self.tokens.append(
                    Token(
                        type_=token_type,
                        value=value,
                        index=self.start,
                        source=self.source,
                    )
                )
            else:
                self.tokens.append(
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
            self.tokens.append(
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
        assert not l.tokens  # current expression should be empty
        assert not l.query_tokens, str(l.query_tokens)  # current query should be empty
        assert not l.tag_name  # current tag name should be empty

        # TODO: replace accept_and_emit_* with direct match and append
        # TODO: .. with integrated whitespace control

        if l.accept_and_emit_raw():
            continue

        if l.accept(r"{{"):
            l.markup_start = l.start
            l.ignore()
            return lex_output_statement

        if l.accept(r"{%"):
            l.markup_start = l.start
            l.ignore()
            return lex_tag

        if l.accept_and_emit_comment():
            continue

        if l.accept_and_emit_content():
            continue

        return None


def lex_output_statement(l: Lexer) -> StateFn | None:
    if l.accept_match(RE_WHITESPACE_CONTROL):
        l.wc.append(WC_MAP[l.source[l.start]])
        l.ignore()
    else:
        l.wc.append(WhitespaceControl.DEFAULT)

    return lex_inside_output_statement


def lex_inside_output_statement(l: Lexer) -> StateFn | None:  # noqa: PLR0911, PLR0912, PLR0915
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
                        expression=l.tokens,
                    )
                )
                l.wc = []
                l.tokens = []
                l.ignore()
                return lex_markup

            l.error(f"unknown symbol '{l.next()}'")
            return None

        return next_state


def lex_tag(l: Lexer) -> StateFn | None:
    if l.accept_match(RE_WHITESPACE_CONTROL):
        l.wc.append(WC_MAP[l.source[l.start]])
        l.ignore()
    else:
        l.wc.append(WhitespaceControl.DEFAULT)

    l.ignore_whitespace()

    if l.accept_match(RE_TAG_NAME):
        l.tag_name = l.source[l.start : l.pos]
        l.ignore()
    else:
        c = l.next()
        l.error(f"expected a tag name, found {c!r}")
        return None

    if l.tag_name == "liquid":
        return lex_inside_liquid_tag
    return lex_inside_tag


def lex_inside_tag(l: Lexer) -> StateFn | None:  # noqa: PLR0911, PLR0912, PLR0915
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
                        expression=l.tokens,
                    )
                )
                l.wc = []
                l.tag_name = ""
                l.tokens = []
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

        l.wc = []
        l.tag_name = ""
        l.line_statements = []
        l.tokens = []
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


def lex_inside_line_statement(l: Lexer) -> StateFn | None:  # noqa: PLR0911, PLR0912, PLR0915
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
                    expression=l.tokens,
                )
            )
            l.tag_name = ""
            l.tokens = []
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
                        expression=l.tokens,
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
                l.tokens = []
                l.ignore()
                return lex_markup

            l.error(f"unknown symbol '{l.next()}'")
            return None

        return next_state


def lex_root(l: Lexer) -> Optional[StateFn]:  # noqa: D103
    c = l.next()

    if c != "$":
        l.error(f"expected '$', found {c!r}")
        return None

    l.emit_query_token(TokenType.ROOT)
    return lex_segment


def lex_segment(l: Lexer) -> Optional[StateFn]:  # noqa: D103, PLR0911
    l.ignore_whitespace()
    c = l.next()

    if c == "":
        # l.error("unexpected end of query")
        return None

    if c == ".":
        if l.peek() == ".":
            l.next()
            l.emit_query_token(TokenType.DOUBLE_DOT)
            return lex_descendant_segment
        return lex_shorthand_selector

    if c == "[":
        l.emit_query_token(TokenType.LBRACKET)
        return lex_inside_bracketed_segment

    if l.filter_depth:
        l.backup()
        return lex_inside_filter

    l.backup()
    return None


def lex_descendant_segment(l: Lexer) -> Optional[StateFn]:
    c = l.next()

    if c == "":
        l.error("bald descendant segment")
        return None

    if c == "*":
        l.emit_query_token(TokenType.WILD)
        return lex_segment

    if c == "[":
        l.emit_query_token(TokenType.LBRACKET)
        return lex_inside_bracketed_segment

    l.backup()

    if l.accept_match(RE_PROPERTY):
        l.emit_query_token(TokenType.PROPERTY)
        return lex_segment

    l.next()
    l.error(f"unexpected descendant selection token {c!r}")
    return None


def lex_shorthand_selector(l: Lexer) -> Optional[StateFn]:  # noqa: D103
    l.ignore()  # ignore dot

    if l.accept_match(RE_WHITESPACE):
        l.error("unexpected whitespace after dot")
        return None

    c = l.next()

    if c == "*":
        l.emit_query_token(TokenType.WILD)
        return lex_segment

    l.backup()

    if l.accept_match(RE_PROPERTY):
        l.emit_query_token(TokenType.PROPERTY)
        return lex_segment

    l.error(f"unexpected shorthand selector {c!r}")
    return None


def lex_inside_bracketed_segment(l: Lexer) -> Optional[StateFn]:  # noqa: D103, PLR0911, PLR0912
    while True:
        l.ignore_whitespace()
        c = l.next()

        if c == "]":
            l.emit_query_token(TokenType.RBRACKET)
            if l.filter_depth:
                return lex_inside_filter
            return lex_segment

        if c == "":
            l.error("unclosed bracketed selection")
            return None

        if c == "*":
            l.emit_query_token(TokenType.WILD)
            continue

        if c == "?":
            l.emit_query_token(TokenType.FILTER)
            l.filter_depth += 1
            return lex_inside_filter

        if c == ",":
            l.emit_query_token(TokenType.COMMA)
            continue

        if c == ":":
            l.emit_query_token(TokenType.COLON)
            continue

        if c == "'":
            # Quoted dict/object key/property name
            return lex_single_quoted_string_inside_bracket_segment

        if c == '"':
            # Quoted dict/object key/property name
            return lex_double_quoted_string_inside_bracket_segment

        # default
        l.backup()

        if l.accept_match(RE_INDEX):
            # Index selector or part of a slice selector.
            l.emit_query_token(TokenType.INDEX)
            continue

        if c == "[":
            return lex_inside_singular_query

        if l.accept_match(RE_PROPERTY):
            l.emit_query_token(TokenType.PROPERTY)
            return lex_inside_singular_query

        l.error(f"unexpected token {c!r} in bracketed selection")
        return None


def lex_inside_filter(l: Lexer) -> Optional[StateFn]:  # noqa: D103, PLR0915, PLR0912, PLR0911
    while True:
        l.ignore_whitespace()
        c = l.next()

        if c == "":
            l.error("unclosed bracketed selection")
            return None

        if c == "]":
            l.filter_depth -= 1
            if len(l.paren_stack) == 1:
                l.error("unbalanced parentheses")
                return None

            l.backup()
            return lex_inside_bracketed_segment

        if c == ",":
            l.emit_query_token(TokenType.COMMA)
            # If we have unbalanced parens, we are inside a function call and a
            # comma separates arguments. Otherwise a comma separates selectors.
            if l.paren_stack:
                continue
            l.filter_depth -= 1
            return lex_inside_bracketed_segment

        if c == "'":
            return lex_single_quoted_string_inside_filter_expression

        if c == '"':
            return lex_double_quoted_string_inside_filter_expression

        if c == "(":
            l.emit_query_token(TokenType.LPAREN)
            # Are we in a function call? If so, a function argument contains parens.
            if l.paren_stack:
                l.paren_stack[-1] += 1
            continue

        if c == ")":
            l.emit_query_token(TokenType.RPAREN)
            # Are we closing a function call or a parenthesized expression?
            if l.paren_stack:
                if l.paren_stack[-1] == 1:
                    l.paren_stack.pop()
                else:
                    l.paren_stack[-1] -= 1
            continue

        if c == "$":
            l.emit_query_token(TokenType.ROOT)
            return lex_segment

        if c == "@":
            l.emit_query_token(TokenType.CURRENT)
            return lex_segment

        if c == ".":
            l.backup()
            return lex_segment

        if c == "!":
            if l.peek() == "=":
                l.next()
                l.emit_query_token(TokenType.NE)
            else:
                l.emit_query_token(TokenType.NOT)
            continue

        if c == "=":
            if l.peek() == "=":
                l.next()
                l.emit_query_token(TokenType.EQ)
                continue

            l.backup()
            l.error(f"unexpected filter selector token {c!r}")
            return None

        if c == "<":
            if l.peek() == "=":
                l.next()
                l.emit_query_token(TokenType.LE)
            else:
                l.emit_query_token(TokenType.LT)
            continue

        if c == ">":
            if l.peek() == "=":
                l.next()
                l.emit_query_token(TokenType.GE)
            else:
                l.emit_query_token(TokenType.GT)
            continue

        l.backup()

        if l.accept("&&"):
            l.emit_query_token(TokenType.AND)
        elif l.accept("||"):
            l.emit_query_token(TokenType.OR)
        elif l.accept("true"):
            l.emit_query_token(TokenType.TRUE)
        elif l.accept("false"):
            l.emit_query_token(TokenType.FALSE)
        elif l.accept("null"):
            l.emit_query_token(TokenType.NULL)
        elif l.accept_match(RE_FLOAT):
            l.emit_query_token(TokenType.FLOAT)
        elif l.accept_match(RE_INT):
            l.emit_query_token(TokenType.INT)
        elif l.accept_match(RE_FUNCTION_NAME) and l.peek() == "(":
            # Keep track of parentheses for this function call.
            l.paren_stack.append(1)
            l.emit_query_token(TokenType.FUNCTION)
            l.next()
            l.ignore()  # ignore LPAREN
        else:
            l.error(f"unexpected filter selector token {c!r}")
            return None


def lex_inside_singular_query(l: Lexer) -> StateFn | None:  # noqa: PLR0911, PLR0912
    while True:
        l.ignore_whitespace()
        c = l.next()

        if c == "]":
            if l.singular_query_depth:
                l.emit_query_token(TokenType.RBRACKET)
                l.singular_query_depth -= 1
                continue

            l.backup()
            return lex_inside_bracketed_segment

        if c == "":
            l.error("unclosed singular query selector")
            return None

        if c == ".":
            l.ignore()
            if l.accept_match(RE_WHITESPACE):
                l.error("unexpected whitespace after dot")
                return None

            if l.accept_match(RE_PROPERTY):
                l.emit_query_token(TokenType.PROPERTY)
            else:
                l.error("trailing dot in singular query selector")
                return None

        elif c == "[":
            l.ignore()
            l.ignore_whitespace()

            if l.peek() == "'":
                # We're relying on lex_.. to check for closing square bracket.
                return lex_single_quoted_string_inside_singular_query

            if l.peek() == '"':
                return lex_double_quoted_string_inside_singular_query

            if l.accept_match(RE_INDEX):
                l.emit_query_token(TokenType.INDEX)
            elif l.accept_match(RE_PROPERTY):
                l.emit_query_token(TokenType.PROPERTY)
                l.singular_query_depth += 1

            if not l.accept("]"):
                l.error("unclosed singular query selector")
                return None

            l.ignore()  # skip "]"


def lex_string_factory(
    quote: str,
    state: StateFn,
    *,
    inside_query: bool = False,
    inside_singular_query: bool = False,
) -> StateFn:
    """Return a state function for scanning string literals.

    Arguments:
        quote: One of `'` or `"`. The string delimiter.
        state: The state function to return control to after scanning the string.
        inside_query: Indicate if we're emitting from inside a query.
        inside_singular_query: Indicate if we're scanning a string from a singular query
            selector.
    """
    tt = (
        TokenType.SINGLE_QUOTE_STRING if quote == "'" else TokenType.DOUBLE_QUOTE_STRING
    )

    def _lex_string(l: Lexer) -> Optional[StateFn]:
        l.ignore()  # ignore opening quote

        if l.peek() == "":
            # an empty string
            l.emit_query_token(tt) if inside_query else l.emit_token(tt)
            l.next()
            l.ignore()
            return state

        while True:
            c = l.next()

            if c == "\\":
                peeked = l.peek()
                if peeked in ESCAPES or peeked == quote:
                    l.next()
                else:
                    l.error("invalid escape")
                    return None

            if not c:
                l.error(f"unclosed string starting at index {l.start}")
                return None

            if c == quote:
                l.backup()
                l.emit_query_token(tt) if inside_query else l.emit_token(tt)
                l.next()
                l.ignore()  # ignore closing quote
                if inside_singular_query:
                    l.ignore_whitespace()
                    if not l.accept("]"):
                        l.error("unclosed singular query selector")
                        return None
                return state

    return _lex_string


lex_single_quoted_string_inside_bracket_segment = lex_string_factory(
    "'", lex_inside_bracketed_segment, inside_query=True
)

lex_double_quoted_string_inside_bracket_segment = lex_string_factory(
    '"', lex_inside_bracketed_segment, inside_query=True
)

lex_single_quoted_string_inside_singular_query = lex_string_factory(
    "'",
    lex_inside_singular_query,
    inside_query=True,
    inside_singular_query=True,
)

lex_double_quoted_string_inside_singular_query = lex_string_factory(
    '"',
    lex_inside_singular_query,
    inside_query=True,
    inside_singular_query=True,
)

lex_single_quoted_string_inside_filter_expression = lex_string_factory(
    "'", lex_inside_filter, inside_query=True
)

lex_double_quoted_string_inside_filter_expression = lex_string_factory(
    '"', lex_inside_filter, inside_query=True
)

lex_single_quoted_string_inside_output_statement = lex_string_factory(
    "'", lex_inside_output_statement
)

lex_double_quoted_string_inside_output_statement = lex_string_factory(
    '"', lex_inside_output_statement
)

lex_single_quoted_string_inside_tag_expression = lex_string_factory("'", lex_inside_tag)

lex_double_quoted_string_inside_tag_expression = lex_string_factory('"', lex_inside_tag)

lex_single_quoted_string_inside_line_statement = lex_string_factory(
    "'", lex_inside_line_statement
)

lex_double_quoted_string_inside_line_statement = lex_string_factory(
    '"', lex_inside_line_statement
)


def lex_query_factory(next_state: StateFn) -> StateFn:
    def _lex_query(l: Lexer) -> StateFn | None:
        state: Optional[StateFn] = lex_segment
        while state is not None:
            state = state(l)

        if l.markup and l.markup[-1].type_ == TokenType.ERROR:
            return None

        l.tokens.append(
            QueryToken(
                type_=TokenType.QUERY,
                path=parse_query(l.query_tokens),
                start=l.query_tokens[0].index,
                stop=l.pos - 1,
                source=l.source,
            )
        )

        l.query_tokens = []
        return next_state

    return _lex_query


lex_query_inside_output_statement = lex_query_factory(lex_inside_output_statement)
lex_query_inside_tag_expression = lex_query_factory(lex_inside_tag)
lex_query_inside_line_statement = lex_query_factory(lex_inside_line_statement)


def lex_range_factory(next_state: StateFn) -> StateFn:
    def _lex_range(l: Lexer) -> StateFn | None:
        # TODO: handle IndexError from pop
        rparen = l.tokens.pop()
        assert is_token_type(rparen, TokenType.RPAREN)

        range_stop_token = l.tokens.pop()
        if range_stop_token.type_ not in (
            TokenType.INT,
            TokenType.SINGLE_QUOTE_STRING,
            TokenType.DOUBLE_QUOTE_STRING,
            TokenType.QUERY,
        ):
            # TODO: fix error index
            l.error(
                "expected an integer or variable to stop a range expression, "
                f"found {range_stop_token.type_.name}"
            )
            return None

        dotdot = l.tokens.pop()
        if not is_token_type(dotdot, TokenType.DOUBLE_DOT):
            # TODO: fix error index
            l.error("malformed range expression")
            return None

        range_start_token = l.tokens.pop()
        if range_start_token.type_ not in (
            TokenType.INT,
            TokenType.SINGLE_QUOTE_STRING,
            TokenType.DOUBLE_QUOTE_STRING,
            TokenType.QUERY,
        ):
            # TODO: fix error index
            l.error(
                "expected an integer or variable to start a range expression, "
                f"found {range_start_token.type_.name}"
            )
            return None

        lparen = l.tokens.pop()
        if not is_token_type(lparen, TokenType.LPAREN):
            # TODO: fix error index
            l.error("range expressions must be surrounded by parentheses")
            return None

        l.tokens.append(
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


def tokenize_query(query: str) -> list[Token]:
    l = Lexer(query)

    state: Optional[StateFn] = lex_root
    while state is not None:
        state = state(l)

    if c := l.next():
        l.error(f"expected '.', '..' or a bracketed selection, found {c!r}")

    if l.markup:
        last_token = l.markup[-1]
        if isinstance(last_token, ErrorToken):
            raise LiquidSyntaxError(last_token.message, token=last_token)

    return l.query_tokens
