"""The standard `match` function extension."""

import re

from liquid2.query.function_extensions import ExpressionType
from liquid2.query.function_extensions import FilterFunction

from ._pattern import map_re


class Match(FilterFunction):
    """The standard `match` function."""

    arg_types = [ExpressionType.VALUE, ExpressionType.VALUE]
    return_type = ExpressionType.LOGICAL

    def __call__(self, string: str, pattern: object) -> bool:
        """Return `True` if _string_ matches _pattern_, or `False` otherwise."""
        if not isinstance(pattern, str):
            return False

        try:
            # re.fullmatch caches compiled patterns internally
            return bool(re.fullmatch(map_re(pattern), string))
        except (TypeError, re.error):
            return False
