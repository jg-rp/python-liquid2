<h1 align="center">Python Liquid2</h1>

<p align="center">
Liquid templates for Python, with some extra features.
</p>

---

**Table of Contents**

- [Install](#install)
- [Links](#links)
- [Quick start](#quick-start)
- [Related Projects](#related-projects)

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

## Links

- Documentation: TODO
- Change Log: https://github.com/jg-rp/python-liquid2/blob/main/CHANGES.md
- PyPi: TODO
- Source Code: https://github.com/jg-rp/python-liquid2
- Issue Tracker: https://github.com/jg-rp/python-liquid2/issues

## Quick start

### `render()`

Here's a very simple example that renders a template from a string of text with the package-level `render()` function. The template has just one placeholder variable `you`, which we've given the value `"World"`.

```python
from liquid2 import render

print(render("Hello, {{ you }}!", you="World"))
# Hello, World!
```

### `parse()`

Often you'll want to render the same template several times with different variables. We can parse source text without immediately rendering it using the `parse()` function. `parse()` returns a `Template` instance with a `render()` method.

```python
from liquid2 import parse

template = parse("Hello, {{ you }}!")
print(template.render(you="World"))  # Hello, World!
print(template.render(you="Liquid"))  # Hello, Liquid!
```

### Configure

Both `parse()` and `render()` are convenience functions that use the default Liquid environment. For all but the simplest cases you'll want to configure an instance of `Environment`, then load and render templates from that.

```python
from liquid2 import CachingFileSystemLoader
from liquid2 import Environment

env = Environment(
    auto_escape=True,
    loader=CachingFileSystemLoader("./templates"),
)
```

Then, using `env.from_string()` or `env.get_template()`, we can create a `Template` from a string or read from the file system, respectively.

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
