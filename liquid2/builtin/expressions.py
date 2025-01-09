"""Expression for built in, standard tags."""

from __future__ import annotations

import re
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
from typing import TypeAlias
from typing import TypeVar
from typing import Union
from typing import cast

from markupsafe import Markup
from markupsafe import escape

from liquid2 import PathToken
from liquid2 import RenderContext
from liquid2 import Token
from liquid2 import TokenStream
from liquid2 import TokenType
from liquid2 import is_output_token
from liquid2 import is_path_token
from liquid2 import is_range_token
from liquid2 import is_template_string_token
from liquid2 import is_token_type
from liquid2.exceptions import LiquidSyntaxError
from liquid2.exceptions import LiquidTypeError
from liquid2.expression import Expression
from liquid2.limits import to_int
from liquid2.unescape import unescape

if TYPE_CHECKING:
    from liquid2 import OutputToken
    from liquid2 import PathT
    from liquid2 import RenderContext
    from liquid2 import TokenT


class Null(Expression):
    __slots__ = ()

    def __eq__(self, other: object) -> bool:
        return other is None or isinstance(other, Null)

    def __str__(self) -> str:
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

    def __str__(self) -> str:
        return "empty"

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

    def __str__(self) -> str:
        return "blank"

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

    def __str__(self) -> str:
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

    def __str__(self) -> str:
        return "true"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, TrueLiteral) and self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)


class FalseLiteral(Literal[bool]):
    __slots__ = ()

    def __init__(self, token: TokenT) -> None:
        super().__init__(token, False)  # noqa: FBT003

    def __str__(self) -> str:
        return "false"

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


class ArrayLiteral(Expression):
    __slots__ = ("items",)

    def __init__(self, token: TokenT, items: list[Expression]):
        super().__init__(token)
        self.items = items

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ArrayLiteral) and self.items == other.items

    def __str__(self) -> str:
        return ", ".join(str(e) for e in self.items)

    def __hash__(self) -> int:
        return hash(tuple(self.items))

    def __sizeof__(self) -> int:
        return super().__sizeof__() + sys.getsizeof(self.items)

    def evaluate(self, context: RenderContext) -> list[object]:
        return [e.evaluate(context) for e in self.items]

    async def evaluate_async(self, context: RenderContext) -> list[object]:
        return [await e.evaluate_async(context) for e in self.items]

    def children(self) -> list[Expression]:
        return self.items

    @staticmethod
    def parse(stream: TokenStream, left: Expression) -> ArrayLiteral:
        items: list[Expression] = [left]
        while stream.current().type_ == TokenType.COMMA:
            stream.next()  # ignore comma
            items.append(parse_primitive(stream.current()))
            stream.next()
        return ArrayLiteral(left.token, items)


class TemplateString(Expression):
    __slots__ = ("template",)

    def __init__(self, token: TokenT, template: list[Token | OutputToken]):
        super().__init__(token)
        self.template: list[Expression] = []

        for _token in template:
            if is_token_type(_token, TokenType.SINGLE_QUOTE_STRING):
                self.template.append(
                    StringLiteral(
                        _token, unescape(_token.value.replace("\\'", "'"), token=_token)
                    )
                )
            elif is_token_type(_token, TokenType.DOUBLE_QUOTE_STRING):
                self.template.append(
                    StringLiteral(_token, unescape(_token.value, token=_token))
                )
            elif is_output_token(_token):
                self.template.append(
                    FilteredExpression.parse(TokenStream(_token.expression))
                )
            else:
                raise LiquidSyntaxError(
                    "unexpected token in template string", token=_token
                )

    def __eq__(self, other: object) -> bool:
        return isinstance(other, TemplateString) and self.template == other.template

    def __str__(self) -> str:
        return repr(
            "".join(
                e.value if isinstance(e, StringLiteral) else f"${{{e}}}"
                for e in self.template
            )
        )

    def __hash__(self) -> int:
        return hash(tuple(self.template))

    def __sizeof__(self) -> int:
        return sum(sys.getsizeof(expr) for expr in self.template)

    def evaluate(self, context: RenderContext) -> str:
        return "".join(
            _to_liquid_string(expr.evaluate(context)) for expr in self.template
        )

    async def evaluate_async(self, context: RenderContext) -> object:
        return "".join(
            [
                _to_liquid_string(await expr.evaluate_async(context))
                for expr in self.template
            ]
        )

    def children(self) -> list[Expression]:
        return self.template


