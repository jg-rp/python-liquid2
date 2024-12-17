"""A template loader that loads templates from a dictionary of strings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from liquid2.exceptions import TemplateNotFoundError
from liquid2.loader import BaseLoader
from liquid2.loader import TemplateSource

if TYPE_CHECKING:
    from liquid2 import Environment
    from liquid2.context import RenderContext


class DictLoader(BaseLoader):
    """A loader that loads templates from a dictionary.

    Args:
        templates: A dictionary mapping template names to template source strings.
    """

    def __init__(self, templates: dict[str, str]):
        super().__init__()
        self.templates = templates

    def get_source(
        self,
        env: Environment,  # noqa: ARG002
        template_name: str,
        *,
        context: RenderContext | None = None,  # noqa: ARG002
        **kwargs: object,  # noqa: ARG002
    ) -> TemplateSource:
        """Get the source, filename and reload helper for a template."""
        try:
            source = self.templates[template_name]
        except KeyError as err:
            raise TemplateNotFoundError(template_name) from err

        return TemplateSource(source, template_name, None)


# TODO: caching dict loader
