This page gets you started using Liquid with Python. See [Liquid syntax](syntax.md) for an introduction to writing Liquid templates.

## Install

Install Python Liquid2 from [PyPi](https://pypi.org/project/python-liquid2/) using [pip](https://pip.pypa.io/en/stable/getting-started/):

```console
python -m pip install python-liquid2
```

Or [Pipenv](https://pipenv.pypa.io/en/latest/):

```console
pipenv install python-liquid2
```

Or [Poetry](https://python-poetry.org/):

```console
poetry add python-liquid2
```

## `render()`

Here's a very simple example that renders a template from a string of text with the package-level [`render()`](api/convenience.md#liquid2.render) function. The template has just one placeholder variable `you`, which we've given the value `"World"`.

```python
from liquid2 import render

print(render("Hello, {{ you }}!", you="World"))
# Hello, World!
```

## `parse()`

Often you'll want to render the same template several times with different variables. We can parse source text without immediately rendering it using the [`parse()`](api/convenience.md#liquid2.parse) function. `parse()` returns a [`Template`](api/template.md) instance with a `render()` method.

```python
from liquid2 import parse

template = parse("Hello, {{ you }}!")
print(template.render(you="World"))  # Hello, World!
print(template.render(you="Liquid"))  # Hello, Liquid!
```

## Configure

Both [`parse()`](api/convenience.md#liquid2.parse) and [`render()`](api/convenience.md#liquid2.render) are convenience functions that use the [default Liquid environment](environment.md). For all but the simplest cases you'll want to configure an instance of [`Environment`](api/environment.md), then load and render templates from that.

```python
from liquid2 import CachingFileSystemLoader
from liquid2 import Environment

env = Environment(
    auto_escape=True,
    loader=CachingFileSystemLoader("./templates"),
)
```

Then, using `env.from_string()` or `env.get_template()`, we can create a [`Template`](api/template.md) from a string or read from the file system, respectively.

```python
# ... continued from above
template = env.from_string("Hello, {{ you }}!")
print(template.render(you="World"))  # Hello, World!

# Try to load "./templates/index.html"
another_template = env.get_template("index.html")
data = {"some": {"thing": [1, 2, 3]}}
result = another_template.render(**data)
```

Unless you happen to have a relative folder called `templates` with a file called `index.html` within it, we would expect a `TemplateNotFoundError` to be raised when running the example above.

## What's next?

Read more about [configuring Liquid environments](environment.md), [template loaders](loading_templates.md) and [managing render context data](render_context.md).
