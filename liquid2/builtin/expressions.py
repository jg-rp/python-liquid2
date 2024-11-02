"""Expression for built in, standard tags."""

from __future__ import annotations

import sys
from decimal import Decimal
from itertools import islice
from typing import TYPE_CHECKING
from typing import Any
from typing import Collection
from typing import Generic
from typing import Iterator
from typing import Mapping
from typing import Sequence
from typing import TypeVar
from typing import cast

from markupsafe import Markup

from liquid2 import RenderContext
from liquid2 import Token
from liquid2 import TokenType
from liquid2 import is_query_token
from liquid2 import is_range_token
from liquid2 import is_token_type
from liquid2.exceptions import LiquidSyntaxError
from liquid2.exceptions import LiquidTypeError
from liquid2.expression import Expression
from liquid2.limits import to_int
from liquid2.query import word_to_query

if TYPE_CHECKING:
    from liquid2 import RenderContext
    from liquid2 import TokenStream
    from liquid2 import TokenT
    from liquid2.query import JSONPathQuery


class Null(Expression):
    __slots__ = ()

    def __eq__(self, other: object) -> bool:
        return other is None or isinstance(other, Null)

    def __str__(self) -> str:  # pragma: no cover
        return ""

    def __hash__(self) -> int:
        return hash(self.__class__)

    def evaluate(self, _: RenderContext) -> None:
        return None

    def children(self) -> list[Expression]:
        return []


class Empty(Expression):
    __slots__ = ()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Empty):
            return True
        return isinstance(other, (list, dict, str)) and not other

    def __str__(self) -> str:  # pragma: no cover
        return ""

    def __hash__(self) -> int:
        return hash(self.__class__)

    def evaluate(self, _: RenderContext) -> Empty:
        return self

    def children(self) -> list[Expression]:
        return []


def is_empty(obj: object) -> bool:
    """Return True if _obj_ is considered empty."""
    return isinstance(obj, (list, dict, str)) and not obj


class Blank(Expression):
    __slots__ = ()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str) and (not other or other.isspace()):
            return True
        if isinstance(other, (list, dict)) and not other:
            return True
        return isinstance(other, Blank)

    def __str__(self) -> str:  # pragma: no cover
        return ""

    def __hash__(self) -> int:
        return hash(self.__class__)

    def evaluate(self, _: RenderContext) -> Blank:
        return self

    def children(self) -> list[Expression]:
        return []


def is_blank(obj: object) -> bool:
    """Return True if _obj_ is considered blank."""
    if isinstance(obj, str) and (not obj or obj.isspace()):
        return True
    return isinstance(obj, (list, dict)) and not obj


class Continue(Expression):
    __slots__ = ()

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Continue)

    def __str__(self) -> str:  # pragma: no cover
        return "continue"

    def __hash__(self) -> int:
        return hash(self.__class__)

    def evaluate(self, _: RenderContext) -> int:
        return 0

    def children(self) -> list[Expression]:
        return []


T = TypeVar("T")


class Literal(Expression, Generic[T]):
    __slots__ = ("value",)

    def __init__(self, token: TokenT, value: T):
        super().__init__(token=token)
        self.value = value

    def __str__(self) -> str:
        return repr(self.value)

    def __eq__(self, other: object) -> bool:
        return self.value == other

    def __hash__(self) -> int:
        return hash(self.value)

    def __sizeof__(self) -> int:
        return sys.getsizeof(self.value)

    def evaluate(self, _: RenderContext) -> object:
        return self.value

    def children(self) -> list[Expression]:
        return []


class TrueLiteral(Literal[bool]):
    __slots__ = ()

    def __init__(self, token: TokenT) -> None:
        super().__init__(token, True)  # noqa: FBT003

    def __eq__(self, other: object) -> bool:
        return isinstance(other, TrueLiteral) and self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)


class FalseLiteral(Literal[bool]):
    __slots__ = ()

    def __init__(self, token: TokenT) -> None:
        super().__init__(token, False)  # noqa: FBT003

    def __eq__(self, other: object) -> bool:
        return isinstance(other, TrueLiteral) and self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)


class StringLiteral(Literal[str]):
    __slots__ = ()

    def __init__(self, token: TokenT, value: str):
        super().__init__(token, value)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, StringLiteral) and self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __sizeof__(self) -> int:
        return sys.getsizeof(self.value)

    def evaluate(self, context: RenderContext) -> str | Markup:
        if context.auto_escape:
            return Markup(self.value)
        return self.value


class IntegerLiteral(Literal[int]):
    __slots__ = ()

    def __init__(self, token: TokenT, value: int):
        super().__init__(token, value)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, IntegerLiteral) and self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)


class FloatLiteral(Literal[float]):
    __slots__ = ()

    def __init__(self, token: TokenT, value: float):
        super().__init__(token, value)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FloatLiteral) and self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)