RE_PROPERTY = re.compile(r"[\u0080-\uFFFFa-zA-Z_][\u0080-\uFFFFa-zA-Z0-9_-]*")
Segments: TypeAlias = tuple[Union[str, int, "Segments"], ...]


class Path(Expression):
    __slots__ = ("path",)

    def __init__(self, token: TokenT, path: PathT) -> None:
        super().__init__(token=token)
        self.path: list[Path | int | str] = []
        for segment in path:
            if isinstance(segment, PathToken):
                self.path.append(Path(segment, segment.path))
            elif isinstance(segment, str):
                self.path.append(unescape(segment, token))
            else:
                self.path.append(segment)

    def __str__(self) -> str:
        it = iter(self.path)
        buf = [str(next(it))]
        for segment in it:
            if isinstance(segment, Path):
                buf.append(f"[{segment}]")
            elif isinstance(segment, str):
                if RE_PROPERTY.fullmatch(segment):
                    buf.append(f".{segment}")
                else:
                    buf.append(f"[{segment!r}]")
            else:
                buf.append(f"[{segment}]")
        return "".join(buf)

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Path) and self.path == other.path

    def __sizeof__(self) -> int:
        return super().__sizeof__() + sys.getsizeof(self.path)

    def evaluate(self, context: RenderContext) -> object:
        return context.get(
            [p.evaluate(context) if isinstance(p, Path) else p for p in self.path],
            token=self.token,
        )

    async def evaluate_async(self, context: RenderContext) -> object:
        return await context.get_async(
            [
                await p.evaluate_async(context) if isinstance(p, Path) else p
                for p in self.path
            ],
            token=self.token,
        )

    def children(self) -> list[Expression]:
        return [p for p in self.path if isinstance(p, Path)]

    def head(self) -> int | str | Path:
        return self.path[0]

    def tail(self) -> int | str | Path:
        return self.path[-1]

    def segments(self) -> Segments:
        """Return this path's segments as a tuple of strings and ints.

        Segments can also be nested tuples of strings, ints and tuples if the path
        contains nested paths.
        """
        segments: list[str | int | Segments] = []
        for segment in self.path:
            if isinstance(segment, Path):
                segments.append(segment.segments())
            else:
                segments.append(segment)
        return tuple(segments)


