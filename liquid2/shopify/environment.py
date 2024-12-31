"""An environment that's configured for maximum compatibility with Shopify/Liquid.

This environment will be updated without concern for backwards incompatible changes to
template rendering behavior.
"""

from ..environment import Environment as DefaultEnvironment  # noqa: TID252
from .filters._base64 import base64_decode
from .filters._base64 import base64_encode
from .filters._base64 import base64_url_safe_decode
from .filters._base64 import base64_url_safe_encode
from .tags.tablerow_tag import TablerowTag


class Environment(DefaultEnvironment):
    """An environment configured for maximum compatibility with Shopify/Liquid."""

    def setup_tags_and_filters(self) -> None:
        """Set up Shopify compatible tags and filters."""
        super().setup_tags_and_filters()
        self.tags["tablerow"] = TablerowTag(self)
        self.filters["base64_decode"] = base64_decode
        self.filters["base64_encode"] = base64_encode
        self.filters["base64_url_safe_decode"] = base64_url_safe_decode
        self.filters["base64_url_safe_encode"] = base64_url_safe_encode
