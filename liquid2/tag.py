"""Base class for all Liquid tags."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ast import Node
    from .environment import Environment
    from .stream import TokenStream


class Tag(ABC):
    """Base class for all built-in and custom template tags."""

    def __init__(self, env: Environment):
        self.env = env

    @abstractmethod
    def parse(self, stream: TokenStream) -> Node:
        """Return a parse tree node by parsing tokens from the given stream."""
