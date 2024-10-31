"""JSONPath expression lexical scanner."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from typing import Callable
from typing import Optional
from typing import Pattern

from .exceptions import LiquidSyntaxError
from .query import parse
from .token import Comment
from .token import Content
from .token import Lines
from .token import Output
from .token import Raw
from .token import Tag
from .token import Token
from .token import TokenType
from .token import WhitespaceControl

if TYPE_CHECKING:
    from .query import JSONPathQuery
    from .token import Markup


RE_CONTENT = re.compile(r".+?(?=(\{\{|\{%|\{#+|$))", re.DOTALL)

RE_COMMENT = re.compile(
    r"\{(?P<hashes>#+)([\-+~]?)(.*)([\-+~]?)(?P=hashes)\}", re.DOTALL
)

RE_RAW = re.compile(
    r"\{%([\-+~]?)\s*raw\s([\-+~]?)%\}(.*)\{%([\-+~]?)\s*endraw\s([\-+~]?)%\}",
    re.DOTALL,
)


RE_OUTPUT_END = re.compile(r"([+\-~]?)\}\}")
RE_TAG_END = re.compile(r"([+\-~]?)%\}")
RE_WHITESPACE_CONTROL = re.compile(r"[+\-~]")

RE_TRUE = re.compile(r"\btrue\b")
RE_FALSE = re.compile(r"\bfalse\b")
RE_AND = re.compile(r"\band\b")
RE_OR = re.compile(r"\bor\b")
RE_IN = re.compile(r"\bin\b")
RE_NOT = re.compile(r"\bnot\b")
RE_CONTAINS = re.compile(r"\bcontains\b")
RE_NIL = re.compile(r"\bnil\b")
RE_NULL = re.compile(r"\bnull\b")
RE_IF = re.compile(r"\bif\b")
RE_ELSE = re.compile(r"\belse\b")
RE_WITH = re.compile(r"\bwith\b")
RE_REQUIRED = re.compile(r"\brequired\b")
RE_AS = re.compile(r"\bas\b")
RE_FOR = re.compile(r"\bfor\b")

RE_WORD = re.compile(r"[\u0080-\uFFFFa-zA-Z_][\u0080-\uFFFFa-zA-Z0-9_-]*")
RE_TAG_NAME = re.compile(r"\b[a-z][a-z_0-9]*\b")

RE_WHITESPACE = re.compile(r"[ \n\r\t]+")
RE_LINE_SPACE = re.compile(r"[ \t]+")

RE_PROPERTY = re.compile(r"[\u0080-\uFFFFa-zA-Z_][\u0080-\uFFFFa-zA-Z0-9_-]*")
RE_INDEX = re.compile(r"-?[0-9]+")
RE_INT = re.compile(r"-?[0-9]+(?:[eE]\+?[0-9]+)?")
# RE_FLOAT includes numbers with a negative exponent and no decimal point.
RE_FLOAT = re.compile(r"(:?-?[0-9]+\.[0-9]+(?:[eE][+-]?[0-9]+)?)|(-?[0-9]+[eE]-[0-9]+)")
RE_FUNCTION_NAME = re.compile(r"[a-z][a-z_0-9]*")
ESCAPES = frozenset(["b", "f", "n", "r", "t", "u", "/", "\\"])

WC_MAP = {
    "": WhitespaceControl.DEFAULT,
    "-": WhitespaceControl.MINUS,
    "+": WhitespaceControl.PLUS,
    "~": WhitespaceControl.TILDE,
}

WC_DEFAULT = (WhitespaceControl.DEFAULT, WhitespaceControl.DEFAULT)

StateFn = Callable[["Lexer"], Optional["StateFn"]]


class Lexer:
    """Liquid template lexical scanner."""

    __slots__ = (
        "query_tokens",
        "filter_depth",
        "line_start",
        "line_statements",
        "markup",
        "markup_start",
        "paren_stack",
        "pos",
        "source",
        "start",
        "tag_name",
        "tokens",
        "wc",
    )

    def __init__(self, source: str) -> None:
        self.filter_depth = 0
        """Filter nesting level."""

        self.paren_stack: list[int] = []
        """A running count of parentheses for each, possibly nested, function call.
        
        If the stack is empty, we are not in a function call. Remember that
        function arguments can be arbitrarily nested in parentheses.
        """

        self.markup: list[Markup] = []
        """Markup resulting from scanning a Liquid template."""

        self.tokens: list[Token | JSONPathQuery] = []
        """Tokens from the current expression."""

        self.line_statements: list[Tag | Comment] = []
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

        self.source = source
        """The template source text being scanned."""

    def run(self) -> None:
        """Populate _self.tokens_."""
        state: Optional[StateFn] = lex_markup
        while state is not None:
            state = state(self)

    def emit_token(self, t: TokenType) -> None:
        """Append a token of type _t_ to the output tokens list."""
        self.tokens.append(
            Token(
                t,
                self.source[self.start : self.pos],
                self.start,
                self.source,
            )
        )
        self.start = self.pos

    def emit_query_token(self, t: TokenType) -> None:
        """Append a token of type _t_ to the output tokens list."""
        self.query_tokens.append(
            Token(
                t,
                self.source[self.start : self.pos],
                self.start,
                self.source,
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
                msg, token=Token(TokenType.ERROR, msg, self.pos, self.source)
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
                Content(
                    self.start,
                    self.pos,
                    match.group(0),
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
                Raw(
                    self.start,
                    self.pos,
                    (
                        WC_MAP[match.group(1)],
                        WC_MAP[match.group(2)],
                        WC_MAP[match.group(4)],
                        WC_MAP[match.group(5)],
                    ),
                    match.group(3),
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
                Comment(
                    self.start,
                    self.pos,
                    (
                        WC_MAP[match.group(2)],
                        WC_MAP[match.group(4)],
                    ),
                    match.group(3),
                    match.group(1),
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
        self.tokens.append(
            Token(
                TokenType.ERROR,
                self.source[self.start : self.pos],
                self.start,
                self.source,
                msg,
            )
        )


def lex_markup(l: Lexer) -> StateFn | None:
    while True:
        assert not l.tokens  # current expression should be empty
        assert not l.query_tokens, str(l.query_tokens)  # current query should be empty
        assert not l.tag_name  # current tag name should be empty

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

        assert l.pos == len(l.source), f"{l.pos} != {len(l.source)}"
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

        if l.accept_end_output_statement():
            l.markup.append(
                Output(
                    l.markup_start,
                    l.pos,
                    (l.wc[0], l.wc[1]),
                    l.tokens,
                )
            )
            l.wc = []
            l.tokens = []
            l.ignore()
            return lex_markup

        if l.accept_match(RE_TRUE):
            l.emit_token(TokenType.TRUE)
        elif l.accept_match(RE_FALSE):
            l.emit_token(TokenType.FALSE)
        elif l.accept_match(RE_AND):
            l.emit_token(TokenType.AND_WORD)
        elif l.accept_match(RE_OR):
            l.emit_token(TokenType.OR_WORD)
        elif l.accept_match(RE_IN):
            l.emit_token(TokenType.IN)
        elif l.accept_match(RE_NOT):
            l.emit_token(TokenType.NOT_WORD)
        elif l.accept_match(RE_CONTAINS):
            l.emit_token(TokenType.CONTAINS)
        elif l.accept_match(RE_NULL) or l.accept_match(RE_NIL):
            l.emit_token(TokenType.NULL)
        elif l.accept_match(RE_IF):
            l.emit_token(TokenType.IF)
        elif l.accept_match(RE_ELSE):
            l.emit_token(TokenType.ELSE)
        elif l.accept_match(RE_WITH):
            l.emit_token(TokenType.WITH)
        elif l.accept_match(RE_REQUIRED):
            l.emit_token(TokenType.REQUIRED)
        elif l.accept_match(RE_AS):
            l.emit_token(TokenType.AS)
        elif l.accept_match(RE_FOR):
            l.emit_token(TokenType.FOR)
        elif l.accept_match(RE_WORD):
            peeked = l.peek()
            if peeked == "." or peeked == "[":  # noqa: PLR1714
                l.emit_query_token(TokenType.PROPERTY)
                return lex_query_inside_output_statement
            l.emit_token(TokenType.WORD)
        elif l.accept_match(RE_FLOAT):
            l.emit_token(TokenType.FLOAT)
        elif l.accept_match(RE_INT):
            l.emit_token(TokenType.INT)
        elif l.accept(">="):
            l.emit_token(TokenType.GE)
        elif l.accept("<="):
            l.emit_token(TokenType.LE)
        elif l.accept("=="):
            l.emit_token(TokenType.EQ)
        elif l.accept("!=") or l.accept("<>"):
            l.emit_token(TokenType.NOT_WORD)
        elif l.accept(".."):
            l.emit_token(TokenType.DOUBLE_DOT)
        elif l.accept("||"):
            l.emit_token(TokenType.DOUBLE_PIPE)
        else:
            c = l.next()

            if c == "'":
                return lex_single_quoted_string_inside_output_statement
            if c == '"':
                return lex_double_quoted_string_inside_output_statement
            if c == "(":
                l.emit_token(TokenType.LPAREN)
            elif c == ")":
                l.emit_token(TokenType.RPAREN)
            elif c == "<":
                l.emit_token(TokenType.LT)
            elif c == ">":
                l.emit_token(TokenType.GT)
            elif c == ":":
                l.emit_token(TokenType.COLON)
            elif c == ",":
                l.emit_token(TokenType.COMMA)
            elif c == "|":
                l.emit_token(TokenType.PIPE)
            elif c == "=":
                l.emit_token(TokenType.ASSIGN)
            elif c == "$":
                l.ignore()
                return lex_query_inside_output_statement
            elif c == "[":
                return lex_query_inside_output_statement

            l.error(f"unknown symbol '{c}'")
            return None


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

        if l.accept_end_tag():
            l.markup.append(
                Tag(
                    l.markup_start,
                    l.pos,
                    (l.wc[0], l.wc[1]),
                    l.tag_name,
                    l.tokens,
                )
            )
            l.wc = []
            l.tag_name = ""
            l.tokens = []
            l.ignore()
            return lex_markup

        if l.accept_match(RE_TRUE):
            l.emit_token(TokenType.TRUE)
        elif l.accept_match(RE_FALSE):
            l.emit_token(TokenType.FALSE)
        elif l.accept_match(RE_AND):
            l.emit_token(TokenType.AND_WORD)
        elif l.accept_match(RE_OR):
            l.emit_token(TokenType.OR_WORD)
        elif l.accept_match(RE_IN):
            l.emit_token(TokenType.IN)
        elif l.accept_match(RE_NOT):
            l.emit_token(TokenType.NOT_WORD)
        elif l.accept_match(RE_CONTAINS):
            l.emit_token(TokenType.CONTAINS)
        elif l.accept_match(RE_NULL) or l.accept_match(RE_NIL):
            l.emit_token(TokenType.NULL)
        elif l.accept_match(RE_IF):
            l.emit_token(TokenType.IF)
        elif l.accept_match(RE_ELSE):
            l.emit_token(TokenType.ELSE)
        elif l.accept_match(RE_WITH):
            l.emit_token(TokenType.WITH)
        elif l.accept_match(RE_REQUIRED):
            l.emit_token(TokenType.REQUIRED)
        elif l.accept_match(RE_AS):
            l.emit_token(TokenType.AS)
        elif l.accept_match(RE_FOR):
            l.emit_token(TokenType.FOR)
        elif l.accept_match(RE_WORD):
            peeked = l.peek()
            if peeked == "." or peeked == "[":  # noqa: PLR1714
                l.emit_query_token(TokenType.PROPERTY)
                return lex_query_inside_tag_expression
            l.emit_token(TokenType.WORD)
        elif l.accept_match(RE_FLOAT):
            l.emit_token(TokenType.FLOAT)
        elif l.accept_match(RE_INT):
            l.emit_token(TokenType.INT)
        elif l.accept(">="):
            l.emit_token(TokenType.GE)
        elif l.accept("<="):
            l.emit_token(TokenType.LE)
        elif l.accept("=="):
            l.emit_token(TokenType.EQ)
        elif l.accept("!=") or l.accept("<>"):
            l.emit_token(TokenType.NOT_WORD)
        elif l.accept(".."):
            l.emit_token(TokenType.DOUBLE_DOT)
        elif l.accept("||"):
            l.emit_token(TokenType.DOUBLE_PIPE)
        else:
            c = l.next()

            if c == "'":
                return lex_single_quoted_string_inside_tag_expression

            if c == '"':
                return lex_double_quoted_string_inside_tag_expression

            if c == "(":
                l.emit_token(TokenType.LPAREN)
            elif c == ")":
                l.emit_token(TokenType.RPAREN)
            elif c == "<":
                l.emit_token(TokenType.LT)
            elif c == ">":
                l.emit_token(TokenType.GT)
            elif c == ":":
                l.emit_token(TokenType.COLON)
            elif c == ",":
                l.emit_token(TokenType.COMMA)
            elif c == "|":
                l.emit_token(TokenType.PIPE)
            elif c == "=":
                l.emit_token(TokenType.ASSIGN)
            elif c == "$":
                l.ignore()
                return lex_query_inside_tag_expression
            elif c == "[":
                return lex_query_inside_tag_expression
            else:
                l.error(f"unknown symbol '{c}'")
                return None


def lex_inside_liquid_tag(l: Lexer) -> StateFn | None:
    l.ignore_whitespace()

    if l.accept_end_tag():
        l.markup.append(
            Lines(
                l.markup_start,
                l.pos,
                (l.wc[0], l.wc[1]),
                "liquid",
                l.line_statements,
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
    else:
        l.next()
        l.error("expected a tag name")
        return None

    return lex_inside_line_statement


def lex_inside_line_statement(l: Lexer) -> StateFn | None:  # noqa: PLR0911, PLR0912, PLR0915
    while True:
        l.ignore_line_space()

        if l.accept_end_tag():
            l.ignore()
            l.line_statements.append(
                Tag(
                    l.line_start,
                    l.pos,
                    WC_DEFAULT,
                    l.tag_name,
                    l.tokens,
                )
            )

            l.markup.append(
                Lines(
                    l.markup_start,
                    l.pos,
                    (l.wc[0], l.wc[1]),
                    "liquid",
                    l.line_statements,
                )
            )

            l.wc = []
            l.tag_name = ""
            l.line_statements = []
            l.tokens = []
            l.ignore()
            return lex_markup

        if l.accept_match(RE_TRUE):
            l.emit_token(TokenType.TRUE)
        elif l.accept_match(RE_FALSE):
            l.emit_token(TokenType.FALSE)
        elif l.accept_match(RE_AND):
            l.emit_token(TokenType.AND_WORD)
        elif l.accept_match(RE_OR):
            l.emit_token(TokenType.OR_WORD)
        elif l.accept_match(RE_IN):
            l.emit_token(TokenType.IN)
        elif l.accept_match(RE_NOT):
            l.emit_token(TokenType.NOT_WORD)
        elif l.accept_match(RE_CONTAINS):
            l.emit_token(TokenType.CONTAINS)
        elif l.accept_match(RE_NULL) or l.accept_match(RE_NIL):
            l.emit_token(TokenType.NULL)
        elif l.accept_match(RE_IF):
            l.emit_token(TokenType.IF)
        elif l.accept_match(RE_ELSE):
            l.emit_token(TokenType.ELSE)
        elif l.accept_match(RE_WITH):
            l.emit_token(TokenType.WITH)
        elif l.accept_match(RE_REQUIRED):
            l.emit_token(TokenType.REQUIRED)
        elif l.accept_match(RE_AS):
            l.emit_token(TokenType.AS)
        elif l.accept_match(RE_FOR):
            l.emit_token(TokenType.FOR)
        elif l.accept_match(RE_WORD):
            peeked = l.peek()
            if peeked == "." or peeked == "[":  # noqa: PLR1714
                l.emit_query_token(TokenType.PROPERTY)
                return lex_query_inside_line_statement
            l.emit_token(TokenType.WORD)
        elif l.accept_match(RE_FLOAT):
            l.emit_token(TokenType.FLOAT)
        elif l.accept_match(RE_INT):
            l.emit_token(TokenType.INT)
        elif l.accept(">="):
            l.emit_token(TokenType.GE)
        elif l.accept("<="):
            l.emit_token(TokenType.LE)
        elif l.accept("=="):
            l.emit_token(TokenType.EQ)
        elif l.accept("!=") or l.accept("<>"):
            l.emit_token(TokenType.NOT_WORD)
        elif l.accept(".."):
            l.emit_token(TokenType.DOUBLE_DOT)
        elif l.accept("||"):
            l.emit_token(TokenType.DOUBLE_PIPE)
        else:
            c = l.next()

            if c == "'":
                return lex_single_quoted_string_inside_line_statement

            if c == '"':
                return lex_double_quoted_string_inside_line_statement

            if c == "(":
                l.emit_token(TokenType.LPAREN)
            elif c == ")":
                l.emit_token(TokenType.RPAREN)
            elif c == "<":
                l.emit_token(TokenType.LT)
            elif c == ">":
                l.emit_token(TokenType.GT)
            elif c == ":":
                l.emit_token(TokenType.COLON)
            elif c == ",":
                l.emit_token(TokenType.COMMA)
            elif c == "|":
                l.emit_token(TokenType.PIPE)
            elif c == "=":
                l.emit_token(TokenType.ASSIGN)
            elif c == "$":
                l.ignore()
                return lex_query_inside_line_statement
            elif c == "[":
                return lex_query_inside_line_statement
            elif c == "\r":
                l.ignore()  # TODO:
            elif c == "\n":
                l.ignore()
                l.line_statements.append(
                    Tag(
                        l.line_start,
                        l.pos,
                        WC_DEFAULT,
                        l.tag_name,
                        l.tokens,
                    )
                )
                l.tag_name = ""
                l.tokens = []
                return lex_inside_liquid_tag

            # TODO: line comment
            else:
                l.error(f"unknown symbol '{c}'")
                return None


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
        l.error("unexpected end of query")
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


def lex_inside_bracketed_segment(l: Lexer) -> Optional[StateFn]:  # noqa: PLR0911, D103
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


def lex_string_factory(
    quote: str,
    state: StateFn,
    *,
    inside_query: bool = False,
) -> StateFn:
    """Return a state function for scanning string literals.

    Arguments:
        quote: One of `'` or `"`. The string delimiter.
        state: The state function to return control to after scanning the string.
        inside_query: Indicate if we're emitting from inside a query.
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
                return state

    return _lex_string


lex_single_quoted_string_inside_bracket_segment = lex_string_factory(
    "'", lex_inside_bracketed_segment, inside_query=True
)

lex_double_quoted_string_inside_bracket_segment = lex_string_factory(
    '"', lex_inside_bracketed_segment, inside_query=True
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
    def _lex_query(l: Lexer) -> StateFn:
        # TODO: implement singular query selector
        state: Optional[StateFn] = lex_segment
        while state is not None:
            state = state(l)

        l.tokens.append(parse(l.query_tokens))
        l.query_tokens = []
        return next_state

    return _lex_query


lex_query_inside_output_statement = lex_query_factory(lex_inside_output_statement)
lex_query_inside_tag_expression = lex_query_factory(lex_inside_tag)
lex_query_inside_line_statement = lex_query_factory(lex_inside_line_statement)


def tokenize(source: str) -> list[Markup]:
    """Scan Liquid template _source_ and return a list of Markup objects."""
    lexer = Lexer(source)
    lexer.run()

    if lexer.tokens:
        last_token = lexer.tokens[-1]
        if isinstance(last_token, Token) and last_token.type_ == TokenType.ERROR:
            raise LiquidSyntaxError(last_token.message, token=last_token)

    return lexer.markup
