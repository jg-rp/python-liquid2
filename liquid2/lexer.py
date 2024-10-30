"""JSONPath expression lexical scanner."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from typing import Callable
from typing import List
from typing import Optional
from typing import Pattern
from typing import Tuple

from .exceptions import LiquidSyntaxError
from .token import EOI
from .token import Comment
from .token import Content
from .token import Error
from .token import Lines
from .token import Output
from .token import Raw
from .token import Tag
from .token import Token
from .token import TokenType
from .token import WhitespaceControl

if TYPE_CHECKING:
    from .token import Markup


RE_CONTENT = re.compile(r".+?(?!(?:\{\{|\{%|\{#+}}))", re.DOTALL)

RE_COMMENT = re.compile(
    r"\{(?P<hashes>#+)([\-+~]?)(.*)([\-+~]?)(?P=hashes)\}", re.DOTALL
)

RE_RAW = re.compile(
    r"\{%([\-+~]?)\s*raw\s([\-+~]?)%\}(.*)\{%([\-+~]?)\s*endraw\s([\-+~]?)%\}",
    re.DOTALL,
)


RE_OUTPUT_END = re.compile(r"([+\-~]?)\}\}")
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

StateFn = Callable[["Lexer"], Optional["StateFn"]]


class Lexer:
    """Liquid template lexical scanner."""

    __slots__ = (
        "query_tokens",
        "filter_depth",
        "line_statements",
        "markup",
        "markup_start",
        "paren_stack",
        "pos",
        "source",
        "start",
        "tag_name",
        "tokens",
    )

    def __init__(self, source: str) -> None:
        self.filter_depth = 0
        """Filter nesting level."""

        self.paren_stack: List[int] = []
        """A running count of parentheses for each, possibly nested, function call.
        
        If the stack is empty, we are not in a function call. Remember that
        function arguments can be arbitrarily nested in parentheses.
        """

        self.markup: List[Markup] = []
        """Markup resulting from scanning a Liquid template."""

        self.tokens: List[Token] = []
        """Tokens from the current expression."""

        self.line_statements: list[Tag | Comment | Error]
        """Markup resulting from scanning a sequence of line statements."""

        self.query_tokens: List[Token] = []
        """Tokens from the current query."""

        self.start = 0
        """Pointer to the start of the current token."""

        self.pos = 0
        """Pointer to the current character."""

        self.markup_start = -1
        """Pointer to the start of the current expression."""

        self.tag_name = ""
        """The name of the current tag."""

        self.source = source
        """The template source text being scanned."""

    def run(self) -> None:
        """Populate _self.tokens_."""
        state: Optional[StateFn] = self.lex_markup
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
        self.tokens.append(
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
                    self.source,
                )
            )
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
                    self.source,
                )
            )
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
                    self.source,
                )
            )
            return True
        return False

    def accept_end_output_statement(self) -> bool:
        """Accepts the output end sequence, possibly preceded by whitespace control."""
        match = RE_OUTPUT_END.match(self.source, self.pos)
        if match:
            wc_group = match.group(1)
            if wc_group:
                self.pos += 1
                # TODO: don't emit wc
                self.emit_token(TokenType.WC)

            self.pos += 2
            return True
        return False

    def ignore_whitespace(self) -> bool:
        """Move the pointer past any whitespace."""
        if self.pos != self.start:
            msg = (
                "must emit or ignore before consuming whitespace "
                f"({self.source[self.start: self.pos]})"
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

    def lex_markup(self) -> StateFn | None:
        while True:
            assert not self.tokens  # current expression should be empty
            assert not self.query_tokens  # current query should be empty
            assert not self.tag_name  # current tag name should be empty

            self.accept_and_emit_raw()
            self.accept_and_emit_comment()
            self.accept_and_emit_content()

            if self.accept(r"{{"):
                self.markup_start = self.start
                self.ignore()
                return self.lex_inside_output_statement

            if self.accept(r"{%"):
                self.markup_start = self.start
                self.ignore()
                return self.lex_inside_tag

            assert self.pos == len(self.source)
            self.markup.append(EOI(self.start, self.pos, self.source))
            return None

    def lex_inside_output_statement(self) -> StateFn | None:
        if self.accept(RE_WHITESPACE_CONTROL):
            self.emit_token(TokenType.WC)

        while True:
            self.ignore_whitespace()

            # TODO: end whitespace control
            if self.accept_end_output_statement():
                self.markup.append(
                    Output(
                        self.markup_start,
                        self.pos,
                        self.tokens,
                        self.source,
                    )
                )
                self.tokens = []
                return self.lex_markup

            if self.accept_match(RE_TRUE):
                self.emit_token(TokenType.TRUE)
            elif self.accept_match(RE_FALSE):
                self.emit_token(TokenType.FALSE)
            elif self.accept_match(RE_AND):
                self.emit_token(TokenType.AND_WORD)
            elif self.accept_match(RE_OR):
                self.emit_token(TokenType.OR_WORD)
            elif self.accept_match(RE_IN):
                self.emit_token(TokenType.IN)
            elif self.accept_match(RE_NOT):
                self.emit_token(TokenType.NOT_WORD)
            elif self.accept_match(RE_CONTAINS):
                self.emit_token(TokenType.CONTAINS)
            elif self.accept_match(RE_NULL) or self.accept_match(RE_NIL):
                self.emit_token(TokenType.NULL)
            elif self.accept_match(RE_IF):
                self.emit_token(TokenType.IF)
            elif self.accept_match(RE_ELSE):
                self.emit_token(TokenType.ELSE)
            elif self.accept_match(RE_WITH):
                self.emit_token(TokenType.WITH)
            elif self.accept_match(RE_REQUIRED):
                self.emit_token(TokenType.REQUIRED)
            elif self.accept_match(RE_AS):
                self.emit_token(TokenType.AS)
            elif self.accept_match(RE_FOR):
                self.emit_token(TokenType.FOR)
            elif self.accept_match(RE_WORD):
                peeked = self.peek()
                if peeked == "." or peeked == "[":
                    return self.lex_query_inside_output_statement
                self.emit_token(TokenType.WORD)
            elif self.accept_match(RE_FLOAT):
                self.emit_token(TokenType.FLOAT)
            elif self.accept_match(RE_INT):
                self.emit_token(TokenType.INT)
            elif self.accept(">="):
                self.emit_token(TokenType.GE)
            elif self.accept("<="):
                self.emit_token(TokenType.LE)
            elif self.accept("=="):
                self.emit_token(TokenType.EQ)
            elif self.accept("!=") or self.accept("<>"):
                self.emit_token(TokenType.NOT_WORD)
            elif self.accept(".."):
                self.emit_token(TokenType.DOUBLE_DOT)
            elif self.accept("||"):
                self.emit_token(TokenType.DOUBLE_PIPE)
            else:
                c = self.next()

                if c == "'":
                    return self.lex_single_quoted_string_inside_output_statement

                if c == '"':
                    return self.lex_double_quoted_string_inside_output_statement

                if c == "(":
                    self.emit_token(TokenType.LPAREN)
                elif c == ")":
                    self.emit_token(TokenType.RPAREN)
                elif c == "<":
                    self.emit_token(TokenType.LT)
                elif c == ">":
                    self.emit_token(TokenType.GT)
                elif c == ":":
                    self.emit_token(TokenType.COLON)
                elif c == ",":
                    self.emit_token(TokenType.COMMA)
                elif c == "|":
                    self.emit_token(TokenType.PIPE)
                elif c == "=":
                    self.emit_token(TokenType.ASSIGN)

                raise LiquidSyntaxError(f"unknown symbol '{c}'")

    def lex_inside_tag(self) -> StateFn | None:
        if self.accept(RE_WHITESPACE_CONTROL):
            self.emit_token(TokenType.WC)

        self.ignore_whitespace()

        if self.accept(RE_TAG_NAME):
            self.tag_name = self.source[self.start : self.pos]
        else:
            c = self.next()
            raise LiquidSyntaxError(f"expected a tag name, found {c!r}")

        if self.tag_name == "liquid":
            return self.lex_inside_liquid_tag

        while True:
            self.ignore_whitespace()

            # TODO:
            # TODO: end whitespace control
            if self.accept_end_tag():
                self.markup.append(
                    Tag(
                        self.markup_start,
                        self.pos,
                        self.tag_name,
                        self.tokens,
                        self.source,
                    )
                )
                self.tokens = []
                return self.lex_markup

            if self.accept_match(RE_TRUE):
                self.emit_token(TokenType.TRUE)
            elif self.accept_match(RE_FALSE):
                self.emit_token(TokenType.FALSE)
            elif self.accept_match(RE_AND):
                self.emit_token(TokenType.AND_WORD)
            elif self.accept_match(RE_OR):
                self.emit_token(TokenType.OR_WORD)
            elif self.accept_match(RE_IN):
                self.emit_token(TokenType.IN)
            elif self.accept_match(RE_NOT):
                self.emit_token(TokenType.NOT_WORD)
            elif self.accept_match(RE_CONTAINS):
                self.emit_token(TokenType.CONTAINS)
            elif self.accept_match(RE_NULL) or self.accept_match(RE_NIL):
                self.emit_token(TokenType.NULL)
            elif self.accept_match(RE_IF):
                self.emit_token(TokenType.IF)
            elif self.accept_match(RE_ELSE):
                self.emit_token(TokenType.ELSE)
            elif self.accept_match(RE_WITH):
                self.emit_token(TokenType.WITH)
            elif self.accept_match(RE_REQUIRED):
                self.emit_token(TokenType.REQUIRED)
            elif self.accept_match(RE_AS):
                self.emit_token(TokenType.AS)
            elif self.accept_match(RE_FOR):
                self.emit_token(TokenType.FOR)
            elif self.accept_match(RE_WORD):
                peeked = self.peek()
                if peeked == "." or peeked == "[":
                    return self.lex_query_inside_tag_expression
                self.emit_token(TokenType.WORD)
            elif self.accept_match(RE_FLOAT):
                self.emit_token(TokenType.FLOAT)
            elif self.accept_match(RE_INT):
                self.emit_token(TokenType.INT)
            elif self.accept(">="):
                self.emit_token(TokenType.GE)
            elif self.accept("<="):
                self.emit_token(TokenType.LE)
            elif self.accept("=="):
                self.emit_token(TokenType.EQ)
            elif self.accept("!=") or self.accept("<>"):
                self.emit_token(TokenType.NOT_WORD)
            elif self.accept(".."):
                self.emit_token(TokenType.DOUBLE_DOT)
            elif self.accept("||"):
                self.emit_token(TokenType.DOUBLE_PIPE)
            else:
                c = self.next()

                if c == "'":
                    return self.lex_single_quoted_string_inside_tag_expression

                if c == '"':
                    return self.lex_double_quoted_string_inside_tag_expression

                if c == "(":
                    self.emit_token(TokenType.LPAREN)
                elif c == ")":
                    self.emit_token(TokenType.RPAREN)
                elif c == "<":
                    self.emit_token(TokenType.LT)
                elif c == ">":
                    self.emit_token(TokenType.GT)
                elif c == ":":
                    self.emit_token(TokenType.COLON)
                elif c == ",":
                    self.emit_token(TokenType.COMMA)
                elif c == "|":
                    self.emit_token(TokenType.PIPE)
                elif c == "=":
                    self.emit_token(TokenType.ASSIGN)

                raise LiquidSyntaxError(f"unknown symbol '{c}'")

    def lex_inside_liquid_tag(self) -> StateFn | None:
        self.ignore_whitespace()

        if self.accept_end_tag():
            # TODO: WC
            self.markup.append(
                Lines(
                    self.markup_start,
                    self.pos,
                    "liquid",
                    self.line_statements,
                    self.source,
                )
            )

            self.tag_name = ""
            self.line_statements = []
            self.tokens = []
            return self.lex_markup

        if self.accept(RE_TAG_NAME):
            self.tag_name = self.source[self.start : self.pos]
        else:
            self.next()
            raise LiquidSyntaxError("expected a tag name")

        return self.lex_inside_line_statement

    def lex_inside_line_statement(self) -> StateFn | None:
        raise NotImplementedError

    def lex_root(self) -> Optional[StateFn]:  # noqa: D103
        c = self.next()

        if c != "$":
            self.error(f"expected '$', found {c!r}")
            return None

        self.emit(TokenType.ROOT)
        return self.lex_segment

    def lex_segment(self) -> Optional[StateFn]:  # noqa: D103, PLR0911
        if self.ignore_whitespace() and not self.peek():
            self.error("unexpected trailing whitespace")
            return None

        c = self.next()

        if c == "":
            self.emit(TokenType.EOF)
            return None

        if c == ".":
            if self.peek() == ".":
                self.next()
                self.emit(TokenType.DOUBLE_DOT)
                return self.lex_descendant_segment
            return self.lex_shorthand_selector

        if c == "[":
            self.emit(TokenType.LBRACKET)
            return self.lex_inside_bracketed_segment

        if self.filter_depth:
            self.backup()
            return self.lex_inside_filter

        self.error(f"expected '.', '..' or a bracketed selection, found {c!r}")
        return None

    def lex_descendant_segment(self) -> Optional[StateFn]:
        c = self.next()

        if c == "":
            self.error("bald descendant segment")
            return None

        if c == "*":
            self.emit(TokenType.WILD)
            return self.lex_segment

        if c == "[":
            self.emit(TokenType.LBRACKET)
            return self.lex_inside_bracketed_segment

        self.backup()

        if self.accept_match(RE_PROPERTY):
            self.emit(TokenType.PROPERTY)
            return self.lex_segment

        self.next()
        self.error(f"unexpected descendant selection token {c!r}")
        return None

    def lex_shorthand_selector(self) -> Optional[StateFn]:  # noqa: D103
        self.ignore()  # ignore dot

        if self.accept_match(RE_WHITESPACE):
            self.error("unexpected whitespace after dot")
            return None

        c = self.next()

        if c == "*":
            self.emit(TokenType.WILD)
            return self.lex_segment

        self.backup()

        if self.accept_match(RE_PROPERTY):
            self.emit(TokenType.PROPERTY)
            return self.lex_segment

        self.error(f"unexpected shorthand selector {c!r}")
        return None

    def lex_inside_bracketed_segment(self) -> Optional[StateFn]:  # noqa: PLR0911, D103
        while True:
            self.ignore_whitespace()
            c = self.next()

            if c == "]":
                self.emit(TokenType.RBRACKET)
                if self.filter_depth:
                    return self.lex_inside_filter
                return self.lex_segment

            if c == "":
                self.error("unclosed bracketed selection")
                return None

            if c == "*":
                self.emit(TokenType.WILD)
                continue

            if c == "?":
                self.emit(TokenType.FILTER)
                self.filter_depth += 1
                return self.lex_inside_filter

            if c == ",":
                self.emit(TokenType.COMMA)
                continue

            if c == ":":
                self.emit(TokenType.COLON)
                continue

            if c == "'":
                # Quoted dict/object key/property name
                return self.lex_single_quoted_string_inside_bracket_segment

            if c == '"':
                # Quoted dict/object key/property name
                return self.lex_double_quoted_string_inside_bracket_segment

            # default
            self.backup()

            if self.accept_match(RE_INDEX):
                # Index selector or part of a slice selector.
                self.emit(TokenType.INDEX)
                continue

            self.error(f"unexpected token {c!r} in bracketed selection")
            return None

    def lex_inside_filter(self) -> Optional[StateFn]:  # noqa: D103, PLR0915, PLR0912, PLR0911
        while True:
            self.ignore_whitespace()
            c = self.next()

            if c == "":
                self.error("unclosed bracketed selection")
                return None

            if c == "]":
                self.filter_depth -= 1
                if len(self.paren_stack) == 1:
                    self.error("unbalanced parentheses")
                    return None

                self.backup()
                return self.lex_inside_bracketed_segment

            if c == ",":
                self.emit(TokenType.COMMA)
                # If we have unbalanced parens, we are inside a function call and a
                # comma separates arguments. Otherwise a comma separates selectors.
                if self.paren_stack:
                    continue
                self.filter_depth -= 1
                return self.lex_inside_bracketed_segment

            if c == "'":
                return self.lex_single_quoted_string_inside_filter_expression

            if c == '"':
                return self.lex_double_quoted_string_inside_filter_expression

            if c == "(":
                self.emit(TokenType.LPAREN)
                # Are we in a function call? If so, a function argument contains parens.
                if self.paren_stack:
                    self.paren_stack[-1] += 1
                continue

            if c == ")":
                self.emit(TokenType.RPAREN)
                # Are we closing a function call or a parenthesized expression?
                if self.paren_stack:
                    if self.paren_stack[-1] == 1:
                        self.paren_stack.pop()
                    else:
                        self.paren_stack[-1] -= 1
                continue

            if c == "$":
                self.emit(TokenType.ROOT)
                return self.lex_segment

            if c == "@":
                self.emit(TokenType.CURRENT)
                return self.lex_segment

            if c == ".":
                self.backup()
                return self.lex_segment

            if c == "!":
                if self.peek() == "=":
                    self.next()
                    self.emit(TokenType.NE)
                else:
                    self.emit(TokenType.NOT)
                continue

            if c == "=":
                if self.peek() == "=":
                    self.next()
                    self.emit(TokenType.EQ)
                    continue

                self.backup()
                self.error(f"unexpected filter selector token {c!r}")
                return None

            if c == "<":
                if self.peek() == "=":
                    self.next()
                    self.emit(TokenType.LE)
                else:
                    self.emit(TokenType.LT)
                continue

            if c == ">":
                if self.peek() == "=":
                    self.next()
                    self.emit(TokenType.GE)
                else:
                    self.emit(TokenType.GT)
                continue

            self.backup()

            if self.accept("&&"):
                self.emit(TokenType.AND)
            elif self.accept("||"):
                self.emit(TokenType.OR)
            elif self.accept("true"):
                self.emit(TokenType.TRUE)
            elif self.accept("false"):
                self.emit(TokenType.FALSE)
            elif self.accept("null"):
                self.emit(TokenType.NULL)
            elif self.accept_match(RE_FLOAT):
                self.emit(TokenType.FLOAT)
            elif self.accept_match(RE_INT):
                self.emit(TokenType.INT)
            elif self.accept_match(RE_FUNCTION_NAME) and self.peek() == "(":
                # Keep track of parentheses for this function call.
                self.paren_stack.append(1)
                self.emit(TokenType.FUNCTION)
                self.next()
                self.ignore()  # ignore LPAREN
            else:
                self.error(f"unexpected filter selector token {c!r}")
                return None

    def lex_string_factory(self, quote: str, state: StateFn) -> StateFn:
        """Return a state function for scanning string literals.

        Arguments:
            quote: One of `'` or `"`. The string delimiter.
            state: The state function to return control to after scanning the string.
        """
        tt = (
            TokenType.SINGLE_QUOTE_STRING
            if quote == "'"
            else TokenType.DOUBLE_QUOTE_STRING
        )

        def _lex_string(self) -> Optional[StateFn]:
            self.ignore()  # ignore opening quote

            if self.peek() == "":
                # an empty string
                self.emit(tt)
                self.next()
                self.ignore()
                return state

            while True:
                c = self.next()

                if c == "\\":
                    peeked = self.peek()
                    if peeked in ESCAPES or peeked == quote:
                        self.next()
                    else:
                        self.error("invalid escape")
                        return None

                if not c:
                    self.error(f"unclosed string starting at index {self.start}")
                    return None

                if c == quote:
                    self.backup()
                    self.emit(tt)
                    self.next()
                    self.ignore()  # ignore closing quote
                    return state

        return _lex_string

    lex_single_quoted_string_inside_bracket_segment = lex_string_factory(
        "'", lex_inside_bracketed_segment
    )

    lex_double_quoted_string_inside_bracket_segment = lex_string_factory(
        '"', lex_inside_bracketed_segment
    )

    lex_single_quoted_string_inside_filter_expression = lex_string_factory(
        "'", lex_inside_filter
    )

    lex_double_quoted_string_inside_filter_expression = lex_string_factory(
        '"', lex_inside_filter
    )


def lex(query: str) -> Tuple[Lexer, List[Token]]:
    """Return a lexer for _query_ and an array to be populated with Tokens."""
    lexer = Lexer(query)
    return lexer, lexer.tokens


def tokenize(query: str) -> List[Token]:
    """Scan JSONPath expression _query_ and return a list of tokens."""
    lexer, tokens = lex(query)
    lexer.run()

    if tokens and tokens[-1].type_ == TokenType.ERROR:
        raise LiquidSyntaxError(tokens[-1].message, token=tokens[-1])

    return tokens
