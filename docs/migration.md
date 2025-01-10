# Migration guide

When compared to [Python Liquid](https://github.com/jg-rp/liquid) and [Shopify/Liquid](https://github.com/Shopify/liquid), Liquid2 adds features, subtly changes the syntax of Liquid templates and changes the template engine's Python API. This is not "Python Liquid version 2", but a Python implementation of "Liquid2", which is mostly backwards compatible with other implementations.

## Approach to compatibility and stability

With [Python Liquid](https://github.com/jg-rp/liquid), our primary objectives were render behavior stability and Shopify/Liquid compatibility, in that order. Later we introduced `liquid.future.Environment`, which sacrificed some stability for greater Shopify/Liquid compatibility as Shopify/Liquid and our understanding of it changed.

Now, with Python Liquid2, render behavior stability is still the top priority, but the default environment deliberately deviates from Shopify/Liquid in several ways, "fixing" and adding often requested features that Shopify can't due to their large user base and the technical debt that comes with it.

In most cases these fixes and features are backwards compatible with Shopify/Liquid, requiring little or no modification to legacy Liquid templates. To ease transition from legacy templates to Liquid2 templates, we include a `liquid2.shopify.Environment`, which is configured to include some legacy tags that didn't make it in to the default environment.

### Why is render stability so important?

When developing a conventional website, for example, templates are developed along side application code. Template authors and application developers might be different people or different teams, but templates are known at deployment time, and all templates can probably be parsed upfront and held in memory. In this scenario it's a pain if your template render engine introduces behavioral changes, but it's manageable.

Python Liquid2 caters for situations where templates change and grow with an application's user base. Not only can templates change after the application is deployed, but the number of templates could be huge, far more than can be expected to fit in memory all at once.

Behavioral stability is essential when application users are responsible for maintaining templates. It is impractical or unreasonable to expect authors to update their templates on demand.

Whether shopify/Liquid compatibility is important to you or not, if you're developing a multi-tenant application where users are responsible for maintaining templates, you should seriously consider building in an opt-in upgrade path for template authors to transition to updated syntax and features.

## New features

### More whitespace control

Along with a [`default_trim`](api/environment.md#liquid2.Environment.default_trim) configuration option, tags and the output statement now support `+`, `-` and `~` for controlling whitespace in templates. By default, `~` will remove newlines but retain space and tab characters.

Here we use `~` to remove the newline after the opening `for` tag, but preserve indentation before `<li>`.

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

### Array construction syntax

If the left-hand side of a filtered expression (those found in output statements, the `assign` tag and the `echo` tag) is a comma separated list of primitive expressions, an array-like object will be created with those items.

```liquid2
{% assign my_array = a, b, '42', false -%}
{% for item in my_array -%}
    - {{ item }}
{% endfor %}
```

or, using a `{% liquid %}` tag:

```liquid2
{% liquid
    assign my_array = a, b, '42', false
    for item in my_array
        echo "- ${item}\n"
    endfor %}
```

With `a` set to `"Hello"` and `b` set to `"World"`, both of the examples above produce the following output.

```plain title="output"
- Hello
- World
- 42
- false
```

### String interpolation

String literals support interpolation using JavaScript-style `${` and `}` delimiters. Liquid template strings don't use backticks like JavaScript. Any single or double quoted string can use `${variable_name}` placeholders for automatic variable substitution.

`${` can be escaped with `\${` to prevent variable substitution.

Liquid template strings are effectively a shorthand alternative to `capture` tags or chains of `append` filters. These two tags equivalent.

```liquid2
{% capture greeting %}
Hello, {{ you | capitalize }}!
{% endcapture %}

{% assign greeting = 'Hello, ${you | capitalize}!' %}
```

### Logical `not`

Logical expressions now support negation with the `not` operator and grouping terms with parentheses by default. Previously this was an opt-in feature.

In this example, `{% if not user %}` is equivalent to `{% unless user %}`, however, `not` can also be used after `and` and `or`, like `{% if user.active and not user.title %}`, potentially saving nested `if` and `unless` tags.

```liquid2
{% if not user %}
  please log in
{% else %}
  hello user
{% endif %}
```

### Ternary expressions

Inline conditional expression are now supported by default. Previously this was an opt-in feature. If omitted, the `else` branch defaults to an instance of `Undefined`.

```liquid2
{{ a if b else c }}
{{ a | upcase if b == 'foo' else c || split }}
```

### Dedicated comment syntax

Comments surrounded by `{#` and `#}` are enabled by default. Additional `#`'s can be added to comment out blocks of markup that already contain comments, as long as hashes are balanced.

```liquid2
{## comment this out for now
{% for x in y %}
    {# x could be empty #}
    {{ x | default: TODO}}
{% endfor %}
##}
```

### Better string literal parsing

String literals are now allowed to contain markup delimiters (`{{`, `}}`, `{%`, `%}`, `{#` and `#}`) and support c-like escape sequence to allow for including quote characters, literal newline characters and `\uXXXX` Unicode code points.

```liquid2
{% assign x = "Hi \uD83D\uDE00!" %}
{{ x }}
```

```plain title="output"
Hi 😀!
```

### Unicode identifiers

Identifiers and paths resolving to variables can contain Unicode characters (templates are assumed to be UTF-8 encoded). For example:

```liquid2
{% assign 😀 = 'smiley' %}
{{ 😀 }}
```

### Scientific notation

Integer and float literals can use scientific notation, like `1.2e3` or `1e-2`.

### Common argument delimiters

Filter and tag named arguments can be separated by a `:` or `=`. Previously only `:` was allowed.

### Template inheritance

Template inheritance is now built-in. Previously [`{% extends %}`](tag_reference.md#extends) and [`{% block %}`](tag_reference.md#block) tags were available from a separate package.

### i18n and l10n

Internationalization and localization tags and filters are now built in and enabled by default. Previously these were in a separate package.

See [currency](filter_reference.md#currency), [datetime](filter_reference.md#datetime), [money](filter_reference.md#money), [decimal](filter_reference.md#decimal), [unit](filter_reference.md#unit), [gettext](filter_reference.md#gettext), [t](filter_reference.md#t) and [translate](tag_reference.md#translate).

### Serializable templates

Instances of `Template` are now serializable. Use `str(template)` or `pickle.dump(template)`.

### Better exceptions

Error messages have been improved and exceptions inheriting from `LiquidError` expose line and column numbers, and have `detailed_message()` and error `context()` methods.

```liquid2
{% assign foo = (0..3) %}
{% for x foo %}
    {{ x }}
{% endfor %}
```

```plain title="error message"
liquid2.exceptions.LiquidSyntaxError: expected IN, found WORD
  -> '{% for x foo %}' 2:9
  |
2 | {% for x foo %}
  |          ^^^ expected IN, found WORD
```

## Features that have been removed

- We no longer offer "lax" or "warn" modes, previously controlled by the `tolerance` argument to `Environment`. The assertion is that errors should be loud and we should be made aware as early as possible, whether you're an experienced developer or not.
- It's not currently possible to change Liquid markup delimiters (`{{`, `}}`, `{%` and `%}`).
- Async filters have not been implemented, but can be if there is a demand.
- Contextual template analysis has not been implemented, but can be if there is a demand.
- Template tag analysis (analyzing tokens instead of a syntax tree) has not been implemented, but can be if there is a demand.
- Liquid Babel used to allow simple, zero-argument filters in the arguments to the `translate` tag. The `translate` tag bundled in to Liquid2 does not allow the use of filters here.
- There's no Django template backend or Flask extension for Python Liquid2. Open an issue if these are things that would be useful to you.
- The [Liquid JSONPath](https://github.com/jg-rp/liquid-jsonpath) project has not yet been ported to Python Liquid2. Open an issue if yuo'd like to see JSONPath syntax added to Liquid2.

## API changes

These are the most notable changes. Please raise an [issue](https://github.com/jg-rp/python-liquid2/issues) or start a discussion if I've missed anything or you need help with migration.

- Package level `Template` can no longer be used as a convenience function for creating a template from a string. Use [`parse()`](api/convenience.md#liquid2.parse), [`render()`](api/convenience.md#liquid2.render) or [`DEFAULT_ENVIRONMENT.from_string()`](api/environment.md#liquid2.Environment.from_string) instead.
- `StrictUndefined` now plays nicely with the `default` filter. Previously we had a separate `StrictDefaultUndefined` class.
- [`FileSystemLoader`](api/loaders.md#liquid2.FileSystemLoader) now takes an optional default file extension to use when looking for files that don't already have an extension. Previously there was a separate `FileExtensionLoader`.
- `AwareBoundTemplate` (a template with a built-in `template` drop) has been removed, but can be added as a feature later if there is a demand.
- The `auto_reload` and `cache_size` arguments to `Environment` have been removed. Now caching is handle by template loaders, not the environment. For example, pass a [`CachingFileSystemLoader`](api/loaders.md#liquid2.CachingFileSystemLoader) as the `loader` argument to `Environment` instead of a `FileSystemLoader`.
- The `strict_filters` argument to `Environment` has been removed. Unknown filters now always raise an `UnknownFilterError`.
- `TemplateNotFound` has been renamed to `TemplateNotFoundError`.
- `Context` has been renamed to [`RenderContext`](api/render_context.md) and now takes a mandatory `template` argument instead of `env`. All other arguments to `RenderContext` are now keyword only.
- `FilterValueError` and `FilterArgumentError` have been removed. `LiquidValueError` and `LiquidTypeError` should be used instead. In some cases where `FilterValueError` was deliberately ignored before, `LiquidValueError` is now raised.
- The exception `NoSuchFilterFunc`, raised when rendering a template that uses a filter that is not defined in `Environment.filters`, has been renamed to `UnknownFilterError`.
- The `@liquid_filter` decorator has been removed. Now filter implementations are expected to raise a `LiquidTypeError` in the event of an argument with an unacceptable type.
- [`Environment.tags`](api/environment.md#liquid2.Environment.tags) is now a mapping of tag names to `Tag` instances. It used to be a mapping of names to `Tag` classes.

### Custom tags

[docs](custom_tags.md)

The lexer has been completely rewritten and the token's it produces bear little resemblance to those produced by any of the several parsing functions from Python Liquid. Now we have a single lexer that scans source text content, tags, statements and expressions in a single pass, and a parser that delegates the parsing of those tokens to classes implementing `Tag`.

These changes were necessary to support "proper" string literals with escaping, Unicode support and interpolation.

As before, `Tag` instances are responsible for returning `Node`s from `Tag.parse()`. And nodes still have the familiar `render_to_output()` abstract method.

As a result of these changes, custom tags are now limited to using tokens recognized by the lexer. Previously, custom tags would be passed their expression as a string to be parsed however you see fit, now tags are passed a sequence of tokens.

For now I recommend familiarizing yourself with the different [tokens][liquid2.token.TokenT] generated by the lexer and have a look at the [custom tags docs](custom_tags.md). Note that the [`TokenStream`](api/tokens.md#liquid2.TokenStream) interface has changed too.

As always, open an [issue](https://github.com/jg-rp/python-liquid2/issues) or start a discussion if you need any help with migration.

## Package dependencies

The following packages are dependencies of Python Liquid2.

- Markupsafe>=3
- Babel>=2
- python-dateutil
- pytz
- typing-extensions
