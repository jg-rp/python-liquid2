"""Shortcode hook copied from the mkdocs-material project, then simplified.

https://github.com/squidfunk/mkdocs-material/blob/master/material/overrides/hooks/shortcodes.py
"""

# Copyright (c) 2016-2024 Martin Donath <martin.donath@squidfunk.com>

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from __future__ import annotations

import posixpath
import re
from re import Match
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mkdocs.config.defaults import MkDocsConfig
    from mkdocs.structure.files import File
    from mkdocs.structure.files import Files
    from mkdocs.structure.pages import Page


def on_page_markdown(
    markdown: str,
    *,
    page: Page,
    config: MkDocsConfig,  # noqa: ARG001
    files: Files,
) -> str:
    # Replace callback
    def replace(match: Match[str]) -> str:
        _type, args = match.groups()
        args = args.strip()
        if _type == "version":
            return _badge_for_version(args, page, files)
        if _type == "shopify":
            return _badge_for_shopify_compatible(page, files)
        if _type == "liquid2":
            return _badge_for_liquid2(page, files)
        if _type == "compat":
            return _badge_for_compatibility_warning(page, files)
        raise RuntimeError(f"Unknown shortcode: {_type}")

    # Find and replace all external asset URLs in current page
    return re.sub(r"<!-- md:(\w+)(.*?) -->", replace, markdown, flags=re.I | re.M)


# Resolve path of file relative to given page - the posixpath always includes
# one additional level of `..` which we need to remove
def _resolve_path(path: str, page: Page, files: Files) -> str:
    path, anchor, *_ = f"{path}#".split("#")
    path = _resolve(files.get_file_from_path(path), page)  # type: ignore
    return "#".join([path, anchor]) if anchor else path


# Resolve path of file relative to given page - the posixpath always includes
# one additional level of `..` which we need to remove
def _resolve(file: File, page: Page) -> str:
    path = posixpath.relpath(file.src_uri, page.file.src_uri)
    return posixpath.sep.join(path.split(posixpath.sep)[1:])


def _badge(icon: str, text: str = "", type: str = "") -> str:
    classes = f"mdx-badge mdx-badge--{type}" if type else "mdx-badge"
    return "".join(
        [
            f'<span class="{classes}">',
            *([f'<span class="mdx-badge__icon">{icon}</span>'] if icon else []),
            *([f'<span class="mdx-badge__text">{text}</span>'] if text else []),
            "</span>",
        ]
    )


def _badge_for_version(text: str, page: Page, files: Files) -> str:
    icon = "material-tag-outline"
    href = _resolve_path("conventions.md#version", page, files)
    return _badge(
        icon=f"[:{icon}:]({href} 'Minimum version')",
        text=text or "",
    )


def _badge_for_liquid2(page: Page, files: Files) -> str:
    icon = "material-water-plus-outline"
    href = _resolve_path("conventions.md#liquid2", page, files)
    return _badge(icon=f"[:{icon}:]({href} 'New to Liquid2')")


def _badge_for_compatibility_warning(page: Page, files: Files) -> str:
    icon = "material-water-alert-outline"
    href = _resolve_path("conventions.md#compatibility", page, files)
    return _badge(icon=f"[:{icon}:]({href} 'Compatibility warning')")


def _badge_for_shopify_compatible(page: Page, files: Files) -> str:
    icon = "material-water-check-outline"
    href = _resolve_path("conventions.md#shopify", page, files)
    return _badge(icon=f"[:{icon}:]({href} 'Shopify/Liquid compatible')")
