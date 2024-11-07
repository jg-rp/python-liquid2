"""Analyze variable, tag and filter usage by traversing a template's syntax tree."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import DefaultDict
from typing import Literal

from .ast import BlockNode
from .ast import ConditionalBlockNode
from .builtin import FilteredExpression
from .builtin import Identifier
from .builtin import Path
from .builtin import StringLiteral
from .builtin import TernaryFilteredExpression
from .builtin.tags.case_tag import MultiExpressionBlockNode
from .builtin.tags.extends_tag import BlockNode as InheritanceBlockNode
from .builtin.tags.extends_tag import _BlockStackItem
from .builtin.tags.extends_tag import stack_blocks
from .context import RenderContext
from .exceptions import StopRender
from .exceptions import TemplateInheritanceError
from .exceptions import TemplateNotFound
from .exceptions import TemplateTraversalError
from .token import is_lines_token
from .token import is_tag_token
from .utils import ReadOnlyChainMap

if TYPE_CHECKING:
    from . import TokenT
    from .ast import MetaNode
    from .ast import Node
    from .expression import Expression
    from .template import Template

RE_SPLIT_IDENT = re.compile(r"(\.|\[)")


@dataclass(slots=True)
class Span:
    """The location of a variable, tag or filter in a template."""

    template_name: str
    start: int
    end: int

    def __str__(self) -> str:
        return f"{self.template_name}[{self.start}:{self.end}]"


@dataclass(frozen=True, kw_only=True)
class TemplateAnalysis:
    """The result of analyzing a template using `Template.analyze()`.

    Args:
        variables: All referenced variables, whether they are in scope or not.
            Including references to names such as `forloop` from the `for` tag.
        local_variables: Template variables that are added to the template local
            scope, whether they are subsequently used or not.
        global_variables: Template variables that, on the given line number and
            "file", are out of scope or are assumed to be "global". That is, expected to
            be included by the application developer rather than a template author.
        failed_visits: Names of AST `Node` and `Expression` objects that
            could not be visited, probably because they do not implement a `children`
            method.
        unloadable_partials: Names or identifiers of partial templates that
            could not be loaded. This will be empty if `follow_partials` is `False`.
        filters: All filters found during static analysis.
        tags: All tags found during static analysis.
    """

    variables: dict[Path, list[Span]]
    local_variables: dict[Identifier, list[Span]]
    global_variables: dict[Path, list[Span]]
    failed_visits: dict[str, list[Span]]
    unloadable_partials: dict[str, list[Span]]
    filters: dict[str, list[Span]]
    tags: dict[str, list[Span]]


class _TemplateCounter:
    """Count references to variable names in a Liquid template.

    Args:
        template: The Liquid template to analyze.
        follow_partials: If `True`, the reference counter will try to load partial
            templates and count variable references in those partials too. Default's to
            `True`.
        raise_for_failures: If `True`, will raise an exception if an `ast.Node` or
            `expression.Expression` does not define a `children()` method, or if a
            partial template can not be loaded.

            When `False`, no exception is raised and a mapping of failed
            nodes/expressions is available as the `failed_visits` property. A mapping of
            unloadable partial templates are stored in the `unloadable_partials`
            property.
    """

    def __init__(
        self,
        template: Template,
        *,
        follow_partials: bool = True,
        raise_for_failures: bool = True,
        scope: None | ReadOnlyChainMap = None,
        template_locals: None | DefaultDict[Identifier, list[Span]] = None,
        partial_locals: None | DefaultDict[Identifier, list[Span]] = None,
        partials: None | list[tuple[str, None | dict[str, str]]] = None,
    ) -> None:
        self.template = template
        self._template_name = self.template.name or "<string>"
        self.follow_partials = follow_partials
        self.raise_for_failures = raise_for_failures

        # Names that are added to the template "local" scope.
        self.template_locals: DefaultDict[Identifier, list[Span]] = (
            template_locals if template_locals is not None else defaultdict(list)
        )

        self.partial_locals: DefaultDict[Identifier, list[Span]] = (
            partial_locals if partial_locals is not None else defaultdict(list)
        )

        # Names that are referenced but are not in the template local scope
        self.template_globals: DefaultDict[Path, list[Span]] = defaultdict(list)

        # Names that are referenced by a Liquid expression.
        self.variables: DefaultDict[Path, list[Span]] = defaultdict(list)

        # Tag and filter names.
        self.filters: dict[str, list[Span]] = defaultdict(list)
        self.tags: dict[str, list[Span]] = defaultdict(list)

        # Nodes and Expressions that don't implement a `children()` method.
        self.failed_visits: dict[str, list[Span]] = defaultdict(list)

        # Tags that load templates with an expression that can not be analyzed
        # statically.
        self.unloadable_partials: dict[str, list[Span]] = defaultdict(list)

        # Block scoped names.
        self._scope = scope if scope is not None else ReadOnlyChainMap()

        # Partial templates (include, render, etc.)
        self._partials = partials if partials is not None else []

        self._empty_context = RenderContext(self.template)

    def analyze(self) -> _TemplateCounter:
        """Traverse the template's syntax tree and count variables as we go.

        It is not safe to call this method multiple times.
        """
        for node in self.template.nodes:
            try:
                self._analyze(node)
            except StopRender:
                break

        self._raise_for_failures()
        return self

    async def analyze_async(self) -> _TemplateCounter:
        """An async version of `_TemplateVariableCounter.analyze()`."""
        for node in self.template.nodes:
            try:
                await self._analyze_async(node)
            except StopRender:
                break

        self._raise_for_failures()
        return self

    def _analyze(self, node: Node) -> None:
        self._count_tag(node)

        for child in node.children():
            self._analyze_expression(child)
            self._expression_hook(child)
            self._update_template_scope(child)

            if child.block_scope:
                self._scope.push({n: None for n in child.block_scope})

            if self.follow_partials:
                if child.load_mode == "include":
                    self._analyze_include(child)
                elif child.load_mode == "render":
                    self._analyze_render(child)
                elif child.load_mode == "extends":
                    self._analyze_template_inheritance_chain(child, self.template)
                    raise StopRender("stop static analysis")
                elif child.load_mode is not None:
                    raise TemplateTraversalError(
                        f"unknown load mode '{child.load_mode}'"
                    )

            # Recurse
            if child.node:
                self._analyze(child.node)

            if child.block_scope:
                self._scope.pop()

    async def _analyze_async(self, node: Node) -> None:
        self._count_tag(node)

        for child in node.children():
            self._analyze_expression(child)
            await self._async_expression_hook(child)
            self._update_template_scope(child)

            if child.block_scope:
                self._scope.push({n: None for n in child.block_scope})

            if self.follow_partials:
                if child.load_mode == "include":
                    await self._analyze_include_async(child)
                elif child.load_mode == "render":
                    await self._analyze_render_async(child)
                elif child.load_mode == "extends":
                    await self._analyze_template_inheritance_chain_async(
                        child, self.template
                    )
                    raise StopRender("stop static analysis")
                elif child.load_mode is not None:
                    raise TemplateTraversalError(
                        f"unknown load mode '{child.load_mode}'"
                    )

            # Recurse
            if child.node:
                await self._analyze_async(child.node)

            if child.block_scope:
                self._scope.pop()

    def _analyze_expression(self, child: MetaNode) -> None:
        if not child.expression:
            return

        refs = self._update_expression_refs(child.expression)
        for query, token in refs.queries:
            self.variables[query].append(
                Span(self._template_name, token.start, token.stop)
            )

        # Check refs that are not in scope or in the local namespace before
        # pushing the next block scope. This should highlight names that are
        # expected to be "global".
        for query, token in refs.queries:
            _query = query.head()
            if (
                _query not in self._scope
                and Identifier(_query, token=token) not in self.template_locals
            ):
                self.template_globals[query].append(
                    Span(self._template_name, token.start, token.stop)
                )

        for filter_name, token in refs.filters:
            self.filters[filter_name].append(
                Span(self._template_name, token.start, token.stop)
            )

    def _update_template_scope(self, child: MetaNode) -> None:
        if not child.template_scope:
            return

        for name in child.template_scope:
            self.template_locals[name].append(
                Span(self._template_name, name.token.start, name.token.stop)
            )

    def _update_expression_refs(self, expression: Expression) -> References:
        """Return a list of references used in the given expression."""
        refs: References = References()

        if isinstance(expression, Path):
            refs.append_variable(expression, expression.token)

        elif isinstance(expression, FilteredExpression):
            refs.append_filters([(f.name, f.token) for f in expression.filters or []])

        elif isinstance(expression, TernaryFilteredExpression):
            refs.append_filters([(f.name, f.token) for f in expression.filters or []])
            refs.append_filters(
                [(f.name, f.token) for f in expression.tail_filters or []]
            )

        for expr in expression.children():
            refs.extend(self._update_expression_refs(expr))

        return refs

    def _analyze_include(self, child: MetaNode) -> None:
        name, load_context = self._make_load_context(child, "include")
        if name is None or load_context is None:
            return

        try:
            template = self._get_template(
                name, load_context, self._template_name, child
            )
        except TemplateNotFound:
            return

        # Partial templates rendered in "include" mode share the same template local
        # namespace as their parent template. Note that block scoped variables have
        # already been pushed and will be popped by the caller.
        refs = _TemplateCounter(
            template,
            follow_partials=self.follow_partials,
            scope=self._scope,
            template_locals=self.template_locals,
            partial_locals=self.partial_locals,
            raise_for_failures=self.raise_for_failures,
            partials=self._partials,
        ).analyze()

        self._update_reference_counters(refs)

    async def _analyze_include_async(self, child: MetaNode) -> None:
        name, load_context = self._make_load_context(child, "include")
        if name is None or load_context is None:
            return

        try:
            template = await self._get_template_async(
                name, load_context, self._template_name, child
            )
        except TemplateNotFound:
            return

        refs = await _TemplateCounter(
            template,
            follow_partials=self.follow_partials,
            scope=self._scope,
            template_locals=self.template_locals,
            partial_locals=self.partial_locals,
            raise_for_failures=self.raise_for_failures,
            partials=self._partials,
        ).analyze_async()

        self._update_reference_counters(refs)

    def _analyze_render(self, child: MetaNode) -> None:
        name, load_context = self._make_load_context(child, "render")
        if name is None or load_context is None:
            return

        try:
            template = self._get_template(
                name, load_context, self._template_name, child
            )
        except TemplateNotFound:
            return

        # Partial templates rendered in "render" mode do not share the parent template
        # local namespace. We do not pass the current block scope stack to "rendered"
        # templates either.
        scope: dict[str, object] = (
            {n: None for n in child.block_scope} if child.block_scope else {}
        )

        refs = _TemplateCounter(
            template,
            follow_partials=self.follow_partials,
            scope=ReadOnlyChainMap(scope),
            raise_for_failures=self.raise_for_failures,
            partials=self._partials,
        ).analyze()

        self._update_reference_counters(refs, update_locals=True)

    async def _analyze_render_async(self, child: MetaNode) -> None:
        name, load_context = self._make_load_context(child, "render")
        if name is None or load_context is None:
            return

        try:
            template = await self._get_template_async(
                name, load_context, self._template_name, child
            )
        except TemplateNotFound:
            return

        scope: dict[str, object] = (
            {n: None for n in child.block_scope} if child.block_scope else {}
        )

        refs = await _TemplateCounter(
            template,
            follow_partials=self.follow_partials,
            scope=ReadOnlyChainMap(scope),
            raise_for_failures=self.raise_for_failures,
            partials=self._partials,
        ).analyze_async()

        self._update_reference_counters(refs, update_locals=True)

    def _analyze_template_inheritance_chain(
        self,
        node: MetaNode,
        template: Template,
    ) -> None:
        name, load_context = self._make_load_context(node, "extends")
        if name is None or load_context is None:
            return

        stack_context = self._empty_context.copy(
            node.token, namespace={}, template=template
        )
        stack_context.tag_namespace["extends"] = defaultdict(list)

        # Guard against recursive `extends`.
        seen: set[str] = set()

        # Add blocks from the leaf template to the stack context.
        extends_name, _ = self._stack_blocks(stack_context, template, count_tags=False)
        assert extends_name
        seen.add(extends_name)

        try:
            parent = self._get_template(name, load_context, self._template_name, node)
        except TemplateNotFound:
            return

        parent_template_name, _ = self._stack_blocks(stack_context, parent)

        if parent_template_name:
            if parent_template_name in seen:
                raise TemplateInheritanceError(
                    f"circular extends {parent_template_name!r}",
                    token=node.token,
                    filename=template.name,
                )
            seen.add(parent_template_name)

        while parent_template_name:
            try:
                parent = self._get_template(
                    parent_template_name, load_context, self._template_name, node
                )
            except TemplateNotFound:
                return

            parent_template_name, _ = self._stack_blocks(stack_context, parent)
            if parent_template_name:
                if parent_template_name in seen:
                    raise TemplateInheritanceError(
                        f"circular extends {parent_template_name!r}", token=node.token
                    )
                seen.add(parent_template_name)

        refs = _InheritanceChainCounter(
            parent,
            stack_context,
            follow_partials=self.follow_partials,
            scope=ReadOnlyChainMap({"block": None}, self._scope),
            template_locals=self.template_locals,
            partial_locals=self.partial_locals,
            raise_for_failures=self.raise_for_failures,
            partials=self._partials,
        ).analyze()

        self._update_reference_counters(refs)

    async def _analyze_template_inheritance_chain_async(
        self, node: MetaNode, template: Template
    ) -> None:
        name, load_context = self._make_load_context(node, "extends")
        if name is None or load_context is None:
            return

        stack_context = self._empty_context.copy(token=node.token, namespace={})
        stack_context.tag_namespace["extends"] = defaultdict(list)

        # Guard against recursive `extends`.
        seen: set[str] = set()

        # Add blocks from the leaf template to the stack context.
        extends_name, _ = self._stack_blocks(stack_context, template, count_tags=False)
        assert extends_name
        seen.add(extends_name)

        try:
            parent = await self._get_template_async(
                name, load_context, self._template_name, node
            )
        except TemplateNotFound:
            return

        parent_template_name, _ = self._stack_blocks(stack_context, parent)

        if parent_template_name:
            if parent_template_name in seen:
                raise TemplateInheritanceError(
                    f"circular extends {parent_template_name!r}",
                    token=node.token,
                    filename=template.name,
                )
            seen.add(parent_template_name)

        while parent_template_name:
            try:
                parent = await self._get_template_async(
                    parent_template_name, load_context, self._template_name, node
                )
            except TemplateNotFound:
                return

            parent_template_name, _ = self._stack_blocks(stack_context, parent)
            if parent_template_name:
                if parent_template_name in seen:
                    raise TemplateInheritanceError(
                        f"circular extends {parent_template_name!r}", token=node.token
                    )
                seen.add(parent_template_name)

        refs = await _InheritanceChainCounter(
            parent,
            stack_context,
            follow_partials=self.follow_partials,
            scope=ReadOnlyChainMap({"block": None}, self._scope),
            template_locals=self.template_locals,
            partial_locals=self.partial_locals,
            raise_for_failures=self.raise_for_failures,
            partials=self._partials,
        ).analyze_async()

        self._update_reference_counters(refs)

    def _make_load_context(
        self, child: MetaNode, load_mode: Literal["extends", "include", "render"]
    ) -> tuple[str | None, dict[str, str] | None]:
        # Partial templates rendered in "include" mode might use a variable template
        # name. We can't statically analyze a partial template unless it's name is a
        # literal string (or possibly an integer, but unlikely).
        if load_mode == "include" and not isinstance(child.expression, StringLiteral):
            self.unloadable_partials[str(child.expression)].append(
                Span(self._template_name, child.token.start, child.token.stop)
            )
            return None, None

        if not isinstance(child.expression, StringLiteral):
            raise TemplateTraversalError(
                f"can't load from a variable expression when in {load_mode!r} mode",
                token=child.token,
            )

        name = child.expression.value
        load_context = child.load_context or {}

        if (name, load_context) in self._partials:
            return None, None

        self._partials.append((name, load_context))
        return name, load_context

    def _get_template(
        self,
        name: str,
        load_context: dict[str, str],
        parent_name: str,
        parent_node: MetaNode,
    ) -> Template:
        try:
            return self._empty_context.env.get_template(
                name,
                global_context_data=None,
                context=None,
                **load_context,
            )
        except TemplateNotFound:
            self.unloadable_partials[name].append(
                Span(parent_name, parent_node.token.start, parent_node.token.stop)
            )
            raise

    async def _get_template_async(
        self,
        name: str,
        load_context: dict[str, str],
        parent_name: str,
        parent_node: MetaNode,
    ) -> Template:
        try:
            return await self._empty_context.env.get_template_async(
                name,
                global_context_data=None,
                context=None,
                **load_context,
            )
        except TemplateNotFound:
            self.unloadable_partials[name].append(
                Span(parent_name, parent_node.token.start, parent_node.token.stop)
            )
            raise

    def _stack_blocks(
        self,
        stack_context: RenderContext,
        template: Template,
        *,
        count_tags: bool = True,
    ) -> tuple[str | None, list[InheritanceBlockNode]]:
        template_name = template.name or "<string>"
        ast_extends_node, ast_block_nodes = stack_blocks(stack_context, template)

        # Count `extends` and `block` tags here, as we don't get the chance later.
        if count_tags and ast_extends_node:
            self.tags[ast_extends_node.tag].append(
                Span(
                    template_name,
                    ast_extends_node.token.start,
                    ast_extends_node.token.stop,
                )
            )

        for ast_node in ast_block_nodes:
            self.tags[ast_node.tag].append(
                Span(template_name, ast_node.token.start, ast_node.token.stop)
            )

        if ast_extends_node:
            return ast_extends_node.name.value, ast_block_nodes
        return None, ast_block_nodes

    def _count_tag(self, node: Node) -> None:
        token = node.token
        if not isinstance(
            node, (BlockNode, ConditionalBlockNode, MultiExpressionBlockNode)
        ) and (is_tag_token(token) or is_lines_token(token)):
            self.tags[token.name].append(
                Span(self._template_name, token.start, token.stop)
            )

    def _update_reference_counters(
        self, refs: _TemplateCounter, *, update_locals: bool = False
    ) -> None:
        # Accumulate references from the partial/child template into its parent.
        for query, locations in refs.variables.items():
            self.variables[query].extend(locations)

        if update_locals:
            for ident, locations in refs.template_locals.items():
                self.partial_locals[ident].extend(locations)

        for query, locations in refs.template_globals.items():
            self.template_globals[query].extend(locations)

        for node_name, locations in refs.failed_visits.items():
            self.failed_visits[node_name].extend(locations)

        for template_name, locations in refs.unloadable_partials.items():
            self.unloadable_partials[template_name].extend(locations)

        for filter_name, locations in refs.filters.items():
            self.filters[filter_name].extend(locations)

        for tag_name, locations in refs.tags.items():
            self.tags[tag_name].extend(locations)

    def _raise_for_failures(self) -> None:
        if self.raise_for_failures and self.failed_visits:
            msg_target = next(iter(self.failed_visits.keys()))
            if len(self.failed_visits) > 1:
                msg = (
                    f"{msg_target} (+{len(self.failed_visits) -1} more) "
                    "does not implement a 'children' method"
                )
            else:
                msg = f"{msg_target} does not implement a 'children' method"
            raise TemplateTraversalError(f"failed visit: {msg}", token=None)

        if self.raise_for_failures and self.unloadable_partials:
            msg_target = next(iter(self.unloadable_partials.keys()))
            if len(self.unloadable_partials) > 1:
                msg = (
                    f"partial template '{msg_target}' "
                    f"(+{len(self.unloadable_partials) -1} more) "
                    "could not be loaded"
                )
            else:
                msg = f"partial template '{msg_target}' could not be loaded"
            raise TemplateTraversalError(f"failed visit: {msg}", token=None)

    def _expression_hook(self, child: MetaNode) -> None:
        pass

    async def _async_expression_hook(self, child: MetaNode) -> None:
        pass


class _InheritanceChainCounter(_TemplateCounter):
    def __init__(
        self,
        base_template: Template,
        stack_context: RenderContext,
        *,
        parent_block_stack_item: _BlockStackItem | None = None,
        follow_partials: bool = True,
        raise_for_failures: bool = True,
        scope: ReadOnlyChainMap | None = None,
        template_locals: DefaultDict[Identifier, list[Span]] | None = None,
        partial_locals: DefaultDict[Identifier, list[Span]] | None = None,
        partials: list[tuple[str, dict[str, str] | None]] | None = None,
    ) -> None:
        self.stack_context = stack_context
        self.parent_block_stack_item = parent_block_stack_item
        super().__init__(
            template=base_template,
            follow_partials=follow_partials,
            raise_for_failures=raise_for_failures,
            scope=scope,
            template_locals=template_locals,
            partial_locals=partial_locals,
            partials=partials,
        )

    def _analyze(self, node: Node) -> None:
        if isinstance(node, InheritanceBlockNode):
            return self._analyze_block(node)
        return super()._analyze(node)

    async def _analyze_async(self, node: Node) -> None:
        if isinstance(node, InheritanceBlockNode):
            return await self._analyze_block_async(node)
        return await super()._analyze_async(node)

    def _expression_hook(self, child: MetaNode) -> None:
        expression = child.expression
        if not expression:
            return

        if not self.parent_block_stack_item:
            return

        if self._contains_super(expression):
            template = self._make_template(self.parent_block_stack_item)
            scope: dict[str, object] = {ident: None for ident in self.template_locals}
            refs = _InheritanceChainCounter(
                template,
                self.stack_context,
                follow_partials=self.follow_partials,
                scope=ReadOnlyChainMap({"block": None}, self._scope, scope),
                raise_for_failures=self.raise_for_failures,
                partials=self._partials,
            ).analyze()

            self._update_reference_counters(refs)

    async def _async_expression_hook(self, child: MetaNode) -> None:
        expression = child.expression
        if not expression:
            return

        if not self.parent_block_stack_item:
            return

        if self._contains_super(expression):
            template = self._make_template(self.parent_block_stack_item)
            scope: dict[str, object] = {ident: None for ident in self.template_locals}
            refs = await _InheritanceChainCounter(
                template,
                self.stack_context,
                follow_partials=self.follow_partials,
                scope=ReadOnlyChainMap({"block": None}, self._scope, scope),
                raise_for_failures=self.raise_for_failures,
                partials=self._partials,
            ).analyze_async()

            self._update_reference_counters(refs)

    def _contains_super(self, expression: Expression) -> bool:
        if (
            isinstance(expression, Path)
            and expression.head() == "block"
            and expression.tail() == "super"
        ):
            return True

        # XXX: TODO: TernaryFilteredExpression

        if isinstance(expression, FilteredExpression) and (
            isinstance(expression.left, Path)
            and expression.left.head() == "block"
            and expression.left.tail() == "super"
        ):
            return True

        return any(self._contains_super(expr) for expr in expression.children())

    def _analyze_block(self, block: InheritanceBlockNode) -> None:
        block_stacks: dict[str, list[_BlockStackItem]] = (
            self.stack_context.tag_namespace["extends"]
        )

        block_stack_item = block_stacks[block.name][0]
        template = self._make_template(block_stack_item)
        scope: dict[str, object] = {ident: None for ident in self.template_locals}

        refs = _InheritanceChainCounter(
            template,
            self.stack_context,
            follow_partials=self.follow_partials,
            scope=ReadOnlyChainMap({"block": None}, self._scope, scope),
            raise_for_failures=self.raise_for_failures,
            partials=self._partials,
            parent_block_stack_item=block_stack_item.parent,
        ).analyze()

        self._update_reference_counters(refs)

    async def _analyze_block_async(self, block: InheritanceBlockNode) -> None:
        block_stacks: dict[str, list[_BlockStackItem]] = (
            self.stack_context.tag_namespace["extends"]
        )

        block_stack_item = block_stacks[block.name][0]
        template = self._make_template(block_stack_item)
        scope: dict[str, object] = {ident: None for ident in self.template_locals}

        refs = await _InheritanceChainCounter(
            template,
            self.stack_context,
            follow_partials=self.follow_partials,
            scope=ReadOnlyChainMap({"block": None}, self._scope, scope),
            raise_for_failures=self.raise_for_failures,
            partials=self._partials,
            parent_block_stack_item=block_stack_item.parent,
        ).analyze_async()

        self._update_reference_counters(refs)

    def _make_template(self, item: _BlockStackItem) -> Template:
        return self.template.env.template_class(
            self.template.env,
            nodes=[item.block.block],
            name=item.source_name,
        )


class References:
    """Collect references for Template.analyze and friends."""

    def __init__(self) -> None:
        self.queries: list[tuple[Path, TokenT]] = []
        self.filters: list[tuple[str, TokenT]] = []

    def append_variable(self, var: Path, token: TokenT) -> None:
        """Add a variable reference."""
        self.queries.append((var, token))

    def append_filters(self, filters: list[tuple[str, TokenT]]) -> None:
        """Add references to filters."""
        self.filters.extend(filters)

    def extend(self, refs: References) -> None:
        """Incorporate references from another References."""
        self.queries.extend(refs.queries)
        self.filters.extend(refs.filters)