class RangeLiteral(Expression):
    __slots__ = ("start", "stop")

    def __init__(self, token: TokenT, start: Expression, stop: Expression):
        super().__init__(token=token)
        self.start = start
        self.stop = stop

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, RangeLiteral)
            and self.start == other.start
            and self.stop == other.stop
        )

    def __str__(self) -> str:
        return f"({self.start}..{self.stop})"

    def __hash__(self) -> int:
        return hash((self.start, self.stop))

    def __sizeof__(self) -> int:
        return (
            super().__sizeof__() + sys.getsizeof(self.start) + sys.getsizeof(self.stop)
        )

    def _make_range(self, start: Any, stop: Any) -> range:
        try:
            start = to_int(start)
        except ValueError:
            start = 0

        try:
            stop = to_int(stop)
        except ValueError:
            stop = 0

        # Descending ranges don't work
        if start > stop:
            return range(0)

        return range(start, stop + 1)

    def evaluate(self, context: RenderContext) -> range:
        return self._make_range(
            self.start.evaluate(context), self.stop.evaluate(context)
        )

    async def evaluate_async(self, context: RenderContext) -> range:
        return self._make_range(
            await self.start.evaluate_async(context),
            await self.stop.evaluate_async(context),
        )

    def children(self) -> list[Expression]:
        return [self.start, self.stop]


class Query(Expression):
    __slots__ = ("path",)

    def __init__(self, token: TokenT, path: JSONPathQuery) -> None:
        super().__init__(token=token)
        self.path = path

    def __str__(self) -> str:
        return str(self.path)

    def __hash__(self) -> int:
        return hash(self.path)

    def __sizeof__(self) -> int:
        return super().__sizeof__() + sys.getsizeof(self.path)

    def evaluate(self, context: RenderContext) -> object:
        assert self.token
        return context.get(self.path, token=self.token)

    def children(self) -> list[Expression]:
        return [Query(token=q.token, path=q) for q in self.path.children()]  # type: ignore


Primitive = Literal[Any] | RangeLiteral | Query | Null


class FilteredExpression(Expression):
    __slots__ = ("left", "filters")

    def __init__(
        self,
        token: TokenT,
        left: Expression,
        filters: list[Filter] | None = None,
    ) -> None:
        super().__init__(token=token)
        self.left = left
        self.filters = filters

    def evaluate(self, context: RenderContext) -> object:
        rv = self.left.evaluate(context)
        if self.filters:
            for f in self.filters:
                rv = f.evaluate(rv, context)
        return rv

    async def evaluate_async(self, context: RenderContext) -> object:
        rv = await self.left.evaluate_async(context)
        if self.filters:
            for f in self.filters:
                rv = await f.evaluate_async(rv, context)
        return rv

    def children(self) -> list[Expression]:
        children = [self.left]
        if self.filters:
            for filter_ in self.filters:
                children.extend(filter_.children())
        return children

    @staticmethod
    def parse(stream: TokenStream) -> FilteredExpression | TernaryFilteredExpression:
        """Return a new FilteredExpression parsed from _tokens_."""
        left = parse_primitive(stream.next())
        filters = Filter.parse(stream, delim=(TokenType.PIPE,))

        if is_token_type(stream.current(), TokenType.IF):
            return TernaryFilteredExpression.parse(
                FilteredExpression(left.token, left, filters), stream
            )
        return FilteredExpression(left.token, left, filters)


def parse_primitive(token: TokenT) -> Expression:  # noqa: PLR0911
    """Parse _token_ as a primitive expression."""
    if is_token_type(token, TokenType.TRUE):
        return TrueLiteral(token=token)

    if is_token_type(token, TokenType.FALSE):
        return FalseLiteral(token=token)

    if is_token_type(token, TokenType.NULL):
        return Null(token=token)

    if is_token_type(token, TokenType.WORD):
        if token.value == "empty":
            return Empty(token=token)
        if token.value == "blank":
            return Blank(token=token)
        return Query(token, word_to_query(token))

    if is_token_type(token, TokenType.INT):
        # TODO: scientific notation
        return IntegerLiteral(token, to_int(token.value))

    if is_token_type(token, TokenType.FLOAT):
        return FloatLiteral(token, float(token.value))

    if is_token_type(token, TokenType.SINGLE_QUOTE_STRING) or is_token_type(
        token, TokenType.DOUBLE_QUOTE_STRING
    ):
        return StringLiteral(token, token.value)

    if is_query_token(token):
        return Query(token, token.path)

    if is_range_token(token):
        return RangeLiteral(
            token, parse_primitive(token.start), parse_primitive(token.stop)
        )

    raise LiquidSyntaxError(
        f"expected a primitive expression, found {token.type_.name}",
        token=token,
    )


