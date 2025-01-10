A Liquid tag is defined by a class extending [`Tag`](api/tag.md). It has just one abstract method, [`parse()`](api/tag.md#liquid2.Tag.parse), which takes an instance of [`TokenStream`](api/tokens.md#liquid2.TokenStream) and returns a [`Node`](api/ast.md#liquid2.Node). The returned node will be added to a template's abstract syntax tree and, when rendered, its [`render_to_output()`](api/ast.md#liquid2.Node.render_to_output) method will be called.

`render_to_output()` receives the active [render context](api/render_context.md) and an output buffer. It is responsible for either updating the render context or writing to the buffer, or both.

!!! tip

    See [liquid2/builtin/tags](https://github.com/jg-rp/python-liquid2/tree/main/liquid2/builtin/tags) for lots of examples.

## Add a tag

To add a tag, add an item to [`Environment.tags`](api/environment.md#liquid2.Environment.tags). It's a regular dictionary mapping tag names to instances of [`Tag`](api/tag.md).

This example implements the `with` tag, which allows template authors to define block scoped variables. `{% with %}` is a _block tag_. It has a start tag, an end tag (`{% endwith %}`), and Liquid markup in between. We should ensure that we leave the closing tag token on the stream.

### The tag

```python title="with_tag.py"

from liquid2 import BlockNode
from liquid2 import Node
from liquid2 import Tag
from liquid2 import TokenStream
from liquid2.builtin import parse_keyword_arguments

from .with_node import WithNode

class WithTag(Tag):

    def parse(self, stream: TokenStream) -> Node:
        token = stream.next()
        assert isinstance(token, TagToken)

        tokens = TokenStream(token.expression)
        args = parse_keyword_arguments(tokens)
        block = BlockNode(
            stream.current(), self.env.parser.parse_block(stream, ("endwith",))
        )

        stream.expect_tag("endwith")
        end_tag_token = stream.current()
        assert isinstance(end_tag_token, TagToken)

        return WithNode(token, args, block, end_tag_token)
```

The next token in the stream should always be an instance of [`TagToken`](api/tokens.md#liquid2.token.TagToken), describing the tag we're parsing. We use `assert` to confirm this and please Python's static type checker.

`TagToken` has an `expression` property, being a list of tokens representing the tag's expression. In this case we expect the expression to be an argument list, so we use the built-in `parse_keyword_arguments()` parse the expression tokens for us.

Next we need to parse the tag's block using `self.env.parser.parse_block()`. We pass it the token stream and tell it the name of the tag that will close the block. You'll notice that all tags have access to the current [`Environment`](environment.md) and all nodes must have an associated token. Those tokens are used to generate rich, informative error messages.

We pass the "end" token to `WithNode` for the benefit of Template serialization. If you're not interested in serializing a parsed template back to a string, there's no need to store `end_tag_token`.

### The node

```python title="with_node.py"
from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Iterable
from typing import TextIO

from liquid2 import BlockNode
from liquid2 import Node
from liquid2 import TagToken
from liquid2.builtin import Identifier

if TYPE_CHECKING:
    from liquid2 import Expression
    from liquid2 import RenderContext
    from liquid2 import TokenT
    from liquid2.builtin import KeywordArgument

class WithNode(Node):

    def __init__(
        self,
        token: TokenT,
        args: list[KeywordArgument],
        block: BlockNode,
        end_tag_token: TagToken,
    ):
        super().__init__(token)
        self.args = args
        self.block = block
        self.end_tag_token = end_tag_token
        self.blank = self.block.blank

    def __str__(self) -> str:
        assert isinstance(self.token, TagToken)
        args = " " + ", ".join(str(p) for p in self.args) if self.args else ""
        return (
            f"{{%{self.token.wc[0]} with{args} {self.token.wc[1]}%}}"
            f"{self.block}"
            f"{{%{self.end_tag_token.wc[0]} endwith {self.end_tag_token.wc[1]}%}}"
        )

    def render_to_output(self, context: RenderContext, buffer: TextIO) -> int:
        """Render the node to the output buffer."""
        namespace = dict(arg.evaluate(context) for arg in self.args)
        with context.extend(namespace):
            return self.block.render(context, buffer)

    async def render_to_output_async(
        self, context: RenderContext, buffer: TextIO
    ) -> int:
        """Render the node to the output buffer."""
        namespace = dict([await arg.evaluate_async(context) for arg in self.args])
        with context.extend(namespace):
            return await self.block.render_async(context, buffer)

    def expressions(self) -> Iterable[Expression]:
        """Return this node's expressions."""
        yield from (arg.value for arg in self.args)

    def children(
        self,
        static_context: RenderContext,
        *,
        include_partials: bool = True,
    ) -> Iterable[Node]:
        """Return this node's children."""
        yield self.block

    def block_scope(self) -> Iterable[Identifier]:
        """Return variables this node adds to the node's block scope."""
        yield from (Identifier(p.name, token=p.token) for p in self.args)
```

`WithNode.render_to_output()` evaluates its arguments, extends the render context and renders its block to the output buffer. The [`RenderContext.extend`](api/render_context.md#liquid2.RenderContext.extend) context manager is used to ensure the variables added by our tag go out of scope after the block has been rendered.

`expressions()`, `children()` and `block_Scope()` are all used for static analysis. It is the node's responsibility to report its child nodes, any instances of `Expression` that it maintains and the names of any variables it adds to template and/or block scope. If you don't plan to use Liquid's [static analysis](static_analysis.md) features, you can omit these methods.

The `__str__()` method is used for template serialization. It should return a string representation of the node using valid Liquid syntax. If you're not interested in serializing a parsed template back to a string, you can omit `__str__()`.

### Usage

We can now add an instance of `WithTag` to [`Environment.tags`](api/environment.md#liquid2.Environment.tags).

```python
from liquid2 import Environment

from .with_tag import WithTag

env = Environment()
env.tags["with"] = WithTag(env)

template = env.from_string(
"{% with greeting: 'Hello', name: 'Sally' -%}"
"  {{ greeting }}, {{ name }}!"
"{%- endwith %}"
)

print(template.render()) # Hello, Sally
```

## Replace a tag

To replace a default tag implementation with your own, simply update the [`tags`](api/environment.md#liquid2.Environment.tags) dictionary on your [environment](environment.md).

```python
from liquid2 import Environment
from .my_tag import MyTag

env = Environment()
env.tags["my_tag_name"] = MyTag(env)

# ...
```

## Remove a tag

Remove a built-in tag by deleting it from your [environment's](environment.md) [`tags`](api/environment.md#liquid2.Environment.tags) dictionary. The example removes the [`macro`](tag_reference.md#macro-and-call) `call` tags.

```python
from liquid import Environment

env = Environment()
del env.tags["macro"]
del env.tags["call"]

# ...
```

!!! tip

    You can add, remove and replace tags on `liquid2.DEFAULT_ENVIRONMENT` too. Convenience functions [`parse()`](api/convenience.md#liquid2.parse) and [`render()`](api/convenience.md#liquid2.render) use `DEFAULT_ENVIRONMENT`
