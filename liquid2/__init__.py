from typing import Any
from typing import Iterator
from typing import Mapping
from typing import TextIO

from .token import BlockCommentToken
from .token import CommentToken
from .token import InlineCommentToken
from .token import ContentToken
from .token import LinesToken
from .token import OutputToken
from .token import PathT
from .token import PathToken
from .token import RawToken
from .token import TagToken
from .token import Token
from .token import TokenT
from .token import TokenType
from .token import WhitespaceControl
from .token import is_comment_token
from .token import is_content_token
from .token import is_lines_token
from .token import is_output_token
from .token import is_path_token
from .token import is_range_token
from .token import is_raw_token
from .token import is_tag_token
from .token import is_token_type
from .token import is_template_string_token
from .stream import TokenStream
from .expression import Expression
from .tag import Tag
from .ast import BlockNode
from .ast import ConditionalBlockNode
from .ast import Node
from .context import RenderContext
from .unescape import unescape
from .environment import Environment
from .lexer import tokenize
from .template import Template
from .builtin import CachingDictLoader
from .builtin import DictLoader
from .builtin import ChoiceLoader
from .builtin import CachingChoiceLoader
from .builtin import CachingFileSystemLoader
from .builtin import FileSystemLoader
from .builtin import PackageLoader
from .builtin import CachingLoaderMixin
from .loader import TemplateSource
from .undefined import StrictUndefined
from .undefined import Undefined
from .undefined import FalsyStrictUndefined
from .exceptions import TemplateNotFoundError
from .messages import MessageTuple
from .messages import Translations
from .messages import extract_from_template

from .__about__ import __version__

DEFAULT_ENVIRONMENT = Environment()


def parse(
    source: str,
    *,
    name: str = "",
    globals: Mapping[str, object] | None = None,
) -> Template:
    """Parse _source_ as a Liquid template using the default environment.

    Args:
        source: Liquid template source code.
        name: An optional name for the template used in error messages.
        globals: Variables that will be available to the resulting template.

    Return:
        A new template bound to the default environment.
    """
    return DEFAULT_ENVIRONMENT.from_string(source, name=name, globals=globals)


def render(source: str, *args: Any, **kwargs: Any) -> str:
    """Parse and render _source_ as a Liquid template using the default environment.

    Additional arguments are passed to `dict()` and will be available as template
    variables.

    Args:
        source: Liquid template source code.
        *args: dict-like arguments added to the template render context.
        **kwargs: dict-like arguments added to the template render context.

    Return:
        The result of rendering _source_ as a Liquid template.
    """
    return DEFAULT_ENVIRONMENT.from_string(source).render(*args, **kwargs)


async def render_async(source: str, *args: Any, **kwargs: Any) -> str:
    """Parse and render _source_ as a Liquid template using the default environment.

    Additional arguments are passed to `dict()` and will be available as template
    variables.

    Args:
        source: Liquid template source code.
        *args: dict-like arguments added to the template render context.
        **kwargs: dict-like arguments added to the template render context.

    Return:
        The result of rendering _source_ as a Liquid template.
    """
    template = DEFAULT_ENVIRONMENT.from_string(source)
    return await template.render_async(*args, **kwargs)


def extract_liquid(
    fileobj: TextIO,
    keywords: list[str],
    comment_tags: list[str] | None = None,
    options: dict[object, object] | None = None,  # noqa: ARG001
) -> Iterator[MessageTuple]:
    """A babel compatible translation message extraction method for Liquid templates.

    See https://babel.pocoo.org/en/latest/messages.html

    Keywords are the names of Liquid filters or tags operating on translatable
    strings. For a filter to contribute to message extraction, it must also
    appear as a child of a `FilteredExpression` and be a `TranslatableFilter`.
    Similarly, tags must produce a node that is a `TranslatableTag`.

    Where a Liquid comment contains a prefix in `comment_tags`, the comment
    will be attached to the translatable filter or tag immediately following
    the comment. Python Liquid's non-standard shorthand comments are not
    supported.

    Options are arguments passed to the `liquid.Template` constructor with the
    contents of `fileobj` as the template's source. Use `extract_from_template`
    to extract messages from an existing template bound to an existing
    environment.
    """
    template = parse(fileobj.read())
    return extract_from_template(
        template=template,
        keywords=keywords,
        comment_tags=comment_tags,
    )


__all__ = (
    "__version__",
    "BlockCommentToken",
    "BlockNode",
    "CachingChoiceLoader",
    "CachingDictLoader",
    "CachingFileSystemLoader",
    "CachingLoaderMixin",
    "ChoiceLoader",
    "CommentToken",
    "ConditionalBlockNode",
    "ContentToken",
    "DEFAULT_ENVIRONMENT",
    "DictLoader",
    "Environment",
    "Expression",
    "extract_liquid",
    "FalsyStrictUndefined",
    "FileSystemLoader",
    "InlineCommentToken",
    "is_comment_token",
    "is_content_token",
    "is_lines_token",
    "is_output_token",
    "is_path_token",
    "is_range_token",
    "is_raw_token",
    "is_tag_token",
    "is_template_string_token",
    "is_token_type",
    "LinesToken",
    "Node",
    "OutputToken",
    "PackageLoader",
    "parse",
    "PathT",
    "PathToken",
    "RawToken",
    "render_async",
    "render",
    "RenderContext",
    "StrictUndefined",
    "Tag",
    "TagToken",
    "Template",
    "TemplateNotFoundError",
    "TemplateSource",
    "Token",
    "tokenize",
    "TokenStream",
    "TokenT",
    "TokenType",
    "Undefined",
    "unescape",
    "WhitespaceControl",
    "Translations",
)