class TernaryFilteredExpression(Expression):
    __slots__ = ("left", "condition", "alternative", "filters", "tail_filters")

    def __init__(
        self,
        token: TokenT,
        left: FilteredExpression,
        condition: BooleanExpression,
        alternative: Expression | None = None,
        filters: list[Filter] | None = None,
        tail_filters: list[Filter] | None = None,
    ) -> None:
        super().__init__(token=token)
        self.left = left
        self.condition = condition
        self.alternative = alternative
        self.filters = filters
        self.tail_filters = tail_filters

    def evaluate(self, context: RenderContext) -> object:
        rv: object = None

        if self.condition.evaluate(context):
            rv = self.left.evaluate(context)
        elif self.alternative:
            rv = self.alternative.evaluate(context)
            if self.filters:
                for f in self.filters:
                    rv = f.evaluate(rv, context)

        if self.tail_filters:
            for f in self.tail_filters:
                rv = f.evaluate(rv, context)

        return rv

    async def evaluate_async(self, context: RenderContext) -> object:
        rv: object = None

        if await self.condition.evaluate_async(context):
            rv = await self.left.evaluate_async(context)
        elif self.alternative:
            rv = await self.alternative.evaluate_async(context)
            if self.filters:
                for f in self.filters:
                    rv = await f.evaluate_async(rv, context)

        if self.tail_filters:
            for f in self.tail_filters:
                rv = await f.evaluate_async(rv, context)

        return rv

    def children(self) -> list[Expression]:
        children = self.left.children()
        children.append(self.condition)

        if self.alternative:
            children.append(self.alternative)

        if self.filters:
            for filter_ in self.filters:
                children.extend(filter_.children())

        if self.tail_filters:
            for filter_ in self.tail_filters:
                children.extend(filter_.children())

        return children

    @staticmethod
    def parse(
        expr: FilteredExpression, stream: TokenStream
    ) -> TernaryFilteredExpression:
        """Return a new TernaryFilteredExpression parsed from tokens in _stream_."""
        stream.expect(TokenType.IF)
        next(stream)  # move past `if`
        condition = BooleanExpression.parse(stream)
        alternative: Expression | None = None
        filters: list[Filter] | None = None
        tail_filters: list[Filter] | None = None

        if is_token_type(stream.current(), TokenType.ELSE):
            next(stream)  # move past `else`
            alternative = parse_primitive(stream.next())

            if stream.current().type_ == TokenType.PIPE:
                filters = Filter.parse(stream, delim=(TokenType.PIPE,))

        if stream.current().type_ == TokenType.DOUBLE_PIPE:
            tail_filters = Filter.parse(
                stream, delim=(TokenType.PIPE, TokenType.DOUBLE_PIPE)
            )

        return TernaryFilteredExpression(
            expr.token, expr, condition, alternative, filters, tail_filters
        )


class Filter:
    __slots__ = ("name", "args", "token")

    def __init__(
        self,
        token: TokenT,
        name: str,
        arguments: list[KeywordArgument | PositionalArgument],
    ) -> None:
        self.token = token
        self.name = name
        self.args = arguments

    def __str__(self) -> str:
        if self.args:
            return f"{self.name}: {''.join(str(arg for arg in self.args))}"
        return self.name

    def evaluate(self, left: object, context: RenderContext) -> object:
        func = context.filter(self.name, token=self.token)
        positional_args, keyword_args = self.evaluate_args(context)
        try:
            return func(left, *positional_args, **keyword_args)
        except TypeError as err:
            raise LiquidTypeError(f"{self.name}: {err}", token=self.token) from err
        except LiquidTypeError as err:
            err.token = self.token
            raise err

    async def evaluate_async(self, left: object, context: RenderContext) -> object:
        func = context.filter(self.name, token=self.token)
        positional_args, keyword_args = await self.evaluate_args_async(context)

        if hasattr(func, "filter_async"):
            # TODO:
            raise NotImplementedError(":(")

        try:
            return func(left, *positional_args, **keyword_args)
        except TypeError as err:
            raise LiquidTypeError(f"{self.name}: {err}", token=self.token) from err
        except LiquidTypeError as err:
            err.token = self.token
            raise err

    def evaluate_args(
        self, context: RenderContext
    ) -> tuple[list[object], dict[str, object]]:
        positional_args: list[object] = []
        keyword_args: dict[str, object] = {}
        for arg in self.args:
            name, value = arg.evaluate(context)
            if name:
                keyword_args[name] = value
            else:
                positional_args.append(value)

        return positional_args, keyword_args

    async def evaluate_args_async(
        self, context: RenderContext
    ) -> tuple[list[object], dict[str, object]]:
        positional_args: list[object] = []
        keyword_args: dict[str, object] = {}
        for arg in self.args:
            name, value = await arg.evaluate_async(context)
            if name:
                keyword_args[name] = value
            else:
                positional_args.append(value)

        return positional_args, keyword_args

    def children(self) -> list[Expression]:
        return [arg.value for arg in self.args]

    @staticmethod
    def parse(  # noqa: PLR0912
        stream: TokenStream,
        *,
        delim: tuple[TokenType, ...],
    ) -> list[Filter]:
        """Parse as any filters as possible from tokens in _stream_."""
        filters: list[Filter] = []

        while stream.current().type_ in delim:
            next(stream)
            stream.expect(TokenType.WORD)
            filter_token = cast(Token, stream.next())  # TODO:
            filter_name = filter_token.value
            filter_arguments: list[KeywordArgument | PositionalArgument] = []

            if stream.current().type_ == TokenType.COLON:
                next(stream)  # Move past ':'
                while True:
                    token = stream.current()
                    if is_token_type(token, TokenType.WORD):
                        if stream.peek().type_ in (
                            TokenType.ASSIGN,
                            TokenType.COLON,
                        ):
                            # A named or keyword argument
                            stream.next()  # skip = or :
                            stream.next()
                            filter_arguments.append(
                                KeywordArgument(
                                    token.value, parse_primitive(stream.current())
                                )
                            )
                        else:
                            # A positional query that is a single word
                            filter_arguments.append(
                                PositionalArgument(
                                    Query(
                                        token,
                                        word_to_query(token),
                                    )
                                )
                            )
                    elif is_query_token(token):
                        filter_arguments.append(
                            PositionalArgument(Query(token, token.path))
                        )
                    elif token.type_ in (
                        TokenType.INT,
                        TokenType.FLOAT,
                        TokenType.SINGLE_QUOTE_STRING,
                        TokenType.DOUBLE_QUOTE_STRING,
                        TokenType.FALSE,
                        TokenType.TRUE,
                        TokenType.NULL,
                    ):
                        filter_arguments.append(
                            PositionalArgument(parse_primitive(stream.current()))
                        )
                    elif token.type_ == TokenType.COMMA:
                        # XXX: leading, trailing and duplicate commas are OK
                        pass
                    else:
                        break

                    stream.next()

            filters.append(Filter(filter_token, filter_name, filter_arguments))

        return filters


