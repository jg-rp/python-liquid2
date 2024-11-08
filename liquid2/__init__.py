from typing import Mapping

from .token import CommentToken
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
from .stream import TokenStream
from .tag import Tag
from .ast import BlockNode
from .ast import ConditionalBlockNode
from .ast import MetaNode
from .ast import Node
from .context import RenderContext
from .unescape import unescape
from .environment import Environment
from .lexer import tokenize
from .template import Template
from .builtin import DictLoader


DEFAULT_ENVIRONMENT = Environment()


def parse(source: str, globals: Mapping[str, object] | None = None) -> Template:
    """Parse _source_ as a Liquid template using the default environment.

    Args:
        source: Liquid template source code.
        globals: Variables that will be available to the resulting template.

    Return:
        A new template bound to the default environment.
    """
    return DEFAULT_ENVIRONMENT.from_string(source, globals=globals)


# TODO: expose undefined
# TODO: expose some loaders

__all__ = (
    "BlockNode",
    "CommentToken",
    "ConditionalBlockNode",
    "ContentToken",
    "DEFAULT_ENVIRONMENT",
    "DictLoader",
    "Environment",
    "is_comment_token",
    "is_content_token",
    "is_lines_token",
    "is_output_token",
    "is_path_token",
    "is_range_token",
    "is_raw_token",
    "is_tag_token",
    "is_token_type",
    "LinesToken",
    "MetaNode",
    "Node",
    "OutputToken",
    "parse",
    "PathT",
    "PathToken",
    "RawToken",
    "RenderContext",
    "Tag",
    "TagToken",
    "Template",
    "Token",
    "tokenize",
    "TokenStream",
    "TokenT",
    "TokenType",
    "unescape",
    "WhitespaceControl",
)
