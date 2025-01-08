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

## What's next?

See [loading templates](loading_templates.md) for more information about configuring a template loader, [undefined variables](variables_and_drops.md#undefined-variables) for information about managing undefined variables and [whitespace control](whitespace_control.md) for information about customizing whitespace control behavior.
