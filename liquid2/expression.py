"""Base class for all Liquid expressions."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Iterable

if TYPE_CHECKING:
    from liquid2 import TokenT

    from .context import RenderContext


class Expression(ABC):
    """Base class for all Liquid expressions."""

    __slots__ = ("token",)

    def __init__(self, token: TokenT) -> None:
        self.token = token

    @abstractmethod
    def evaluate(self, context: RenderContext) -> object:
        """Evaluate the expression in the given render context."""

    async def evaluate_async(self, context: RenderContext) -> object:
        """An async version of `liquid.expression.Expression.evaluate`."""
        return self.evaluate(context)

    @abstractmethod
    def children(self) -> Iterable[Expression]:
        """Return this expression's child expressions."""
