"""The standard _include_ tag."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Iterable
from typing import Sequence
from typing import TextIO

from liquid2 import Expression
from liquid2 import Node
from liquid2 import Tag
from liquid2 import TagToken
from liquid2 import TokenStream
from liquid2 import TokenType
from liquid2.ast import Partial
from liquid2.ast import PartialScope
from liquid2.builtin import Identifier
from liquid2.builtin import Literal
from liquid2.builtin import parse_keyword_arguments
from liquid2.builtin import parse_primitive
from liquid2.builtin import parse_string_or_identifier
from liquid2.exceptions import LiquidSyntaxError

if TYPE_CHECKING:
    from liquid2 import RenderContext
    from liquid2 import TokenT
    from liquid2.builtin import KeywordArgument


class IncludeNode(Node):
    """The standard _include_ tag."""

    __slots__ = ("name", "name", "loop", "var", "alias", "args")

    tag = "include"

    def __init__(
        self,
        token: TokenT,
        name: Expression,
        *,
        loop: bool,
        var: Expression | None,
        alias: Identifier | None,
        args: list[KeywordArgument] | None,
    ) -> None:
        super().__init__(token)
        self.name = name
        self.loop = loop
        self.var = var
        self.alias = alias
        self.args = args or []

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        name = self.name.evaluate(context)
        template = context.env.get_template(str(name), context=context, tag=self.tag)
        namespace: dict[str, object] = dict(arg.evaluate(context) for arg in self.args)

        character_count = 0

        with context.extend(namespace, template=template):
            if self.var:
                val = self.var.evaluate(context)
                key = self.alias or template.name.split(".")[0]

                if isinstance(val, Sequence) and not isinstance(val, str):
                    # TODO: raise for loop limit
                    for itm in val:
                        namespace[key] = itm
                        character_count += template.render_with_context(
                            context, buffer, partial=True
                        )
                else:
                    namespace[key] = val
                    character_count = template.render_with_context(
                        context, buffer, partial=True
                    )
            else:
                character_count = template.render_with_context(
                    context, buffer, partial=True
                )

        return character_count

    async def render_to_output_async(
        self, context: RenderContext, buffer: TextIO
    ) -> int:
        """Render the node to the output buffer."""
        name = await self.name.evaluate_async(context)
        template = await context.env.get_template_async(
            str(name), context=context, tag=self.tag
        )
        namespace: dict[str, object] = dict(
            [await arg.evaluate_async(context) for arg in self.args]
        )

        character_count = 0

        with context.extend(namespace, template=template):
            if self.var:
                val = await self.var.evaluate_async(context)
                key = self.alias or template.name.split(".")[0]

                if isinstance(val, Sequence) and not isinstance(val, str):
                    # TODO: raise for loop limit
                    for itm in val:
                        namespace[key] = itm
                        character_count += await template.render_with_context_async(
                            context, buffer, partial=True
                        )
                else:
                    namespace[key] = val
                    character_count = await template.render_with_context_async(
                        context, buffer, partial=True
                    )
            else:
                character_count = await template.render_with_context_async(
                    context, buffer, partial=True
                )

        return character_count

    def children(
        self, static_context: RenderContext, *, _include_partials: bool = True
    ) -> Iterable[Node]:
        """Return this node's children."""
        if _include_partials:
            name = self.name.evaluate(static_context)
            template = static_context.env.get_template(
                str(name), context=static_context, tag=self.tag
            )
            yield from template.nodes

    async def children_async(
        self, static_context: RenderContext, *, _include_partials: bool = True
    ) -> Iterable[Node]:
        """Return this node's children."""
        if _include_partials:
            name = await self.name.evaluate_async(static_context)
            template = await static_context.env.get_template_async(
                str(name), context=static_context, tag=self.tag
            )
            return template.nodes
        return []

    def expressions(self) -> Iterable[Expression]:
        """Return this node's expressions."""
        yield self.name
        if self.var:
            yield self.var
        yield from (arg.value for arg in self.args)

    def partial_scope(self) -> Partial | None:
        """Return information about a partial template loaded by this node."""
        scope: list[Identifier] = [
            Identifier(arg.name, token=arg.token) for arg in self.args
        ]

        if self.var:
            if self.alias:
                scope.append(self.alias)
            elif isinstance(self.name, Literal):
                scope.append(
                    Identifier(
                        str(self.name.value).split(".", 1)[0], token=self.name.token
                    )
                )

        return Partial(name=self.name, scope=PartialScope.SHARED, in_scope=scope)


class IncludeTag(Tag):
    """The standard _include_ tag."""

    block = False
    node_class = IncludeNode

    def parse(self, stream: TokenStream) -> Node:
        """Parse tokens from _stream_ into an AST node."""
        token = stream.current()
        assert isinstance(token, TagToken)

        if not token.expression:
            raise LiquidSyntaxError(
                "expected the name of a template to include", token=token
            )

        tokens = TokenStream(token.expression)

        # The name of the template to include. Could be a string literal or a
        # query that resolves to a string.
        name = parse_primitive(tokens.next())
        # TODO: raise if not Query or StringLiteral

        loop = False
        var: Expression | None = None
        alias: Identifier | None = None

        if tokens.current().type_ == TokenType.FOR and tokens.peek().type_ not in (
            TokenType.COLON,
            TokenType.COMMA,
        ):
            tokens.next()  # Move past "for"
            loop = True
            var = parse_primitive(tokens.next())
            if tokens.current().type_ == TokenType.AS:
                tokens.next()  # Move past "as"
                alias = parse_string_or_identifier(tokens.next())
        elif tokens.current().type_ == TokenType.WITH and tokens.peek().type_ not in (
            TokenType.COLON,
            TokenType.COMMA,
        ):
            tokens.next()  # Move past "with"
            var = parse_primitive(tokens.next())
            if tokens.current().type_ == TokenType.AS:
                tokens.next()  # Move past "as"
                alias = parse_string_or_identifier(tokens.next())

        args = parse_keyword_arguments(tokens)
        tokens.expect_eos()
        return self.node_class(token, name, loop=loop, var=var, alias=alias, args=args)
