# Migration guide

When compared to [Python Liquid version 1](https://github.com/jg-rp/liquid), Liquid2 changes both the Python API **and** Liquid syntax and features. Liquid2's default syntax and semantics are backwards compatible with version 1 and Shopify/Liquid, mostly.

## Approach to compatibility and stability

With Python Liquid version 1, our primary objectives were render behavior stability and Shopify/Liquid compatibility, in that order. Later we introduced `liquid.future.Environment`, which sacrificed some stability for greater Shopify/Liquid compatibility as Shopify/Liquid and our understanding of it changed.

Now, with Python Liquid version 2, render behavior stability is still the top priority, but the default environment deliberately deviates from Shopify/Liquid in several ways, "fixing" and adding often requested features that Shopify can't due to their large user base and the technical debt that comes with it.

In most cases these fixes and features are backwards compatible with Shopify/Liquid, requiring little or no modification to legacy Liquid templates. To ease transition from legacy templates to Liquid2 templates we include a `liquid2.shopify.Environment`, which is configured to include some legacy tags that didn't make it in to the default environment.

### Why is render stability so important?

When developing a conventional website, for example, templates are developed along side application code. Template authors and application developers might be different people or different teams, but templates are known at deployment time, and all templates can probably be parsed upfront and held in memory. In this scenario it's a pain if your template render engine introduces behavioral changes, but it's manageable.

Python Liquid caters for situations where templates change and grow with an application's user base. Not only can templates change after the application is deployed, but the number of templates could be huge, far more than can be expected to fit in memory at one time.

Behavioral stability is essential when application users are responsible for maintaining templates. It is impractical or unreasonable to expect authors to update their templates TODO: …

Whether shopify/Liquid compatibility is important to you or not, if you’re developing a multi-tenant application where users are responsible for maintaining templates, you should seriously consider building in an opt-in upgrade path for template authors to TODO: …

## New features

The following features are new or are now built-in where they weren't before.

- More whitespace control. Along with a `default_trim` configuration option, tags and the output statement now support `+`, `-` and `~` for controlling whitespace in templates. By default, `~` will remove newlines but retain space and tab characters.
- Logical expressions now support negation with the `not` operator and grouping terms with parentheses by default.
- Ternary expressions are now available by default. For example, `{{ a if b else c }}` or `{{ a | upcase if b == 'foo' else c || split }}`.
- Inline comments surrounded by `{#` and `#}` are enabled by default. Additional `#`’s can be added to comment out blocks of markup that already contain comments, as long as the number of hashes match.
- String literals are allowed to contain markup delimiters (`{{`, `}}`, `{%`, `%}`, `{#` and `#}`) and support c-like escape sequence to allow for including quote characters.
- Filter and tag named arguments can be separated by a `:` or `=`.
- Template inheritance is now built-in. Previously `{% extends %}` and `{% block %}` tags were available from a separate package.
- Internationalization and localization tags and filters are now built-in. Previously these were in a separate package.
- Templates are now serializable. Use `str(template)` or `pickle.dump(template)`.
- Error messages have been improved and exceptions include line and column numbers.
- A new test suite is included if you'd like to implement Liquid2 in another language.

## Features that have been removed

These features are not yet included in Python Liquid2, but can be if there is a demand.

- Async filters have not been implemented.
- Contextual template analysis has not been implemented.
- Template tag analysis (analyzing tokens instead of a syntax tree) has not been implemented.
- The `@liquid_filter` decorator has been removed. Now filter implementations are expected to raise a `LiquidTypeError` in the even of an argument with an unacceptable type.
- Liquid Babel used to allow simple, zero-argument filters in the arguments to the `translate` tag. The `translate` tag bundled in to Liquid2 does not allow the use of filters here.

## API changes

These are the most notable changes. Please raise an [issue](https://github.com/jg-rp/python-liquid2/issues) or start a discussion if I've missed anything or you need help with migration.

- Package level `Template` can no longer be used as a convenience function for creating a template from a string. Use `parse()` or `DEFAULT_ENVIRONMENT.from_string()` instead.
- StrictUndefined now plays nicely with the `default` filter. Previously we had a separate `StrictDefaultUndefined` class.
- `FileSystemLoader` now takes an optional default file extension to use when looking for files that don't already have an extension. Previously there was a separate `FileExtensionLoader`.
- `AwareBoundTemplate` (a template with a built-in `template` drop) has been removed, but can be added as a feature later if there is a demand.
- The `auto_reload` and `cache_size` arguments to `Environment` have been removed. Now caching is handle by template loaders, not the environment. For example, pass a `CachingFileSystemLoader` as the `loader` argument to `Environment` instead of a `FileSystemLoader`.
- `TemplateNotFound` has been renamed to `TemplateNotFoundError`.
- `Context` has been renamed to `RenderContext` and now takes a mandatory `template` argument instead of `env`. All other arguments to `RenderContext` are now keyword only.

### Template and expression parsing

The lexer has been completely rewritten and the token's it produces bare little resemblance to those produced by any of the several parsing functions from Python Liquid version 1. Now we have a single lexer that scans source text content, tags, statements and expressions in a single pass, and a parser that delegates the parsing of those tokens to classes implementing `Tag`.

As before, `Tag` instances are responsible for returning `Node`s from `Tag.parse()`. And nodes still have the familiar `render_to_output()` abstract method.

For now I recommend familiarizing yourself with the different `Token` classes generated by the lexer, and refer to built-in tag implementations for examples of using various `Expression.parse()` static methods to parse expressions.

As always, open an [issue](https://github.com/jg-rp/python-liquid2/issues) or start a discussion if you need any help with migration.

## Performance

TODO:

- Benchmarks show Python Liquid2 to be more JIT friendly

## Package dependencies

The following packages are dependencies of Python Liquid2.

- Markupsafe>=2
- Babel>=2
- python-dateutil
- pytz
