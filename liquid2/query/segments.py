"""JSONPath child and descendant segment definitions."""

from __future__ import annotations

import random
from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Iterable
from typing import Mapping
from typing import Sequence
from typing import Tuple

from .exceptions import JSONPathRecursionError
from .selectors import NameSelector
from .selectors import WildcardSelector

if TYPE_CHECKING:
    from liquid2.token import Token

    from .environment import JSONPathEnvironment
    from .node import JSONPathNode
    from .query import SelectorTuple
    from .selectors import JSONPathSelector


class JSONPathSegment(ABC):
    """Base class for all JSONPath segments."""

    __slots__ = ("env", "token", "selectors")

    def __init__(
        self,
        *,
        env: JSONPathEnvironment,
        token: Token,
        selectors: Tuple[JSONPathSelector, ...],
    ) -> None:
        self.env = env
        self.token = token
        self.selectors = selectors

    @abstractmethod
    def resolve(self, nodes: Iterable[JSONPathNode]) -> Iterable[JSONPathNode]:
        """Apply this segment to each `JSONPathNode` in _nodes_."""

    def as_tuple(self) -> SelectorTuple | str:
        """Return this segment's selectors as a tuple of strings or nested tuples."""
        if len(self.selectors) == 1:
            return self.selectors[0].as_tuple()
        return tuple(selector.as_tuple() for selector in self.selectors)


class JSONPathChildSegment(JSONPathSegment):
    """The JSONPath child selection segment."""

    def resolve(self, nodes: Iterable[JSONPathNode]) -> Iterable[JSONPathNode]:
        """Select children of each node in _nodes_."""
        for node in nodes:
            for selector in self.selectors:
                yield from selector.resolve(node)

    def __str__(self) -> str:
        return f"[{', '.join(str(itm) for itm in self.selectors)}]"

    def __eq__(self, __value: object) -> bool:
        return (
            isinstance(__value, JSONPathChildSegment)
            and self.selectors == __value.selectors
            and self.token == __value.token
        )

    def __hash__(self) -> int:
        return hash((self.selectors, self.token))


class JSONPathRecursiveDescentSegment(JSONPathSegment):
    """The JSONPath recursive descent segment."""

    def resolve(self, nodes: Iterable[JSONPathNode]) -> Iterable[JSONPathNode]:
        """Select descendants of each node in _nodes_."""
        for node in nodes:
            for _node in self._visit(node):
                for selector in self.selectors:
                    yield from selector.resolve(_node)

    def _visit(self, node: JSONPathNode, depth: int = 1) -> Iterable[JSONPathNode]:
        """Depth-first, pre-order node traversal."""
        if depth > self.env.max_recursion_depth:
            raise JSONPathRecursionError("recursion limit exceeded", token=self.token)

        yield node

        if isinstance(node.value, Mapping):
            for name, val in node.value.items():
                if isinstance(val, (Mapping, Sequence)):
                    _node = node.new_child(val, name)
                    yield from self._visit(_node, depth + 1)
        elif not isinstance(node.value, str) and isinstance(node.value, Sequence):
            for i, element in enumerate(node.value):
                if isinstance(element, (Mapping, Sequence)):
                    _node = node.new_child(element, i)
                    yield from self._visit(_node, depth + 1)

    def __str__(self) -> str:
        if len(self.selectors) == 1:
            match self.selectors[0]:
                case NameSelector(name=name):
                    return f"..{name}"
                case WildcardSelector():
                    return "..*"

        return f"..[{', '.join(str(itm) for itm in self.selectors)}]"

    def __eq__(self, __value: object) -> bool:
        return (
            isinstance(__value, JSONPathRecursiveDescentSegment)
            and self.selectors == __value.selectors
        )

    def __hash__(self) -> int:
        return hash(("..", self.selectors, self.token))
