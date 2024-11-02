"""JSONPath configuration.

A JSONPathEnvironment is where you'd register functions extensions and
control recursion limits, for example.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Type
from typing import Union

from . import function_extensions
from .exceptions import JSONPathNameError
from .exceptions import JSONPathTypeError
from .filter_expressions import ComparisonExpression
from .filter_expressions import FilterExpressionLiteral
from .filter_expressions import FilterQuery
from .filter_expressions import FunctionExtension
from .filter_expressions import LogicalExpression
from .function_extensions import ExpressionType
from .function_extensions import FilterFunction
from .parse import Parser
from .query import JSONPathQuery

if TYPE_CHECKING:
    from liquid2.token import Token

    from .filter_expressions import Expression


JSONValue = Union[
    Sequence[Any],
    Mapping[str, Any],
    str,
    int,
    float,
    None,
    bool,
]
"""JSON-like data, as you would get from `json.load()`."""


class JSONPathEnvironment:
    """JSONPath configuration.

    ## Class attributes

    Attributes:
        max_int_index (int): The maximum integer allowed when selecting array items by
            index. Defaults to `(2**53) - 1`.
        min_int_index (int): The minimum integer allowed when selecting array items by
            index. Defaults to `-(2**53) + 1`.
        max_recursion_depth (int): The maximum number of dict/objects and/or
            arrays/lists the recursive descent selector can visit before a
            `JSONPathRecursionError` is thrown.
        parser_class (Parser): The parser to use when parsing tokens from the lexer.
        nondeterministic (bool): If `True`, enable nondeterminism when iterating objects
            and visiting nodes with the recursive descent segment. Defaults to `False`.
    """

    parser_class: Type[Parser] = Parser

    max_int_index = (2**53) - 1
    min_int_index = -(2**53) + 1
    max_recursion_depth = 100

    nondeterministic = False

    def __init__(self) -> None:
        self.parser: Parser = self.parser_class(env=self)
        """The parser bound to this environment."""

        self.function_extensions: dict[str, FilterFunction] = {}
        """A list of function extensions available to filters."""

        self.setup_function_extensions()

    def parse(self, tokens: list[Token]) -> JSONPathQuery:  # noqa: A003
        """Prepare a JSONPath expression ready for repeated application.

        Arguments:
            tokens: Tokens produces by the lexer.

        Returns:
            A `JSONPathQuery` ready to match against a JSON-like value.

        Raises:
            JSONPathSyntaxError: If _query_ is invalid.
            JSONPathTypeError: If filter functions are given arguments of an
                unacceptable type.
        """
        return JSONPathQuery(
            env=self, segments=tuple(self.parser.parse(tokens)), token=tokens[0]
        )

    def setup_function_extensions(self) -> None:
        """Initialize function extensions."""
        self.function_extensions["length"] = function_extensions.Length()
        self.function_extensions["count"] = function_extensions.Count()
        self.function_extensions["match"] = function_extensions.Match()
        self.function_extensions["search"] = function_extensions.Search()
        self.function_extensions["value"] = function_extensions.Value()

    def validate_function_extension_signature(
        self, token: Token, args: list[Any]
    ) -> list[Any]:
        """Compile-time validation of function extension arguments."""
        try:
            func = self.function_extensions[token.value]
        except KeyError as err:
            raise JSONPathNameError(
                f"function {token.value!r} is not defined", token=token
            ) from err

        self.check_well_typedness(token, func, args)
        return args

    def check_well_typedness(
        self,
        token: Token,
        func: FilterFunction,
        args: list[Expression],
    ) -> None:
        """Check the well-typedness of a function's arguments at compile-time."""
        # Correct number of arguments?
        if len(args) != len(func.arg_types):
            raise JSONPathTypeError(
                f"{token.value!r}() requires {len(func.arg_types)} arguments",
                token=token,
            )

        # Argument types
        for idx, typ in enumerate(func.arg_types):
            arg = args[idx]
            if typ == ExpressionType.VALUE:
                if not (
                    isinstance(arg, FilterExpressionLiteral)
                    or (isinstance(arg, FilterQuery) and arg.query.singular_query())
                    or (self._function_return_type(arg) == ExpressionType.VALUE)
                ):
                    raise JSONPathTypeError(
                        f"{token.value}() argument {idx} must be of ValueType",
                        token=token,
                    )
            elif typ == ExpressionType.LOGICAL:
                if not isinstance(
                    arg, (FilterQuery, LogicalExpression, ComparisonExpression)
                ):
                    raise JSONPathTypeError(
                        f"{token.value}() argument {idx} must be of LogicalType",
                        token=token,
                    )
            elif typ == ExpressionType.NODES and not (
                isinstance(arg, FilterQuery)
                or self._function_return_type(arg) == ExpressionType.NODES
            ):
                raise JSONPathTypeError(
                    f"{token.value}() argument {idx} must be of NodesType",
                    token=token,
                )

    def _function_return_type(self, expr: Expression) -> Optional[ExpressionType]:
        """Return a filter function's return type.

        Returns `None` if _expr_ is not a function expression.
        """
        if not isinstance(expr, FunctionExtension):
            return None
        func = self.function_extensions.get(expr.name)
        if isinstance(func, FilterFunction):
            return func.return_type
        return None
