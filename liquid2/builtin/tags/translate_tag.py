"""Tag and node definition for the "trans" or "translate" tag."""

from __future__ import annotations

import itertools
import re
from gettext import NullTranslations
from typing import TYPE_CHECKING
from typing import Any
from typing import Iterable
from typing import NamedTuple
from typing import TextIO
from typing import cast

from markupsafe import Markup

from liquid2 import Tag
from liquid2 import TagToken
from liquid2 import TokenStream
from liquid2.ast import BlockNode
from liquid2.ast import Node
from liquid2.builtin import FilteredExpression
from liquid2.builtin import KeywordArgument
from liquid2.builtin import Path
from liquid2.builtin import StringLiteral
from liquid2.builtin import parse_keyword_arguments
from liquid2.builtin.content import ContentNode
from liquid2.builtin.output import OutputNode
from liquid2.exceptions import TranslationSyntaxError
from liquid2.limits import to_int
from liquid2.messages import MESSAGES
from liquid2.messages import MessageText
from liquid2.messages import TranslatableTag
from liquid2.messages import Translations
from liquid2.messages import line_number
from liquid2.stringify import to_liquid_string

if TYPE_CHECKING:
    from liquid2 import Expression
    from liquid2 import RenderContext
    from liquid2.token import TokenT


class MessageBlock(NamedTuple):
    """The AST block, text and placeholder variables representing a message block."""

    block: BlockNode
    text: str
    vars: list[str]  # noqa: A003


class TranslateNode(Node, TranslatableTag):
    """The built-in _translate_ tag node."""

    __slots__ = (
        "args",
        "singular",
        "singular_block",
        "singular_vars",
        "plural",
    )

    default_translations = NullTranslations()
    translations_var = "translations"
    message_count_var = "count"
    message_context_var = "context"
    re_vars = re.compile(r"(?<!%)%\((\w+)\)s")

    def __init__(
        self,
        token: TokenT,
        *,
        args: dict[str, KeywordArgument],
        singular: MessageBlock,
        plural: MessageBlock | None,
    ):
        super().__init__(token)
        self.args = args
        self.singular_block, self.singular, self.singular_vars = singular
        self.plural = plural

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        translations = self._resolve_translations(context)
        namespace = {k: expr.value.evaluate(context) for k, expr in self.args.items()}
        count = self._resolve_count(context, namespace)
        message_context = self._resolve_message_context(context, namespace)

        with context.extend(namespace):
            message_text, _vars = self.gettext(
                translations,
                count=count,
                message_context=message_context,
            )
            message_vars = {v: context.resolve(v) for v in _vars}

        buffer.write(self.format_message(context, message_text, message_vars))
        return True

    async def render_to_output_async(
        self, context: RenderContext, buffer: TextIO
    ) -> int:
        """Render the node to the output buffer."""
        translations = self._resolve_translations(context)
        namespace = {
            k: await expr.value.evaluate_async(context) for k, expr in self.args.items()
        }
        count = self._resolve_count(context, namespace)
        message_context = self._resolve_message_context(context, namespace)

        with context.extend(namespace):
            message_text, _vars = self.gettext(
                translations,
                count=count,
                message_context=message_context,
            )
            message_vars = {v: context.resolve(v) for v in _vars}

        buffer.write(self.format_message(context, message_text, message_vars))
        return True

    def _resolve_translations(self, context: RenderContext) -> Translations:
        """Return a translations object from the current render context."""
        return cast(
            Translations,
            context.resolve(self.translations_var, self.default_translations),
        )

    def _resolve_count(
        self,
        context: RenderContext,  # noqa: ARG002
        block_scope: dict[str, object],
    ) -> int | None:
        """Return a message count.

        Uses the current render context and/or the translation's block scope.
        """
        try:
            return to_int(block_scope.get(self.message_count_var, 1))  # defaults to 1
        except ValueError:
            return 1

    def _resolve_message_context(
        self,
        context: RenderContext,  # noqa: ARG002
        block_scope: dict[str, object],
    ) -> str | None:
        """Return the message context string.

        Uses the current render context and/or the translation block scope.
        """
        message_context = block_scope.pop(self.message_context_var, None)
        if message_context:
            return (
                str(message_context)
                if not isinstance(message_context, str)
                else message_context
            )  # Just in case we get a Markupsafe object.
        return None

    def gettext(
        self,
        translations: Translations,
        count: int | None,
        message_context: str | None,
    ) -> tuple[str, Iterable[str]]:
        """Get translated text from the given translations object."""
        if self.plural and count:
            if message_context:
                text = translations.npgettext(
                    message_context, self.singular, self.plural.text, count
                )
            else:
                text = translations.ngettext(self.singular, self.plural.text, count)
            return text, itertools.chain(self.singular_vars, self.plural.vars)

        if message_context:
            text = translations.pgettext(message_context, self.singular)
        else:
            text = translations.gettext(self.singular)
        return text, self.singular_vars

    def format_message(
        self,
        context: RenderContext,
        message_text: str,
        message_vars: dict[str, Any],
    ) -> str:
        """Return the message string formatted with the given message variables."""
        if context.env.auto_escape:
            message_text = Markup(message_text)

        with context.extend(namespace=message_vars):
            _vars = {
                k: to_liquid_string(
                    context.resolve(k), auto_escape=context.env.auto_escape
                )
                for k in self.re_vars.findall(message_text)
            }

        return message_text % _vars

    def children(
        self,
        static_context: RenderContext,  # noqa: ARG002
        *,
        include_partials: bool = True,  # noqa: ARG002
    ) -> Iterable[Node]:
        """Return this node's children."""
        yield self.singular_block

        if self.plural:
            yield self.plural.block

    def expressions(self) -> Iterable[Expression]:
        """Return this node's expressions."""
        yield from (arg.value for arg in self.args.values())

    def messages(self) -> Iterable[MessageText]:  # noqa: D102
        if not self.singular:
            return ()

        message_context = self.args.get(self.message_context_var)

        if self.plural:
            if message_context and isinstance(message_context.value, StringLiteral):
                funcname = "npgettext"
                message: MESSAGES = (
                    (message_context.value.value, "c"),
                    self.singular,
                    self.plural.text,
                )
            else:
                funcname = "ngettext"
                message = (self.singular, self.plural.text)
        elif message_context and isinstance(message_context.value, StringLiteral):
            funcname = "pgettext"
            message = ((message_context.value.value, "c"), self.singular)
        else:
            funcname = "gettext"
            message = (self.singular,)

        return (
            MessageText(
                lineno=line_number(self.token),
                funcname=funcname,
                message=message,
            ),
        )