class KeywordArgument:
    __slots__ = ("token", "name", "value")

    def __init__(self, name: str, value: Expression) -> None:
        self.token = value.token
        self.name = name
        self.value = value

    def evaluate(self, context: RenderContext) -> tuple[str, object]:
        return (self.name, self.value.evaluate(context))

    async def evaluate_async(self, context: RenderContext) -> tuple[str, object]:
        return (self.name, await self.value.evaluate_async(context))


class PositionalArgument:
    __slots__ = (
        "token",
        "value",
    )

    def __init__(self, value: Expression) -> None:
        self.token = value.token
        self.value = value

    def evaluate(self, context: RenderContext) -> tuple[None, object]:
        return (None, self.value.evaluate(context))

    async def evaluate_async(self, context: RenderContext) -> tuple[None, object]:
        return (None, await self.value.evaluate_async(context))


class SymbolArgument:
    __slots__ = (
        "token",
        "name",
    )

    def __init__(self, token: TokenT, name: str) -> None:
        self.token = token
        self.name = name


class BooleanExpression(Expression):
    __slots__ = ("expression",)

    def __init__(self, token: TokenT, expression: Expression) -> None:
        super().__init__(token=token)
        self.expression = expression

    def evaluate(self, context: RenderContext) -> object:
        return is_truthy(self.expression.evaluate(context))

    async def evaluate_async(self, context: RenderContext) -> object:
        return is_truthy(await self.expression.evaluate_async(context))

    @staticmethod
    def parse(stream: TokenStream) -> BooleanExpression:
        """Return a new BooleanExpression parsed from tokens in _stream_."""
        expr = parse_boolean_primitive(stream)
        return BooleanExpression(expr.token, expr)

    def children(self) -> list[Expression]:
        return [self.expression]


PRECEDENCE_LOWEST = 1
PRECEDENCE_LOGICALRIGHT = 2
PRECEDENCE_LOGICAL_OR = 3
PRECEDENCE_LOGICAL_AND = 4
PRECEDENCE_RELATIONAL = 5
PRECEDENCE_MEMBERSHIP = 6
PRECEDENCE_PREFIX = 7

PRECEDENCES = {
    TokenType.EQ: PRECEDENCE_RELATIONAL,
    TokenType.LT: PRECEDENCE_RELATIONAL,
    TokenType.GT: PRECEDENCE_RELATIONAL,
    TokenType.NE: PRECEDENCE_RELATIONAL,
    TokenType.LE: PRECEDENCE_RELATIONAL,
    TokenType.GE: PRECEDENCE_RELATIONAL,
    TokenType.CONTAINS: PRECEDENCE_MEMBERSHIP,
    TokenType.IN: PRECEDENCE_MEMBERSHIP,
    TokenType.AND: PRECEDENCE_LOGICAL_AND,
    TokenType.OR: PRECEDENCE_LOGICAL_OR,
    TokenType.NOT: PRECEDENCE_PREFIX,
    TokenType.RPAREN: PRECEDENCE_LOWEST,
}

BINARY_OPERATORS = frozenset(
    [
        TokenType.EQ,
        TokenType.LT,
        TokenType.GT,
        TokenType.NE,
        TokenType.LE,
        TokenType.GE,
        TokenType.CONTAINS,
        TokenType.IN,
        TokenType.AND,
        TokenType.OR,
    ]
)


def parse_boolean_primitive(  # noqa: PLR0912
    stream: TokenStream, precedence: int = PRECEDENCE_LOWEST
) -> Expression:
    """Parse a Boolean expression from tokens in _stream_."""
    left: Expression
    token = next(stream, None)

    match token:
        case Token.True_():
            left = TrueLiteral(token=token)
        case Token.False_():
            left = FalseLiteral(token=token)
        case Token.Null():
            left = Null(token=token)
        case Token.Word(value):
            if value == "empty":
                left = Empty(token=token)
            elif value == "blank":
                left = Blank(token=token)
            else:
                left = Query(token, compile(parse_query(value)))
        case Token.RangeLiteral(start, stop):
            left = RangeLiteral(token, parse_primitive(start), parse_primitive(stop))
        case Token.StringLiteral(value):
            left = StringLiteral(token, value)
        case Token.IntegerLiteral(value):
            left = IntegerLiteral(token, value)
        case Token.FloatLiteral(value):
            left = FloatLiteral(token, value)
        case Token.Query(path):
            left = Query(token, compile(path))
        case Token.Not():
            left = LogicalNotExpression.parse(stream)
        case Token.LeftParen():
            left = parse_grouped_expression(stream)
        case _:
            raise LiquidSyntaxError(
                "expected a primitive expression, "
                f"found {stream.current().__class__.__name__}",
                token=stream.current(),
            )

    while True:
        token = stream.current()
        if (
            not token
            or PRECEDENCES.get(token.__class__, PRECEDENCE_LOWEST) < precedence
        ):
            break

        if token.__class__ not in BINARY_OPERATORS:
            return left

        left = parse_infix_expression(stream, left)

    return left


