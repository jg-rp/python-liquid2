# Python Liquid2

Liquid is a template language, where source text (the template) contains placeholders for variables, conditional expressions for including or excluding blocks of text, and loops for repeating blocks of text. Plus other syntax for manipulating variables and combining multiple templates into a single output.

Python Liquid2 is a flexible, non-evaluating Liquid template engine. We cater for situations where templates change and grow with an application's user base, and the authors of those templates are potentially untrusted.

## Features

- **Flexible:** Add to, remove or replace built-in [tags](tag_reference.md) and [filters](filter_reference.md) to suite your needs. Also choose from several built-in [template loaders](loading_templates.md) or define your own [custom template loader](loading_templates.md#custom-loaders).

- **Asynchronous:** For situations where you have too many templates to fit in memory or those templates change frequently, they can be loaded asynchronously from file systems, databases or over a network. Similarly, template data can be fetch lazily at render time, also asynchronously.

- **Template inheritance:** Python Liquid2 has built-in [template inheritance](tag_reference.md#extends) features. As well and [including](tag_reference.md#include) or [rendering](tag_reference.md#render) a partial template, you can [extend](tag_reference.md#extends) parent templates by defining template [blocks](tag_reference.md#block).

- **Static analysis:** Python Liquid2 exposes a syntax tree for each template and [built-in tools](static_analysis.md) for analyzing tag, filter and variable usage. You can also extract comment text and have the option of loading and analyzing included/rendered/extended templates too.

- **Internationalization and localization:** Templates have built-in support for translator comments and extracting message catalogs, plus filters for formatting currency, dates, times and numbers for international users.

- **Compatible:** Python Liquid2 mostly is backwards compatible with [Shopify/Liquid](https://github.com/Shopify/liquid), the original authors of the Liquid template language.

## Get started

Have a look at the [quick start](quick_start.md) guide and browse through the built-in [tags](tag_reference.md) and [filters](filter_reference.md).

If you're coming from Python Liquid version 1, check out the [migration guide](migration.md).
