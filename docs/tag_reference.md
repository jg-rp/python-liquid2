## Comments

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

Comments can be used to add documentation to your templates or "comment out" chunks of Liquid markup and text so that it wont be rendered. The recommended comment syntax is to surround comment text with `{#` and `#}`.

```liquid2
{# This is a comment #}
{#
    Comments can
    span
    multiple lines
#}
```

We can safely comment-out Liquid markup, and add hashes so as not to conflict with existing comments.

```liquid2
{## comment this out for now
{% for x in y %}
    {# x could be empty #}
    {{ x | default: TODO}}
{% endfor %}
##}
```

Inside [liquid tags](#liquid), any line starting with a hash will be considered a comment.

```liquid2
{% liquid
  # This is a comment
  echo "Hello"
%}
```

### Block comments

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
{% comment %} ... {% endcomment %}
```

Block comments start with the `comment` tag and end with the `endcomment` tag. It is OK for comment text to contain matching `comment`/`endcomment` or `raw`/`endraw` pairs, but is a syntax error if `comment` or `raw` tags are unbalanced.

```liquid2
{% comment %}This is a comment{% endcomment %}
{% comment %}
    Comments can
    span
    multiple lines
{% endcomment %}
```

### Inline comments

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
{% # ... %}
```

An inline comment is a tag called `#`. Everything after the hash up to the end tag delimiter (`%}`) is comment text. Text can span multiple lines, but each line must start with a `#`.

```liquid2
{% # This is a comment %}
{%-
  # Comments can span multiple lines,
  # but every line must start with a hash.
-%}
```

## assign

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
{% assign <identifier> = <expression> %}
```

The `assign` tag is used to define and initialize new variables or reassign existing variables.

```liquid2
{% assign foo = "bar" %}
foo is equal to {{ foo }}.

{% assign foo = 42 %}
foo is now equal to {{ foo }}.
```

The _expression_ on the right-hand side of the assignment operator (`=`) can be any Liquid _primitive_.

| Primitive expression | Examples                                                                                       |
| -------------------- | ---------------------------------------------------------------------------------------------- |
| Boolean literal      | `true` or `false`                                                                              |
| Null literal         | `null` or `nil`                                                                                |
| Integer literal      | `123` or `1e2` <!-- md:liquid2 -->                                                             |
| Float literal        | `1.23` or `1.2e3` <!-- md:liquid2 -->                                                          |
| String literal       | `"Hello"` or `'g\'day'` <!-- md:liquid2 --> or `#!liquid2 'Hello, ${you}'` <!-- md:liquid2 --> |
| Range                | `(1..5)` or `(x..y)`                                                                           |
| A path to a variable | `foo` or `foo.bar` or `foo.bar[0]` or `foo["some thing"].bar`                                  |

### Filters

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
{% assign <identifier> = <expression> | <filter> [| <filter> ...] %}
```

Values can be modified prior to assignment using filters. Filters are applied to an expression using the pipe symbol (`|`), followed by the filter's name and, possibly, some filter arguments. Filter arguments appear after a colon (`:`) and are separated by commas (,).

Multiple filters can be chained together, effectively piping the output of one filter into the input of another.

```liquid2
{% assign foo = "bar" | upcase %}
foo is equal to {{ foo }}.

{% assign foo = 42 | plus: 7 | modulo: 3 %}
foo is now equal to {{ foo }}.
```

### Ternary expressions

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

```
{% assign <identifier> = <expression> if <expression> else <expression> %}
```

Inline conditional expressions can be used as an alternative to the longer for [`{% if %}` tag](#if).

```liquid2
{% assign foo = "bar" if x.y == z else "baz" %}
```

Filters can be applied to either branch.

```liquid2
{% assign foo = "bar" | upcase if x else "baz" | capitalize %}
```

Or to the result of the conditional expression as a whole using _tail filters_. Notice the double pipe symbol (`||`).

```liquid2
{% assign foo = "bar" if x else "baz" || upcase | append: "!" %}
```

## capture

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
{% capture <identifier> %} <liquid markup> {% endcapture %}
```

The `capture` tag renders the contents of its block and saves the resulting string as a new variable, or reassigns an existing variable.

```liquid2
{% capture welcome_message %}
  Hello, {{ customer.name }}! Welcome to our store.
{% endcapture %}

{{ welcome_message }}
```

In some cases, it can be easier to use a template string <!-- md:liquid2 -->.

```liquid2
{% assign welcome_message = "Hello, ${ customer.name }! Welcome to our store." %}
```

## case

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
{% case <expression> %}
  [ {% when <expression> %} <liquid markup> ] ...
  [ {% else %} <liquid markup> ]
{% endcase %}
```

The `case` tag evaluates an expression, matching the result against one or move `when` clauses. In the event of a match, the `when` block is rendered. The `else` clause is rendered if no `when` clauses match the `case` expression.

```liquid2
{% assign day = "Monday" %}

{% case day %}
  {% when "Monday" %}
    Start of the work week!
  {% when "Friday" %}
    It's almost the weekend!
  {% when "Saturday" or "Sunday" %}
    Enjoy your weekend!
  {% else %}
    Just another weekday.
{% endcase %}
```

## cycle

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
{% cycle [ <string or identifier>: ] <expression> [, <expression> ... ] %}
```

Render the next item in an iterator, initializing the and rendering the first value if it does not yet exist. When the items are exhausted, the iterator starts again from the beginning.

```liquid2
{% cycle 'odd', 'even' %}
{% cycle 'odd', 'even' %}
{% cycle 'odd', 'even' %}
```

You can give `cycle` a name to further distinguish multiple iterators with the same items.

```liquid2
{% cycle 'odd', 'even' %}
{% cycle 'odd', 'even' %}
{% cycle inner: 'odd', 'even' %}
```

## decrement

## echo

## extends

### block

## for

## if

### break

### continue

## include

## increment

## liquid

## macro

### call

## raw

## render

## translate

## unless

## with
