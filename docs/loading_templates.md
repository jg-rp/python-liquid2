A template loader is a class inheriting from [`BaseLoader`](api/loaders.md#liquid2.loader.BaseLoader). It is responsible for finding template source text given a name or identifier, and will be called upon whenever you or a tag call [`Environment.get_template()`](api/environment.md#liquid2.Environment.get_template) or await [`Environment.get_template_async()`](api/environment.md#liquid2.Environment.get_template_async).

To use one of the template loaders described here, pass an instance of your chosen loader as the `loader` argument when constructing a Liquid [`Environment`](environment.md).

## Built-in loaders

### Dictionary loader

[`DictLoader`](api/loaders.md#liquid2.DictLoader) is a template loader that stores template source text in memory using a dictionary. If you're experimenting with Liquid or if all your templates are known at application startup time and they all fit in RAM, then `DictLoader` is a good choice.

Simply pass a dictionary mapping template names to template source text to the `DictLoader` constructor.

```python
from liquid2 import DictLoader
from liquid2 import Environment

env = Environment(
    loader=DictLoader(
        {
            "index": "{% render 'header' %}\nbody\n{% render 'footer' %}",
            "header": "some header",
            "footer": "a footer",
        }
    )
)

template = env.get_template("index")
print(template.render())
```

```plain title="output"
some header
body
a footer
```

### Caching dictionary loader

[`CachingDictLoader`](api/loaders.md#liquid2.CachingDictLoader) is a [dictionary loader](#dictionary-loader) that maintains an in-memory LRU cache of parsed templates, so as to avoid parsing the same source text multiple times unnecessarily.

As well as a dictionary mapping template names to template source text, the `CachingDictLoader` constructor takes an optional `capacity` argument to control the maximum size of the cache. The default capacity is 300 templates.

```python
from liquid2 import CachingDictLoader
from liquid2 import Environment

env = Environment(
    loader=CachingDictLoader(
        {
            "index": "{% render 'header' %}\nbody\n{% render 'footer' %}",
            "header": "some header",
            "footer": "a footer",
        }
    )
)

template = env.get_template("index")
assert env.get_template("index") is template
```

### File system loader

[`FileSystemLoader`](api/loaders.md#liquid2.FileSystemLoader) is a template loader that reads source text from files on a file system. Its first argument, `search_path`, is a path to a folder containing Liquid templates, either as a string or `pathlib.Path`. `search_path` can also be a list of paths to search in order.

In this example, calls to [`Environment.get_template()`](api/environment.md#liquid2.Environment.get_template) will look for templates in a folder called `templates` relative to the current directory.

```python
from liquid2 import Environment
from liquid2 import FileSystemLoader

env = Environment(loader=FileSystemLoader("templates/"))
```

If a file called `index.html` exists in `./templates`, we could render it with `{% render 'index.html' %}`. To avoid having to include `.html` in every `render` tag, we can give `FileSystemLoader` a default file extension. It should include a leading `.`.

```python
from liquid2 import Environment
from liquid2 import FileSystemLoader

env = Environment(loader=FileSystemLoader("templates/", ext=".html"))
```

If your templates are organized in sub folders of `./templates`, you can include the relative path to a template in a `render` tag, `{% render 'snippets/footer' %}`, but you won't be allowed to escape out of `./templates`. This would raise a `TemplateNotFoundError`.

```liquid2
{% render '../../path/to/private/file' %}
```

### Caching file system loader

TODO

### Package loader

TODO

### Choice loader

TODO

## Load context

TODO:

## Matter

TODO

## Caching mixin

TODO

## Custom loaders

TODO