def parse_infix_expression(stream: TokenStream, left: Expression) -> Expression:  # noqa: PLR0911
    """Return a logical, comparison, or membership expression parsed from _stream_."""
    token = next(stream, None)
    assert token is not None
    precedence = PRECEDENCES.get(token.__class__, PRECEDENCE_LOWEST)

    match token:
        case Token.Eq():
            return EqExpression(
                token, left, parse_boolean_primitive(stream, precedence)
            )
        case Token.Lt():
            return LtExpression(
                token, left, parse_boolean_primitive(stream, precedence)
            )
        case Token.Gt():
            return GtExpression(
                token, left, parse_boolean_primitive(stream, precedence)
            )
        case Token.Ne():
            return NeExpression(
                token, left, parse_boolean_primitive(stream, precedence)
            )
        case Token.Le():
            return LeExpression(
                token, left, parse_boolean_primitive(stream, precedence)
            )
        case Token.Ge():
            return GeExpression(
                token, left, parse_boolean_primitive(stream, precedence)
            )
        case Token.Contains():
            return ContainsExpression(
                token, left, parse_boolean_primitive(stream, precedence)
            )
        case Token.In():
            return InExpression(
                token, left, parse_boolean_primitive(stream, precedence)
            )
        case Token.And():
            return LogicalAndExpression(
                token, left, parse_boolean_primitive(stream, precedence)
            )
        case Token.Or():
            return LogicalOrExpression(
                token, left, parse_boolean_primitive(stream, precedence)
            )
        case _:
            raise LiquidSyntaxError(
                f"expected an infix expression, found {token.__class__.__name__}",
                token=token,
            )


def parse_grouped_expression(stream: TokenStream) -> Expression:
    """Parse an expression from tokens in _stream_ until the next right parenthesis."""
    expr = parse_boolean_primitive(stream)
    token = next(stream, None)

    while not isinstance(token, Token.RightParen):
        if token is None:
            raise LiquidSyntaxError("unbalanced parentheses", token=token)

        if token.__class__ not in BINARY_OPERATORS:
            raise LiquidSyntaxError(
                "expected an infix expression, "
                f"found {stream.current().__class__.__name__}",
                token=token,
            )

        expr = parse_infix_expression(stream, expr)

    if not isinstance(token, Token.RightParen):
        raise LiquidSyntaxError("unbalanced parentheses", token=token)

    return expr


class LogicalNotExpression(Expression):
    __slots__ = ("expression",)

    def __init__(self, token: TokenT, expression: Expression) -> None:
        super().__init__(token=token)
        self.expression = expression

    def evaluate(self, context: RenderContext) -> object:
        return not is_truthy(self.expression.evaluate(context))

    async def evaluate_async(self, context: RenderContext) -> object:
        return not is_truthy(await self.expression.evaluate_async(context))

    @staticmethod
    def parse(stream: TokenStream) -> Expression:
        expr = parse_boolean_primitive(stream)
        return LogicalNotExpression(expr.token, expr)

    def children(self) -> list[Expression]:
        return [self.expression]


class LogicalAndExpression(Expression):
    __slots__ = ("left", "right")

    def __init__(self, token: TokenT, left: Expression, right: Expression) -> None:
        super().__init__(token=token)
        self.left = left
        self.right = right

    def evaluate(self, context: RenderContext) -> object:
        return is_truthy(self.left.evaluate(context)) and is_truthy(
            self.right.evaluate(context)
        )

    async def evaluate_async(self, context: RenderContext) -> object:
        return is_truthy(await self.left.evaluate_async(context)) and is_truthy(
            await self.right.evaluate_async(context)
        )

    def children(self) -> list[Expression]:
        return [self.left, self.right]


class LogicalOrExpression(Expression):
    __slots__ = ("left", "right")

    def __init__(self, token: TokenT, left: Expression, right: Expression) -> None:
        super().__init__(token=token)
        self.left = left
        self.right = right

    def evaluate(self, context: RenderContext) -> object:
        return is_truthy(self.left.evaluate(context)) or is_truthy(
            self.right.evaluate(context)
        )

    async def evaluate_async(self, context: RenderContext) -> object:
        return is_truthy(await self.left.evaluate_async(context)) or is_truthy(
            await self.right.evaluate_async(context)
        )

    def children(self) -> list[Expression]:
        return [self.left, self.right]


