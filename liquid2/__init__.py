from typing import Mapping

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
from .undefined import StrictUndefined
from .undefined import Undefined
from .exceptions import TemplateNotFoundError

from .__about__ import __version__

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


__all__ = (
    "__version__",
    "BlockCommentToken",
    "BlockNode",
    "CachingChoiceLoader",
    "CachingDictLoader",
    "CachingFileSystemLoader",
    "ChoiceLoader",
    "CommentToken",
    "ConditionalBlockNode",
    "ContentToken",
    "DEFAULT_ENVIRONMENT",
    "DictLoader",
    "Environment",
    "Expression",
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
    "is_token_type",
    "LinesToken",
    "Node",
    "OutputToken",
    "PackageLoader",
    "parse",
    "PathT",
    "PathToken",
    "RawToken",
    "RenderContext",
    "StrictUndefined",
    "Tag",
    "TagToken",
    "Template",
    "TemplateNotFoundError",
    "Token",
    "tokenize",
    "TokenStream",
    "TokenT",
    "TokenType",
    "Undefined",
    "unescape",
    "WhitespaceControl",
)
