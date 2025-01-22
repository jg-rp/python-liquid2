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

Currency (aka money) formatting. Return the input number formatted as currency for the current locale. See also [`money`](#money).

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

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<number> | divided_by: <number>
```

Divide a number by another number. The result is rounded down to the nearest integer if the divisor is an integer.

```liquid2
{{ 16 | divided_by: 4 }}
{{ 5 | divided_by: 3 }}
```

```plain title="output"
4
1
```

If you divide by a float, the result will be a float.

```liquid2
{{ 20 | divided_by: 7 }}
{{ 20 | divided_by: 7.0 }}
```

```plain title="output"
2
2.857142857142857
```

If either the input or argument are not an integer or float, Liquid will try to convert them to an integer or float. If the input can't be converted, `0` will be used instead. If the argument can't be converted, an exception is raised.

```liquid2
{{ "20" | divided_by: "7" }}
{{ "hello" | divided_by: 2 }}
```

```plain title="output"
2
0
```

## downcase

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | downcase
```

Return the input string with all characters in lowercase.

```liquid2
{{ 'Hello, World!' | downcase }}
```

```plain title="output"
hello, world!
```

If the input is not a string, Liquid will convert it to a string before forcing characters to lowercase.

```liquid2
{{ 5 | downcase }}
```

```plain title="output"
5
```

If the input is undefined, an empty string is returned.

## escape

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | escape
```

Return the input string with characters `&`, `<` and `>` converted to HTML-safe sequences.

```liquid2
{{ "Have you read 'James & the Giant Peach'?" | escape }}
```

```plain title="output"
Have you read &#39;James &amp; the Giant Peach&#39;?
```

## escape_once

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | escape_once
```

Return the input string with characters `&`, `<` and `>` converted to HTML-safe sequences while preserving existing HTML escape sequences.

```liquid2
{{ "Have you read 'James &amp; the Giant Peach'?" | escape_once }}
```

```plain title="output"
Have you read &#39;James &amp; the Giant Peach&#39;?
```

## find

<!-- md:version 0.3.0 -->
<!-- md:shopify -->

```
<array> | find: <string>[, <object>]
```

Return the first item in the input array that contains a property, given as the first argument, equal to the value given as the second argument. If no such item exists, `null` is returned.

In this example we select the first page in the "Programming" category.

```json title="data"
{
  "pages": [
    {
      "id": 1,
      "title": "Introduction to Cooking",
      "category": "Cooking",
      "tags": ["recipes", "beginner", "cooking techniques"]
    },
    {
      "id": 2,
      "title": "Top 10 Travel Destinations in Europe",
      "category": "Travel",
      "tags": ["Europe", "destinations", "travel tips"]
    },
    {
      "id": 3,
      "title": "Mastering JavaScript",
      "category": "Programming",
      "tags": ["JavaScript", "web development", "coding"]
    }
  ]
}
```

```liquid2
{% assign page = pages | find: 'category', 'Programming' %}
{{ page.title }}
```

```plain title="output"
Mastering JavaScript
```

### Lambda expressions

<!-- md:version 0.3.0 -->
<!-- md:liquid2 -->

```
<array> | find: <lambda expression>
```

We can pass a lambda expression as an argument to `find` to select the first item matching an arbitrary Boolean expression (one that evaluates to true or false). Using the same data as above, this example finds the first page with a "web development" tag.

```liquid2
{% assign page = pages | find: item => 'web development' in item.tags %}
{{ page.title }}
```

```plain title="output"
Mastering JavaScript
```

## find_index

Return the index of the first item in the input array that contains a property, given as the first argument, equal to the value given as the second argument. If no such item exists, `null` is returned.

In this example we find the index for the first page in the "Programming" category.

```json title="data"
{
  "pages": [
    {
      "id": 1,
      "title": "Introduction to Cooking",
      "category": "Cooking",
      "tags": ["recipes", "beginner", "cooking techniques"]
    },
    {
      "id": 2,
      "title": "Top 10 Travel Destinations in Europe",
      "category": "Travel",
      "tags": ["Europe", "destinations", "travel tips"]
    },
    {
      "id": 3,
      "title": "Mastering JavaScript",
      "category": "Programming",
      "tags": ["JavaScript", "web development", "coding"]
    }
  ]
}
```

```liquid2
{% assign index = pages | find_index: 'category', 'Programming' %}
{{ pages[index].title }}
```

```plain title="output"
Mastering JavaScript
```

### Lambda expressions

<!-- md:version 0.3.0 -->
<!-- md:liquid2 -->

```
<array> | find_index: <lambda expression>
```

We can pass a lambda expression as an argument to `find_index` to get the index for the first item matching an arbitrary Boolean expression (one that evaluates to true or false). Using the same data as above, this example finds the first page with a "web development" tag.

```liquid2
{% assign index = pages | find_index: item => 'web development' in item.tags %}
{{ page[index].title }}
```

```plain title="output"
Mastering JavaScript
```

## first

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<sequence> | first
```

Return the first item of the input sequence. The input could be array-like or a mapping, but not a string.

```liquid2
{{ "Ground control to Major Tom." | split: " " | first }}
```

```plain title="output"
Ground
```

If the input sequence is undefined, empty or not a sequence, `nil` is returned.

## floor

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<number> | floor
```

Return the input down to the nearest whole number. Liquid tries to convert the input to a number before the filter is applied.

```liquid2
{{ 1.2 | floor }}
{{ 2.0 | floor }}
{{ 183.357 | floor }}
{{ -5.4 | floor }}
{{ "3.5" | floor }}
```

```plain title="output"
1
2
183
-6
3
```

If the input can't be converted to a number, `0` is returned.

## has

<!-- md:version 0.3.0 -->
<!-- md:shopify -->

```
<array> | has: <string>[, <object>]
```

Return `true` if the input array contains an object with a property identified by the first argument that is equal to the object given as the second argument. `false` is returned if none of the items in the input array contain such a property/value.

In this example we test to see if any pages are in the "Programming" category.

```json title="data"
{
  "pages": [
    {
      "id": 1,
      "title": "Introduction to Cooking",
      "category": "Cooking",
      "tags": ["recipes", "beginner", "cooking techniques"]
    },
    {
      "id": 2,
      "title": "Top 10 Travel Destinations in Europe",
      "category": "Travel",
      "tags": ["Europe", "destinations", "travel tips"]
    },
    {
      "id": 3,
      "title": "Mastering JavaScript",
      "category": "Programming",
      "tags": ["JavaScript", "web development", "coding"]
    }
  ]
}
```

```liquid2
{% assign has_programming_page = pages | has: 'category', 'Programming' %}
{{ has_programming_page }}
```

```plain title="output"
true
```

### Lambda expressions

<!-- md:version 0.3.0 -->
<!-- md:liquid2 -->

```
<array> | has: <lambda expression>
```

Use the same data as above, we can pass a lambda expression to `has` to test against an arbitrary Boolean expression (one that evaluates to true or false).

This example test for a page with a category equal to "programming" or "Programming".

```liquid2
{% assign has_programming_page = pages | has: p => p.category == 'programming' or p.category == 'Programming' %}
{{ has_programming_page }}
```

```plain title="output"
true
```

## gettext

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

```
<string> | gettext[: <identifier>: <object> ... ]
```

Return the localized translation of the input message without pluralization or message context.

```liquid2
{{ "Hello, World!" | gettext }}
```

```plain title="output"
Hallo Welt!
```

Any keyword arguments are used to populate message variables. If `user.name` is `"Sue"`:

```liquid2
{{ "Hello, %(you)s" | gettext: you: user.name }}
```

```plain title="output"
Hallo Sue!
```

## join

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<array> | join[: <string>]
```

Return the items in the input array as a single string, separated by the argument string. If the
input is not an array, Liquid will convert it to one. If input array items are not strings, they
will be converted to strings before joining.

```liquid2
{% assign beatles = "John, Paul, George, Ringo" | split: ", " -%}

{{ beatles | join: " and " }}
```

```plain title="output"
John and Paul and George and Ringo
```

If an argument string is not given, it defaults to a single space.

```liquid2
{% assign beatles = "John, Paul, George, Ringo" | split: ", " -%}

{{ beatles | join }}
```

```plain title="output"
John Paul George Ringo
```

## json

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

```
<object> | json
```

Return the input object serialized to a JSON (JavaScript Object Notation) string.

```json title="data"
{
  "product": {
    "id": 1234,
    "name": "Football"
  }
}
```

```liquid2
{{ product | json }}
```

```plain title="output"
{ "id": 1234, "name": "Football" }
```

## last

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<array> | last
```

Return the last item in the array-like input.

```liquid2
{{ "Ground control to Major Tom." | split: " " | last }}
```

```plain title="output"
Tom.
```

If the input is undefined, empty, string or a number, `nil` will be returned.

## lstrip

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | lstrip
```

Return the input string with all leading whitespace removed. If the input is not a string, it will
be converted to a string before stripping whitespace.

```liquid2
{{ "          So much room for activities          " | lstrip }}!
```

```plain title="output"
So much room for activities          !
```

## map

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

```
<array> | map: <string | lambda expression>
```

Extract properties from an array of objects into a new array.

For example, if `pages` is an array of objects with a `category` property:

```json title="data"
{
  "pages": [
    { "category": "business" },
    { "category": "celebrities" },
    { "category": "lifestyle" },
    { "category": "sports" },
    { "category": "technology" }
  ]
}
```

```liquid2
{% assign categories = pages | map: "category" -%}

{% for category in categories -%}
- {{ category }}
{%- endfor %}
```

```plain title="output"
- business
- celebrities
- lifestyle
- sports
- technology
```

### Lambda expressions

<!-- md:version 0.3.0 -->
<!-- md:liquid2 -->

You can use a lambda expression to select arbitrary nested properties and array items from a sequence of objects.

For example, if `pages` is an array of objects with a `tags` property, which is an array of strings:

```json title="data"
{
  "pages": [
    {
      "id": 1,
      "title": "Introduction to Cooking",
      "category": "Cooking",
      "tags": ["recipes", "beginner", "cooking techniques"]
    },
    {
      "id": 2,
      "title": "Top 10 Travel Destinations in Europe",
      "category": "Travel",
      "tags": ["Europe", "destinations", "travel tips"]
    },
    {
      "id": 3,
      "title": "Mastering JavaScript",
      "category": "Programming",
      "tags": ["JavaScript", "web development", "coding"]
    }
  ]
}
```

```liquid2
{% assign first_tags = pages | map: page => page.tags[0] -%}
{{ first_tags | json }}
```

```plain title="output"
["recipes", "Europe", "JavaScript"]
```

## minus

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<number> | minus: <number>
```

Return the result of subtracting one number from another. If either the input or argument are not a number, Liquid will try to convert them to a number. If that conversion fails, `0` is used instead.

```liquid2
{{ 4 | minus: 2 }}
{{ "16" | minus: 4 }}
{{ 183.357 | minus: 12.2 }}
{{ "hello" | minus: 10 }}
```

```plain title="output"
2
12
171.157
-10
```

## modulo

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<number> | modulo: <number>
```

Return the remainder from the division of the input by the argument.

```liquid2
{{ 3 | modulo: 2 }}
{{ "24" | modulo: "7" }}
{{ 183.357 | modulo: 12 }}
```

```plain title="output"
1
3
3.357
```

If either the input or argument are not an integer or float, Liquid will try to convert them to an
integer or float. If the input can't be converted, `0` will be used instead. If the argument can't
be converted, an exception is raised.

## money

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

`money` is an alias for [`currency`](#currency).

## money_with_currency

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

`money_with_currency` is an alias for [`currency`](#currency) with the default format set to `"¤#,##0.00 ¤¤"`.

## money_without_currency

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

`money_without_currency` is an alias for [`currency`](#currency) with the default format set to `"#,##0.00¤"`.

## money_without_trailing_zeros

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

`money_without_trailing_zeros` is an alias for [`currency`](#currency) with the default format set to `"¤#,###"` and `currency_digits` set to `False`.

## newline_to_br

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | newline_to_br
```

Return the input string with `\n` and `\r\n` replaced with `<br />\n`.

```liquid2
{% capture string_with_newlines %}
Hello
there
{% endcapture %}

{{ string_with_newlines | newline_to_br }}
```

```plain title="output"


<br />
Hello<br />
there<br />

```

## ngettext

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

```
<string> | ngettext: <string>, <number> [, <identifier>: <object> ... ]
```

Return the localized translation of the input message with pluralization. The first positional argument is the plural form of the message. The second is a number used to determine if the singular or plural message should be used.

```liquid2
{% assign count = "Earth,Tatooine" | split: "," | size %}
{{ "Hello, World!" | ngetetxt: "Hello, Worlds!", count }}
```

```plain title="output"
Hallo Welten!
```

Any keyword arguments are used to populate message variables. If `user.name` is `"Sue"` and `count` is `1`:

```liquid2
{{ "Hello, %(you)s" | ngetetxt: "Hello, everyone!", count, you: user.name }}
```

```plain title="output"
Hallo Sue!
```

## npgettext

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

````
<string> | npgettext: <string>, <string>, <number> [, <identifier>: <object> ... ]
``

Return the localized translation of the input message with pluralization and a message context. The first positional argument is the message context string, the second is the plural form of the message, and the third is a number used to determine if the singular or plural message should be used.

```liquid2
{% assign count = "Earth,Tatooine" | split: "," | size %}
{{ "Hello, World!" | ngetetxt: "extra special greeting", "Hello, Worlds!", count }}
````

```plain title="output"
Hallo Welten!
```

Any keyword arguments are used to populate message variables. If `user.name` is `"Sue"` and `count` is `1`:

```liquid2
{{ "Hello, %(you)s" | ngetetxt: "extra special greeting", "Hello, everyone!", count, you: user.name }}
```

```plain title="output"
Hallo Sue!
```

## pgettext

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

```
<string> | pgettext: <string> [, <identifier>: <object> ... ]
```

Return the localized translation of the input message with additional message context. Message context is used to give translators extra information about where the messages is to be used.

```liquid2
{{ "Hello, World!" | pgettext: "extra special greeting" }}
```

```plain title="output"
Hallo Welt!
```

Any keyword arguments are used to populate message variables. If `user.name` is `"Sue"`:

```liquid2
{{ "Hello, %(you)s" | pgettext: "extra special greeting", you: user.name }}
```

```plain title="output"
Hallo Sue!
```

## plus

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<number> | plus: <number>
```

Return the result of adding one number to another. If either the input or argument are not a number, Liquid will try to convert them to a number. If that conversion fails, `0` is used instead.

```liquid2
{{ 4 | plus: 2 }}
{{ "16" | plus: "4" }}
{{ 183.357 | plus: 12 }}
```

```plain title="output"
6
20
195.357
```

## prepend

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | prepend: <string>
```

Return the argument concatenated with the filter input.

```liquid2
{{ "apples, oranges, and bananas" | prepend: "Some fruit: " }}
```

```plain title="output"
Some fruit: apples, oranges, and bananas
```

If either the input value or argument are not a string, they will be coerced to a string before
concatenation.

```liquid2
{% assign a_number = 7.5 -%}
{{ 42 | prepend: a_number }}
{{ nosuchthing | prepend: 'World!' }}
```

```plain title="output"
7.542
World!
```

## reject

<!-- md:version 0.3.0 -->
<!-- md:liquid2 -->

```
<array> | reject: <string>[, <object>]
```

Return a copy of the input array including only those objects that have a property, named with the first argument, **that is not equal to** a value, given as the second argument. If a second argument is not given, only elements with the named property that are falsy will be included.

```json title="data"
{
  "products": [
    { "title": "Vacuum", "type": "house", "available": true },
    { "title": "Spatula", "type": "kitchen", "available": false },
    { "title": "Television", "type": "lounge", "available": true },
    { "title": "Garlic press", "type": "kitchen", "available": true }
  ]
}
```

```liquid2
All products:
{% for product in products -%}
- {{ product.title }}
{% endfor %}

{%- assign kitchen_products = products | reject: "type", "kitchen" -%}

Non kitchen products:
{% for product in kitchen_products -%}
- {{ product.title }}
{% endfor %}

{%- assign unavailable_products = products | reject: "available" -%}

Unavailable products:
{% for product in unavailable_products -%}
- {{ product.title }}
{% endfor %}
```

```plain title="output"
All products:
- Vacuum
- Spatula
- Television
- Garlic press
Non kitchen products:
- Vacuum
- Television
Unavailable products:
- Spatula
```

## remove

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | remove: <string>
```

Return the input with all occurrences of the argument string removed.

```liquid2
{{ "I strained to see the train through the rain" | remove: "rain" }}
```

```plain title="output"
I sted to see the t through the
```

If either the filter input or argument are not a string, they will be coerced to a string before
substring removal.

## remove_first

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | remove_first: <string>
```

Return a copy of the input string with the first occurrence of the argument string removed.

```liquid2
{{ "I strained to see the train through the rain" | remove_first: "rain" }}
```

```plain title="output"
I sted to see the train through the rain
```

If either the filter input or argument are not a string, they will be coerced to a string before substring removal.

## remove_last

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | remove_last: <string>
```

Return a copy of the input string with the last occurrence of the argument string removed.

```liquid2
{{ "I strained to see the train through the rain" | remove_last: "rain" }}
```

```plain title="output"
I strained to see the train through the
```

If either the filter input or argument are not a string, they will be coerced to a string before substring removal.

## replace

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | replace: <string>[, <string>]
```

Return the input with all occurrences of the first argument replaced with the second argument. If
the second argument is omitted, it will default to an empty string, making `replace` behave like
`remove`.

```liquid2
{{ "Take my protein pills and put my helmet on" | replace: "my", "your" }}
```

```plain title="output"
Take your protein pills and put your helmet on
```

If either the filter input or argument are not a string, they will be coerced to a string before
replacement.

## replace_first

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | replace_first: <string>[, <string>]
```

Return a copy of the input string with the first occurrence of the first argument replaced with the second argument. If the second argument is omitted, it will default to an empty string, making `replace_first` behave like `remove_first`.

```liquid2
{{ "Take my protein pills and put my helmet on" | replace_first: "my", "your" }}
```

```plain title="output"
Take your protein pills and put my helmet on
```

If either the filter input or argument are not a string, they will be coerced to a string before replacement.

## replace_last

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | replace_last: <string>, <string>
```

Return a copy of the input string with the last occurrence of the first argument replaced with the second argument.

```liquid2
{{ "Take my protein pills and put my helmet on" | replace_first: "my", "your" }}
```

```plain title="output"
Take my protein pills and put your helmet on
```

If either the filter input or argument are not a string, they will be coerced to a string before replacement.

## reverse

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<array> | reverse
```

Return a copy of the input array with the items in reverse order. If the filter input is a string, `reverse` will return the string unchanged.

```liquid2
{% assign my_array = "apples, oranges, peaches, plums" | split: ", " -%}

{{ my_array | reverse | join: ", " }}
```

```plain title="output"
plums, peaches, oranges, apples
```

## round

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<number> | round[: <number>]
```

Return the input number rounded to the given number of decimal places. The number of digits defaults to `0`.

```liquid2
{{ 1.2 | round }}
{{ 2.7 | round }}
{{ 183.357 | round: 2 }}
```

```plain title="output"
1
3
183.36
```

If either the filter input or its optional argument are not an integer or float, they will be converted to an integer or float before rounding.

## rstrip

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | rstrip
```

Return the input string with all trailing whitespace removed. If the input is not a string, it will be converted to a string before stripping whitespace.

```liquid2
{{ "          So much room for activities          " | rstrip }}!
```

```plain title="output"
          So much room for activities!
```

## safe

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

```
<string> | safe
```

Return the input string marked as safe to use in an HTML or XML document. If the filter input is not a string, it will be converted to an HTML-safe string.

With auto-escape enabled and the following global variables:

```json title="data"
{
  "username": "Sally",
  "greeting": "</p><script>alert('XSS!');</script>"
}
```

```liquid2 title="template"
<p>{{ greeting }}, {{ username }}</p>
<p>{{ greeting | safe }}, {{ username }}</p>
```

```html title="output"
<p>&lt;/p&gt;&lt;script&gt;alert(&#34;XSS!&#34;);&lt;/script&gt;, Sally</p>
<p></p><script>alert('XSS!');</script>, Sally</p>
```

## size

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<object> | size
```

Return the size of the input object. Works on strings, arrays and hashes.

```liquid2
{{ "Ground control to Major Tom." | size }}
{{ "apples, oranges, peaches, plums" | split: ", " | size }}
```

```plain title="output"
28
4
```

## slice

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<sequence> | slice: <int>[, <int>]
```

Return a substring or subsequence of the input string or array. The first argument is the zero-based start index. The second, optional argument is the length of the substring or sequence, which defaults to `1`.

```liquid2
{{ "Liquid" | slice: 0 }}
{{ "Liquid" | slice: 2 }}
{{ "Liquid" | slice: 2, 5 }}
{% assign beatles = "John, Paul, George, Ringo" | split: ", " -%}
{{ beatles | slice: 1, 2 | join: " " }}
```

```plain title="output"
L
q
quid
Paul George
```

If the first argument is negative, the start index is counted from the end of the sequence.

```liquid2
{{ "Liquid" | slice: -3 }}
{{ "Liquid" | slice: -3, 2 }}
{% assign beatles = "John, Paul, George, Ringo" | split: ", " -%}
{{ beatles | slice: -2, 2 | join: " " }}
```

```plain title="output"
u
ui
George Ringo
```

## sort

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

````
<array> | sort[: <string>]
``

Return a copy of the input array with its elements sorted.

```liquid
{% assign my_array = "zebra, octopus, giraffe, Sally Snake" | split: ", " -%}
{{ my_array | sort | join: ", " }}
````

```plain title="output"
Sally Snake, giraffe, octopus, zebra
```

The optional argument is a sort key. If given, it should be the name of a property and the filter's input should be an array of objects.

```json title="data"
{
  "collection": {
    "products": [
      { "title": "A Shoe", "price": "9.95" },
      { "title": "A Tie", "price": "0.50" },
      { "title": "A Hat", "price": "2.50" }
    ]
  }
}
```

```liquid2 title="template"
{% assign products_by_price = collection.products | sort: "price" -%}
{% for product in products_by_price %}
  <h4>{{ product.title }}</h4>
{% endfor %}
```

```plain title="output"
<h4>A Tie</h4>
<h4>A Hat</h4>
<h4>A Shoe</h4>
```

## sort_natural

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<array> | sort_natural[: <string>]
```

Return a copy of the input array with its elements sorted case-insensitively. Array items will be compared by their string representations, forced to lowercase.

```liquid2
{% assign my_array = "zebra, octopus, giraffe, Sally Snake" | split: ", " -%}
{{ my_array | sort_natural | join: ", " }}
```

```plain title="output"
giraffe, octopus, Sally Snake, zebra
```

The optional argument is a sort key. If given, it should be the name of a property and the filter's input should be an array of objects. Array elements are compared using the lowercase string representation of that property.

```json title="data"
{
  "collection": {
    "products": [
      { "title": "A Shoe", "company": "Cool Shoes" },
      { "title": "A Tie", "company": "alpha Ties" },
      { "title": "A Hat", "company": "Beta Hats" }
    ]
  }
}
```

```liquid2 title="template"
{% assign products_by_company = collection.products | sort_natural: "company" %}
{% for product in products_by_company %}
  <h4>{{ product.title }}</h4>
{% endfor %}
```

```plain title="output"
<h4>A Tie</h4>
<h4>A Hat</h4>
<h4>A Shoe</h4>
```

## sort_numeric

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

```
<sequence> | sort_numeric[: <string>]
```

Return a new array/list with items from the input sequence sorted by any integers and/or floats found in the string representation of each item. Note the difference between `sort_numeric` and `sort` in this example.

```liquid2
{% assign foo = '1.2.1, v1.10.0, v1.1.0, v1.2.2' | split: ', ' -%}
{{ foo | sort_numeric | join: ', ' }}
{{ foo | sort | join: ', ' }}

{% assign bar = '107, 12, 0001' | split: ', ' -%}
{{ bar | sort_numeric | join: ', ' }}
{{ bar | sort | join: ', ' }}
```

```plain title="output"
v1.1.0, 1.2.1, v1.2.2, v1.10.0
1.2.1, v1.1.0, v1.10.0, v1.2.2

0001, 12, 107
0001, 107, 12
```

The optional string argument is the name of a key/property to use as the sort key. In which case each item in the input sequence should be a dict/hash/mapping, each with said key/property.

`sort_numeric` will work as expected when given arrays/lists/tuples of integers, floats and/or Decimals, but will be slower than using standard `sort`.

If an input sequence contains strings (or arbitrary objects that get stringified) that do not have numeric characters, they will be pushed to the end of the resulting list, probably in the same order as in the input sequence.

## split

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | split: <string>
```

Return an array of strings that are the input string split on the filter's argument string.

```liquid2
{% assign beatles = "John, Paul, George, Ringo" | split: ", " -%}

{% for member in beatles %}
  {{- member }}
{% endfor %}
```

```plain title="output"
John
Paul
George
Ringo
```

If the argument is undefined or an empty string, the input will be split at every character.

```liquid2
{{ "Hello there" | split: nosuchthing | join: "#" }}
```

```plain title="output"
H#e#l#l#o# #t#h#e#r#e
```

## strip

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | strip
```

Return the input string with all leading and trailing whitespace removed. If the input is not a string, it will be converted to a string before stripping whitespace.

```liquid2
{{ "          So much room for activities          " | strip }}!
```

```plain title="output"
So much room for activities!
```

## strip_html

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | strip_html
```

Return the input string with all HTML tags removed.

```liquid2
{{ "Have <em>you</em> read <strong>Ulysses</strong>?" | strip_html }}
```

```plain title="output"
Have you read Ulysses?
```

## strip_newlines

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | strip_newlines
```

Return the input string with `\n` and `\r\n` removed.

```liquid2
{% capture string_with_newlines %}
Hello
there
{% endcapture -%}

{{ string_with_newlines | strip_newlines }}
```

```plain title="output"
Hellothere
```

## sum

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<array> | sum[: <string>]
```

Return the sum of all numeric elements in an array.

```liquid2
{% assign array = '1,2,3' | split: ',' -%}
{{ array | sum }}
```

```plain title="output"
6
```

If the optional string argument is given, it is assumed that array items are hash/dict/mapping-like, and the argument should be the name of a property/key. The values at `array[property]` will be summed.

## t

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

```
<string> | t[: <string>[, <identifier>: <object> ... ]] -> <string>
```

Return the localized translation of the input message. For example, if a German [Translations](babel.md#message-catalogs) object is found in the current render context:

```liquid2
{{ "Hello, World!" | t }}
```

```plain title="output"
Hallo Welt!
```

If given, the first and only positional argument is a message context string. It will be used to give translators extra information about where the message is to be used. With the default configuration, keyword arguments `plural` and `count` are reserved for specifying a pluralizable message.

```liquid2
{{ "Hello, World!" | t: plural: 'Hello, Worlds!', count: 2 }}
```

```plain title="output"
Hallo Welten!
```

The remaining keyword arguments are used to populate translatable message variables. If `user.name` is `"Sue"`:

```liquid2
{{ "Hello, %(you)s" | t: you: user.name }}
```

```plain title="output"
Hallo Sue!
```

## times

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<number> | times: <number>
```

Return the product of the input number and the argument. If either the input or argument are not a number, Liquid will try to convert them to a number. If that conversion fails, `0` is used instead.

```liquid2
{{ 3 | times: 2 }}
{{ "24" | times: "7" }}
{{ 183.357 | times: 12 }}
```

```plain title="output"
6
168
2200.284
```

## truncate

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | truncate[: <integer>[, <string>]]
```

Return a truncated version of the input string. The first argument, length, defaults to `50`. The second argument defaults to an ellipsis (`...`).

If the length of the input string is less than the given length (first argument), the input string will be truncated to `length` minus the length of the second argument, with the second argument appended.

```liquid2
{{ "Ground control to Major Tom." | truncate: 20 }}
{{ "Ground control to Major Tom." | truncate: 25, ", and so on" }}
{{ "Ground control to Major Tom." | truncate: 20, "" }}
```

```plain title="output"
Ground control to...
Ground control, and so on
Ground control to Ma
```

## truncatewords

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | truncatewords[: <integer>[, <string>]]
```

Return the input string truncated to the specified number of words, with the second argument appended. The number of words (first argument) defaults to `15`. The second argument defaults to an ellipsis (`...`).

If the input string already has fewer than the given number of words, it is returned unchanged.

```liquid2
{{ "Ground control to Major Tom." | truncatewords: 3 }}
{{ "Ground control to Major Tom." | truncatewords: 3, "--" }}
{{ "Ground control to Major Tom." | truncatewords: 3, "" }}
```

```plain title="output"
Ground control to...
Ground control to--
Ground control to
```

## uniq

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<array> | uniq[: <string>]
```

Return a copy of the input array with duplicate elements removed.

```liquid2
{% assign my_array = "ants, bugs, bees, bugs, ants" | split: ", " -%}
{{ my_array | uniq | join: ", " }}
```

```plain title="output"
ants, bugs, bees
```

If an argument is given, it should be the name of a property and the filter's input should be an array of objects.

```json title="data"
{
  "collection": {
    "products": [
      { "title": "A Shoe", "company": "Cool Shoes" },
      { "title": "A Tie", "company": "alpha Ties" },
      { "title": "Another Tie", "company": "alpha Ties" },
      { "title": "A Hat", "company": "Beta Hats" }
    ]
  }
}
```

```liquid2 title="template"
{% assign one_product_from_each_company = collections.products | uniq: "company" -%}
{% for product in one_product_from_each_company -%}
  - product.title
{% endfor %}
```

```plain title="output"
- A Shoe
- A Tie
- A Hat
```

## unit

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

```
<number> | unit: <string>
  [, denominator: <number>]
  [, denominator_unit: <string>]
  [, length: <string>]
  [, format: <string>]
```

Return the input number formatted with the given units according to the current locale. The first, required positional argument is a [CLDR](https://cldr.unicode.org/) measurement unit [code](https://github.com/unicode-org/cldr/blob/latest/common/validity/unit.xml).

```liquid2
{{ 12 | unit: 'length-meter' }}
```

```plain title="output"
12 meters
```

### length

`length` can be one of "short", "long" or "narrow", defaulting to "long".

```liquid
{{ 12 | unit: 'length-meter' }}
{{ 12 | unit: 'length-meter', length: 'short' }}
{{ 12 | unit: 'length-meter', length: 'long' }}
{{ 12 | unit: 'length-meter', length: 'narrow' }}
```

```plain title="output"
12 meters
12 m
12 meters
12m
```

Or, if the current locale is set to `fr`.

```liquid2
{% with locale:"fr" %}
  {{ 12 | unit: 'length-meter' }}
  {{ 12 | unit: 'length-meter', length: 'short' }}
  {{ 12 | unit: 'length-meter', length: 'long' }}
  {{ 12 | unit: 'length-meter', length: 'narrow' }}
{% endwith %}
```

```plain title="output"
12 mètres
12 m
12 mètres
12m
```

### format

`format` is an optional decimal format string, described in the [Locale Data Markup Language specification (LDML)](https://unicode.org/reports/tr35/).

```liquid2
{{ 12 | unit: 'length-meter', format: '#,##0.00' }}
```

```plain title="output"
12.00 meters
```

### Compound Units

If a `denominator` and/or `denominator_unit` is given, the value will be formatted as a compound unit.

```liquid2
{{ 150 | unit: 'kilowatt', denominator_unit: 'hour' }}
{{ 32.5 | unit: 'ton', denominator: 15, denominator_unit: 'hour' }}
```

```plain title="output"
150 kilowatts per hour
32.5 tons per 15 hours
```

Or, if the current locale is set to `fi`.

```liquid2
{% with locale:"fi" %}
  {{ 150 | unit: 'kilowatt', denominator_unit: 'hour' }}
  {{ 32.5 | unit: 'ton', denominator: 15, denominator_unit: 'hour' }}
{% endwith %}
```

```plain title="output"
150 kilowattia / tunti
32,5 am. tonnia/15 tuntia
```

## upcase

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | upcase
```

Return the input string with all characters in uppercase.

```liquid2
{{ 'Hello, World!' | upcase }}
```

```plain title="output"
HELLO, WORLD!
```

## url_decode

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | url_decode
```

Return the input string with `%xx` escapes replaced with their single-character equivalents. Also replaces `'+'` with `' '`.

```liquid2
{{ "My+email+address+is+bob%40example.com%21" | url_decode }}
```

```plain title="output"
My email address is bob@example.com!
```

## url_encode

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<string> | url_encode
```

Return the input string with URL reserved characters %-escaped. Also replaces `' '` with `'+'`.

```liquid2
{{ My email address is bob@example.com! | url_encode }}
```

```plain title="output"
My+email+address+is+bob%40example.com%21
```

## where

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
<array> | where: <string>[, <object>]
```

Return a copy of the input array including only those objects that have a property, named with the first argument, equal to a value, given as the second argument. If a second argument is not given, only elements with the named property that are truthy will be included.

```json title="data"
{
  "products": [
    { "title": "Vacuum", "type": "house", "available": true },
    { "title": "Spatula", "type": "kitchen", "available": false },
    { "title": "Television", "type": "lounge", "available": true },
    { "title": "Garlic press", "type": "kitchen", "available": true }
  ]
}
```

```liquid2
All products:
{% for product in products -%}
- {{ product.title }}
{% endfor %}

{%- assign kitchen_products = products | where: "type", "kitchen" -%}

Kitchen products:
{% for product in kitchen_products -%}
- {{ product.title }}
{% endfor %}

{%- assign available_products = products | where: "available" -%}

Available products:
{% for product in available_products -%}
- {{ product.title }}
{% endfor %}
```

```plain title="output"
All products:
- Vacuum
- Spatula
- Television
- Garlic press

Kitchen products:
- Spatula
- Garlic press

Available product:
- Vacuum
- Television
- Garlic press
```

### Lambda expressions

<!-- md:version 0.3.0 -->
<!-- md:liquid2 -->

```
<array> | where: <lambda expression>
```

Use a lambda expression to select array items according to an arbitrary Boolean expression (one that evaluates to true or false).

In this example we select pages that have a "coding" tag.

```json title="data"
{
  "pages": [
    {
      "id": 1,
      "title": "Introduction to Cooking",
      "category": "Cooking",
      "tags": ["recipes", "beginner", "cooking techniques"]
    },
    {
      "id": 2,
      "title": "Top 10 Travel Destinations in Europe",
      "category": "Travel",
      "tags": ["Europe", "destinations", "travel tips"]
    },
    {
      "id": 3,
      "title": "Mastering JavaScript",
      "category": "Programming",
      "tags": ["JavaScript", "web development", "coding"]
    }
  ]
}
```

```liquid2
{% assign coding_pages = pages | where: page => page.tags contains 'coding' %}
{{ coding_pages | map: page => page.title | json }}
```

```plain title="output"
["Mastering JavaScript"]
```
