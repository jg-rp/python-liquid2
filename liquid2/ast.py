"""Base class for all template nodes."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import Literal
from typing import NamedTuple
from typing import TextIO

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

    @abstractmethod
    def children(self) -> list[MetaNode]:
        """Return a list of child nodes and/or expressions associated with this node."""
        # TODO: cache children?


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

    def children(self) -> list[MetaNode]:
        """Return a list of child nodes and/or expressions associated with this node."""
        return [MetaNode(token=self.token, node=node) for node in self.nodes]


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

    def children(self) -> list[MetaNode]:
        """Return a list of child nodes and/or expressions associated with this node."""
        return [MetaNode(token=self.token, expression=self.expression, node=self.block)]


class MetaNode(NamedTuple):
    """An AST node and expression pair with optional scope and load data.

    Args:
        token: The child's first token.
        expression: An `liquid.expression.Expression`. If not `None`, this expression is
            expected to be related to the given `liquid.ast.Node`.
        node: A `liquid.ast.Node`. Typically a `BlockNode` or `ConditionalBlockNode`.
        template_scope: A list of names the parent node adds to the template "local"
            scope. For example, the built-in `assign`, `capture`, `increment` and
            `decrement` tags all add names to the template scope. This helps us
            identify, through static analysis, names that are assumed to be "global".
        block_scope: A list of names available to the given child node. For example,
            the `for` tag adds the name "forloop" for the duration of its block.
        load_mode: If not `None`, indicates that the given expression should be used to
            load a partial template. In "render" mode, the partial will be analyzed in
            an isolated namespace, without access to the parent's template local scope.
            In "include" mode, the partial will have access to the parents template
            local scope and the parent's scope can be updated by the partial template
            too.
        load_context: Meta data a template `Loader` might need to find the source
            of a partial template.
    """

    token: TokenT  # XXX: every expression and node has a token already
    expression: Expression | None = None
    node: Node | None = None
    template_scope: list[Identifier] | None = None
    block_scope: list[Identifier] | None = None
    load_mode: Literal["render", "include", "extends"] | None = None
    load_context: dict[str, str] | None = None
