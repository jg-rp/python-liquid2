# Liquid environments

Template parsing and rendering behavior is configured using an instance of [`Environment`](api/environment.md). Once configured, you'd parse templates with [`Environment.from_string()`](api/environment.md#liquid2.Environment.from_string) or [`Environment.get_template()`](api/environment.md#liquid2.Environment.get_template), both of which return an instance of [`Template`](api/template.md).

## The default environment

The default environment, `liquid2.DEFAULT_ENVIRONMENT`, and an instance of `Environment` without any arguments are equivalent to the following `Environment` subclass and constructor arguments.

```python
from liquid2 import DictLoader
from liquid2 import Environment
from liquid2 import Template
from liquid2 import Undefined
from liquid2 import WhitespaceControl
from liquid2.builtin import register_default_tags_and_filters
from liquid2.lexer import Lexer

class MyLiquidEnvironment(Environment):
    context_depth_limit = 30
    loop_iteration_limit = None
    loop_namespace_limit = None
    output_stream_limit = None
    suppress_blank_control_flow_blocks = True
    lexer_class = Lexer
    template_class = Template

    def setup_tags_and_filters(self):
        register_default_tags_and_filters(self)


env = MyLiquidEnvironment(
    loader=DictLoader(),
    globals=None,
    auto_escape=False,
    undefined=Undefined,
    default_trim=WhitespaceControl.PLUS
)
```

## Managing tags and filters

As you'd expect, [`register_default_tags_and_filters()`](api/builtin.md#liquid2.builtin.register_default_tags_and_filters) registers all the default tags and filters with the environment. You are encouraged to override `setup_tags_and_filters()` in your `Environment` subclasses to add optional or custom tags and filters, remove unwanted default tags and filters, and possibly replace default implementation with your own.

It's also OK to manipulate [`Environment.tags`](api/environment.md#liquid2.Environment.tags) and [`Environment.filters`](api/environment.md#liquid2.Environment.filters) directly after an `Environment` instance has been created. They are just dictionaries mapping tag names to instances of [`Tag`](api/tag.md) and filter names to callables, respectively.

```python
from liquid2 import Environment

env = Environment()
del env.tags["include"]
```

## Managing global variables

