from liquid2 import Token
from liquid2 import TokenType

from .environment import JSONPathEnvironment
from .environment import JSONValue
from .query import JSONPathQuery

DEFAULT_ENV = JSONPathEnvironment()
parse_query = DEFAULT_ENV.parse

Query = JSONPathQuery


def word_to_query(token: Token) -> JSONPathQuery:
    """Return _word_ as a JSONPath query containing a single shorthand name selector."""
    return parse_query(
        [
            Token(
                type_=TokenType.PROPERTY,
                value=token.value,
                index=token.index,
                source=token.source,
            )
        ]
    )


__all__ = (
    "JSONPathQuery",
    "JSONValue",
    "Query",
    "parse_query",
    "word_to_query",
)
