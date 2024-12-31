"""A parsed template, ready to be rendered."""

from __future__ import annotations

from io import StringIO
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Awaitable
from typing import Mapping
from typing import TextIO

from .context import RenderContext
from .exceptions import LiquidError
from .exceptions import LiquidInterrupt
from .exceptions import LiquidSyntaxError
from .exceptions import StopRender
from .output import LimitedStringIO
from .static_analysis import Segments
from .static_analysis import _analyze
from .static_analysis import _analyze_async
from .utils import ReadOnlyChainMap

if TYPE_CHECKING:
    from .ast import Node
    from .environment import Environment
    from .loader import UpToDate
    from .static_analysis import TemplateAnalysis


class Template:
    """A parsed template ready to be rendered.

    Don't try to instantiate `Template` directly. Use [`parse()`][liquid2.parse],
    [`Environment.from_string()`][liquid2.Environment.from_string] or
    [`Environment.get_template()`][liquid2.Environment.get_template] instead.
    """

    __slots__ = (
        "env",
        "nodes",
        "name",
        "path",
        "global_data",
        "overlay_data",
        "uptodate",
    )

    def __init__(
        self,
        env: Environment,
        nodes: list[Node],
        *,
        name: str = "",
        path: str | Path | None = None,
        global_data: Mapping[str, object] | None = None,
        overlay_data: Mapping[str, object] | None = None,
    ) -> None:
        self.env = env
        self.nodes = nodes
        self.name = name
        self.path = path
        self.global_data = global_data or {}
        self.overlay_data = overlay_data or {}
        self.uptodate: UpToDate = None

    def __str__(self) -> str:
        return "".join(str(n) for n in self.nodes)

    def full_name(self) -> str:
        """Return this template's path, if available, joined with its name."""
        if self.path:
            path = Path(self.path)
            return str(path / self.name if not path.name else path)
        return self.name

    def render(self, *args: Any, **kwargs: Any) -> str:
        """Render this template with _args_ and _kwargs_ added to the render context.

        _args_ and _kwargs_ are passed to `dict()`.
        """
        buf = self._get_buffer()
        context = RenderContext(
            self,
            global_data=self.make_globals(dict(*args, **kwargs)),
        )
        self.render_with_context(context, buf)
        return buf.getvalue()

    async def render_async(self, *args: Any, **kwargs: Any) -> str:
        """Render this template with _args_ and _kwargs_ added to the render context.

        _args_ and _kwargs_ are passed to `dict()`.
        """
        buf = self._get_buffer()
        context = RenderContext(
            self,
            global_data=self.make_globals(dict(*args, **kwargs)),
        )
        await self.render_with_context_async(context, buf)
        return buf.getvalue()

    def render_with_context(
        self,
        context: RenderContext,
        buf: TextIO,
        *args: Any,
        partial: bool = False,
        block_scope: bool = False,
        **kwargs: Any,
    ) -> int:
        """Render this template using an existing render context and output buffer."""
        namespace = dict(*args, **kwargs)
        character_count = 0

        with context.extend(namespace):
            for node in self.nodes:
                try:
                    character_count += node.render(context, buf)
                except StopRender:
                    break
                except LiquidInterrupt as err:
                    if not partial or block_scope:
                        raise LiquidSyntaxError(
                            f"unexpected '{err}'",
                            token=node.token,
                            template_name=self.full_name(),
                        ) from err
                    raise
                except LiquidError as err:
                    if not err.template_name:
                        err.template_name = self.full_name()
                    raise

        return character_count

    async def render_with_context_async(
        self,
        context: RenderContext,
        buf: TextIO,
        *args: Any,
        partial: bool = False,
        block_scope: bool = False,
        **kwargs: Any,
    ) -> int:
        """Render this template using an existing render context and output buffer."""
        namespace = dict(*args, **kwargs)
        character_count = 0

        with context.extend(namespace):
            for node in self.nodes:
                try:
                    character_count += await node.render_async(context, buf)
                except StopRender:
                    break
                except LiquidInterrupt as err:
                    if not partial or block_scope:
                        raise LiquidSyntaxError(
                            f"unexpected '{err}'",
                            token=node.token,
                            template_name=self.full_name(),
                        ) from err
                    raise
                except LiquidError as err:
                    if not err.template_name:
                        err.template_name = self.full_name()
                    raise

        return character_count

    def make_globals(self, render_args: Mapping[str, object]) -> Mapping[str, object]:
        """Return a mapping including render arguments and template globals."""
        return ReadOnlyChainMap(
            render_args,
            self.overlay_data,
            self.global_data,
        )

    def analyze(self, *, include_partials: bool = True) -> TemplateAnalysis:
        """Statically analyze this template and any included/rendered templates.

        Args:
            include_partials: If `True`, we will try to load partial templates and
                analyze those templates too.
        """
        return _analyze(self, include_partials=include_partials)

    async def analyze_async(self, *, include_partials: bool = True) -> TemplateAnalysis:
        """An async version of `analyze`."""
        return await _analyze_async(self, include_partials=include_partials)

    def is_up_to_date(self) -> bool:
        """Return _False_ if the template has been modified, _True_ otherwise."""
        if self.uptodate is None:
            return True

        uptodate = self.uptodate()
        if not isinstance(uptodate, bool):
            return False
        return uptodate

    async def is_up_to_date_async(self) -> bool:
        """An async version of _is_up_to_date()_.

        If _template.uptodate_ is a coroutine, it wil be awaited. Otherwise it will be
        called just like _is_up_to_date_.
        """
        if self.uptodate is None:
            return True

        uptodate = self.uptodate()
        if isinstance(uptodate, Awaitable):
            return await uptodate
        return uptodate

    def _get_buffer(self) -> StringIO:
        if self.env.output_stream_limit is None:
            return StringIO()
        return LimitedStringIO(limit=self.env.output_stream_limit)

    def variables(self, *, include_partials: bool = True) -> list[str]:
        """Return a list of variables used in this template without path segments.

        Includes variables that are _local_ to the template, like those crated with
        `{% assign %}` and `{% capture %}`.

        See also [global_variables][liquid2.Template.global_variables].

        Args:
            include_partials: If `True`, will try to load and find variables in
                included/rendered templates too.

        Returns:
            A list of distinct _root segments_ for variables in this template.
        """
        return list(self.analyze(include_partials=include_partials).variables)

    async def variables_async(self, *, include_partials: bool = True) -> list[str]:
        """Return a list of variables used in this template without path segments.

        Includes variables that are _local_ to the template, like those crated with
        `{% assign %}` and `{% capture %}`.

        See also [global_variables][liquid2.Template.global_variables].

        Args:
            include_partials: If `True`, will try to load and find variables in
                included/rendered templates too.

        Returns:
            A list of distinct _root segments_ for variables in this template.
        """
        return list(
            (await self.analyze_async(include_partials=include_partials)).variables
        )

    def variable_paths(self, *, include_partials: bool = True) -> list[str]:
        """Return a list of variables used in this template including all path segments.

        Includes variables that are _local_ to the template, like those crated with
        `{% assign %}` and `{% capture %}`.

        See also [global_variable_paths][liquid2.Template.global_variable_paths].

        Args:
            include_partials: If `True`, will try to load and find variables in
                included/rendered templates too.

        Returns:
            A list of distinct paths for variables in this template.
        """
        analysis = self.analyze(include_partials=include_partials)
        return list(
            {str(v) for v in chain.from_iterable(list(analysis.variables.values()))}
        )

    async def variable_paths_async(self, *, include_partials: bool = True) -> list[str]:
        """Return a list of variables used in this template including all path segments.

        Includes variables that are _local_ to the template, like those crated with
        `{% assign %}` and `{% capture %}`.

        See also [global_variable_paths][liquid2.Template.global_variable_paths].

        Args:
            include_partials: If `True`, will try to load and find variables in
                included/rendered templates too.

        Returns:
            A list of distinct paths for variables in this template.
        """
        analysis = await self.analyze_async(include_partials=include_partials)
        return list(
            {str(v) for v in chain.from_iterable(list(analysis.variables.values()))}
        )

    def variable_segments(self, *, include_partials: bool = True) -> list[Segments]:
        """Return a list of variables used in this template, each as a list of segments.

        Includes variables that are _local_ to the template, like those crated with
        `{% assign %}` and `{% capture %}`.

        See also [global_variable_segments][liquid2.Template.global_variable_segments].

        Args:
            include_partials: If `True`, will try to load and find variables in
                included/rendered templates too.

        Returns:
            A list of distinct paths for variables in this template.
        """
        analysis = self.analyze(include_partials=include_partials)
        return [
            v.segments
            for v in set(chain.from_iterable(list(analysis.variables.values())))
        ]

    async def variable_segments_async(
        self, *, include_partials: bool = True
    ) -> list[Segments]:
        """Return a list of variables used in this template, each as a list of segments.

        Includes variables that are _local_ to the template, like those crated with
        `{% assign %}` and `{% capture %}`.

        See also [global_variable_segments][liquid2.Template.global_variable_segments].

        Args:
            include_partials: If `True`, will try to load and find variables in
                included/rendered templates too.

        Returns:
            A list of distinct paths for variables in this template.
        """
        analysis = await self.analyze_async(include_partials=include_partials)
        return [
            v.segments
            for v in set(chain.from_iterable(list(analysis.variables.values())))
        ]

    def global_variables(self, *, include_partials: bool = True) -> list[str]:
        """Return a list of variables used in this template without path segments.

        Excludes variables that are _local_ to the template, like those crated with
        `{% assign %}` and `{% capture %}`.

        Args:
            include_partials: If `True`, will try to load and find variables in
                included/rendered templates too.

        Returns:
            A list of distinct _root segments_ for variables in this template.
        """
        return list(self.analyze(include_partials=include_partials).globals)

    async def global_variables_async(
        self, *, include_partials: bool = True
    ) -> list[str]:
        """Return a list of variables used in this template without path segments.

        Excludes variables that are _local_ to the template, like those crated with
        `{% assign %}` and `{% capture %}`.

        Args:
            include_partials: If `True`, will try to load and find variables in
                included/rendered templates too.

        Returns:
            A list of distinct _root segments_ for variables in this template.
        """
        return list(
            (await self.analyze_async(include_partials=include_partials)).globals
        )

    def global_variable_paths(self, *, include_partials: bool = True) -> list[str]:
        """Return a list of variables used in this template including all path segments.

        Excludes variables that are _local_ to the template, like those crated with
        `{% assign %}` and `{% capture %}`.

        Args:
            include_partials: If `True`, will try to load and find variables in
                included/rendered templates too.

        Returns:
            A list of distinct paths for variables in this template.
        """
        analysis = self.analyze(include_partials=include_partials)
        return list(
            {str(v) for v in chain.from_iterable(list(analysis.globals.values()))}
        )

    async def global_variable_paths_async(
        self, *, include_partials: bool = True
    ) -> list[str]:
        """Return a list of variables used in this template including all path segments.

        Excludes variables that are _local_ to the template, like those crated with
        `{% assign %}` and `{% capture %}`.

        Args:
            include_partials: If `True`, will try to load and find variables in
                included/rendered templates too.

        Returns:
            A list of distinct paths for variables in this template.
        """
        analysis = await self.analyze_async(include_partials=include_partials)
        return list(
            {str(v) for v in chain.from_iterable(list(analysis.globals.values()))}
        )

    def global_variable_segments(
        self, *, include_partials: bool = True
    ) -> list[Segments]:
        """Return a list of variables used in this template, each as a list of segments.

        Excludes variables that are _local_ to the template, like those crated with
        `{% assign %}` and `{% capture %}`.

        Args:
            include_partials: If `True`, will try to load and find variables in
                included/rendered templates too.

        Returns:
            A list of distinct paths for variables in this template.
        """
        analysis = self.analyze(include_partials=include_partials)
        return [
            v.segments
            for v in set(chain.from_iterable(list(analysis.globals.values())))
        ]

    async def global_variable_segments_async(
        self, *, include_partials: bool = True
    ) -> list[Segments]:
        """Return a list of variables used in this template, each as a list of segments.

        Excludes variables that are _local_ to the template, like those crated with
        `{% assign %}` and `{% capture %}`.

        Args:
            include_partials: If `True`, will try to load and find variables in
                included/rendered templates too.

        Returns:
            A list of distinct paths for variables in this template.
        """
        analysis = await self.analyze_async(include_partials=include_partials)
        return [
            v.segments
            for v in set(chain.from_iterable(list(analysis.globals.values())))
        ]

    def filter_names(self, *, include_partials: bool = True) -> list[str]:
        """Return a list of filter names used in this template."""
        return list(self.analyze(include_partials=include_partials).filters)

    async def filter_names_async(self, *, include_partials: bool = True) -> list[str]:
        """Return a list of filter names used in this template."""
        return list(
            (await self.analyze_async(include_partials=include_partials)).filters
        )

    def tag_names(self, *, include_partials: bool = True) -> list[str]:
        """Return a list of tag names used in this template."""
        return list(self.analyze(include_partials=include_partials).tags)

    async def tag_names_async(self, *, include_partials: bool = True) -> list[str]:
        """Return a list of tag names used in this template."""
        return list((await self.analyze_async(include_partials=include_partials)).tags)
