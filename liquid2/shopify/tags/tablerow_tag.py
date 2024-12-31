"""The _tablerow_ tag."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Iterable
from typing import Iterator
from typing import Mapping
from typing import TextIO

from liquid2 import BlockNode
from liquid2 import Expression
from liquid2 import Node
from liquid2 import Tag
from liquid2 import TagToken
from liquid2 import TokenStream
from liquid2.builtin import Identifier
from liquid2.builtin import LoopExpression
from liquid2.exceptions import BreakLoop
from liquid2.exceptions import ContinueLoop
from liquid2.exceptions import LiquidSyntaxError
from liquid2.limits import to_int

if TYPE_CHECKING:
    from liquid2 import TokenT
    from liquid2.context import RenderContext


class TablerowNode(Node):
    """The _tablerow_ tag."""

    __slots__ = ("expression", "block", "end_tag_token")

    def __init__(
        self,
        token: TokenT,
        expression: LoopExpression,
        block: BlockNode,
        end_tag_token: TagToken,
    ):
        super().__init__(token)
        self.expression = expression
        self.block = block
        self.end_tag_token = end_tag_token
        self.blank = False

    def __str__(self) -> str:
        assert isinstance(self.token, TagToken)
        return (
            f"{{%{self.token.wc[0]} tablerowloop "
            f"{self.expression} {self.token.wc[1]}%}}"
            f"{self.block}"
            f"{{%{self.end_tag_token.wc[0]} endtablerowloop "
            f"{self.end_tag_token.wc[1]}%}}"
        )

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        name = self.expression.identifier
        it, length = self.expression.evaluate(context)

        context.raise_for_loop_limit(length)

        if self.expression.cols is None:
            cols = length
        else:
            cols = _int_or_zero(self.expression.cols.evaluate(context))

        # Number of Unicode "characters" written to the output buffer.
        character_count = 0

        drop = TableRow(
            name=f"{name}-{self.expression.iterable}",
            it=it,
            length=length,
            ncols=cols,
        )

        namespace: dict[str, Any] = {
            "tablerowloop": drop,
            name: None,
        }

        character_count += buffer.write('<tr class="row1">\n')
        _break = False

        with context.extend(namespace):
            for item in drop:
                namespace[name] = item
                character_count += buffer.write(f'<td class="col{drop.col}">')

                try:
                    character_count += self.block.render(context=context, buffer=buffer)
                except BreakLoop:
                    _break = True
                except ContinueLoop:
                    pass

                character_count += buffer.write("</td>")

                if drop.col_last and not drop.last:
                    character_count += buffer.write(
                        f'</tr>\n<tr class="row{drop.row + 1}">'
                    )

                if _break:
                    break

        character_count += buffer.write("</tr>\n")
        return character_count

    async def render_to_output_async(
        self, context: RenderContext, buffer: TextIO
    ) -> int:
        """Render the node to the output buffer."""
        name = self.expression.identifier
        it, length = await self.expression.evaluate_async(context)

        context.raise_for_loop_limit(length)

        if self.expression.cols is None:
            cols = length
        else:
            cols = _int_or_zero(await self.expression.cols.evaluate_async(context))

        # Number of Unicode "characters" written to the output buffer.
        character_count = 0

        drop = TableRow(
            name=f"{name}-{self.expression.iterable}",
            it=it,
            length=length,
            ncols=cols,
        )

        namespace: dict[str, Any] = {
            "tablerowloop": drop,
            name: None,
        }

        character_count += buffer.write('<tr class="row1">\n')
        _break = False

        with context.extend(namespace):
            for item in drop:
                namespace[name] = item
                character_count += buffer.write(f'<td class="col{drop.col}">')

                try:
                    character_count += await self.block.render_async(
                        context=context, buffer=buffer
                    )
                except BreakLoop:
                    _break = True
                except ContinueLoop:
                    pass

                character_count += buffer.write("</td>")

                if drop.col_last and not drop.last:
                    character_count += buffer.write(
                        f'</tr>\n<tr class="row{drop.row + 1}">'
                    )

                if _break:
                    break

        character_count += buffer.write("</tr>\n")
        return character_count

    def children(
        self,
        static_context: RenderContext,  # noqa: ARG002
        *,
        include_partials: bool = True,  # noqa: ARG002
    ) -> Iterable[Node]:
        """Return this node's children."""
        yield self.block

    def expressions(self) -> Iterable[Expression]:
        """Return this node's expressions."""
        yield self.expression

    def block_scope(self) -> Iterable[Identifier]:
        """Return variables this node adds to the node's block scope."""
        yield Identifier(self.expression.identifier, token=self.expression.token)
        yield Identifier("tablerowloop", token=self.token)


