"""Translation related objects and message extraction."""

from __future__ import annotations

import os
from abc import ABC
from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any
from typing import Iterable
from typing import Iterator
from typing import NamedTuple
from typing import Union

from babel.messages import Catalog
from typing_extensions import Protocol

from .builtin import Filter
from .builtin import FilteredExpression
from .builtin import TernaryFilteredExpression
from .builtin.comment import CommentNode
from .context import RenderContext
from .token import TokenT
from .token import is_tag_token

if TYPE_CHECKING:
    from .ast import Node
    from .environment import Environment
    from .expression import Expression
    from .template import Template


DEFAULT_KEYWORDS = {
    "t": None,
    "trans": None,
    "translate": None,
    "gettext": None,
    "ngettext": (1, 2),
    "pgettext": ((1, "c"), 2),
    "npgettext": ((1, "c"), 2, 3),
}

DEFAULT_COMMENT_TAGS = [
    "Translators:",
]


class Translations(Protocol):
    """Message catalog interface.

    An object implementing this protocol is expected to be available in
    a render context.

    Could be a `GNUTranslations` instance from the `gettext` module,
    a Babel `Translations` object, or any object implementing `gettext`,
    `ngettext`, `pgettext` and `npgettext` methods.
    """

    def gettext(self, message: str) -> str:
        """Lookup the message in the catalog."""

    def ngettext(self, singular: str, plural: str, n: int) -> str:
        """Do plural-forms message lookup."""

    def pgettext(self, context: str, message: str) -> str:
        """Lookup the context and message in the catalog."""

    def npgettext(self, context: str, singular: str, plural: str, n: int) -> str:
        """Do plural-forms context and message lookup."""


MESSAGES = Union[
    str,
    tuple[str, ...],
    tuple[tuple[str, str], str],
    tuple[tuple[str, str], str, str],
]

SPEC = Union[
    tuple[int, ...],
    tuple[tuple[int, str], int],
    tuple[tuple[int, str], int, int],
]


class MessageTuple(NamedTuple):
    """The tuple expected to be returned from babel extraction methods."""

    lineno: int
    funcname: str
    message: MESSAGES
    comments: list[str]


class MessageText(NamedTuple):
    """Partial message tuple returned from translatable tags."""

    lineno: int
    funcname: str
    message: MESSAGES


class TranslatableTag(ABC):
    """Base class for translatable tags."""

    @abstractmethod
    def messages(self) -> Iterable[MessageText]:
        """Generate a sequence of translation messages."""


class TranslatableFilter(ABC):
    """Base class for translatable filters."""

    @abstractmethod
    def message(
        self,
        left: Expression,
        _filter: Filter,
        lineno: int,
    ) -> MessageText | None:
        """Return a translation message."""


def extract_from_templates(
    *templates: Template,
    keywords: dict[str, Any] | None = None,
    comment_tags: list[str] | None = None,
    strip_comment_tags: bool = False,
) -> Catalog:
    """Extract messages from one or more templates.

    This function returns a single ``babel.messages.Catalog`` containing
    messages from all the given templates.

    :param templates: templates to extract messages from.
    :param keywords: a Babel compatible mapping of translatable "function"
        names to argument specs. The included translation filters and tag
        transform their messages into typical *gettext format, regardless
        of their names.
    param comment_tags: a list of translator tags to search for and
        include in extracted messages.
    param strip_comment_tags: if `True`, remove comment tags from collected
        message comments.
    """
    keywords = keywords or DEFAULT_KEYWORDS
    comment_tags = comment_tags or DEFAULT_COMMENT_TAGS
    catalog = Catalog()
    for template in templates:
        for lineno, funcname, messages, comments in extract_from_template(
            template, keywords, comment_tags
        ):
            # A partial reimplementation of Babel's messages.extract function.
            # See https://github.com/python-babel/babel/blob/master/babel/messages/extract.py#L262
            spec: SPEC = keywords[funcname] or (1,)
            if not isinstance(messages, (list, tuple)):
                messages = (messages,)  # noqa: PLW2901
            if not messages:
                continue
            if len(spec) != len(messages):
                continue

            # Assumes context is the first item in the spec
            if isinstance(spec[0], tuple):
                # context aware message
                context = messages[spec[0][0] - 1][0]
                message = [messages[i - 1] for i in spec[1:]]
            else:
                context = None
                message = [messages[i - 1] for i in spec if isinstance(i, int)]

            if not message[0]:
                # Empty message
                continue

            if strip_comment_tags:
                comments = _strip_comment_tags(comments, comment_tags)  # noqa: PLW2901

            # Use the template's path if it has one
            template_name = template.name
            if isinstance(template.path, Path):
                template_name = str(template.path.joinpath(template_name))
            elif isinstance(template.path, str):
                template_name = os.path.join(template.path, template_name)

            catalog.add(
                message[0] if len(message) == 1 else message,  # type: ignore
                "",
                [(template_name, lineno)],
                auto_comments=comments,
                context=context,
            )

    return catalog


# def extract_liquid(
#     fileobj: TextIO,
#     keywords: list[str],
#     comment_tags: list[str] | None = None,
# ) -> Iterator[MessageTuple]:
#     """A babel compatible extraction method for Python Liquid templates.

