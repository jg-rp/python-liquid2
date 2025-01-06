"""Template parsing and rendering configuration."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Callable
from typing import ClassVar
from typing import Mapping
from typing import Type

from .builtin import DictLoader
from .builtin import register_default_tags_and_filters
from .exceptions import LiquidError
from .lexer import Lexer
from .parser import Parser
from .template import Template
from .token import WhitespaceControl
from .undefined import Undefined

if TYPE_CHECKING:
    from .ast import Node
    from .context import RenderContext
    from .loader import BaseLoader
    from .tag import Tag
    from .token import TokenT


class Environment:
    """Template parsing and rendering configuration.

    An `Environment` is where you might register custom tags and filters, or store
    global context variables that should be included with every template.

    Args:
        loader: A template loader from which template source text will be read when
            calling [get_template][liquid2.Environment.get_template] or when rendering
            with the built-in `{% include %}` and `{% render %}`, among others. If
            `None`, the environment will be configured with an empty
            [DictLoader][liquid2.DictLoader].
        globals: An optional mapping of template variables that will be added to the
            render context of all templates rendered from the environment.
        auto_escape: If `True`, automatically escape HTML text upon output, unless the
            text is explicitly marked as "safe".
        undefined: The [Undefined][liquid2.Undefined] type used to represent template
            variables that don't exist.
        default_trim: The automatic whitespace stripping mode to use. This mode can then
            be overridden by template authors per Liquid tag using whitespace control
            symbols (`-`, `+`, `~`).
    """

    context_depth_limit: ClassVar[int] = 30
    """Maximum number of times a render context can be extended or wrapped before
    raising a `ContextDepthError`."""

    loop_iteration_limit: ClassVar[int | None] = None
    """Maximum number of loop iterations allowed before a `LoopIterationLimitError` is
    raised."""

    local_namespace_limit: ClassVar[int | None] = None
    """Maximum number of bytes (according to sys.getsizeof) allowed in a template's
    local namespace before a `LocalNamespaceLimitError` is raised. We only count the
    size of the namespaces values, not the size of keys/names."""

    output_stream_limit: ClassVar[int | None] = None
    """Maximum number of bytes that can be written to a template's output stream before
    raising an `OutputStreamLimitError`."""

    suppress_blank_control_flow_blocks: bool = True
    """If True (the default), indicates that blocks rendering to whitespace only will
    not be output."""

    lexer_class = Lexer
    """The lexer class to use when scanning template source text."""

    template_class = Template
    """The template class to use after parsing source text."""

    def __init__(
        self,
        *,
        loader: BaseLoader | None = None,
        globals: Mapping[str, object] | None = None,
        auto_escape: bool = False,
        undefined: Type[Undefined] = Undefined,
        default_trim: WhitespaceControl = WhitespaceControl.PLUS,
    ) -> None:
        self.loader = loader or DictLoader({})
        self.globals = globals or {}
        self.auto_escape = auto_escape
        self.undefined = undefined

        self.default_trim: WhitespaceControl = (
            WhitespaceControl.PLUS
            if default_trim == WhitespaceControl.DEFAULT
            else default_trim
        )
        """The default whitespace trimming mode."""

        self.filters: dict[str, Callable[..., Any]] = {}
        """The environment's filter register, mapping filter names to callables."""

        self.tags: dict[str, Tag] = {}
        """The environment's tag register, mapping tag names to instances of `Tag`."""

        self.setup_tags_and_filters()
        self.parser = Parser(self)

    def setup_tags_and_filters(self) -> None:
        """Add tags and filters to this environment.

        This is called once when initializing an environment. Override this method
        in your custom environments.
        """
        register_default_tags_and_filters(self)

    def tokenize(self, source: str) -> list[TokenT]:
        """Scan Liquid template _source_ and return a list of Markup objects."""
        lexer = self.lexer_class(source)
        lexer.run()
        return lexer.markup

    def parse(self, source: str) -> list[Node]:
        """Compile template source text and return an abstract syntax tree."""
        return self.parser.parse(self.tokenize(source))

    def from_string(
        self,
        source: str,
        *,
        name: str = "",
        path: str | Path | None = None,
        globals: Mapping[str, object] | None = None,
        overlay_data: Mapping[str, object] | None = None,
    ) -> Template:
        """Create a template from a string."""
        try:
            return self.template_class(
                self,
                self.parse(source),
                name=name,
                path=path,
                global_data=self.make_globals(globals),
                overlay_data=overlay_data,
            )
        except LiquidError as err:
            if path:
                path = Path(path)
                template_name = str(path / name if not path.name else path)
            else:
                template_name = name
            if not err.template_name:
                err.template_name = template_name
            raise

    def get_template(
        self,
        name: str,
        *,
        globals: Mapping[str, object] | None = None,
        context: RenderContext | None = None,
        **kwargs: object,
    ) -> Template:
        """Load and parse a template using the configured loader.

        Args:
            name: The template's name. The loader is responsible for interpreting
                the name. It could be the name of a file or some other identifier.
            globals: A mapping of render context variables attached to the
                resulting template.
            context: An optional render context that can be used to narrow the template
                source search space.
            kwargs: Arbitrary arguments that can be used to narrow the template source
                search space.

        Raises:
            TemplateNotFound: If a template with the given name can not be found.
        """
        try:
            return self.loader.load(
                env=self,
                name=name,
                globals=self.make_globals(globals),
                context=context,
                **kwargs,
            )
        except LiquidError as err:
            if not err.template_name:
                err.template_name = name
            raise

    async def get_template_async(
        self,
        name: str,
        *,
        globals: Mapping[str, object] | None = None,
        context: RenderContext | None = None,
        **kwargs: object,
    ) -> Template:
        """An async version of `get_template()`."""
        try:
            return await self.loader.load_async(
                env=self,
                name=name,
                globals=self.make_globals(globals),
                context=context,
                **kwargs,
            )
        except LiquidError as err:
            if not err.template_name:
                err.template_name = name
            raise

    def make_globals(
        self,
        globals: Mapping[str, object] | None = None,  # noqa: A002
    ) -> dict[str, object]:
        """Combine environment globals with template globals."""
        if globals:
            # Template globals take priority over environment globals.
            return {**self.globals, **globals}
        return dict(self.globals)

    def trim(
        self,
        text: str,
        left_trim: WhitespaceControl,
        right_trim: WhitespaceControl,
    ) -> str:
        """Return _text_ after applying whitespace control."""
        if left_trim == WhitespaceControl.DEFAULT:
            left_trim = self.default_trim

        if right_trim == WhitespaceControl.DEFAULT:
            right_trim = self.default_trim

        if left_trim == right_trim:
            if left_trim == WhitespaceControl.MINUS:
                return text.strip()
            if left_trim == WhitespaceControl.TILDE:
                return text.strip("\r\n")
            return text

        if left_trim == WhitespaceControl.MINUS:
            text = text.lstrip()
        elif left_trim == WhitespaceControl.TILDE:
            text = text.lstrip("\r\n")

        if right_trim == WhitespaceControl.MINUS:
            text = text.rstrip()
        elif right_trim == WhitespaceControl.TILDE:
            text = text.rstrip("\r\n")

        return text
