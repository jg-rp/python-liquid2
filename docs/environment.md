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

## Customizing whitespace control

[`Environment.trim()`](api/environment.md#liquid2.Environment.trim) is called when stripping whitespace from template content according to tag whitespace control characters (`-`, `+` and `~`). By default, `-` will trim all whitespace, `+` will retain all whitespace regardless of [`Environment.default_trim`](api/environment.md#liquid2.Environment.default_trim), and `~` will remove only `\r` and `\n` characters.

Override [`Environment.trim()`](api/environment.md#liquid2.Environment.trim) to define your own whitespace control behavior.

```python
from liquid2 import Environment
from liquid2 import WhitespaceControl

class MyLiquidEnvironment(Environment):

    def trim(
        self,
        text: str,
        left_trim: WhitespaceControl,
        right_trim: WhitespaceControl,
    ) -> str:
        """Return _text_ after applying whitespace control."""
        if left_trim == WhitespaceControl.DEFAULT:
            left_trim = self.default_trim

        if right_trim == WhitespaceControl.DEFAULT:
            right_trim = self.default_trim

        if left_trim == right_trim:
            if left_trim == WhitespaceControl.MINUS:
                return text.strip()
            if left_trim == WhitespaceControl.TILDE:
                return text.strip("\r\n")
            return text

        if left_trim == WhitespaceControl.MINUS:
            text = text.lstrip()
        elif left_trim == WhitespaceControl.TILDE:
            text = text.lstrip("\r\n")

        if right_trim == WhitespaceControl.MINUS:
            text = text.rstrip()
        elif right_trim == WhitespaceControl.TILDE:
            text = text.rstrip("\r\n")

        return text
```
