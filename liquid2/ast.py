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
from .output import NullIO
from .token import TagToken
from .token import is_tag_token

if TYPE_CHECKING:
    from .builtin import BooleanExpression
    from .builtin import Identifier
    from .context import RenderContext
    from .expression import Expression
    from .token import TokenT


class Node(ABC):
    """Base class for all template nodes."""

    __slots__ = ("token", "blank")

    def __init__(self, token: TokenT) -> None:
        super().__init__()
        self.token = token

        self.blank = True
        """If True, indicates that the node, when rendered, produces no output text
        or only whitespace.
        
        The output node (`{{ something }}`) and echo tag are exception. Even if they
        evaluate to an empty or blank string, they are not considered "blank".
        """

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
        static_context: RenderContext,  # noqa: ARG002
        *,
        include_partials: bool = True,  # noqa: ARG002
    ) -> Iterable[Node]:
        """Return this node's children."""
        return []

    async def children_async(
        self,
        static_context: RenderContext,
        *,
        include_partials: bool = True,
    ) -> Iterable[Node]:
        """An async version of `children()`."""
        return self.children(static_context, include_partials=include_partials)

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
        self.blank = all(node.blank for node in nodes)

    def __str__(self) -> str:
        return "".join(str(n) for n in self.nodes)

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        if context.env.suppress_blank_control_flow_blocks and self.blank:
            buf = NullIO()
            for node in self.nodes:
                node.render(context, buf)
            return 0
        return sum(node.render(context, buffer) for node in self.nodes)

    async def render_to_output_async(
        self, context: RenderContext, buffer: TextIO
    ) -> int:
        """Render the node to the output buffer."""
        if context.env.suppress_blank_control_flow_blocks and self.blank:
            buf = NullIO()
            for node in self.nodes:
                await node.render_async(context, buf)
            return 0
        return sum([await node.render_async(context, buffer) for node in self.nodes])

    def children(
        self,
        static_context: RenderContext,  # noqa: ARG002
        *,
        include_partials: bool = True,  # noqa: ARG002
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
        self.blank = block.blank

    def __str__(self) -> str:
        assert isinstance(self.token, TagToken)
        return (
            f"{{%{self.token.wc[0]} elsif {self.expression} {self.token.wc[1]}%}}"
            f"{self.block}"
        )

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
        self,
        static_context: RenderContext,  # noqa: ARG002
        *,
        include_partials: bool = True,  # noqa: ARG002
    ) -> Iterable[Node]:
        """Return this node's children."""
        yield self.block

    def expressions(self) -> Iterable[Expression]:
        """Return this node's expressions."""
        yield self.expression
