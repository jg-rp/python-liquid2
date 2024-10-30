"""The standard `count` function extension."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .filter_function import ExpressionType
from .filter_function import FilterFunction

if TYPE_CHECKING:
    from liquid2.query.node import JSONPathNodeList


class Count(FilterFunction):
    """The built-in `count` function."""

    arg_types = [ExpressionType.NODES]
    return_type = ExpressionType.VALUE

    def __call__(self, node_list: JSONPathNodeList) -> int:
        """Return the number of nodes in the node list."""
        return len(node_list)
