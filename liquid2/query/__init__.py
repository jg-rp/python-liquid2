from liquid2 import Token
from liquid2 import TokenType

from .environment import JSONPathEnvironment
from .query import JSONPathQuery

DEFAULT_ENV = JSONPathEnvironment()
parse = DEFAULT_ENV.parse

Query = JSONPathQuery


def word_to_query(token: Token) -> JSONPathQuery:
    """Return _word_ as a JSONPath query containing a single shorthand name selector."""
    return parse(
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
    "Query",
    "parse",
    "word_to_query",
)