class EqExpression(Expression):
    __slots__ = ("left", "right")

    def __init__(self, token: TokenT, left: Expression, right: Expression) -> None:
        super().__init__(token=token)
        self.left = left
        self.right = right

    def evaluate(self, context: RenderContext) -> object:
        return _eq(self.left.evaluate(context), self.right.evaluate(context))

    async def evaluate_async(self, context: RenderContext) -> object:
        return _eq(
            await self.left.evaluate_async(context),
            await self.right.evaluate_async(context),
        )

    def children(self) -> list[Expression]:
        return [self.left, self.right]


class NeExpression(Expression):
    __slots__ = ("left", "right")

    def __init__(self, token: TokenT, left: Expression, right: Expression) -> None:
        super().__init__(token=token)
        self.left = left
        self.right = right

    def evaluate(self, context: RenderContext) -> object:
        return not _eq(self.left.evaluate(context), self.right.evaluate(context))

    async def evaluate_async(self, context: RenderContext) -> object:
        return not _eq(
            await self.left.evaluate_async(context),
            await self.right.evaluate_async(context),
        )

    def children(self) -> list[Expression]:
        return [self.left, self.right]


class LeExpression(Expression):
    __slots__ = ("left", "right")

    def __init__(self, token: TokenT, left: Expression, right: Expression) -> None:
        super().__init__(token=token)
        self.left = left
        self.right = right

    def evaluate(self, context: RenderContext) -> object:
        left = self.left.evaluate(context)
        right = self.right.evaluate(context)
        return _eq(left, right) or _lt(self.token, left, right)

    async def evaluate_async(self, context: RenderContext) -> object:
        left = await self.left.evaluate_async(context)
        right = await self.right.evaluate_async(context)
        return _eq(left, right) or _lt(self.token, left, right)

    def children(self) -> list[Expression]:
        return [self.left, self.right]


class GeExpression(Expression):
    __slots__ = ("left", "right")

    def __init__(self, token: TokenT, left: Expression, right: Expression) -> None:
        super().__init__(token=token)
        self.left = left
        self.right = right

    def evaluate(self, context: RenderContext) -> object:
        left = self.left.evaluate(context)
        right = self.right.evaluate(context)
        return _eq(left, right) or _lt(self.token, right, left)

    async def evaluate_async(self, context: RenderContext) -> object:
        left = await self.left.evaluate_async(context)
        right = await self.right.evaluate_async(context)
        return _eq(left, right) or _lt(self.token, right, left)

    def children(self) -> list[Expression]:
        return [self.left, self.right]


class LtExpression(Expression):
    __slots__ = ("left", "right")

    def __init__(self, token: TokenT, left: Expression, right: Expression) -> None:
        super().__init__(token=token)
        self.left = left
        self.right = right

    def evaluate(self, context: RenderContext) -> object:
        return _lt(
            self.token, self.left.evaluate(context), self.right.evaluate(context)
        )

    async def evaluate_async(self, context: RenderContext) -> object:
        return not _eq(
            await self.left.evaluate_async(context),
            await self.right.evaluate_async(context),
        )

    def children(self) -> list[Expression]:
        return [self.left, self.right]


class GtExpression(Expression):
    __slots__ = ("left", "right")

    def __init__(self, token: TokenT, left: Expression, right: Expression) -> None:
        super().__init__(token=token)
        self.left = left
        self.right = right

    def evaluate(self, context: RenderContext) -> object:
        return _lt(
            self.token, self.right.evaluate(context), self.left.evaluate(context)
        )

    async def evaluate_async(self, context: RenderContext) -> object:
        return _lt(
            self.token,
            await self.right.evaluate_async(context),
            await self.left.evaluate_async(context),
        )

    def children(self) -> list[Expression]:
        return [self.left, self.right]


class ContainsExpression(Expression):
    __slots__ = ("left", "right")

    def __init__(self, token: TokenT, left: Expression, right: Expression) -> None:
        super().__init__(token=token)
        self.left = left
        self.right = right

    def evaluate(self, context: RenderContext) -> object:
        return _contains(
            self.token, self.left.evaluate(context), self.right.evaluate(context)
        )

    async def evaluate_async(self, context: RenderContext) -> object:
        return _contains(
            self.token,
            await self.left.evaluate_async(context),
            await self.right.evaluate_async(context),
        )

    def children(self) -> list[Expression]:
        return [self.left, self.right]


class InExpression(Expression):
    __slots__ = ("left", "right")

    def __init__(self, token: TokenT, left: Expression, right: Expression) -> None:
        super().__init__(token=token)
        self.left = left
        self.right = right

    def evaluate(self, context: RenderContext) -> object:
        return _contains(
            self.token, self.right.evaluate(context), self.left.evaluate(context)
        )

    async def evaluate_async(self, context: RenderContext) -> object:
        return _contains(
            self.token,
            await self.right.evaluate_async(context),
            await self.left.evaluate_async(context),
        )

    def children(self) -> list[Expression]:
        return [self.left, self.right]