Primitive = Literal[Any] | RangeLiteral | Path | Null


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

    def __str__(self) -> str:
        filters = (
            " | " + " | ".join(str(f) for f in self.filters) if self.filters else ""
        )
        return f"{self.left}{filters}"

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
        """Return a new FilteredExpression parsed from _stream_."""
        left = parse_primitive(stream.next())
        if stream.current().type_ == TokenType.COMMA:
            # Array literal syntax
            left = ArrayLiteral.parse(stream, left)
        filters = Filter.parse(stream, delim=(TokenType.PIPE,))

        if is_token_type(stream.current(), TokenType.IF):
            return TernaryFilteredExpression.parse(
                FilteredExpression(left.token, left, filters), stream
            )

        stream.expect_eos()
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
        return Path(token, [token.value])

    if is_token_type(token, TokenType.INT):
        return IntegerLiteral(token, to_int(float(token.value)))

    if is_token_type(token, TokenType.FLOAT):
        return FloatLiteral(token, float(token.value))

    if is_token_type(token, TokenType.DOUBLE_QUOTE_STRING):
        return StringLiteral(token, unescape(token.value, token=token))

    if is_token_type(token, TokenType.SINGLE_QUOTE_STRING):
        return StringLiteral(
            token, unescape(token.value.replace("\\'", "'"), token=token)
        )

    if is_template_string_token(token):
        return TemplateString(token, token.template)

    if is_path_token(token):
        return Path(token, token.path)

    if is_range_token(token):
        return RangeLiteral(
            token, parse_primitive(token.range_start), parse_primitive(token.range_stop)
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

    def __str__(self) -> str:
        buf = [f"{self.left} if {self.condition}"]

        if self.alternative:
            buf.append(f" else {self.alternative}")

        if self.filters:
            buf.append(" | " + " | ".join(str(f) for f in self.filters))

        if self.tail_filters:
            buf.append(" || " + " | ".join(str(f) for f in self.tail_filters))

        return "".join(buf)

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
        stream.next()  # move past `if`
        condition = BooleanExpression.parse(stream)
        alternative: Expression | None = None
        filters: list[Filter] | None = None
        tail_filters: list[Filter] | None = None

        if is_token_type(stream.current(), TokenType.ELSE):
            stream.next()  # move past `else`
            alternative = parse_primitive(stream.next())

            if stream.current().type_ == TokenType.PIPE:
                filters = Filter.parse(stream, delim=(TokenType.PIPE,))

        if stream.current().type_ == TokenType.DOUBLE_PIPE:
            tail_filters = Filter.parse(
                stream, delim=(TokenType.PIPE, TokenType.DOUBLE_PIPE)
            )

        stream.expect_eos()
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
            return f"{self.name}: {''.join(str(arg) for arg in self.args)}"
        return self.name

    def evaluate(self, left: object, context: RenderContext) -> object:
        func = context.filter(self.name, token=self.token)
        positional_args, keyword_args = self.evaluate_args(context)
        try:
            return func(left, *positional_args, **keyword_args)
        except TypeError as err:
            raise LiquidTypeError(str(err), token=self.token) from err
        except LiquidTypeError as err:
            err.token = self.token
            raise err

    async def evaluate_async(self, left: object, context: RenderContext) -> object:
        func = context.filter(self.name, token=self.token)
        positional_args, keyword_args = await self.evaluate_args_async(context)

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
            stream.next()
            stream.expect(TokenType.WORD)
            filter_token = cast(Token, stream.next())
            filter_name = filter_token.value
            filter_arguments: list[KeywordArgument | PositionalArgument] = []

            if stream.current().type_ == TokenType.COLON:
                stream.next()  # Move past ':'
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
                                PositionalArgument(Path(token, [token.value]))
                            )
                    elif is_template_string_token(token):
                        filter_arguments.append(
                            PositionalArgument(TemplateString(token, token.template))
                        )
                    elif is_path_token(token):
                        filter_arguments.append(
                            PositionalArgument(Path(token, token.path))
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
                        # Leading, trailing and duplicate commas are OK
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

    def __str__(self) -> str:
        return f"{self.name}:{self.value}"

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

    def __str__(self) -> str:
        return str(self.value)

    def evaluate(self, context: RenderContext) -> tuple[None, object]:
        return (None, self.value.evaluate(context))

    async def evaluate_async(self, context: RenderContext) -> tuple[None, object]:
        return (None, await self.value.evaluate_async(context))


class Parameter:
    """A name, possibly with a default value."""

    __slots__ = ("token", "name", "value")

    def __init__(self, token: TokenT, name: str, value: Expression | None) -> None:
        self.token = token
        self.name = name
        self.value = value

    def __str__(self) -> str:
        return f"{self.name}:{self.value}" if self.value else self.name


class BooleanExpression(Expression):
    __slots__ = ("expression",)

    def __init__(self, token: TokenT, expression: Expression) -> None:
        super().__init__(token=token)
        self.expression = expression

    def __str__(self) -> str:
        def _str(expression: Expression, parent_precedence: int) -> str:
            if isinstance(expression, LogicalAndExpression):
                precedence = PRECEDENCE_LOGICAL_AND
                op = "and"
                left = _str(expression.left, precedence)
                right = _str(expression.right, precedence)
            elif isinstance(expression, LogicalOrExpression):
                precedence = PRECEDENCE_LOGICAL_OR
                op = "or"
                left = _str(expression.left, precedence)
                right = _str(expression.right, precedence)
            elif isinstance(expression, LogicalNotExpression):
                operand_str = _str(expression.expression, PRECEDENCE_PREFIX)
                expr = f"not {operand_str}"
                if parent_precedence > PRECEDENCE_PREFIX:
                    return f"({expr})"
                return expr
            else:
                return str(expression)

            expr = f"{left} {op} {right}"
            if precedence < parent_precedence:
                return f"({expr})"
            return expr

        return _str(self.expression, 0)

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
    TokenType.AND_WORD: PRECEDENCE_LOGICAL_AND,
    TokenType.OR_WORD: PRECEDENCE_LOGICAL_OR,
    TokenType.NOT_WORD: PRECEDENCE_PREFIX,
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
        TokenType.AND_WORD,
        TokenType.OR_WORD,
    ]
)


