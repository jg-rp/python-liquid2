"""The standard _render_ tag."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Sequence
from typing import TextIO

from liquid2 import Markup
from liquid2 import Node
from liquid2 import Token
from liquid2.ast import MetaNode
from liquid2.builtin import Identifier
from liquid2.builtin import StringLiteral
from liquid2.builtin import parse_keyword_arguments
from liquid2.builtin import parse_primitive
from liquid2.builtin import parse_string_or_identifier
from liquid2.context import RenderContext
from liquid2.exceptions import LiquidSyntaxError
from liquid2.tag import Tag
from liquid2.tokens import TokenStream

from .for_tag import ForLoop

if TYPE_CHECKING:
    from liquid2 import TokenT
    from liquid2.builtin import KeywordArgument
    from liquid2.context import RenderContext
    from liquid2.expression import Expression


class RenderNode(Node):
    """The standard _render_ tag."""

    __slots__ = ("name", "name", "loop", "var", "alias", "args")

    tag = "render"
    disabled = set(["include"])  # noqa: C405

    def __init__(
        self,
        token: TokenT,
        name: StringLiteral,
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
        template = context.env.get_template(
            self.name.value, context=context, tag=self.tag
        )
        namespace: dict[str, object] = dict(arg.evaluate(context) for arg in self.args)

        character_count = 0

        # New context with globals and filters from the parent, plus the read only
        # namespace containing render arguments and bound variable.
        ctx = context.copy(
            token=self.token,
            namespace=namespace,
            disabled_tags=self.disabled,
            carry_loop_iterations=True,
            template=template,
        )

        if self.var:
            val = self.var.evaluate(context)
            key = self.alias or template.name.split(".")[0]

            if self.loop and isinstance(val, Sequence) and not isinstance(val, str):
                # TODO: raise for loop limit
                forloop = ForLoop(
                    name=key,
                    it=iter(val),
                    length=len(val),
                    parentloop=context.env.undefined("parentloop", token=self.token),
                )

                namespace["forloop"] = forloop
                namespace[key] = None

                for itm in forloop:
                    namespace[key] = itm
                    character_count += template.render_with_context(
                        ctx, buffer, partial=True, block_scope=True
                    )
            else:
                namespace[key] = val
                character_count = template.render_with_context(
                    ctx, buffer, partial=True, block_scope=True
                )
        else:
            character_count = template.render_with_context(
                ctx, buffer, partial=True, block_scope=True
            )

        return character_count

    async def render_to_output_async(
        self, context: RenderContext, buffer: TextIO
    ) -> int:
        """Render the node to the output buffer."""
        template = await context.env.get_template_async(
            self.name.value, context=context, tag=self.tag
        )

        namespace: dict[str, object] = dict(
            [await arg.evaluate_async(context) for arg in self.args]
        )

        character_count = 0

        # New context with globals and filters from the parent, plus the read only
        # namespace containing render arguments and bound variable.
        ctx = context.copy(
            token=self.token,
            namespace=namespace,
            disabled_tags=self.disabled,
            carry_loop_iterations=True,
            template=template,
        )

        if self.var:
            val = await self.var.evaluate_async(context)
            key = self.alias or template.name.split(".")[0]

            if self.loop and isinstance(val, Sequence) and not isinstance(val, str):
                # TODO: raise for loop limit
                forloop = ForLoop(
                    name=key,
                    it=iter(val),
                    length=len(val),
                    parentloop=context.env.undefined("parentloop", token=self.token),
                )

                namespace["forloop"] = forloop
                namespace[key] = None

                for itm in forloop:
                    namespace[key] = itm
                    character_count += await template.render_with_context_async(
                        ctx, buffer, partial=True, block_scope=True
                    )
            else:
                namespace[key] = val
                character_count = await template.render_with_context_async(
                    ctx, buffer, partial=True, block_scope=True
                )
        else:
            character_count = await template.render_with_context_async(
                ctx, buffer, partial=True, block_scope=True
            )

        return character_count

    def children(self) -> list[MetaNode]:
        """Return a list of child nodes and/or expressions associated with this node."""
        block_scope: list[Identifier] = [
            Identifier(arg.name, token=arg.token) for arg in self.args
        ]

        children = [
            MetaNode(
                token=self.name.token,
                expression=self.name,
                block_scope=block_scope,
                load_mode="render",
                load_context={"tag": "render"},
            )
        ]

        if self.var:
            if self.alias:
                block_scope.append(self.alias)
            else:
                block_scope.append(
                    Identifier(
                        str(self.name.value).split(".", 1)[0], token=self.name.token
                    )
                )
            children.append(
                MetaNode(
                    token=self.token,
                    expression=self.var,
                )
            )

        for arg in self.args:
            children.append(MetaNode(token=arg.token, expression=arg.value))
        return children


class RenderTag(Tag):
    """The standard _render_ tag."""

    block = False
    node_class = RenderNode

    def parse(self, stream: TokenStream) -> Node:
        """Parse tokens from _stream_ into an AST node."""
        token = stream.current()
        assert isinstance(token, Markup.Tag)

        if not token.expression:
            raise LiquidSyntaxError(
                "expected the name of a template to render", token=token
            )

        tokens = TokenStream(token.expression)

        # The name of the template to render. Must be a string literal.
        name_token = tokens.next()
        match name_token:
            case Token.StringLiteral(value):
                name = StringLiteral(token=name_token, value=value)
            case _token:
                raise LiquidSyntaxError(
                    "expected the name of a template to render as a string literal, "
                    f"found {_token.__class__.__name__}",
                    token=_token,
                )

        loop = False
        var: Expression | None = None
        alias: Identifier | None = None

        if isinstance(tokens.current(), Token.For) and not isinstance(
            tokens.peek(), (Token.Colon, Token.Comma)
        ):
            tokens.next()  # Move past "for"
            loop = True
            var = parse_primitive(tokens.next())
            if isinstance(tokens.current(), Token.As):
                tokens.next()  # Move past "as"
                alias = parse_string_or_identifier(tokens.next())
        elif isinstance(tokens.current(), Token.With) and not isinstance(
            tokens.peek(), (Token.Colon, Token.Comma)
        ):
            tokens.next()  # Move past "with"
            var = parse_primitive(tokens.next())
            if isinstance(tokens.current(), Token.As):
                tokens.next()  # Move past "as"
                alias = parse_string_or_identifier(tokens.next())

        args = parse_keyword_arguments(tokens)
        tokens.expect_eos()
        return self.node_class(token, name, loop=loop, var=var, alias=alias, args=args)
