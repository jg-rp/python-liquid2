By default, all whitespace immediately before and after a tag is preserved. This can result in a lot of unwanted whitespace.

```liquid2
<ul>
{% for x in (1..4) %}
  <li>{{ x }}</li>
{% endfor %}
</ul>
```

```plain title="output"
<ul>

  <li>1</li>

  <li>2</li>

  <li>3</li>

  <li>4</li>

</ul>
```

By inserting special characters inside tags and output statements, template authors can choose what whitespace trimming rules to apply. `-` is used to remove all whitespace until the next printing character, and `~` will trim immediate carriage returns and newlines, leaving spaces and tabs.

There's also `+`, which has no effect with the [default trim](#default-trim) mode.

```liquid2
<ul>
{% for x in (1..4) ~%}
  <li>{{ x }}</li>
{% endfor -%}
</ul>
```

```plain title="output"
<ul>
  <li>1</li>
  <li>2</li>
  <li>3</li>
  <li>4</li>
</ul>
```

## Default trim

You can change the default whitespace trimming mode using the [`default_trim`](api/environment.md) argument when constructing an [`Environment`](environment.md).

Setting `default_trim` to [`WhitespaceControl.MINUS`](api/whitespace_control.md#liquid2.WhitespaceControl.MINUS) will automatically remove all whitespace unless it is explicitly overridden by the template author using `+` or `~`.

Setting `default_trim` to [`WhitespaceControl.TILDE`](api/whitespace_control.md#liquid2.WhitespaceControl.TILDE) will automatically remove immediate carriage returns an newlines unless it is explicitly overridden by the template author using `+` or `-`.

## Customizing whitespace control

[`Environment.trim()`](api/environment.md#liquid2.Environment.trim) is called when stripping whitespace from template content. You can override `trim()` in an [`Environment`](environment.md) subclass to define your own whitespace control behavior, interpreting `-`, `+` and `~` however you see fit.

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

## Suppressing blank control flow blocks

It is assumed that a conditional block containing no template content or output statements should not render its whitespace. For example, the newlines between the tags and spaces before `assign` here are automatically suppressed, regardless of the [default trim](#default-trim) mode.

```liquid2
{% if true %}
    {% assign x = y %}
{% endif %}
```

You can disable this feature by subclassing [`Environment`](api/environment.md) and setting the `suppress_blank_control_flow_blocks` class attribute to `False`.

```python
from liquid2 import Environment

class MyEnvironment(Environment):
    suppress_blank_control_flow_blocks = False
```