def parse_boolean_primitive(  # noqa: PLR0912
    stream: TokenStream, precedence: int = PRECEDENCE_LOWEST
) -> Expression:
    """Parse a Boolean expression from tokens in _stream_."""
    left: Expression
    token = stream.next()

    if is_token_type(token, TokenType.TRUE):
        left = TrueLiteral(token=token)
    elif is_token_type(token, TokenType.FALSE):
        left = FalseLiteral(token=token)
    elif is_token_type(token, TokenType.NULL):
        left = Null(token=token)
    elif is_token_type(token, TokenType.WORD):
        if token.value == "empty":
            left = Empty(token=token)
        elif token.value == "blank":
            left = Blank(token=token)
        else:
            left = Path(token, [token.value])
    elif is_token_type(token, TokenType.INT):
        left = IntegerLiteral(token, to_int(float(token.value)))
    elif is_token_type(token, TokenType.FLOAT):
        left = FloatLiteral(token, float(token.value))
    elif is_token_type(token, TokenType.DOUBLE_QUOTE_STRING):
        left = StringLiteral(token, unescape(token.value, token=token))
    elif is_token_type(token, TokenType.SINGLE_QUOTE_STRING):
        left = StringLiteral(
            token, unescape(token.value.replace("\\'", "'"), token=token)
        )
    elif is_template_string_token(token):
        left = TemplateString(token, token.template)
    elif is_path_token(token):
        left = Path(token, token.path)
    elif is_range_token(token):
        left = RangeLiteral(
            token, parse_primitive(token.range_start), parse_primitive(token.range_stop)
        )
    elif is_token_type(token, TokenType.NOT_WORD):
        left = LogicalNotExpression.parse(stream)
    elif is_token_type(token, TokenType.LPAREN):
        left = parse_grouped_expression(stream)
    else:
        raise LiquidSyntaxError(
            f"expected a primitive expression, found {token.type_.name}",
            token=stream.current(),
        )

    while True:
        token = stream.current()
        if (
            token == stream.eoi
            or PRECEDENCES.get(token.type_, PRECEDENCE_LOWEST) < precedence
        ):
            break

        if token.type_ not in BINARY_OPERATORS:
            return left

        left = parse_infix_expression(stream, left)

    return left