class TablerowTag(Tag):
    """The _tablerow_ tag."""

    node_class = TablerowNode

    def parse(self, stream: TokenStream) -> Node:
        """Parse tokens from _stream_ into an AST node."""
        token = stream.next()
        assert isinstance(token, TagToken)

        if not token.expression:
            raise LiquidSyntaxError("missing expression", token=token)

        expression = LoopExpression.parse(TokenStream(token.expression))
        block_token = stream.current()
        assert block_token is not None
        block = BlockNode(
            block_token, self.env.parser.parse_block(stream, end=("endtablerow"))
        )

        stream.expect_tag("endtablerow")
        end_tag_token = stream.current()
        assert isinstance(end_tag_token, TagToken)

        return self.node_class(
            token,
            expression,
            block,
            end_tag_token,
        )


class TableRow(Mapping[str, object]):
    """The _tablerow_ drop."""

    __slots__ = (
        "name",
        "it",
        "length",
        "ncols",
        "_index",
        "_row",
        "_col",
    )

    _keys = frozenset(
        [
            "length",
            "index",
            "index0",
            "rindex",
            "rindex0",
            "first",
            "last",
            "col",
            "col0",
            "col_first",
            "col_last",
            "row",
        ]
    )

    def __init__(self, name: str, it: Iterator[Any], length: int, ncols: int) -> None:
        self.name = name
        self.it = it
        self.length = length
        self.ncols = ncols
        self._index = -1
        self._row = 1
        self._col = 0

    def __repr__(self) -> str:  # pragma: no cover
        return f"TableRow(name='{self.name}', length={self.length})"

    def __getitem__(self, key: str) -> object:
        if key in self._keys:
            return getattr(self, key)
        raise KeyError(key)

    def __len__(self) -> int:
        return len(self._keys)

    def __iter__(self) -> Iterator[Any]:
        return self

    def __next__(self) -> object:
        self.step()
        return next(self.it)

    @property
    def index(self) -> int:
        """The 1-based index of the current loop iteration."""
        return self._index + 1

    @property
    def index0(self) -> int:
        """The 0-based index of the current loop iteration."""
        return self._index

    @property
    def rindex(self) -> int:
        """The 1-based index, counting from the right, of the current loop iteration."""
        return self.length - self._index

    @property
    def rindex0(self) -> int:
        """The 0-based index, counting from the right, of the current loop iteration."""
        return self.length - self._index - 1

    @property
    def first(self) -> bool:
        """True if this is the first iteration, false otherwise."""
        return self._index == 0

    @property
    def last(self) -> bool:
        """True if this is the last iteration, false otherwise."""
        return self._index == self.length - 1

    @property
    def col(self) -> int:
        """The 1-based index of the current column."""
        return self._col

    @property
    def col0(self) -> int:
        """The 0-based index of the current column."""
        return self._col - 1

    @property
    def col_first(self) -> bool:
        """True if this is the first column. False otherwise."""
        return self._col == 1

    @property
    def col_last(self) -> bool:
        """True if this is the last iteration, false otherwise."""
        return self._col == self.ncols

    @property
    def row(self) -> int:
        """The current row number."""
        return self._row

    def step(self) -> None:
        """Step the tablerowloop forward."""
        self._index += 1
        if self._col == self.ncols:
            self._col = 1
            self._row += 1
        else:
            self._col += 1


def _int_or_zero(arg: object) -> int:
    try:
        return to_int(arg)
    except ValueError:
        return 0
