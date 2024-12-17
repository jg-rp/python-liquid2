"""A parsed template, ready to be rendered."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Awaitable
from typing import Mapping
from typing import TextIO

from .context import RenderContext
from .exceptions import LiquidInterrupt
from .exceptions import LiquidSyntaxError
from .exceptions import StopRender
from .static_analysis import _analyze
from .static_analysis import _analyze_async
from .utils import ReadOnlyChainMap

if TYPE_CHECKING:
    from .ast import Node
    from .environment import Environment
    from .loader import UpToDate
    from .static_analysis import TemplateAnalysis


class Template:
    """A parsed template ready to be rendered."""

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
        """Render this template with _args_ and _kwargs_."""
        buf = StringIO()  # TODO: limited buffer
        context = RenderContext(
            self,
            global_data=self.make_globals(dict(*args, **kwargs)),
        )
        self.render_with_context(context, buf)
        return buf.getvalue()

    async def render_async(self, *args: Any, **kwargs: Any) -> str:
        """Render this template with _args_ and _kwargs_."""
        buf = StringIO()  # TODO: limited buffer
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
                            f"unexpected '{err}'", token=node.token
                        ) from err
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
                            f"unexpected '{err}'", token=node.token
                        ) from err
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