def parse_infix_expression(stream: TokenStream, left: Expression) -> Expression:  # noqa: PLR0911
    """Return a logical, comparison, or membership expression parsed from _stream_."""
    token = stream.next()
    assert token is not None
    precedence = PRECEDENCES.get(token.type_, PRECEDENCE_LOWEST)

    match token.type_:
        case TokenType.EQ:
            return EqExpression(
                token, left, parse_boolean_primitive(stream, precedence)
            )
        case TokenType.LT:
            return LtExpression(
                token, left, parse_boolean_primitive(stream, precedence)
            )
        case TokenType.GT:
            return GtExpression(
                token, left, parse_boolean_primitive(stream, precedence)
            )
        case TokenType.NE:
            return NeExpression(
                token, left, parse_boolean_primitive(stream, precedence)
            )
        case TokenType.LE:
            return LeExpression(
                token, left, parse_boolean_primitive(stream, precedence)
            )
        case TokenType.GE:
            return GeExpression(
                token, left, parse_boolean_primitive(stream, precedence)
            )
        case TokenType.CONTAINS:
            return ContainsExpression(
                token, left, parse_boolean_primitive(stream, precedence)
            )
        case TokenType.IN:
            return InExpression(
                token, left, parse_boolean_primitive(stream, precedence)
            )
        case TokenType.AND_WORD:
            return LogicalAndExpression(
                token, left, parse_boolean_primitive(stream, precedence)
            )
        case TokenType.OR_WORD:
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
    token = stream.next()

    while token.type_ != TokenType.RPAREN:
        if token is None:
            raise LiquidSyntaxError("unbalanced parentheses", token=token)

        if token.type_ not in BINARY_OPERATORS:
            raise LiquidSyntaxError(
                "expected an infix expression, "
                f"found {stream.current().__class__.__name__}",
                token=token,
            )

        expr = parse_infix_expression(stream, expr)

    if token.type_ != TokenType.RPAREN:
        raise LiquidSyntaxError("unbalanced parentheses", token=token)

    return expr