class TranslateTag(Tag):
    """The built-in "trans" or "translate" tag."""

    node_class = TranslateNode

    end = "endtranslate"
    plural_name = "plural"

    re_whitespace = re.compile(r"\s*\n\s*")

    # Override this to disable argument-less filters in translation expression
    # arguments.
    simple_filters = True

    # Override this to disable message whitespace normalization.
    trim_messages = True

    def parse(self, stream: TokenStream) -> TranslateNode:
        """Parse tokens from _stream_ into an AST node."""
        token = stream.next()
        assert isinstance(token, TagToken)

        if token.expression:
            # TODO: no arg filters?
            args = {
                arg.name: arg
                for arg in parse_keyword_arguments(TokenStream(token.expression))
            }
        else:
            args = {}

        message_block_token = stream.current()
        message_block = BlockNode(
            message_block_token,
            self.env.parser.parse_block(stream, end=(self.end, self.plural_name)),
        )

        singular = self.parse_message_block(message_block)

        if stream.is_tag(self.plural_name):
            plural_block_token = stream.next()
            plural_block = BlockNode(
                plural_block_token, self.env.parser.parse_block(stream, end=(self.end,))
            )
            plural: MessageBlock | None = self.parse_message_block(plural_block)
        else:
            plural = None

        stream.expect_tag(self.end)

        return self.node_class(
            token,
            args=args,
            singular=singular,
            plural=plural,
        )

    def parse_message_block(self, block: BlockNode) -> MessageBlock:
        """Return message text and variables from a translation block."""
        message_text: list[str] = []
        message_vars: list[str] = []
        for node in block.nodes:
            if isinstance(node, ContentNode):
                message_text.append(node.text.replace("%", "%%"))  # XXX:
            elif isinstance(node, OutputNode) and isinstance(
                node.expression, FilteredExpression
            ):
                expr = node.expression.left

                if not isinstance(expr, Path):
                    raise TranslationSyntaxError(
                        f"expected a translation variable, found '{expr}'",
                        token=node.token,
                    )

                var = expr.head()

                if node.expression.filters:
                    raise TranslationSyntaxError(
                        f"unexpected filter on translation variable '{expr}'",
                        token=node.token,
                    )

                if not isinstance(var, str):
                    raise TranslationSyntaxError(
                        f"expected a translation variable, found '{expr}'",
                        token=node.token,
                    )

                message_text.append(f"%({var})s")  # XXX:
                message_vars.append(var)

            else:
                raise TranslationSyntaxError(
                    "unexpected tag in translation text",
                    token=node.token,
                )

        msg = "".join(message_text)
        if self.trim_messages:
            msg = self.re_whitespace.sub(" ", msg.strip())

        return MessageBlock(block, msg, message_vars)
