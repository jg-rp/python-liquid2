"""The standard _render_ tag."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Iterable
from typing import Sequence
from typing import TextIO

from liquid2 import Node
from liquid2 import Tag
from liquid2 import TagToken
from liquid2 import TokenStream
from liquid2 import TokenType
from liquid2 import is_token_type
from liquid2.ast import Partial
from liquid2.ast import PartialScope
from liquid2.builtin import Identifier
from liquid2.builtin import Literal
from liquid2.builtin import StringLiteral
from liquid2.builtin import parse_keyword_arguments
from liquid2.builtin import parse_primitive
from liquid2.builtin import parse_string_or_identifier
from liquid2.exceptions import LiquidSyntaxError
from liquid2.exceptions import TemplateNotFoundError

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
        self.blank = False

    def __str__(self) -> str:
        assert isinstance(self.token, TagToken)
        var = ""
        if self.var:
            if self.loop:
                var = f" for {self.var}"
            else:
                var = f" with {self.var}"

        if self.alias:
            var += f" as {self.alias}"
        if self.args:
            var += ","
        args = " " + ", ".join(str(arg) for arg in self.args) if self.args else ""
        return (
            f"{{%{self.token.wc[0]} render "
            f"{self.name}{var}{args} {self.token.wc[1]}%}}"
        )

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        try:
            template = context.env.get_template(
                self.name.value, context=context, tag=self.tag
            )
        except TemplateNotFoundError as err:
            err.token = self.name.token
            err.template_name = context.template.full_name()
            raise

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
                context.raise_for_loop_limit(len(val))
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
        try:
            template = await context.env.get_template_async(
                self.name.value, context=context, tag=self.tag
            )
        except TemplateNotFoundError as err:
            err.token = self.name.token
            err.template_name = context.template.full_name()
            raise

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
                context.raise_for_loop_limit(len(val))
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

    def children(
        self, static_context: RenderContext, *, include_partials: bool = True
    ) -> Iterable[Node]:
        """Return this node's children."""
        if include_partials:
            name = self.name.evaluate(static_context)
            try:
                template = static_context.env.get_template(
                    str(name), context=static_context, tag=self.tag
                )
                yield from template.nodes
            except TemplateNotFoundError as err:
                err.token = self.name.token
                err.template_name = static_context.template.full_name()
                raise

    async def children_async(
        self, static_context: RenderContext, *, include_partials: bool = True
    ) -> Iterable[Node]:
        """Return this node's children."""
        if include_partials:
            name = await self.name.evaluate_async(static_context)
            try:
                template = await static_context.env.get_template_async(
                    str(name), context=static_context, tag=self.tag
                )
                return template.nodes
            except TemplateNotFoundError as err:
                err.token = self.name.token
                err.template_name = static_context.template.full_name()
                raise
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

        return Partial(name=self.name, scope=PartialScope.ISOLATED, in_scope=scope)


class RenderTag(Tag):
    """The standard _render_ tag."""

    block = False
    node_class = RenderNode

    def parse(self, stream: TokenStream) -> Node:
        """Parse tokens from _stream_ into an AST node."""
        token = stream.current()
        assert isinstance(token, TagToken)

        if not token.expression:
            raise LiquidSyntaxError(
                "expected the name of a template to render", token=token
            )

        tokens = TokenStream(token.expression)

        # The name of the template to render. Must be a string literal.
        name_token = tokens.next()

        if is_token_type(name_token, TokenType.SINGLE_QUOTE_STRING) or is_token_type(
            name_token, TokenType.DOUBLE_QUOTE_STRING
        ):
            name = StringLiteral(token=name_token, value=name_token.value)
        else:
            raise LiquidSyntaxError(
                "expected the name of a template to render as a string literal, "
                f"found {name_token.type_.name}",
                token=name_token,
            )

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
