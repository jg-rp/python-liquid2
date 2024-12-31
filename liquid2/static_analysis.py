"""Analyze variable, tag and filter usage by traversing a template's syntax tree."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
from typing import Iterable
from typing import TypeAlias
from typing import Union

from .ast import BlockNode
from .ast import ConditionalBlockNode
from .ast import PartialScope
from .builtin import FilteredExpression
from .builtin import Path
from .builtin import TernaryFilteredExpression
from .builtin.tags.case_tag import MultiExpressionBlockNode
from .context import RenderContext
from .token import is_lines_token
from .token import is_tag_token

if TYPE_CHECKING:
    from .ast import Node
    from .expression import Expression
    from .template import Template


RE_PROPERTY = re.compile(r"[\u0080-\uFFFFa-zA-Z_][\u0080-\uFFFFa-zA-Z0-9_-]*")


@dataclass(slots=True)
class Span:
    """The location of a variable, tag or filter in a template."""

    template_name: str
    start: int
    end: int


Segments: TypeAlias = list[Union[int, str, "Segments"]]


@dataclass(slots=True, frozen=True)
class Variable:
    """A variable as sequence of segments that make up its path and its location.

    Variables with the same segments compare equal, regardless of span.
    """

    segments: Segments
    span: Span = field(hash=False, compare=False)

    def __str__(self) -> str:
        return self._segments_str(self.segments)

    def _segments_str(self, segments: Segments) -> str:
        it = iter(segments)
        buf = [str(next(it))]

        for segment in it:
            if isinstance(segment, list):
                buf.append(f"[{self._segments_str(segment)}]")
            elif isinstance(segment, str):
                if RE_PROPERTY.fullmatch(segment):
                    buf.append(f".{segment}")
                else:
                    buf.append(f"[{segment!r}]")
            else:
                buf.append(f"[{segment}]")
        return "".join(buf)

    def __hash__(self) -> int:
        return hash(str(self))


class _StaticScope:
    def __init__(self, globals: set[str]) -> None:
        self.stack = [globals]

    def __contains__(self, key: str) -> bool:
        return any(key in scope for scope in self.stack)

    def push(self, scope: set[str]) -> _StaticScope:
        self.stack.append(scope)
        return self

    def pop(self) -> set[str]:
        return self.stack.pop()

    def add(self, name: str) -> None:
        """Add a name to the root/template scope."""
        self.stack[0].add(name)


class _VariableMap:
    def __init__(self) -> None:
        self._data: dict[str, list[Variable]] = {}

    def __getitem__(self, var: Variable) -> list[Variable]:
        k = str(var.segments[0])
        if k not in self._data:
            self._data[k] = []
        return self._data[k]

    def add(self, var: Variable) -> None:
        self[var].append(var)

    def as_dict(self) -> dict[str, list[Variable]]:
        return self._data


@dataclass(frozen=True, kw_only=True)
class TemplateAnalysis:
    """The result of analyzing a template using `Template.analyze()`.

    Args:
        variables: All referenced variables, whether they are in scope or not.
            Including references to names such as `forloop` from the `for` tag.
        locals: Template variables that are added to the template local
            scope, whether they are subsequently used or not.
        globals: Template variables that, on the given line number and
            "file", are out of scope or are assumed to be "global". That is, expected to
            be included by the application developer rather than a template author.
        filters: All filters found during static analysis.
        tags: All tags found during static analysis.
    """

    variables: dict[str, list[Variable]]
    globals: dict[str, list[Variable]]
    locals: dict[str, list[Variable]]
    filters: dict[str, list[Span]]
    tags: dict[str, list[Span]]


def _analyze(template: Template, *, include_partials: bool) -> TemplateAnalysis:
    variables = _VariableMap()
    globals = _VariableMap()  # noqa: A001
    locals = _VariableMap()  # noqa: A001

    filters: defaultdict[str, list[Span]] = defaultdict(list)
    tags: defaultdict[str, list[Span]] = defaultdict(list)

    template_scope: set[str] = set()
    root_scope = _StaticScope(template_scope)
    static_context = RenderContext(template)

    # Names of partial templates that have already been analyzed.
    seen: set[str] = set()

    def _visit(node: Node, template_name: str, scope: _StaticScope) -> None:
        if template_name:
            seen.add(template_name)

        # Update tags from node.token
        if not isinstance(
            node, (BlockNode, ConditionalBlockNode, MultiExpressionBlockNode)
        ) and (is_tag_token(node.token) or is_lines_token(node.token)):
            tags[node.token.name].append(
                Span(template_name, node.token.start, node.token.stop)
            )

        # Update variables from node.expressions()
        for expr in node.expressions():
            for var in _extract_variables(expr, template_name):
                variables.add(var)
                root = str(var.segments[0])
                if root not in scope:
                    globals.add(var)

            # Update filters from expr
            for name, span in _extract_filters(expr, template_name):
                filters[name].append(span)

        # Update the template scope from node.template_scope()
        for ident in node.template_scope():
            scope.add(ident)
            locals.add(
                Variable(
                    segments=[ident],
                    span=Span(template_name, ident.token.start, ident.token.stop),
                )
            )

        if partial := node.partial_scope():
            partial_name = str(partial.name.evaluate(static_context))

            if partial_name in seen:
                return

            partial_scope = (
                _StaticScope(set(partial.in_scope))
                if partial.scope == PartialScope.ISOLATED
                else root_scope.push(set(partial.in_scope))
            )

            for child in node.children(
                static_context, include_partials=include_partials
            ):
                seen.add(partial_name)
                _visit(child, partial_name, partial_scope)

            partial_scope.pop()
        else:
            scope.push(set(node.block_scope()))
            for child in node.children(
                static_context, include_partials=include_partials
            ):
                _visit(child, template_name, scope)
            scope.pop()

    for node in template.nodes:
        _visit(node, template.name, root_scope)

    return TemplateAnalysis(
        variables=variables.as_dict(),
        globals=globals.as_dict(),
        locals=locals.as_dict(),
        filters=dict(filters),
        tags=dict(tags),
    )


async def _analyze_async(
    template: Template, *, include_partials: bool
) -> TemplateAnalysis:
    variables = _VariableMap()
    globals = _VariableMap()  # noqa: A001
    locals = _VariableMap()  # noqa: A001

    filters: defaultdict[str, list[Span]] = defaultdict(list)
    tags: defaultdict[str, list[Span]] = defaultdict(list)

    template_scope: set[str] = set()
    root_scope = _StaticScope(template_scope)
    static_context = RenderContext(template)

    # Names of partial templates that have already been analyzed.
    seen: set[str] = set()

    async def _visit(node: Node, template_name: str, scope: _StaticScope) -> None:
        if template_name:
            seen.add(template_name)

        # Update tags from node.token
        if not isinstance(
            node, (BlockNode, ConditionalBlockNode, MultiExpressionBlockNode)
        ) and (is_tag_token(node.token) or is_lines_token(node.token)):
            tags[node.token.name].append(
                Span(template_name, node.token.start, node.token.stop)
            )

        # Update variables from node.expressions()
        for expr in node.expressions():
            for var in _extract_variables(expr, template_name):
                variables.add(var)
                root = str(var.segments[0])
                if root not in scope:
                    globals.add(var)

            # Update filters from expr
            for name, span in _extract_filters(expr, template_name):
                filters[name].append(span)

        # Update the template scope from node.template_scope()
        for ident in node.template_scope():
            scope.add(ident)
            locals.add(
                Variable(
                    segments=[ident],
                    span=Span(template_name, ident.token.start, ident.token.stop),
                )
            )

        if partial := node.partial_scope():
            partial_name = str(partial.name.evaluate(static_context))

            if partial_name in seen:
                return

            partial_scope = (
                _StaticScope(set(partial.in_scope))
                if partial.scope == PartialScope.ISOLATED
                else root_scope.push(set(partial.in_scope))
            )

            for child in await node.children_async(
                static_context, include_partials=include_partials
            ):
                seen.add(partial_name)
                await _visit(child, partial_name, partial_scope)

            partial_scope.pop()
        else:
            scope.push(set(node.block_scope()))
            for child in await node.children_async(
                static_context, include_partials=include_partials
            ):
                await _visit(child, template_name, scope)
            scope.pop()

    for node in template.nodes:
        await _visit(node, template.name, root_scope)

    return TemplateAnalysis(
        variables=variables.as_dict(),
        globals=globals.as_dict(),
        locals=locals.as_dict(),
        filters=dict(filters),
        tags=dict(tags),
    )


def _extract_filters(
    expression: Expression, template_name: str
) -> Iterable[tuple[str, Span]]:
    if (
        isinstance(expression, (FilteredExpression, TernaryFilteredExpression))
        and expression.filters
    ):
        yield from (
            (f.name, Span(template_name, f.token.start, f.token.stop))
            for f in expression.filters
        )

    if isinstance(expression, TernaryFilteredExpression) and expression.tail_filters:
        yield from (
            (f.name, Span(template_name, f.token.start, f.token.stop))
            for f in expression.tail_filters
        )

    for expr in expression.children():
        yield from _extract_filters(expr, template_name)


def _extract_variables(
    expression: Expression, template_name: str
) -> Iterable[Variable]:
    if isinstance(expression, Path):
        yield Variable(
            segments=_segments(expression, template_name),
            span=Span(template_name, expression.token.start, expression.token.stop),
        )

    for expr in expression.children():
        yield from _extract_variables(expr, template_name=template_name)


def _segments(path: Path, template_name: str) -> Segments:
    segments: Segments = []

    for segment in path.path:
        if isinstance(segment, Path):
            segments.append(_segments(segment, template_name))
        else:
            segments.append(segment)

    return segments
