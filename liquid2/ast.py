"""Base class for all template nodes."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from enum import auto
from typing import TYPE_CHECKING
from typing import Iterable
from typing import TextIO

from liquid2.expression import Expression

from .context import RenderContext
from .exceptions import DisabledTagError
from .token import is_tag_token

if TYPE_CHECKING:
    from .builtin import BooleanExpression
    from .builtin import Identifier
    from .context import RenderContext
    from .expression import Expression
    from .token import TokenT


class Node(ABC):
    """Base class for all template nodes."""

    __slots__ = ("token",)

    def __init__(self, token: TokenT) -> None:
        super().__init__()
        self.token = token

    def render(self, context: RenderContext, buffer: TextIO) -> int:
        """Write this node's content to _buffer_."""
        if context.disabled_tags:
            self.raise_for_disabled(context.disabled_tags)
        return self.render_to_output(context, buffer)

    async def render_async(self, context: RenderContext, buffer: TextIO) -> int:
        """Write this node's content to _buffer_."""
        if context.disabled_tags:
            self.raise_for_disabled(context.disabled_tags)
        return await self.render_to_output_async(context, buffer)

    @abstractmethod
    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer.

        Return:
            The number of "characters" written to the output buffer.
        """

    async def render_to_output_async(
        self, context: RenderContext, buffer: TextIO
    ) -> int:
        """An async version of _render_to_output_."""
        return self.render_to_output(context, buffer)

    def raise_for_disabled(self, disabled_tags: set[str]) -> None:
        """Raise a `DisabledTagError` if this node has a name in _disabled_tags_."""
        token = self.token
        if is_tag_token(token) and token.name in disabled_tags:
            raise DisabledTagError(
                f"{token.name} usage is not allowed in this context",
                token=token,
            )

    def children(
        self,
        _static_context: RenderContext,
        *,
        _include_partials: bool = True,
    ) -> Iterable[Node]:
        """Return this node's children."""
        return []

    # TODO: children_async

    def expressions(self) -> Iterable[Expression]:
        """Return this node's expressions."""
        return []

    def template_scope(self) -> Iterable[Identifier]:
        """Return variables this node adds to the template local scope."""
        return []

    def block_scope(self) -> Iterable[Identifier]:
        """Return variables this node adds to the node's block scope."""
        return []

    def partial_scope(self) -> Partial | None:
        """Return information about a partial template loaded by this node."""
        return None


class PartialScope(Enum):
    """The kind of scope a partial template should have when loaded."""

    SHARED = auto()
    ISOLATED = auto()
    INHERITED = auto()


@dataclass(kw_only=True, slots=True)
class Partial:
    """Partial template meta data."""

    name: Expression
    """An expression resolving to the name associated with the partial template."""

    scope: PartialScope
    """The kind of scope the partial template should have when loaded."""

    in_scope: Iterable[Identifier]
    """Names that will be added to the partial template scope."""


class BlockNode(Node):
    """A node containing a sequence of other nodes."""

    __slots__ = ("nodes",)

    def __init__(self, token: TokenT, nodes: list[Node]) -> None:
        super().__init__(token)
        self.nodes = nodes

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        return sum(node.render(context, buffer) for node in self.nodes)

    async def render_to_output_async(
        self, context: RenderContext, buffer: TextIO
    ) -> int:
        """Render the node to the output buffer."""
        return sum([await node.render_async(context, buffer) for node in self.nodes])

    def children(
        self, _static_context: RenderContext, *, _include_partials: bool = True
    ) -> Iterable[Node]:
        """Return this node's children."""
        return self.nodes


class ConditionalBlockNode(Node):
    """A node containing a sequence of other nodes guarded by a Boolean expression."""

    __slots__ = ("block", "expression")

    def __init__(
        self,
        token: TokenT,
        block: BlockNode,
        expression: BooleanExpression,
    ) -> None:
        super().__init__(token)
        self.block = block
        self.expression = expression

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        if self.expression.evaluate(context):
            return self.block.render(context, buffer)
        return 0

    async def render_to_output_async(
        self, context: RenderContext, buffer: TextIO
    ) -> int:
        """Render the node to the output buffer."""
        if await self.expression.evaluate_async(context):
            return await self.block.render_async(context, buffer)
        return 0

    def children(
        self, _static_context: RenderContext, *, _include_partials: bool = True
    ) -> Iterable[Node]:
        """Return this node's children."""
        yield self.block

    def expressions(self) -> Iterable[Expression]:
        """Return this node's expressions."""
        yield self.expression
