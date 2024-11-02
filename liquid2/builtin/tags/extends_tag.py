"""The standard _extends_ and _block_ tags."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import DefaultDict
from typing import Iterator
from typing import Mapping
from typing import Sequence
from typing import TextIO

from markupsafe import Markup as Markupsafe

from liquid2 import Markup
from liquid2 import Token
from liquid2.ast import BlockNode as TemplateBlock
from liquid2.ast import MetaNode
from liquid2.ast import Node
from liquid2.builtin import Identifier
from liquid2.builtin import StringLiteral
from liquid2.builtin import parse_string_or_identifier
from liquid2.exceptions import RequiredBlockError
from liquid2.exceptions import StopRender
from liquid2.exceptions import TemplateInheritanceError
from liquid2.tag import Tag
from liquid2.tokens import TokenStream

if TYPE_CHECKING:
    from liquid2 import Template
    from liquid2 import TokenT
    from liquid2.context import RenderContext


class ExtendsNode(Node):
    """The standard _extends_ tag."""

    __slots__ = ("name",)
    tag = "extends"

    def __init__(self, token: TokenT, name: StringLiteral) -> None:
        super().__init__(token)
        self.name = name

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        base_template = build_block_stacks(
            context,
            context.template,
            self.name.value,
            "extends",
        )

        base_template.render_with_context(context, buffer)
        context.tag_namespace["extends"].clear()
        raise StopRender

    async def render_to_output_async(
        self, context: RenderContext, buffer: TextIO
    ) -> int:
        """Render the node to the output buffer."""
        base_template = await build_block_stacks_async(
            context,
            context.template,
            self.name.value,
            "extends",
        )

        await base_template.render_with_context_async(context, buffer)
        context.tag_namespace["extends"].clear()
        raise StopRender

    def children(self) -> list[MetaNode]:
        """Return a list of child nodes and/or expressions associated with this node."""
        return [
            MetaNode(
                token=self.name.token,
                expression=self.name,
                load_mode="extends",
                load_context={"tag": self.tag},
            )
        ]


class ExtendsTag(Tag):
    """The standard _extends_ tag."""

    block = False
    node_class = ExtendsNode

    def parse(self, stream: TokenStream) -> Node:
        """Parse tokens from _stream_ into an AST node."""
        token = stream.current()
        assert isinstance(token, Markup.Tag)

        tokens = TokenStream(token.expression)
        name_token = tokens.next()
        assert name_token is not None
        name = parse_string_or_identifier(name_token)
        tokens.expect_eos()

        return self.node_class(
            token=token, name=StringLiteral(token=name_token, value=name)
        )


class BlockNode(Node):
    """The standard _block_ tag."""

    __slots__ = ("name", "block", "required")
    tag = "block"

    def __init__(
        self, token: TokenT, name: str, block: TemplateBlock, *, required: bool
    ) -> None:
        super().__init__(token)
        self.name = name
        self.block = block
        self.required = required

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        # We should be in a base template. Render the block at the top of the "stack".
        block_stack: Sequence[_BlockStackItem] = context.tag_namespace.get(
            "extends", {}
        ).get(self.name)

        if not block_stack:
            # This base template is being rendered directly.
            if self.required:
                raise RequiredBlockError(
                    f"block {self.name!r} must be overridden", token=self.token
                )
            with context.extend(
                {
                    "block": BlockDrop(
                        token=self.token,
                        context=context,
                        buffer=buffer,
                        name=self.name,
                        parent=None,
                    )
                }
            ):
                return self.block.render(context, buffer)

        stack_item = block_stack[0]

        if stack_item.required:
            raise RequiredBlockError(
                f"block {self.name!r} must be overridden",
                token=self.token,
                filename=stack_item.source_name,
            )

        ctx = context.copy(
            token=self.token,
            namespace={
                "block": BlockDrop(
                    token=self.token,
                    context=context,
                    buffer=buffer,
                    name=self.name,
                    parent=stack_item.parent,
                )
            },
            carry_loop_iterations=True,
            block_scope=True,
        )

        return stack_item.block.block.render(ctx, buffer)

    async def render_to_output_async(
        self, context: RenderContext, buffer: TextIO
    ) -> int:
        """Render the node to the output buffer."""
        # We should be in a base template. Render the block at the top of the "stack".
        block_stack: Sequence[_BlockStackItem] = context.tag_namespace.get(
            "extends", {}
        ).get(self.name)

        if not block_stack:
            # This base template is being rendered directly.
            if self.required:
                raise RequiredBlockError(
                    f"block {self.name!r} must be overridden", token=self.token
                )
            with context.extend(
                {
                    "block": BlockDrop(
                        token=self.token,
                        context=context,
                        buffer=buffer,
                        name=self.name,
                        parent=None,
                    )
                }
            ):
                return await self.block.render_async(context, buffer)

        stack_item = block_stack[0]

        if stack_item.required:
            raise RequiredBlockError(
                f"block {self.name!r} must be overridden",
                token=self.token,
                filename=stack_item.source_name,
            )

        ctx = context.copy(
            token=self.token,
            namespace={
                "block": BlockDrop(
                    token=self.token,
                    context=context,
                    buffer=buffer,
                    name=self.name,
                    parent=stack_item.parent,
                )
            },
            carry_loop_iterations=True,
            block_scope=True,
        )
        return await stack_item.block.block.render_async(ctx, buffer)

    def children(self) -> list[MetaNode]:
        """Return a list of child nodes and/or expressions associated with this node."""
        return [
            MetaNode(
                token=self.token,
                node=self.block,
                block_scope=[Identifier("block", token=self.token)],
            )
        ]


class BlockTag(Tag):
    """The standard _extends_ tag."""

    block = True
    node_class = BlockNode
    end_block = frozenset(["endblock"])

    def parse(self, stream: TokenStream) -> Node:
        """Parse tokens from _stream_ into an AST node."""
        token = stream.current()
        assert isinstance(token, Markup.Tag)

        tokens = TokenStream(token.expression)
        block_name = parse_string_or_identifier(tokens.next())
        required = isinstance(tokens.next(), Token.Required)
        tokens.expect_eos()

        block_token = stream.next()
        assert block_token is not None  # TODO:
        block = TemplateBlock(
            block_token, self.env.parser.parse_block(stream, end=self.end_block)
        )

        stream.expect_tag("endblock")
        end_block_token = stream.current()
        assert isinstance(end_block_token, Markup.Tag)

        if end_block_token.expression is not None:
            tokens = TokenStream(end_block_token.expression)
            if tokens.current() is not None:
                end_block_name = parse_string_or_identifier(tokens.current())
                if end_block_name != block_name:
                    raise TemplateInheritanceError(
                        f"expected endblock for '{block_name}, "
                        f"found '{end_block_name}'",
                        token=end_block_token,
                    )
                tokens.next()
            tokens.expect_eos()

        return self.node_class(
            token=token, name=block_name, block=block, required=required
        )


@dataclass
class _BlockStackItem:
    token: TokenT
    block: BlockNode
    required: bool
    source_name: str
    parent: _BlockStackItem | None = None


class BlockDrop(Mapping[str, object]):
    """A `block` object with a `super` property."""

    __slots__ = ("token", "buffer", "context", "name", "parent")

    def __init__(
        self,
        *,
        token: TokenT,
        context: RenderContext,
        buffer: TextIO,
        name: str,
        parent: _BlockStackItem | None,
    ) -> None:
        self.token = token
        self.buffer = buffer
        self.context = context
        self.name = name
        self.parent = parent

    def __str__(self) -> str:  # pragma: no cover
        return f"BlockDrop({self.name})"

    def __getitem__(self, key: str) -> object:
        if key != "super":
            raise KeyError(key)

        if not self.parent:
            return self.context.env.undefined("super", token=self.token)

        # NOTE: We're not allowing chaining of references to `super` for now.
        # Just the immediate parent.
        buf = self.context.get_output_buffer(self.buffer)
        with self.context.extend(
            {
                "block": BlockDrop(
                    token=self.parent.token,
                    context=self.context,
                    buffer=buf,
                    name=self.parent.source_name,
                    parent=self.parent.parent,
                )
            }
        ):
            self.parent.block.block.render(self.context, buf)

        if self.context.auto_escape:
            return Markupsafe(buf.getvalue())
        return buf.getvalue()

    def __len__(self) -> int:  # pragma: no cover
        return 1

    def __iter__(self) -> Iterator[str]:  # pragma: no cover
        return iter(["super"])


def build_block_stacks(
    context: RenderContext,
    template: Template,
    parent_name: str,
    tag: str,
) -> Template:
    """Build a stack for each `{% block %}` in the inheritance chain.

    Blocks defined in the base template will be at the top of the stack.

    Args:
        context: A render context to build the block stacks in.
        template: A leaf template with an `extends` tag.
        parent_name: The name of the immediate parent template as a string.
        tag: The name of the `extends` tag, if it is overridden.
    """
    # Guard against recursive `extends`.
    seen: set[str] = set()

    extends_node, _ = stack_blocks(context, template)
    parent = context.env.get_template(parent_name, context=context, tag=tag)
    assert extends_node
    seen.add(extends_node.name.value)

    extends_node, _ = stack_blocks(context, parent)

    if extends_node:
        parent_template_name: str | None = extends_node.name.value
        assert parent_template_name
        if parent_template_name in seen:
            raise TemplateInheritanceError(
                f"circular extends {parent_template_name!r}",
                token=extends_node.token,
                filename=template.name,
            )
        seen.add(parent_template_name)
    else:
        parent_template_name = None

    while parent_template_name:
        parent = context.env.get_template(
            parent_template_name, context=context, tag=tag
        )
        extends_node, _ = stack_blocks(context, parent)

        if extends_node:
            parent_template_name = extends_node.name.value
            assert parent_template_name
            if parent_template_name in seen:
                raise TemplateInheritanceError(
                    f"circular extends {parent_template_name!r}",
                    token=extends_node.token,
                    filename=parent.name,
                )
            seen.add(parent_template_name)
        else:
            parent_template_name = None

    return parent


async def build_block_stacks_async(
    context: RenderContext,
    template: Template,
    parent_name: str,
    tag: str,
) -> Template:
    """Build a stack for each `{% block %}` in the inheritance chain.

    Blocks defined in the base template will be at the top of the stack.

    Args:
        context: A render context to build the block stacks in.
        template: A leaf template with an `extends` tag.
        parent_name: The name of the immediate parent template as a string.
        tag: The name of the `extends` tag, if it is overridden.
    """
    if "extends" not in context.tag_namespace:
        context.tag_namespace["extends"] = defaultdict(list)

    # Guard against recursive `extends`.
    seen: set[str] = set()

    extends_node, _ = stack_blocks(context, template)
    parent = await context.env.get_template_async(parent_name, context=context, tag=tag)
    assert extends_node
    seen.add(extends_node.name.value)

    extends_node, _ = stack_blocks(context, parent)

    if extends_node:
        parent_template_name: str | None = extends_node.name.value
        assert parent_template_name
        if parent_template_name in seen:
            raise TemplateInheritanceError(
                f"circular extends {parent_template_name!r}",
                token=extends_node.token,
                filename=template.name,
            )
        seen.add(parent_template_name)
    else:
        parent_template_name = None

    while parent_template_name:
        parent = await context.env.get_template_async(
            parent_template_name, context=context, tag=tag
        )
        extends_node, _ = stack_blocks(context, parent)

        if extends_node:
            parent_template_name = extends_node.name.value
            assert parent_template_name
            if parent_template_name in seen:
                raise TemplateInheritanceError(
                    f"circular extends {parent_template_name!r}",
                    token=extends_node.token,
                    filename=parent.name,
                )
            seen.add(parent_template_name)
        else:
            parent_template_name = None

    return parent


def find_inheritance_nodes(
    template: Template,
) -> tuple[list["ExtendsNode"], list[BlockNode]]:
    """Return lists of `extends` and `block` nodes from the given template."""
    extends_nodes: list["ExtendsNode"] = []
    block_nodes: list[BlockNode] = []

    for node in template.nodes:
        _visit_node(
            node,
            extends_nodes=extends_nodes,
            block_nodes=block_nodes,
        )

    return extends_nodes, block_nodes


def _visit_node(
    node: Node,
    extends_nodes: list["ExtendsNode"],
    block_nodes: list[BlockNode],
) -> None:
    if isinstance(node, BlockNode):
        block_nodes.append(node)

    if isinstance(node, ExtendsNode):
        extends_nodes.append(node)

    for child in node.children():
        if child.node:
            _visit_node(
                child.node,
                extends_nodes=extends_nodes,
                block_nodes=block_nodes,
            )


def stack_blocks(
    context: RenderContext, template: Template
) -> tuple[ExtendsNode | None, list[BlockNode]]:
    """Find template inheritance nodes in `template`.

    Each node found is pushed on to the appropriate block stack.
    """
    extends, blocks = find_inheritance_nodes(template)
    template_name = str(template.path or template.name)

    if len(extends) > 1:
        raise TemplateInheritanceError(
            "too many 'extends' tags",
            token=extends[1].token,
            filename=template_name,
        )

    seen_block_names: set[str] = set()
    for block in blocks:
        if block.name in seen_block_names:
            raise TemplateInheritanceError(
                f"duplicate block {block.name}",
                token=block.token,
            )
        seen_block_names.add(block.name)

    _store_blocks(context, blocks, template_name)

    if not extends:
        return None, blocks
    # return extends[0].name.evaluate(context), blocks
    return extends[0], blocks


def _store_blocks(
    context: RenderContext, blocks: list[BlockNode], source_name: str
) -> None:
    block_stacks: DefaultDict[str, list[_BlockStackItem]] = context.tag_namespace[
        "extends"
    ]

    for block in blocks:
        stack = block_stacks[block.name]
        required = False if stack and not block.required else block.required

        stack.append(
            _BlockStackItem(
                token=block.token,
                block=block,
                required=required,
                source_name=source_name,
            )
        )

        if len(stack) > 1:
            stack[-2].parent = stack[-1]