class LoopExpression(Expression):
    __slots__ = ("identifier", "iterable", "limit", "offset", "reversed", "cols")

    def __init__(
        self,
        token: TokenT,
        identifier: str,
        iterable: Expression,
        *,
        limit: Expression | None,
        offset: Expression | None,
        reversed_: bool,
        cols: Expression | None,
    ) -> None:
        super().__init__(token)
        self.identifier = identifier
        self.iterable = iterable
        self.limit = limit
        self.offset = offset
        self.reversed = reversed_
        self.cols = cols

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, LoopExpression)
            and self.identifier == other.identifier
            and self.iterable == other.iterable
            and self.limit == other.limit
            and self.offset == other.offset
            and self.cols == other.cols
            and self.reversed == other.reversed
        )

    def __str__(self) -> str:
        buf = [f"{self.identifier} in", str(self.iterable)]

        if self.limit is not None:
            buf.append(f"limit:{self.limit}")

        if self.offset is not None:
            buf.append(f"offset:{self.offset}")

        if self.cols is not None:
            buf.append(f"cols:{self.cols}")

        if self.reversed:
            buf.append("reversed")

        return " ".join(buf)

    def _to_iter(self, obj: object) -> tuple[Iterator[Any], int]:
        if isinstance(obj, Mapping):
            return iter(obj.items()), len(obj)
        if isinstance(obj, range):
            return iter(obj), len(obj)
        if isinstance(obj, Sequence):
            return iter(obj), len(obj)

        raise LiquidTypeError(
            f"expected an iterable at '{self.iterable}', found '{obj}'",
            token=self.token,
        )

    def _eval_int(self, expr: Expression | None, context: RenderContext) -> int | None:
        if expr is None:
            return None

        val = expr.evaluate(context)
        if not isinstance(val, int):
            raise LiquidTypeError(
                f"expected an integer, found {expr.__class__.__name__}",
                token=expr.token,
            )

        return val

    async def _eval_int_async(
        self, expr: Expression | None, context: RenderContext
    ) -> int | None:
        if expr is None:
            return None

        val = await expr.evaluate_async(context)
        if not isinstance(val, int):
            raise LiquidTypeError(
                f"expected an integer, found {expr.__class__.__name__}",
                token=expr.token,
            )

        return val

    def _slice(
        self,
        it: Iterator[object],
        length: int,
        context: RenderContext,
        *,
        limit: int | None,
        offset: int | str | None,
    ) -> tuple[Iterator[object], int]:
        offset_key = f"{self.identifier}-{self.iterable}"

        if limit is None and offset is None:
            context.stopindex(key=offset_key, index=length)
            if self.reversed:
                return reversed(list(it)), length
            return it, length

        if offset == "continue":
            offset = context.stopindex(key=offset_key)
            length = max(length - offset, 0)
        elif offset is not None:
            assert isinstance(offset, int), f"found {offset!r}"
            length = max(length - offset, 0)

        if limit is not None:
            length = min(length, limit)

        stop = offset + length if offset else length
        context.stopindex(key=offset_key, index=stop)
        it = islice(it, offset, stop)

        if self.reversed:
            return reversed(list(it)), length
        return it, length

    def evaluate(self, context: RenderContext) -> tuple[Iterator[object], int]:
        it, length = self._to_iter(self.iterable.evaluate(context))
        limit = self._eval_int(self.limit, context)

        match self.offset:
            case StringLiteral(value=value):
                offset: str | int | None = value
                if offset != "continue":
                    raise LiquidSyntaxError(
                        f"expected 'continue' or an integer, found '{offset}'",
                        token=self.offset.token,
                    )
            case _offset:
                offset = self._eval_int(_offset, context)

        return self._slice(it, length, context, limit=limit, offset=offset)

    async def evaluate_async(
        self, context: RenderContext
    ) -> tuple[Iterator[object], int]:
        it, length = self._to_iter(await self.iterable.evaluate_async(context))
        limit = await self._eval_int_async(self.limit, context)

        if isinstance(self.offset, StringLiteral):
            offset: str | int | None = self.offset.evaluate(context)
            if offset != "continue":
                raise LiquidSyntaxError(
                    f"expected 'continue' or an integer, found '{offset}'",
                    token=self.offset.token,
                )
        else:
            offset = await self._eval_int_async(self.offset, context)

        return self._slice(it, length, context, limit=limit, offset=offset)

    def children(self) -> list[Expression]:
        children = [self.iterable]

        if self.limit is not None:
            children.append(self.limit)

        if self.offset is not None:
            children.append(self.offset)

        if self.cols is not None:
            children.append(self.cols)

        return children

    @staticmethod
    def parse(stream: TokenStream) -> LoopExpression:
        """Parse tokens from _stream_ in to a LoopExpression."""
        token = stream.current()
        identifier = parse_identifier(token)
        next(stream, None)
        stream.expect(Token.In)
        next(stream)  # Move past 'in'
        iterable = parse_primitive(stream.current())
        next(stream)  # Move past identifier

        reversed_ = False
        offset: Expression | None = None
        limit: Expression | None = None

        while True:
            arg_token = next(stream, None)
            match arg_token:
                case Token.Word(value):
                    match value:
                        case "reversed":
                            reversed_ = True
                        case "limit":
                            stream.expect_one_of(Token.Colon, Token.Assign)
                            next(stream)
                            limit = parse_primitive(next(stream, None))
                        case "offset":
                            stream.expect_one_of(Token.Colon, Token.Assign)
                            next(stream)
                            offset_token = next(stream, None)
                            if (
                                isinstance(offset_token, Token.Word)
                                and offset_token.value == "continue"
                            ):
                                offset = StringLiteral(
                                    token=offset_token, value="continue"
                                )
                            else:
                                offset = parse_primitive(offset_token)
                        case _:
                            raise LiquidSyntaxError(
                                "expected 'reversed', 'offset' or 'limit', "
                                f"found '{value}'",
                                token=arg_token,
                            )
                case Token.Comma():
                    continue
                case None:
                    break
                case _:
                    raise LiquidSyntaxError(
                        f"expected 'reversed', 'offset' or 'limit', found '{value}' "
                        f"of type {arg_token.__class__.__name__}",
                        token=arg_token,
                    )

        assert token is not None
        return LoopExpression(
            token,
            identifier,
            iterable,
            limit=limit,
            offset=offset,
            reversed_=reversed_,
            cols=None,
        )


