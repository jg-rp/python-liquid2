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
from .token import BlockCommentToken
from .token import CommentToken
from .token import ContentToken
from .token import ErrorToken
from .token import InlineCommentToken
from .token import LinesToken
from .token import OutputToken
from .token import PathToken
from .token import RangeToken
from .token import RawToken
from .token import TagToken
from .token import TemplateStringToken
from .token import Token
from .token import TokenType
from .token import WhitespaceControl
from .token import is_token_type

if TYPE_CHECKING:
    from .token import TokenT


StateFn = Callable[[], Optional["StateFn"]]


def _compile(*rules: dict[str, str], flags: int = 0) -> Pattern[str]:
    _rules = chain.from_iterable(rule_set.items() for rule_set in rules)
    pattern = "|".join(f"(?P<{name}>{pattern})" for name, pattern in _rules)
    return re.compile(pattern, flags)


class Lexer:
    """Liquid template lexical scanner."""

    RE_LINE_COMMENT = re.compile(r"\#(.*?)(?=(\n|[\-+~]?%\}))")
    RE_REST_OF_LINE = re.compile(r"(.*?)(?=(\n|[\-+~]?%\}))")
    RE_OUTPUT_END = re.compile(r"([+\-~]?)\}\}")
    RE_TAG_END = re.compile(r"([+\-~]?)%\}")
    RE_WHITESPACE_CONTROL = re.compile(r"[+\-~]")

    RE_TAG_NAME = re.compile(r"[a-z][a-z_0-9]*\b")

    RE_WHITESPACE = re.compile(r"[ \n\r\t]+")
    RE_LINE_SPACE = re.compile(r"[ \t]+")
    RE_LINE_TERM = re.compile(r"\r?\n")

    RE_COMMENT_TAG_CHUNK = re.compile(
        r"(.*?)\{%(?:[\-+~]?)\s*"
        r"(?P<COMMENT_CHUNK_END>comment|endcomment|raw|endraw)"
        r".*?(?P<COMMENT_WC_END>[+\-~]?)%\}",
        re.DOTALL,
    )

    RE_PROPERTY = re.compile(r"[\u0080-\uFFFFa-zA-Z_][\u0080-\uFFFFa-zA-Z0-9_-]*")
    RE_INDEX = re.compile(r"-?[0-9]+")
    ESCAPES = frozenset(["b", "f", "n", "r", "t", "u", "/", "\\", "$"])

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
        "FLOAT": r"(?:-?[0-9]+\.[0-9]+(?:[eE][+-]?[0-9]+)?)|(-?[0-9]+[eE]-[0-9]+)",
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
        # old style `{% comment %} some comment {% endcomment %}`
        "COMMENT_TAG": r"\{%(?P<CT_WC>[\-+~]?)\s*comment\b.*?%\}",
        "OUTPUT": r"\{\{(?P<OUT_WC>[\-+~]?)\s*",
        "TAG": r"\{%(?P<TAG_WC>[\-+~]?)\s*(?P<TAG_NAME>[a-z][a-z_0-9]*)",
        "COMMENT": (  # new style `{# some comment #}`
            r"\{(?P<HASHES>#+)(?P<COMMENT_WC0>[\-+~]?)"
            r"(?P<COMMENT_TEXT>.*?)"
            r"(?P<COMMENT_WC1>[\-+~]?)(?P=HASHES)\}"
        ),
        "INLINE_COMMENT": (  # shopify style `{% # some comment %}`
            r"\{%(?P<ILC_WC0>[\-+~]?)\s*#(?P<ILC_TEXT>.*?)(?P<ILC_WC1>[\-+~]?)%\}"
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

    MARKUP_RULES = _compile(MARKUP, flags=re.DOTALL)
    TOKEN_RULES = _compile(NUMBERS, SYMBOLS, WORD)

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
        "template_string_stack",
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

        self.template_string_stack: list[TemplateStringToken]
        """Current, possibly nested, interpolated string."""

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
        state: Optional[StateFn] = self.lex_markup
        while state is not None:
            state = state()

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
                if self.peek() == ".":  # probably a range expression delimiter
                    self.backup()
                    return

                self.ignore()
                self.ignore_whitespace()
                if match := self.RE_PROPERTY.match(self.source, self.pos):
                    self.path_stack[-1].path.append(match.group())
                    self.pos += match.end() - match.start()
                    self.start = self.pos
                    self.path_stack[-1].stop = self.pos
                else:
                    self.error("expected a property name")

            elif c == "]":
                if len(self.path_stack) == 1:
                    self.backup()
                    self.error("unbalanced brackets")
                else:
                    path = self.path_stack.pop()
                    path.stop = self.start
                    self.ignore()
                    self.path_stack[-1].path.append(path)
                    self.path_stack[-1].stop = self.pos

            elif c == "[":
                self.ignore()
                self.ignore_whitespace()

                if self.peek() in ("'", '"'):
                    quote = self.next()
                    self.ignore()
                    self.accept_string(quote=quote)
                    if quote == '"':
                        self.path_stack[-1].path.append(
                            self.source[self.start : self.pos]
                        )
                    else:
                        self.path_stack[-1].path.append(
                            self.source[self.start : self.pos].replace("\\'", "'")
                        )
                    self.next()
                    self.ignore()  # skip closing quote
                    self.ignore_whitespace()

                    if self.next() != "]":
                        self.backup()
                        self.error("invalid variable path")
                    else:
                        self.ignore()
                        self.path_stack[-1].stop = self.start

                elif match := self.RE_INDEX.match(self.source, self.pos):
                    self.path_stack[-1].path.append(int(match.group()))
                    self.pos += match.end() - match.start()
                    self.start = self.pos
                    self.ignore_whitespace()

                    if self.next() != "]":
                        self.backup()
                        self.error("invalid variable path")
                    else:
                        self.ignore()
                        self.path_stack[-1].stop = self.start

                elif match := self.RE_PROPERTY.match(self.source, self.pos):
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
                elif self.peek() == "]":
                    self.error("empty bracketed segment")
                else:
                    self.error("expected a string, index or property name")
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
                if peeked in self.ESCAPES or peeked == quote:
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

    def accept_template_string(self, *, quote: str, expression: list[TokenT]) -> None:
        _type = (
            TokenType.SINGLE_QUOTE_STRING
            if quote == "'"
            else TokenType.DOUBLE_QUOTE_STRING
        )

        # Assumes the opening quote has been consumed.
        if self.peek() == quote:
            # an empty string
            self.next()  # Move past the closing quote.
            expression.append(
                Token(
                    type_=_type,
                    source=self.source,
                    value="",
                    index=self.start,
                )
            )
            self.start = self.pos
            return

        # String token or output token
        # The output token could contain more template strings
        start = self.start
        template_string: list[Token | OutputToken] = []

        while True:
            c = self.next()

            if c == "\\":
                peeked = self.peek()
                if peeked in self.ESCAPES or peeked == quote:
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

            if c == "$" and self.peek() == "{":
                # `${` could be at the start of the string
                if self.pos - 1 > self.start:
                    template_string.append(
                        Token(
                            type_=_type,
                            source=self.source,
                            value=self.source[self.start : self.pos - 1],
                            index=self.start,
                        )
                    )

                self.start = self.pos - 1
                self.next()  # Move past "{"
                self.ignore()
                sub_expression: list[TokenT] = []
                sub_expression_start = self.start

                while True:
                    self.ignore_whitespace()
                    if not self.accept_token(sub_expression):
                        if self.peek() == "}":
                            template_string.append(
                                OutputToken(
                                    type_=TokenType.OUTPUT,
                                    start=sub_expression_start,
                                    stop=self.pos,
                                    wc=(
                                        WhitespaceControl.DEFAULT,
                                        WhitespaceControl.DEFAULT,
                                    ),
                                    expression=sub_expression,
                                    source=self.source,
                                )
                            )
                            self.next()
                            self.ignore()
                            self.start = self.pos
                            break

                        self.error(
                            "unexpected end of template string expression, "
                            f"{self.peek()!r}"
                        )

            if c == quote:
                # template string expression could be at the end of the string
                if self.pos - 1 > self.start:
                    template_string.append(
                        Token(
                            type_=_type,
                            source=self.source,
                            value=self.source[self.start : self.pos - 1],
                            index=self.start,
                        )
                    )

                if len(template_string) == 1 and isinstance(template_string[0], Token):
                    # Just a plain string
                    expression.append(template_string[0])
                else:
                    expression.append(
                        TemplateStringToken(
                            type_=TokenType.SINGLE_QUOTE_TEMPLATE_STRING
                            if quote == "'"
                            else TokenType.DOUBLE_QUOTE_TEMPLATE_STRING,
                            source=self.source,
                            template=template_string,
                            start=start,
                            stop=self.pos,
                        )
                    )

                self.start = self.pos
                return

            if not c:
                raise LiquidSyntaxError(
                    "unclosed string or template string expression",
                    token=ErrorToken(
                        type_=TokenType.ERROR,
                        index=self.start,
                        value=self.source[self.start],
                        markup_start=self.markup_start,
                        markup_stop=self.pos,
                        source=self.source,
                        message="unclosed string or template string expression",
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

    def accept_token(self, expression: list[TokenT]) -> bool:
        match = self.TOKEN_RULES.match(self.source, pos=self.pos)

        if not match:
            return False

        kind = match.lastgroup
        assert kind is not None

        value = match.group()
        self.pos += len(value)

        if kind == "SINGLE_QUOTE_STRING":
            self.ignore()
            self.accept_template_string(quote="'", expression=expression)
        elif kind == "DOUBLE_QUOTE_STRING":
            self.ignore()
            self.accept_template_string(quote='"', expression=expression)
        elif kind == "LBRACKET":
            self.backup()
            self.accept_path()
            expression.append(self.path_stack.pop())

        elif kind == "WORD":
            if self.peek() in (".", "["):
                self.accept_path(carry=True)
                expression.append(self.path_stack.pop())

            elif token_type := self.KEYWORD_MAP.get(value):
                expression.append(
                    Token(
                        type_=token_type,
                        value=value,
                        index=self.start,
                        source=self.source,
                    )
                )
            else:
                expression.append(
                    Token(
                        type_=TokenType.WORD,
                        value=value,
                        index=self.start,
                        source=self.source,
                    )
                )

            self.start = self.pos

        elif token_type := self.TOKEN_MAP.get(kind):
            expression.append(
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
            msg = f"unexpected token {self.source[self.start:self.pos]!r}"
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

        if match := self.RE_WHITESPACE.match(self.source, self.pos):
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

        if match := self.RE_WHITESPACE.match(self.source, self.pos):
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

        if match := self.RE_LINE_SPACE.match(self.source, self.pos):
            whitespace = match.group()
            self.pos += len(whitespace)
            self.start = self.pos
            return whitespace
        return ""

    def error(self, msg: str) -> Never:
        """Emit an error token."""
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

    def lex_markup(self) -> StateFn | None:
        while True:
            match = self.MARKUP_RULES.match(self.source, pos=self.pos)

            if not match:
                assert self.pos == len(
                    self.source
                ), f"{self.pos}:{self.source[self.pos: 10]!r}.."
                return None

            kind = match.lastgroup
            value = match.group()
            self.pos += len(value)

            if kind == "CONTENT":
                self.markup.append(
                    ContentToken(
                        type_=TokenType.CONTENT,
                        start=self.start,
                        stop=self.pos,
                        text=value,
                        source=self.source,
                    )
                )
                self.start = self.pos
                continue

            if kind == "OUTPUT":
                self.markup_start = self.start
                self.wc.append(self.WC_MAP[match.group("OUT_WC")])
                self.ignore()
                return self.lex_inside_output_statement

            if kind == "TAG":
                self.markup_start = self.start
                self.wc.append(self.WC_MAP[match.group("TAG_WC")])
                tag_name = match.group("TAG_NAME")
                self.tag_name = tag_name
                self.ignore()
                return (
                    self.lex_inside_liquid_tag
                    if tag_name == "liquid"
                    else self.lex_inside_tag
                )

            if kind == "COMMENT":
                self.markup.append(
                    CommentToken(
                        type_=TokenType.COMMENT,
                        start=self.start,
                        stop=self.pos,
                        wc=(
                            self.WC_MAP[match.group("COMMENT_WC0")],
                            self.WC_MAP[match.group("COMMENT_WC1")],
                        ),
                        text=match.group("COMMENT_TEXT"),
                        hashes=match.group("HASHES"),
                        source=self.source,
                    )
                )
                continue

            if kind == "RAW":
                self.markup.append(
                    RawToken(
                        type_=TokenType.RAW,
                        start=self.start,
                        stop=self.pos,
                        wc=(
                            self.WC_MAP[match.group("RAW_WC0")],
                            self.WC_MAP[match.group("RAW_WC1")],
                            self.WC_MAP[match.group("RAW_WC2")],
                            self.WC_MAP[match.group("RAW_WC3")],
                        ),
                        text=match.group("RAW_TEXT"),
                        source=self.source,
                    )
                )
                self.start = self.pos
                continue

            if kind == "INLINE_COMMENT":
                self.markup.append(
                    InlineCommentToken(
                        type_=TokenType.COMMENT,
                        start=self.start,
                        stop=self.pos,
                        wc=(
                            self.WC_MAP[match.group("ILC_WC0")],
                            self.WC_MAP[match.group("ILC_WC1")],
                        ),
                        text=match.group("ILC_TEXT"),
                        hashes="",
                        source=self.source,
                    )
                )
                continue

            if kind == "COMMENT_TAG":
                self.markup_start = self.start
                self.wc.append(self.WC_MAP[match.group("CT_WC")])
                self.tag_name = "comment"
                self.ignore()
                return self.lex_inside_block_comment

            self.error("unreachable")

    def lex_inside_output_statement(
        self,
    ) -> StateFn | None:  # noqa: PLR0911, PLR0912, PLR0915
        while True:
            self.ignore_whitespace()
            if not self.accept_token(self.expression):
                if match := self.RE_OUTPUT_END.match(self.source, self.pos):
                    self.wc.append(self.WC_MAP[match.group(1)])
                    self.pos += match.end() - match.start()

                    self.markup.append(
                        OutputToken(
                            type_=TokenType.OUTPUT,
                            start=self.markup_start,
                            stop=self.pos,
                            wc=(self.wc[0], self.wc[1]),
                            expression=self.expression,
                            source=self.source,
                        )
                    )

                    self.wc.clear()
                    self.expression = []
                    self.ignore()
                    return self.lex_markup

                ch = self.peek()
                if ch == "}":
                    self.error("missing bracket detected")
                self.error(f"unexpected {ch!r}")

    def lex_inside_tag(self) -> StateFn | None:
        while True:
            self.ignore_whitespace()
            if not self.accept_token(self.expression):
                if match := self.RE_TAG_END.match(self.source, self.pos):
                    self.wc.append(self.WC_MAP[match.group(1)])
                    self.pos += match.end() - match.start()
                    self.markup.append(
                        TagToken(
                            type_=TokenType.TAG,
                            start=self.markup_start,
                            stop=self.pos,
                            wc=(self.wc[0], self.wc[1]),
                            name=self.tag_name,
                            expression=self.expression,
                            source=self.source,
                        )
                    )
                    self.wc.clear()
                    self.tag_name = ""
                    self.expression = []
                    self.ignore()
                    return self.lex_markup

                ch = self.peek()
                if ch == "}":
                    self.error("missing percent detected")
                if ch == "%":
                    self.error("missing bracket detected")
                self.error(f"unexpected {ch!r}")

    def lex_inside_liquid_tag(self) -> StateFn | None:
        self.line_space.append(self.consume_whitespace())

        if match := self.RE_TAG_END.match(self.source, self.pos):
            self.wc.append(self.WC_MAP[match.group(1)])
            self.pos += match.end() - match.start()
            self.markup.append(
                LinesToken(
                    type_=TokenType.LINES,
                    start=self.markup_start,
                    stop=self.pos,
                    wc=(self.wc[0], self.wc[1]),
                    name="liquid",
                    statements=self.line_statements,
                    whitespace=self.line_space,
                    source=self.source,
                )
            )

            self.wc.clear()
            self.tag_name = ""
            self.line_statements = []
            self.line_space = []
            self.expression = []
            self.ignore()
            return self.lex_markup

        if self.accept(self.RE_TAG_NAME):
            self.tag_name = self.source[self.start : self.pos]
            self.line_start = self.start
            self.ignore()
            return (
                self.lex_inside_liquid_block_comment
                if self.tag_name == "comment"
                else self.lex_inside_line_statement
            )

        if match := self.RE_LINE_COMMENT.match(self.source, self.pos):
            self.pos += match.end() - match.start()
            self.line_statements.append(
                CommentToken(
                    type_=TokenType.COMMENT,
                    start=self.start,
                    stop=self.pos,
                    wc=self.WC_DEFAULT,
                    text=match.group(1),
                    hashes="#",
                    source=self.source,
                )
            )
            self.start = self.pos
            # Line comments don't consume their trailing newline, but
            # lex_inside_line_statement does.
            if self.peek() == "\n":
                self.next()
                self.ignore()
            return self.lex_inside_liquid_tag

        self.next()
        return self.error("expected a tag name")

    def lex_inside_line_statement(self) -> StateFn | None:
        while True:
            self.ignore_line_space()

            if self.accept(self.RE_LINE_TERM):
                self.line_statements.append(
                    TagToken(
                        type_=TokenType.TAG,
                        start=self.line_start,
                        stop=self.start,
                        wc=self.WC_DEFAULT,
                        name=self.tag_name,
                        expression=self.expression,
                        source=self.source,
                    )
                )
                self.ignore()
                self.tag_name = ""
                self.expression = []
                return self.lex_inside_liquid_tag

            if not self.accept_token(self.expression):
                if match := self.RE_TAG_END.match(self.source, self.pos):
                    self.wc.append(self.WC_MAP[match.group(1)])
                    self.pos += match.end() - match.start()
                    self.ignore()
                    self.line_statements.append(
                        TagToken(
                            type_=TokenType.TAG,
                            start=self.line_start,
                            stop=self.pos,
                            wc=self.WC_DEFAULT,
                            name=self.tag_name,
                            expression=self.expression,
                            source=self.source,
                        )
                    )

                    self.markup.append(
                        LinesToken(
                            type_=TokenType.LINES,
                            start=self.markup_start,
                            stop=self.pos,
                            wc=(self.wc[0], self.wc[1]),
                            name="liquid",
                            statements=self.line_statements,
                            whitespace=self.line_space,
                            source=self.source,
                        )
                    )

                    self.wc = []
                    self.tag_name = ""
                    self.line_statements = []
                    self.line_space = []
                    self.expression = []
                    self.ignore()
                    return self.lex_markup

                self.error(f"unknown symbol '{self.next()}'")

    def lex_inside_block_comment(self) -> StateFn | None:
        comment_depth = 1
        raw_depth = 0

        while True:
            # Read comment text up to the next {% comment %}, {% endcomment %},
            # {% raw %}, {% endraw %}, so we can count how many nested tags there are.
            if match := self.RE_COMMENT_TAG_CHUNK.match(self.source, self.pos):
                self.pos += match.end() - match.start()
                tag_name = match.group("COMMENT_CHUNK_END")

                if tag_name == "comment":
                    comment_depth += 1
                elif tag_name == "endcomment":
                    if raw_depth:
                        continue
                    comment_depth -= 1
                    if comment_depth == 0:
                        self.markup.append(
                            BlockCommentToken(
                                type_=TokenType.COMMENT,
                                start=self.markup_start,
                                stop=self.pos,
                                wc=(
                                    self.wc[0],
                                    self.WC_MAP[match.group("COMMENT_WC_END")],
                                ),
                                text=self.source[
                                    self.start : match.start() + len(match.group(1))
                                ],
                                hashes="",
                                source=self.source,
                            )
                        )
                        self.wc.clear()
                        self.tag_name = ""
                        break
                elif tag_name == "raw":
                    raw_depth += 1
                elif tag_name == "endraw" and raw_depth > 0:
                    raw_depth -= 1
            else:
                self.error("unclosed comment block detected")

        if raw_depth > 0:
            self.error("unclosed raw block detected")

        return self.lex_markup

    def lex_inside_liquid_block_comment(self) -> StateFn | None:
        self.ignore_whitespace()
        comment_depth = 1

        while True:
            if match := self.RE_TAG_NAME.match(self.source, self.pos):
                tag_name = match.group()
                self.pos += match.end() - match.start()
                if tag_name == "endcomment":
                    text_end_pos = self.pos - len(tag_name)
                    comment_depth -= 1
                    if comment_depth == 0:
                        self.accept(self.RE_REST_OF_LINE)
                        self.accept(self.RE_LINE_TERM)
                        self.line_statements.append(
                            BlockCommentToken(
                                type_=TokenType.COMMENT,
                                start=self.line_start,
                                stop=self.pos,
                                wc=self.WC_DEFAULT,
                                text=self.source[self.start : text_end_pos],
                                hashes="",
                                source=self.source,
                            )
                        )
                        self.start = self.pos
                        break
                elif tag_name == "comment":
                    comment_depth += 1

                self.accept(self.RE_REST_OF_LINE)
                self.accept(self.RE_LINE_TERM)

            elif match := self.RE_LINE_COMMENT.match(self.source, self.pos):
                self.pos += match.end() - match.start()
                self.accept(self.RE_LINE_TERM)

            else:
                self.error("unclosed comment block detected")

        return self.lex_inside_liquid_tag


def tokenize(source: str) -> list[TokenT]:
    """Scan Liquid template _source_ and return a list of Markup objects."""
    lexer = Lexer(source)
    lexer.run()
    return lexer.markup
