The tags and filters described here are enabled by default in Python Liquid2, but they are all configurable, so you may wish to replace the defaults.

## Currency

The `currency` filter returns the input number formatted as currency for the current locale. For usage examples see [`currency`](filter_reference.md#currency) in the filter reference.

### Options

`currency` defaults to looking for a locale in a render context variable called `locale`, and a currency code in a render context variable called `currency_code`. It outputs in the locale's standard format and falls back to `en_US` and `USD` if those context variables don't exist.

```python
from liquid2 import parse

template = parse("{{ 100457.99 | currency }}")

print(template.render())
print(template.render(currency_code="GBP"))
print(template.render(locale="de", currency_code="CAD"))
```

```plain title="output"
$100,457.99
£100,457.99
100.457,99 CA$
```

To configure `currency`, register a new instance of [`Currency`](api/builtin.md#liquid2.builtin.Currency) with an [`Environment`](environment.md#managing-tags-and-filters), then render your templates from that. See [the API reference](api/builtin.md#liquid2.builtin.Currency) for details of all arguments accepted by `Currency`.

```python
from liquid2.builtin import Currency
from liquid2 import Environment

env = Environment()
env.filters["currency"] = Currency(default_locale="de")
```

### Money

For convenience, some "money" filters are defined that mimic Shopify's money filter behavior. These are instances of [`Currency()`](api/builtin.md#liquid2.builtin.Currency) with specific default formats. All other currency options are set to their defaults.

```python
from liquid2 import parse

template = parse("""\
{% assign amount = 10 %}
{{ amount | money }}
{{ amount | money_with_currency }}
{{ amount | money_without_currency }}
{{ amount | money_without_trailing_zeros }}""")

print(template.render(currency_code="CAD", locale="en_CA"))
```

```plain title="output"
$10.00
$10.00 CAD
10.00
$10
```

## DateTime

The `datetime` filter returns the input _datetime_ formatted for the current locale. For usage examples see [`datetime`](filter_reference.md#datetime) in the filter reference.

### Options

`datetime` defaults to looking for a timezone in a render context variable called `timezone`, a locale in a render context variable called `locale` and a datetime format in a render context variable called `datetime_format`.

```python
from liquid2 import parse

template = parse("{{ 'Apr 1, 2007, 3:30:00 PM' | datetime }}")

print(template.render())
print(template.render(locale="de", datetime_format="long"))
print(template.render(locale="de", timezone="CET", datetime_format="short"))
```

```plain title="output"
Apr 1, 2007, 3:30:00 PM
1. April 2007 um 15:30:00 UTC
01.04.07, 17:30
```

To configure `datetime`, register a new instance of [`DateTime`](api/builtin.md#liquid2.builtin.DateTime) with an [`Environment`](environment.md#managing-tags-and-filters), then render your templates from that. See [the API reference](api/builtin.md#liquid2.builtin.DateTime) for details of all arguments accepted by `DateTime`.

```python
from liquid2.builtin import DateTime
from liquid2 import Environment

env = Environment()
env.filters["datetime"] = DateTime(timezone_var="tz")
```

## Decimal / number

TODO

## Unit

TODO

## Translations

Liquid Babel includes [`gettext`](filter_reference.md#gettext), [`ngettext`](filter_reference.md#ngettext), [`pgettext`](filter_reference.md#pgettext) and [`npgettext`](filter_reference.md#npgettext) filter equivalents to the functions found in [Python's gettext module](https://docs.python.org/3.10/library/gettext.html#gnu-gettext-api). Application developers can choose to use any of these filters, possibly using more user friendly filter names, and/or the more general [`t (translate)`](filter_reference.md#t) filter.

The [`t`](filter_reference.md#t) filter can behave like any of the \*gettext filters, depending on the arguments it is given. Where the \*gettext filters require positional arguments for `context`, `count` and `plural`, `t` reserves optional `count` and `plural` keyword arguments.

Liquid Babel also offers a [`{% translate %}`](tag_reference.md#translate) tag. This is similar to the [`{% trans %}`](https://jinja.palletsprojects.com/en/3.1.x/templates/#i18n) tag found in Jinja or the [`{% blocktranslate %}`](https://docs.djangoproject.com/en/4.1/topics/i18n/translation/#blocktranslate-template-tag) tag found in Django's template language. Again, application developers can configure and customize the included `translate` tag to suit an application's needs.

### Filters

TODO

#### Options

TODO

### Message catalogs

By default, all translation filters and tags will look for a render context variable called `translations`, which must be an object implementing the `Translations` protocol. It is the application developer's responsibility to provide a `Translations` object, being the interface between Liquid and a message catalog.

The `Translations` protocol is defined as follows. It is simply a subset of the [`NullTranslations`](https://docs.python.org/3.10/library/gettext.html#gettext.NullTranslations) class found in the [gettext module](https://docs.python.org/3.10/library/gettext.html#gnu-gettext-api).

```python
class Translations(Protocol):
    def gettext(self, message: str) -> str:
        ...

    def ngettext(self, singular: str, plural: str, n: int) -> str:
        ...

    def pgettext(self, context: str, message: str) -> str:
        ...

    def npgettext(self, context: str, singular: str, plural: str, n: int) -> str:
        ...
```

It could be a [`GNUTranslations`](https://docs.python.org/3.10/library/gettext.html#the-gnutranslations-class) instance, a [Babel `Translations`](https://babel.pocoo.org/en/latest/support.html#extended-translations-class) instance, or any object implementing `gettext`, `ngettext`, `pgettext` and `npgettext` methods.
