All the filters described here are enabled by default in Python Liquid2.

## abs

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<number> | abs
```

Return the absolute value of a number. Works on integers, floats and string representations of integers or floats.

```liquid2
{{ -42 | abs }}
{{ 7.5 | abs }}
{{ '42.0' | abs }}
```

```plain title="output"
42
7.5
42.0
```

Given a value that can't be cast to an integer or float, `0` will be returned.

```liquid2
{{ 'hello' | abs }}
{{ nosuchthing | abs }}
```

```plain title="output"
0
0
```

## append

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | append: <string>
```

Return the input value concatenated with the argument value.

```liquid2
{{ 'Hello, ' | append: 'World!' }}
```

```plain title="output"
Hello, World!
```

If either the input value or argument are not a string, they will be coerced to a string before concatenation.

```liquid2
{% assign a_number = 7.5 -%}
{{ 42 | append: a_number }}
{{ nosuchthing | append: 'World!' }}
```

```plain title="output"
427.5
World!
```

## at_least

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<number> | at_least: <number>
```

Return the maximum of the filter's input value and its argument. If either input value or argument are string representations of an integer or float, they will be cast to an integer or float prior to comparison.

```liquid2
{{ -5.1 | at_least: 8 }}
{{ 8 | at_least: '5' }}
```

```plain title="output"
8
8
```

If either input value or argument can not be cast to an integer or float, `0` will be used instead.

```liquid2
{{ "hello" | at_least: 2 }}
{{ "hello" | at_least: -2 }}
{{ -1 | at_least: "abc" }}
```

```plain title="output"
2
0
0
```

## at_most

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<number> | at_most: <number>
```

Return the minimum of the filter's input value and its argument. If either input value or argument are string representations of an integer or float, they will be cast to an integer or float prior to comparison.

```liquid2
{{ 5 | at_most: 8 }}
{{ '8' | at_most: 5 }}
```

```plain title="output"
5
5
```

If either input value or argument can not be cast to an integer or float, `0` will be used instead.

```liquid2
{{ "hello" | at_most: 2 }}
{{ "hello" | at_most: -2 }}
{{ -1 | at_most: "abc" }}
```

```plain title="output"
0
-2
-1
```

## capitalize

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | capitalize
```

Return the input string with the first character in upper case and the rest lowercase.

```liquid2
{{ 'heLLO, World!' | capitalize }}
```

```plain title="output"
Hello, world!
```

If the input value is not a string, it will be converted to a string.

```liquid2
{{ 42 | capitalize }}
```

```plain title="output"
42
```

## ceil

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<number> | ceil
```

Round the input value up to the nearest whole number. The input value will be converted to a number if it is not an integer or float.

```liquid2
{{ 5.1 | ceil }}
{{ 5.0 | ceil }}
{{ 5 | ceil }}
{{ '5.4' | ceil }}
```

```plain title="output"
6
5
5
5
```

If the input is undefined or can't be converted to a number, `0` is returned.

```liquid2
{{ 'hello' | ceil }}
{{ nosuchthing | ceil }}
```

```plain title="output"
0
0
```

## compact

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<array> | compact[: <string>]
```

Remove `nil`/`null` (or `None` in Python) values from an array-like object. If given, the argument should be the name of a property that exists on each item (hash, dict etc.) in the array-like sequence.

For example, ff `pages` is an array of objects, some of which have a `category` property:

```json title="data"
{
  "pages": [
    { "category": "business" },
    { "category": "celebrities" },
    {},
    { "category": "lifestyle" },
    { "category": "sports" },
    {},
    { "category": "technology" }
  ]
}
```

Without `compact`, iterating those categories will include `nil`/`null` values.

```liquid2
{% assign categories = pages | map: "category" -%}

{% for category in categories -%}
- {{ category }}
{%- endfor %}
```

```plain title="output"
- business
- celebrities
-
- lifestyle
- sports
-
- technology
```

With `compact`, we can remove those missing categories before the loop.

```liquid2
{% assign categories = pages | map: "category" | compact %}