class LogicalNotExpression(Expression):
    __slots__ = ("expression",)

    def __init__(self, token: TokenT, expression: Expression) -> None:
        super().__init__(token=token)
        self.expression = expression

    def __str__(self) -> str:
        return f"not {self.expression}"

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

    def __str__(self) -> str:
        return f"{self.left} and {self.right}"

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

    def __str__(self) -> str:
        return f"{self.left} or {self.right}"

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

    def __str__(self) -> str:
        return f"{self.left} == {self.right}"

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

    def __str__(self) -> str:
        return f"{self.left} != {self.right}"

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

    def __str__(self) -> str:
        return f"{self.left} <= {self.right}"

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

    def __str__(self) -> str:
        return f"{self.left} >= {self.right}"

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

    def __str__(self) -> str:
        return f"{self.left} < {self.right}"

    def evaluate(self, context: RenderContext) -> object:
        return _lt(
            self.token, self.left.evaluate(context), self.right.evaluate(context)
        )

    async def evaluate_async(self, context: RenderContext) -> object:
        return _lt(
            self.token,
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

    def __str__(self) -> str:
        return f"{self.left} > {self.right}"

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

    def __str__(self) -> str:
        return f"{self.left} contains {self.right}"

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

    def __str__(self) -> str:
        return f"{self.left} in {self.right}"

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

    def _to_int(self, obj: object, *, token: TokenT) -> int:
        try:
            return to_int(obj)
        except (ValueError, TypeError) as err:
            raise LiquidTypeError(
                f"expected an integer, found {obj.__class__.__name__}",
                token=token,
            ) from err

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
        limit = (
            self._to_int(self.limit.evaluate(context), token=self.limit.token)
            if self.limit
            else None
        )

        match self.offset:
            case StringLiteral(value=value, token=token):
                offset: str | int | None = value
                if offset != "continue":
                    offset = self._to_int(offset, token=token)
            case None:
                offset = None
            case _offset:
                offset = self._to_int(_offset.evaluate(context), token=_offset.token)

        return self._slice(it, length, context, limit=limit, offset=offset)

    async def evaluate_async(
        self, context: RenderContext
    ) -> tuple[Iterator[object], int]:
        it, length = self._to_iter(await self.iterable.evaluate_async(context))
        limit = (
            self._to_int(
                await self.limit.evaluate_async(context), token=self.limit.token
            )
            if self.limit
            else None
        )

        if self.offset is None:
            offset: str | int | None = None
        elif isinstance(self.offset, StringLiteral):
            offset = self.offset.evaluate(context)
            if offset != "continue":
                offset = self._to_int(offset, token=self.offset.token)
        else:
            offset = self._to_int(
                await self.offset.evaluate_async(context), token=self.offset.token
            )

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
        stream.next()
        stream.expect(TokenType.IN)
        stream.next()  # Move past 'in'
        iterable = parse_primitive(stream.current())
        stream.next()  # Move past identifier

        reversed_ = False
        offset: Expression | None = None
        limit: Expression | None = None
        cols: Expression | None = None

        while True:
            arg_token = stream.next()

            if is_token_type(arg_token, TokenType.WORD):
                match arg_token.value:
                    case "reversed":
                        reversed_ = True
                    case "limit":
                        stream.expect_one_of(TokenType.COLON, TokenType.ASSIGN)
                        stream.next()
                        limit = parse_primitive(stream.next())
                    case "cols":
                        stream.expect_one_of(TokenType.COLON, TokenType.ASSIGN)
                        stream.next()
                        cols = parse_primitive(stream.next())
                    case "offset":
                        stream.expect_one_of(TokenType.COLON, TokenType.ASSIGN)
                        stream.next()
                        offset_token = stream.next()
                        if (
                            is_token_type(offset_token, TokenType.WORD)
                            and offset_token.value == "continue"
                        ):
                            offset = StringLiteral(token=offset_token, value="continue")
                        else:
                            offset = parse_primitive(offset_token)
                    case _:
                        raise LiquidSyntaxError(
                            "expected 'reversed', 'offset' or 'limit', ",
                            token=arg_token,
                        )
            elif is_token_type(arg_token, TokenType.COMMA):
                continue
            elif arg_token.type_ == TokenType.EOI:
                break
            else:
                raise LiquidSyntaxError(
                    "expected 'reversed', 'offset' or 'limit'",
                    token=arg_token,
                )

        stream.expect_eos()
        assert token is not None
        return LoopExpression(
            token,
            identifier,
            iterable,
            limit=limit,
            offset=offset,
            reversed_=reversed_,
            cols=cols,
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


def parse_identifier(token: TokenT) -> Identifier:
    """Parse _token_ as an identifier."""
    if is_token_type(token, TokenType.WORD):
        return Identifier(token.value, token=token)

    raise LiquidSyntaxError(
        f"expected an identifier, found {token.type_.name}",
        token=token,
    )


def parse_string_or_identifier(token: TokenT) -> Identifier:
    """Parse _token_ as an identifier or a string literal.

    Excludes template strings.
    """
    if is_token_type(token, TokenType.DOUBLE_QUOTE_STRING):
        return Identifier(unescape(token.value, token=token), token=token)

    if is_token_type(token, TokenType.SINGLE_QUOTE_STRING):
        return Identifier(
            unescape(token.value.replace("\\'", "'"), token=token), token=token
        )

    if is_token_type(token, TokenType.WORD):
        return Identifier(token.value, token=token)

    raise LiquidSyntaxError(
        f"expected an identifier, found {token.type_.name}",
        token=token,
    )


def parse_string_or_path(token: TokenT) -> StringLiteral | Path:
    """Parse _token_ as a string literal or a path.

    Excludes template strings.
    """
    if is_token_type(token, TokenType.WORD):
        return Path(token, [token.value])

    if is_token_type(token, TokenType.DOUBLE_QUOTE_STRING):
        return StringLiteral(token, unescape(token.value, token=token))

    if is_token_type(token, TokenType.SINGLE_QUOTE_STRING):
        return StringLiteral(
            token, unescape(token.value.replace("\\'", "'"), token=token)
        )

    if is_path_token(token):
        return Path(token, token.path)

    raise LiquidSyntaxError(
        f"expected a string or path, found {token.type_.name}",
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

        if is_token_type(token, TokenType.COMMA):
            # Leading and/or trailing commas are OK.
            token = tokens.next()

        if token.type_ == TokenType.EOI:
            break

        if is_token_type(token, TokenType.WORD):
            tokens.expect_one_of(TokenType.COLON, TokenType.ASSIGN)
            tokens.next()  # Move past ":" or "="
            value = parse_primitive(tokens.next())
            args.append(KeywordArgument(token.value, value))
        else:
            raise LiquidSyntaxError(
                f"expected an argument name, found {token.type_.name}",
                token=token,
            )

    return args


def parse_positional_and_keyword_arguments(
    tokens: TokenStream,
) -> tuple[list[PositionalArgument], list[KeywordArgument]]:
    """Parse _tokens_ into a lists of keyword and positional arguments.

    Argument keys and values can be separated by a colon (`:`) or an equals sign
    (`=`).
    """
    args: list[PositionalArgument] = []
    kwargs: list[KeywordArgument] = []

    while True:
        token = tokens.next()

        if is_token_type(token, TokenType.COMMA):
            # Leading and/or trailing commas are OK.
            token = tokens.next()

        if token.type_ == TokenType.EOI:
            break

        if is_token_type(token, TokenType.WORD) and tokens.current().type_ in (
            TokenType.COLON,
            TokenType.ASSIGN,
        ):
            # A keyword argument
            tokens.next()  # Move past ":" or "="
            value = parse_primitive(tokens.next())
            kwargs.append(KeywordArgument(token.value, value))
        else:
            # A primitive as a positional argument
            args.append(PositionalArgument(parse_primitive(token)))

    return args, kwargs


def parse_parameters(tokens: TokenStream) -> dict[str, Parameter]:
    """Parse _tokens_ as a list of arguments suitable for a macro definition."""
    params: dict[str, Parameter] = {}

    while True:
        token = tokens.next()

        if is_token_type(token, TokenType.COMMA):
            # Leading and/or trailing commas are OK.
            token = tokens.next()

        if token.type_ == TokenType.EOI:
            break

        if is_token_type(token, TokenType.WORD):
            if tokens.current().type_ in (
                TokenType.COLON,
                TokenType.ASSIGN,
            ):
                # A parameter with a default value
                tokens.next()  # Move past ":" or "="
                value = parse_primitive(tokens.next())
                params[token.value] = Parameter(token, token.value, value)
            else:
                params[token.value] = Parameter(token, token.value, None)
        else:
            raise LiquidSyntaxError(
                f"expected a parameter list, found {token.type_.name}",
                token=token,
            )

    return params


def is_truthy(obj: object) -> bool:
    """Return _True_ if _obj_ is considered Liquid truthy."""
    if hasattr(obj, "__liquid__"):
        obj = obj.__liquid__()
    return not (obj is False or obj is None)


def _eq(left: object, right: object) -> bool:
    if hasattr(left, "__liquid__"):
        left = left.__liquid__()

    if hasattr(right, "__liquid__"):
        right = right.__liquid__()

    if isinstance(right, (Empty, Blank)):
        left, right = right, left

    # Remember 1 == True and 0 == False in Python
    if isinstance(right, bool):
        left, right = right, left

    if isinstance(left, bool):
        return isinstance(right, bool) and left == right

    return left == right


def _lt(token: TokenT, left: object, right: object) -> bool:
    if hasattr(left, "__liquid__"):
        left = left.__liquid__()

    if hasattr(right, "__liquid__"):
        right = right.__liquid__()

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


def _to_liquid_string(val: Any, *, auto_escape: bool = False) -> str:
    """Stringify a Python object ready for output in a Liquid template."""
    if isinstance(val, str) or (auto_escape and hasattr(val, "__html__")):
        pass
    elif isinstance(val, bool):
        val = str(val).lower()
    elif val is None:
        val = ""
    elif isinstance(val, range):
        val = f"{val.start}..{val.stop - 1}"
    elif isinstance(val, Sequence):
        if auto_escape:
            val = Markup("").join(
                _to_liquid_string(itm, auto_escape=auto_escape) for itm in val
            )
        else:
            val = "".join(
                _to_liquid_string(itm, auto_escape=auto_escape) for itm in val
            )
    elif isinstance(val, (Empty, Blank)):
        val = ""
    else:
        val = str(val)

    if auto_escape:
        val = escape(val)

    assert isinstance(val, str)
    return val