#     See https://babel.pocoo.org/en/latest/messages.html

#     Keywords are the names of Liquid filters or tags operating on translatable
#     strings. For a filter to contribute to message extraction, it must also
#     appear as a child of a `FilteredExpression` and be a `TranslatableFilter`.
#     Similarly, tags must produce a node that is a `TranslatableTag`.

#     Where a Liquid comment contains a prefix in `comment_tags`, the comment
#     will be attached to the translatable filter or tag immediately following
#     the comment. Python Liquid's non-standard shorthand comments are not
#     supported.

#     Options are arguments passed to the `liquid.Template` constructor with the
#     contents of `fileobj` as the template's source. Use `extract_from_template`
#     to extract messages from an existing template bound to an existing
#     environment.
#     """
#     template = parse(fileobj.read())
#     return extract_from_template(
#         template=template,
#         keywords=keywords,
#         comment_tags=comment_tags,
#     )


def extract_from_template(
    template: Template,
    keywords: Union[list[str], dict[str, Any], None] = None,
    comment_tags: list[str] | None = None,
) -> Iterator[MessageTuple]:
    """Extract translation messages from a Liquid template."""
    _comment_tags = comment_tags or DEFAULT_COMMENT_TAGS
    _comments: list[tuple[int, str]] = []
    _keywords = keywords or DEFAULT_KEYWORDS
    ctx = RenderContext(template)

    def visit_expression(expr: Expression, lineno: int) -> Iterator[MessageTuple]:
        if isinstance(expr, (FilteredExpression, TernaryFilteredExpression)):
            for _lineno, funcname, message in _extract_from_filters(
                template.env, expr, lineno, _keywords
            ):
                if _comments and _comments[-1][0] < lineno - 1:
                    _comments.clear()

                yield MessageTuple(
                    lineno=_lineno,
                    funcname=funcname,
                    message=message,
                    comments=[text for _, text in _comments],
                )
                _comments.clear()

        for expression in expr.children():
            yield from visit_expression(expression, lineno)

    def visit(node: Node) -> Iterator[MessageTuple]:
        token = node.token
        lineno = line_number(token)
        if isinstance(node, CommentNode) and node.text is not None:
            comment_text = node.text.strip()
            for comment_tag in _comment_tags:
                if comment_text.startswith(comment_tag):
                    # Our multi-line comments are wrapped in a tag, so we're
                    # only ever going to have one comment text object to deal
                    # with.
                    _comments.clear()
                    _comments.append((lineno, comment_text))
                    break
        elif (
            is_tag_token(token)
            and token.name in _keywords
            and isinstance(node, TranslatableTag)
        ):
            for lineno, funcname, message in node.messages():
                if _comments and _comments[-1][0] < lineno - 1:
                    _comments.clear()

                yield MessageTuple(
                    lineno=lineno,
                    funcname=funcname,
                    message=message,
                    comments=[text for _, text in _comments],
                )
                _comments.clear()

        for child in node.children(ctx, include_partials=False):
            for expr in child.expressions():
                yield from visit_expression(expr, lineno)
            yield from visit(child)

    for node in template.nodes:
        yield from visit(node)


def _extract_from_filters(
    environment: Environment,
    expression: FilteredExpression | TernaryFilteredExpression,
    lineno: int,
    keywords: Union[list[str], dict[str, Any]],
) -> Iterable[MessageText]:
    if isinstance(expression, FilteredExpression) and expression.filters:
        first_filter = expression.filters[0]
        if first_filter.name in keywords:
            filter_callable = environment.filters.get(first_filter.name)
            if isinstance(filter_callable, TranslatableFilter):  # noqa: SIM102
                if message := filter_callable.message(  # type: ignore
                    expression.left,
                    first_filter,
                    lineno,
                ):
                    yield message

    if isinstance(expression, TernaryFilteredExpression):
        yield from _extract_from_filters(environment, expression.left, lineno, keywords)

        if expression.filters and expression.alternative:
            first_filter = expression.filters[0]
            if first_filter.name in keywords:
                filter_callable = environment.filters.get(first_filter.name)
                if isinstance(filter_callable, TranslatableFilter):  # noqa: SIM102
                    if message := filter_callable.message(  # type: ignore
                        expression.alternative,
                        first_filter,
                        lineno,
                    ):
                        yield message


def _strip_comment_tags(comments: list[str], tags: list[str]) -> list[str]:
    """Similar to Babel's messages.extract._strip_comment_tags."""

    def _strip(line: str) -> str:
        for tag in tags:
            if line.startswith(tag):
                return line[len(tag) :].strip()
        return line

    return [_strip(comment) for comment in comments]


# TODO: be more efficient when finding line numbers in the same source text
def line_number(token: TokenT) -> int:
    """Return _token_'s line number."""
    lines = token.source.splitlines(keepends=True)
    cumulative_length = 0
    target_line_index = -1

    for i, line in enumerate(lines):
        cumulative_length += len(line)
        if token.start < cumulative_length:
            target_line_index = i
            break

    if target_line_index == -1:
        raise ValueError("index is out of bounds for the given string")

    # Line number (1-based)
    return target_line_index + 1