{% for category in categories %}
- {{ category }}
{% endfor %}
```

```plain title="output"
- business
- celebrities
- lifestyle
- sports
- technology
```

Using the optional argument to `compact`, we could avoid using `map` and create an array of pages with a `category` property, rather than an array of categories.

```liquid2
{% assign pages_with_category = pages | compact: "category" %}

{% for page in pages_with_category %}
- {{ page.category }}
{% endfor %}
```

```plain title="output"
- business
- celebrities
- lifestyle
- sports
- technology
```

## concat

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<array> | concat: <array>
```

Create a new array by joining one array-like object with another.

```liquid2
{% assign fruits = "apples, oranges, peaches" | split: ", " %}
{% assign vegetables = "carrots, turnips, potatoes" | split: ", " %}

{% assign everything = fruits | concat: vegetables %}

{% for item in everything %}
- {{ item }}
{% endfor %}
```

```plain title="output"
- apples
- oranges
- peaches
- carrots
- turnips
- potatoes
```

If the input value is not array-like, it will be converted to an array. No conversion is attempted for the argument value.

```liquid2
{% assign fruits = "apples, oranges, peaches" | split: ", " -%}
{% assign things = "hello" | concat: fruits -%}

{% for item in things -%}
- {{ item }}
{% endfor %}
```

!!! warning

    <!-- md:compat --> Python Liquid2 treats strings as sequences, implicitly converting `"hello"` to `["h", "e", "l", "l", "o"]` in this example. Whereas Shopify/Liquid would convert `"hello"` to `["hello"]`.

```plain title="output"
- h
- e
- l
- l
- o
- apples
- oranges
- peaches
```

If the input is a nested array, it will be flattened before concatenation. The argument is not flattened.

```json title="data"
{
  "a": [
    ["a", "x"],
    ["b", ["y", ["z"]]]
  ],
  "b": ["c", "d"]
}
```

```liquid2
{{ a | concat: b | join: '#' }}
```

```plain title="output"
a#x#b#y#z#c#d
```

## currency

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

```
<number> | currency[: group_separator: <boolean>] -> <string>
```

Currency (aka money) formatting. Return the input number formatted as currency for the current locale.

```liquid2
{{ 100457.99 | currency }}
```

```plain title="output"
$100,457.99
```

Use the `group_separator` argument to control the output of the current locale's group separators.

```liquid2
{{ 100457.99 | currency: group_separator: false }}
```

```plain title="output"
$100457.99
```

If the input number is a string, it will be parsed to a decimal according to the current _input locale_.

```liquid2
{% with input_locale: "de", locale: "en_CA" %}
  {{ "100.457,99" | currency }}
{% endwith %}
```

```plain title="output"
US$100,457.99
```

## date

<!-- md:version 0.1.0 -->
<!-- md:shopify -->
<!-- md:compat -->

```
<datetime> | date: <string>
```

Format a date and/or time according the the given format string. The input can be a string, in which case the string will be parsed as a date/time before formatting.

