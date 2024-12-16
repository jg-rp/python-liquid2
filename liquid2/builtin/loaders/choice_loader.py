"""A template loader that delegates to other template loaders."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import List

from liquid2.exceptions import TemplateNotFound
from liquid2.loader import BaseLoader
from liquid2.loader import TemplateSource

from .mixins import CachingLoaderMixin

if TYPE_CHECKING:
    from liquid2 import Environment
    from liquid2 import RenderContext


class ChoiceLoader(BaseLoader):
    """A template loader that delegates to other template loaders.

    Args:
        loaders: A list of loaders implementing `liquid.loaders.BaseLoader`.
    """

    def __init__(self, loaders: List[BaseLoader]):
        super().__init__()
        self.loaders = loaders

    def get_source(
        self,
        env: Environment,
        template_name: str,
        *,
        context: RenderContext | None = None,
        **kwargs: object,
    ) -> TemplateSource:
        """Get source information for a template."""
        for loader in self.loaders:
            try:
                return loader.get_source(env, template_name, context=context, **kwargs)
            except TemplateNotFound:
                pass

        raise TemplateNotFound(template_name)

    async def get_source_async(
        self,
        env: Environment,
        template_name: str,
        *,
        context: RenderContext | None = None,
        **kwargs: object,
    ) -> TemplateSource:
        """Get source information for a template."""
        for loader in self.loaders:
            try:
                return await loader.get_source_async(
                    env, template_name, context=context, **kwargs
                )
            except TemplateNotFound:
                pass

        raise TemplateNotFound(template_name)


class CachingChoiceLoader(CachingLoaderMixin, ChoiceLoader):
    """A `ChoiceLoader` that caches parsed templates in memory.

    Args:
        loaders: A list of loaders implementing `liquid.loaders.BaseLoader`.
        auto_reload: If `True`, automatically reload a cached template if it has been
            updated.
        namespace_key: The name of a global render context variable or loader keyword
            argument that resolves to the current loader "namespace" or "scope".
        capacity: The maximum number of templates to hold in the cache before removing
            the least recently used template.
    """

    def __init__(
        self,
        loaders: List[BaseLoader],
        *,
        auto_reload: bool = True,
        namespace_key: str = "",
        capacity: int = 300,
    ):
        super().__init__(
            auto_reload=auto_reload,
            namespace_key=namespace_key,
            capacity=capacity,
        )

        ChoiceLoader.__init__(self, loaders)