class Identifier(str):
    """A string, token pair."""

    def __new__(
        cls, obj: object, *args: object, token: TokenT, **kwargs: object
    ) -> Identifier:
        instance = super().__new__(cls, obj, *args, **kwargs)
        instance.token = token
        return instance

    def __init__(
        self,
        obj: object,  # noqa: ARG002
        *args: object,  # noqa: ARG002
        token: TokenT,  # noqa: ARG002
        **kwargs: object,  # noqa: ARG002
    ) -> None:
        super().__init__()
        self.token: TokenT

    def __eq__(self, value: object) -> bool:
        return super().__eq__(value)

    def __hash__(self) -> int:
        return super().__hash__()


def parse_identifier(token: TokenT | None) -> Identifier:
    """Parse _token_ as an identifier."""
    match token:
        case Token.Word(value):
            return Identifier(value, token=token)
        case Token.Query(path):
            word = path.as_word()
            if word is None:
                raise LiquidSyntaxError(
                    "expected an identifier, found a path", token=token
                )
            return Identifier(word, token=token)
        case _:
            raise LiquidSyntaxError(
                f"expected an identifier, found {token.__class__.__name__}",
                token=token,
            )


def parse_string_or_identifier(token: TokenT | None) -> Identifier:
    """Parse _token_ as an identifier or a string literal."""
    match token:
        case Token.StringLiteral(value):
            return Identifier(value, token=token)
        case Token.Word(value):
            return Identifier(value, token=token)
        case Token.Query(path):
            word = path.as_word()
            if word is None:
                raise LiquidSyntaxError(
                    "expected an identifier, found a path", token=token
                )
            return Identifier(word, token=token)
        case _:
            raise LiquidSyntaxError(
                f"expected an identifier, found {token.__class__.__name__}",
                token=token,
            )


def parse_keyword_arguments(tokens: TokenStream) -> list[KeywordArgument]:
    """Parse _tokens_ into a list or keyword arguments.

    Argument keys and values can be separated by a colon (`:`) or an equals sign
    (`=`).
    """
    args: list[KeywordArgument] = []

    while True:
        token = tokens.next()
        match token:
            case Token.Comma():
                # XXX: Leading and/or trailing commas are OK.
                continue
            case Token.Word(value=name):
                tokens.expect_one_of(Token.Colon, Token.Assign)
                tokens.next()  # Move past ":" or "="
                value = parse_primitive(tokens.next())
                args.append(KeywordArgument(name, value))
            case Token.Query(path=path):
                word = path.as_word()
                if word is None:
                    raise LiquidSyntaxError(
                        "expected an identifier, found a path", token=token
                    )
                tokens.expect_one_of(Token.Colon, Token.Assign)
                tokens.next()  # Move past ":" or "="
                value = parse_primitive(tokens.next())
                args.append(KeywordArgument(word, value))
            case None:
                break
            case _:
                raise LiquidSyntaxError(
                    "expected a list of keyword arguments, "
                    f"found {token.__class__.__name__}",
                    token=token,
                )

    return args


def is_truthy(obj: object) -> bool:
    """Return _True_ if _obj_ is considered Liquid truthy."""
    if hasattr(obj, "__liquid__"):
        obj = obj.__liquid__()
    return not (obj is False or obj is None)


def _eq(left: object, right: object) -> bool:
    if isinstance(right, (Empty, Blank)):
        left, right = right, left

    # Remember 1 == True and 0 == False in Python
    if isinstance(right, bool):
        left, right = right, left

    if isinstance(left, bool):
        return isinstance(right, bool) and left == right

    return left == right


def _lt(token: TokenT, left: object, right: object) -> bool:
    if isinstance(left, str) and isinstance(right, str):
        return left < right

    if isinstance(left, bool) or isinstance(right, bool):
        return False

    if isinstance(left, (int, float, Decimal)) and isinstance(
        right, (int, float, Decimal)
    ):
        return left < right

    raise LiquidTypeError(
        f"'<' and '>' are not supported between '{left.__class__.__name__}' "
        f"and '{right.__class__.__name__}'",
        token=token,
    )


def _contains(token: TokenT, left: object, right: object) -> bool:
    if isinstance(left, str):
        return str(right) in left
    if isinstance(left, Collection):
        return right in left

    raise LiquidTypeError(
        f"'in' and 'contains' are not supported between '{left.__class__.__name__}' "
        f"and '{right.__class__.__name__}'",
        token=token,
    )