!!! warning

    Python Liquid uses [dateutil](https://dateutil.readthedocs.io/en/stable/) for parsing strings to
    `datetimes`, and `strftime` for formatting. There are likely to be some inconsistencies between this
    and Ruby Liquid's [Time.parse](https://ruby-doc.org/stdlib-3.0.3/libdoc/time/rdoc/Time.html#method-c-parse)
    equivalent parsing and formatting of dates and times.

    In general, Python Liquid will raise an exception if the input value can not be converted to a date
    and/or time. Whereas Ruby Liquid will usually return something without erroring.

```liquid2
{{ "March 14, 2016" | date: "%b %d, %y" }}
```

```plain title="output"
Mar 14, 16
```

The special `'now'` or `'today'` input values can be used to get the current timestamp. `'today'` is an alias for `'now'`. Both include time information.

```liquid2
{{ "now" | date: "%Y-%m-%d %H:%M" }}
```

```plain title="output"
2021-12-02 10:17
```

If the input is undefined, an empty string is returned.

```liquid2
{{ nosuchthing | date: "%Y-%m-%d %H:%M" }}
```

```plain title="output"

```

## datetime

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

```
<datetime> | datetime[: format: <string>] -> <string>
```

Date and time formatting. Return the input _datetime_ formatted according to the current locale. If `dt` is a `datetime.datetime` object `datetime.datetime(2007, 4, 1, 15, 30)`.

```liquid2
{{ dt | datetime }}
```

```plain title="output"
Apr 1, 2007, 3:30:00 PM
```

The optional `format` argument can be one of `'short'`, `'medium'`, `'long'`, `'full'` or a custom format string. `format` defaults to `'medium'`.

```liquid2
{% with timezone: 'America/New_York' %}
  {{ dt | datetime: format: 'full' }}
{% endwith %}
```

```plain title="output"
Sunday, April 1, 2007 at 11:30:00 AM Eastern Daylight Time
```

If the input _datetime_ is a string, it will be parsed to a datetime object.

```liquid2
{% with locale: 'en_GB' %}
  {{ "Apr 1, 2007, 3:30:00 PM UTC+4" | datetime: format: 'short' }}
{% endwith %}
```

```plain title="output"
01/04/2007, 19:30
```

## decimal

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

```
<number> | decimal[: group_separator: <boolean>] -> <string>
```

Decimal number formatting. Return the input number formatted as a decimal for the current locale.

```liquid2
{{ '10000.233' | decimal }}
```

```plain title="output"
10,000.233
```

Use the `group_separator` argument to control the output of the current locale's group separators.

```liquid2
{{ '10000.233' | decimal: group_separator: false }}
```

```plain title="output"
10000.233
```

If the input number is a string, it will be parsed to a decimal according to the current _input locale_.

```liquid2
{% with input_locale: "de" %}
  {{ "100.457,00" | decimal }}
{% endwith %}
```

```plain title="output"
100,457
```

## default

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<expression> | default[: <object>[, allow_false:<bool>]]
```

Return a default value if the input is undefined, `nil`/`null`, `false` or empty, or return the input unchanged otherwise.

```liquid2
{{ product_price | default: 2.99 }}

{%- assign product_price = "" %}
{{ product_price | default: 2.99 }}

{%- assign product_price = 4.99 %}
{{ product_price | default: 2.99 }}
```

```plain title="output"
2.99
2.99
4.99
```

If the optional `allow_false` argument is `true`, an input of `false` will not return the default. `allow_false` defaults to `false`.

```liquid2
{% assign product_reduced = false -%}
{{ product_reduced | default: true, allow_false: true }}
```

```plain title="output"
false
```

If no argument is given, the default value will be an empty string.

```liquid2
{{ product_price | default }}
```

```plain title="output"

```

Empty strings, arrays and objects all cause the default value to be returned. `0` does not.

```liquid2
{{ "" | default: "hello" }}
{{ 0 | default: 99 }}
```

```plain title="output"
hello
0
```

## divided_by

## downcase

## escape

## escape_once

## first

## floor

## gettext

## join

## json

## last

## lstrip

## map

## minus

## modulo

## money

## money_with_currency

## money_without_currency

## money_without_trailing_zeros

## newline_to_br

## ngettext

## npgettext

## pgettext

## plus

## prepend

## remove

## remove_first

## remove_last

## replace

## replace_first

## replace_last

## reverse

## round

## rstrip

## safe

## size

## slice

## sort

## sort_natural

## sort_numeric

## split

## strip

## strip_html

## strip_newlines

## sum

## t

## times

## truncate

## truncatewords

## uniq

## unit

## upcase

## url_decode

## url_encode

## where
