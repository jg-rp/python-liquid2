"""Tag and node definition for the "trans" or "translate" tag."""

from __future__ import annotations

import re
from gettext import NullTranslations
from typing import TYPE_CHECKING
from typing import Iterable
from typing import TextIO
from typing import cast

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

if TYPE_CHECKING:
    from liquid2 import Expression
    from liquid2 import RenderContext
    from liquid2.token import TokenT


class TranslateNode(Node, TranslatableTag):
    """The built-in _translate_ tag node."""

    __slots__ = (
        "args",
        "singular_block",
        "plural_block",
    )

    default_translations = NullTranslations()
    translations_var = "translations"
    message_count_var = "count"
    message_context_var = "context"
    re_whitespace = re.compile(r"\s*\n\s*")

    def __init__(
        self,
        token: TokenT,
        *,
        args: dict[str, KeywordArgument],
        singular_block: BlockNode,
        plural_block: BlockNode | None,
    ):
        super().__init__(token)
        self.args = args
        self.singular_block = singular_block
        self.plural_block = plural_block

    # TODO: __str__

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        translations = self.resolve_translations(context)
        namespace = {k: expr.value.evaluate(context) for k, expr in self.args.items()}
        count = self.resolve_count(context, namespace)
        message_context = self.resolve_message_context(context, namespace)

        message_text = self.gettext(
            translations,
            count=count,
            message_context=message_context,
        )

        with context.extend(namespace):
            template = context.env.from_string(
                message_text,
                name=context.template.name,
                path=context.template.path,
            )
            return template.render_with_context(context, buffer)

    async def render_to_output_async(
        self, context: RenderContext, buffer: TextIO
    ) -> int:
        """Render the node to the output buffer."""
        translations = self.resolve_translations(context)
        namespace = {
            k: await expr.value.evaluate_async(context) for k, expr in self.args.items()
        }
        count = self.resolve_count(context, namespace)
        message_context = self.resolve_message_context(context, namespace)

        message_text = self.gettext(
            translations,
            count=count,
            message_context=message_context,
        )

        with context.extend(namespace):
            template = context.env.from_string(
                message_text,
                name=context.template.name,
                path=context.template.path,
            )
            return await template.render_with_context_async(context, buffer)

    def resolve_translations(self, context: RenderContext) -> Translations:
        """Return a translations object from the current render context."""
        return cast(
            Translations,
            context.resolve(self.translations_var, self.default_translations),
        )

    def resolve_count(
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

    def resolve_message_context(
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
    ) -> str:
        """Get translated text from the given translations object."""
        if self.plural_block and count:
            if message_context:
                return translations.npgettext(
                    message_context,
                    self.block_as_message(self.singular_block),
                    self.block_as_message(self.plural_block),
                    count,
                )

            return translations.ngettext(
                self.block_as_message(self.singular_block),
                self.block_as_message(self.plural_block),
                count,
            )

        if message_context:
            return translations.pgettext(
                message_context, self.block_as_message(self.singular_block)
            )
        return translations.gettext(self.block_as_message(self.singular_block))

    def children(
        self,
        static_context: RenderContext,  # noqa: ARG002
        *,
        include_partials: bool = True,  # noqa: ARG002
    ) -> Iterable[Node]:
        """Return this node's children."""
        yield self.singular_block

        if self.plural_block:
            yield self.plural_block

    def expressions(self) -> Iterable[Expression]:
        """Return this node's expressions."""
        yield from (arg.value for arg in self.args.values())

    def messages(self) -> Iterable[MessageText]:  # noqa: D102
        if not self.singular_block.nodes:
            return ()

        message_context = self.args.get(self.message_context_var)

        if self.plural_block:
            if message_context and isinstance(message_context.value, StringLiteral):
                funcname = "npgettext"
                message: MESSAGES = (
                    (message_context.value.value, "c"),
                    self.block_as_message(self.singular_block),
                    self.block_as_message(self.plural_block),
                )
            else:
                funcname = "ngettext"
                message = (
                    self.block_as_message(self.singular_block),
                    self.block_as_message(self.plural_block),
                )
        elif message_context and isinstance(message_context.value, StringLiteral):
            funcname = "pgettext"
            message = (
                (message_context.value.value, "c"),
                self.block_as_message(self.singular_block),
            )
        else:
            funcname = "gettext"
            message = (self.block_as_message(self.singular_block),)

        return (
            MessageText(
                lineno=line_number(self.token),
                funcname=funcname,
                message=message,
            ),
        )

    def block_as_message(self, block: BlockNode) -> str:
        """Return _block_ as a string with normalized whitespace."""
        return self.re_whitespace.sub(" ", str(block).strip())


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

        self.validate_message_block(message_block)

        if stream.is_tag(self.plural_name):
            plural_block_token = stream.next()
            plural_block = self.validate_message_block(
                BlockNode(
                    plural_block_token,
                    self.env.parser.parse_block(stream, end=(self.end,)),
                )
            )
        else:
            plural_block = None

        stream.expect_tag(self.end)

        return self.node_class(
            token,
            args=args,
            singular_block=message_block,
            plural_block=plural_block,
        )

    def validate_message_block(self, block: BlockNode | None) -> BlockNode | None:
        """Check that a translation message block does not contain disallowed markup."""
        if not block:
            return None

        for node in block.nodes:
            if isinstance(node, ContentNode):
                continue

            if isinstance(node, OutputNode) and isinstance(
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
            else:
                raise TranslationSyntaxError(
                    "unexpected tag in translation text",
                    token=node.token,
                )

        return block
