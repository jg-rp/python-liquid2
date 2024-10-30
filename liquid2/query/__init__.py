from .environment import JSONPathEnvironment
from .query import JSONPathQuery

DEFAULT_ENV = JSONPathEnvironment()
parse = DEFAULT_ENV.parse

__all__ = (
    "JSONPathQuery",
    "parse",
)
