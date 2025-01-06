## As simple as possible

For one-off templates using nothing but the default [tags](tag_reference.md) and [filters](filter_reference.md), and without the possibility of [including](tag_reference.md#include), [rendering](tag_reference.md#render) or [extending](tag_reference.md#extends) other templates, use the package-level [`render()`](api/convenience.md#liquid2.render) function.

It takes template source text as a string and any number of keyword arguments that will be made available as template variables, returning a string.

```python
from liquid2 import render

result = render("Hello, {{ you }}!", you="World")
```

If you want to render the same template multiple times with different data, use the package-level [`parse()`](api/convenience.md#liquid2.parse) function. It takes template source text as a string, an optional name for the template and an optional dictionary of variables to attach to the template. An instance of [`Template`](api/template.md) with a [`render()`](api/template.md#liquid2.Template.render) method is returned.

```python
from liquid2 import parse

template = parse("Hello, {{ you }}!")
result = template.render(you="World")
another_result = template.render(you="Liquid")
```

## Common configuration

Often, at a minimum, you'll want to configure a [template loader](loading_templates.md) that reads template source text from a file system and give Liquid a default file extension to use. Doing this will tell the Liquid engine where to look for templates when [including](tag_reference.md#include), [rendering](tag_reference.md#render) or [extending](tag_reference.md#extends) other templates.

```python
from liquid2 import Environment
from liquid2 import CachingFileSystemLoader

env = Environment(
    loader=CachingFileSystemLoader("path/to/templates", ext=".html"),
)
```

Now, if there's a file called "main.html" in "/path/to/templates/", we can use [`env.get_template()`](api/environment.md##liquid2.Environment.get_template) to load and parse it, along with any templates it [includes](tag_reference.md#include), [renders](tag_reference.md#render) or [extends](tag_reference.md#extends).

```python
# ... continued from above
template = env.get_template("main.html")
data = {"foo": 42, "bar": "hello"}
result = render(**data)
```

See [Liquid environments](environment.md) for more information about configuring an [`Environment`](api/environment.md) and [loading templates](loading_templates.md) for details of the built-in template loaders.