By default, global template variables attached to instances of [`Template`](api/template.md) take priority over global template variables attached to an `Environment`. You can change this priority or otherwise manipulate the `globals` dictionary for a `Template` by overriding [`Environment.make_globals()`](api/environment.md#liquid2.Environment.make_globals).

Also see [Render context data](render_context.md).

```python
from typing import Mapping
from liquid2 import Environment

class MyLiquidEnvironment(Environment):

    def make_globals(
        self,
        globals: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        """Combine environment globals with template globals."""
        if globals:
            # Template globals take priority over environment globals.
            return {**self.globals, **globals}
        return dict(self.globals)
```

## HTML auto escape

When `auto_escape` is `True`, [render context variables](render_context.md) will be automatically escaped to produce HTML-safe strings on output.

You can be explicitly mark strings as _safe_ by wrapping them in `Markup()` and [drops](variables_and_drops.md) can implement the [special `__html__()` method](variables_and_drops.md#__html__).

```python
from markupsafe import Markup
from liquid2 import Environment

env = Environment(auto_escape=True)
template = env.from_string("<p>Hello, {{ you }}</p>")
print(template.render(you=Markup("<em>World!</em>")))
```

## Resource limits

For deployments where template authors are untrusted, you can set limits on some resources to avoid malicious templates from consuming too much memory or too many CPU cycles. Limits are set by subclassing [`Environment`](api/environment.md) and setting some class attributes.

```python
from liquid2 import Environment

class MyEnvironment(Environment):
    context_depth_limit = 30
    local_namespace_limit = 2000
    loop_iteration_limit = 1000
    output_stream_limit = 15000


env = MyEnvironment()

template = env.from_string("""\
{% for x in (1..1000000) %}
{% for y in (1..1000000) %}
    {{ x }},{{ y }}
{% endfor %}
{% endfor %}
""")

template.render()
# liquid2.exceptions.LoopIterationLimitError: loop iteration limit reached
```

### Context depth limit

[`context_depth_limit`](api/environment.md#liquid2.Environment.context_depth_limit) is the maximum number of times a render context can be extended or wrapped before a `ContextDepthError` is raised. This helps us guard against recursive use of the `include` and `render` tags. The default context depth limit is 30.

```python
from liquid2 import Environment
from liquid2 import DictLoader

env = Environment(
    loader=DictLoader(
        {
            "foo": "{% render 'bar' %}",
            "bar": "{% render 'foo' %}",
        }
    )
)

template = env.from_string("{% render 'foo' %}")
template.render()
# liquid2.exceptions.ContextDepthError: maximum context depth reached, possible recursive render
#   -> foo:1:0
#   |
# 1 | {% render 'bar' %}
#   | ^^^^^^^^^^^^^^^^^^ maximum context depth reached, possible recursive render
```

### Local Namespace Limit

[`local_namespace_limit`](api/environment.md#liquid2.Environment.local_namespace_limit) is the maximum number of bytes (according to `sys.getsizeof()`) allowed in a template's local namespace, per render, before a `LocalNamespaceLimitError` exception is raised. Note that we only count the size of the local namespace values, not its keys.

The default `local_namespace_limit` is `None`, meaning there is no limit.

```python
from liquid2 import Environment

class MyEnvironment(Environment):
    local_namespace_limit = 50  # Very low, for demonstration purposes.

env = MyEnvironment()

template = env.from_string("""\
{% assign x = "Nunc est nulla, pellentesque ac dui id erat curae." %}
""")

template.render()
# liquid2.exceptions.LocalNamespaceLimitError: local namespace limit reached
```

!!! warning

    [PyPy](https://doc.pypy.org/en/latest/cpython_differences.html) does not implement `sys.getsizeof`. Instead of a size in bytes, when run with PyPy, `local_namespace_limit` will degrade to being the number of distinct values in a template's local namespace.

### Loop Iteration Limit

[`loop_iteration_limit`](api/environment.md#liquid2.Environment.loop_iteration_limit) is the maximum number of loop iterations allowed before a `LoopIterationLimitError` is raised.

The default `loop_iteration_limit` is `None`, meaning there is no limit.

```python
from liquid2 import Environment

class MyEnvironment(Environment):
    loop_iteration_limit = 999


env = MyEnvironment()

template = env.from_string("""\
{% for x in (1..100) %}
{% for y in (1..100) %}
    {{ x }},{{ y }}
{% endfor %}
{% endfor %}
""")

template.render()
# liquid2.exceptions.LoopIterationLimitError: loop iteration limit reached
```

Other built in tags that contribute to the loop iteration counter are `render`, `include` (when using their `{% render 'thing' for some.thing %}` syntax) and `tablerow`. If a partial template is rendered within a `for` loop, the loop counter is carried over to the render context of the partial template.

### Output Stream Limit

The maximum number of bytes that can be written to a template's output stream, per render, before an `OutputStreamLimitError` exception is raised. The default `output_stream_limit` is `None`, meaning there is no limit.

```python
from liquid2 import Environment

class MyEnvironment(Environment):
    output_stream_limit = 20  # Very low, for demonstration purposes.


env = MyEnvironment()

template = env.from_string("""\
{% if false %}
this is never rendered, so will not contribute the the output byte counter
{% endif %}
Hello, {{ you }}!
""")

template.render(you="World")
# '\nHello, World!\n'

template.render(you="something longer that exceeds our limit")
# liquid2.exceptions.OutputStreamLimitError: output stream limit reached
```

## What's next?

See [loading templates](loading_templates.md) for more information about configuring a template loader, [undefined variables](variables_and_drops.md#undefined-variables) for information about managing undefined variables and [whitespace control](whitespace_control.md) for information about customizing whitespace control behavior.
