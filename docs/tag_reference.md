All the tags described here are enabled by default in Python Liquid2.

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

## Output

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
{{ <expression> }}
```

An expression surrounded by double curly braces, `{{` and `}}`, is an _output statement_. When rendered, the expression will be evaluated and the result inserted into the output text.

In this example the expression is a variable, which will be resolved to a value and the value's string representation will output, but output statements can contain any primitive expression.

```liquid2
Hello, {{ you }}!
```

### Primitive expressions

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
{{ <expression> | <filter> [| <filter> ...] }}
```

Values can be modified prior to output using filters. Filters are applied to an expression using the pipe symbol (`|`), followed by the filter's name and, possibly, some filter arguments. Filter arguments appear after a colon (`:`) and are separated by commas (`,`).

Multiple filters can be chained together, effectively piping the output of one filter into the input of another.

```liquid2
{{ user_name | upcase }}
{{ 42 | plus: 7 | modulo: 3 }}
```

### Ternary expressions

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

```
{{ <expression> if <expression> else <expression> }}
```

Inline conditional expressions can be used as an alternative to the longer form [`{% if %}` tag](#if).

```liquid2
{{ "bar" if x.y == z else "baz" }}
```

Filters can be applied to either branch.

```liquid2
{{ "bar" | upcase if x else "baz" | capitalize }}
```

Or applied to the result of the conditional expression as a whole using _tail filters_. Notice the double pipe symbol (`||`).

```liquid2
{{ "bar" if x else "baz" || upcase | append: "!" }}
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

The _expression_ on the right-hand side of the assignment operator (`=`) follows the syntax described in [Output](#output) above. It can be any [primitive expression](#primitive-expressions), it can include [filters](#filters) or be a [ternary expression](#ternary-expressions).

## capture

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
{% capture <identifier> %} <liquid markup> {% endcapture %}
```

The `capture` tag evaluates the contents of its block and saves the resulting string as a new variable, or reassigns an existing variable, without immediately rendering it.

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

The `case` tag evaluates an expression, matching the result against one or more `when` clauses. In the event of a match, the `when` block is rendered. The `else` clause is rendered if no `when` clauses match the `case` expression.

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

Render the next item in an iterator, initializing it and rendering the first value if it does not yet exist. When the items are exhausted, the iterator starts again from the beginning.

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

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
{% decrement <identifier> %}
```

The `decrement` tag renders the next value in a named counter, reducing the count by one each time. If a counter with the given name does not already exist, it is created automatically and initialized to zero, before subtracting 1 and outputting `-1`.

```liquid2
{% decrement some %}
{% decrement thing %}
{% decrement thing %}
```

## echo

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
{% echo <expression> %}
```

The `echo` tag is equivalent to output statements, an expression surrounded by `{{` and `}}`, just in tag form. It is mostly used inside [`{% liquid %}`](#liquid) tags where plain output statements are not allowed.

```liquid2
Hello, {% echo you %}!
Hello, {{ you }}!

{% liquid
  for product in collection.products
    echo product.title | capitalize
  endfor
%}
```

Just like output statements and the [`assign`](#assign) tag, the expression can be any [primitive expression](#primitive-expressions), it can include [filters](#filters) or be a [ternary expression](#ternary-expressions).

<!-- md:liquid2 -->

```liquid2
{% echo "bar" | upcase if x else "baz" | capitalize %}

{% liquid
  for product in collection.products
    echo product.title | capitalize if "foo" in product.tags
  endfor
%}
```

## extends

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

```
{% extends <template name> %}
```

Together with the [`block`](#block) tag, the `extends` tag allows you to inherit content and Liquid markup from parent templates and define blocks that can be overridden by child templates.

In this example `page.html` inherits from `base.html` and overrides the `content` block. As `page.html` does not define a `footer` block, the footer from `base.html` is used.

```liquid2 title="base.html"
<body>
  <div id="content">{% block content required %}{% endblock %}</div>
  <div id="footer">{% block footer %}Default footer{% endblock %}</div>
</body>
```

```liquid2 title="page.html"
{% extends 'base.html' %}
{% block content %}Hello, {{ you }}!{% endblock %}
```

### block

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

```
{% block <name> [required] %} <Liquid markup> {% endblock [<name>] %}
```

Every `block` tag must have a name that is unique to the template. `endblock` tags can include a name too. If given, the `endblock` name must match the name given at the start of the block.

If the optional `required` argument is given, the block must be overridden by a child template, otherwise a `RequiredBlockError` will be raised.

```liquid2
<body>
  <div id="content">
    {% block content %}
      {% block title %}
        <h1>Some Title</h1>
      {% endblock title %}
    {% endblock content %}
  </div>
  <div id="footer">
    {% block footer %}
      Default footer
    {% endblock footer %}
  </div>
</body>
```

#### Super blocks

A `block` object is available inside every `{% block %}` tag. It has just one property, `super`. If a `{% block %}` is overriding a parent block, `{{ block.super }}` will render the parent's implementation of that block.

In this example we use `{{ block.super }}` in the `footer` block to output the base template's footer with a year appended to it.

```liquid2 title="base"
<head>
  {% block head %}{% endblock %}
<head>
<body>
  <div id="content">{% block content required %}{% endblock %}</div>
  <div id="footer">{% block footer %}Default footer{% endblock %}</div>
</body>
```

```liquid2 title="child"
{% extends "base" %}
{% block content %}Hello, World!{% endblock %}
{% block footer %}{{ block.super }} - 2025{% endblock %}
```

```html title="output"
<body>
  <div id="content">Hello, World!</div>
  <div id="footer">Default footer - 2025</div>
</body>
```

## for

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
{% for <identifier> in <expression>
    [ limit: <expression> ] [ offset: <expression> ] [ reversed ] %}
  <liquid markup>
  [ {% else %} <liquid markup> ]
{% endfor %}
```

The `for` tag renders its block once for each item in an iterable object, like an array/list or mapping/dict/hash. If the iterable is empty and an `else` block given, it will be rendered instead.

```liquid2
{% for product in collection %}
    - {{ product.title }}
{% else %}
    No products available
{% endfor %}
```

Range expression are often used with the `for` tag to loop over increasing integers.

```liquid2
{% for i in (1..4) %}
    {{ i }}
{% endfor %}
```

### limit

If a `limit` argument is given, the loop will stop after the specified number of iterations.

```liquid2
{% for product in collection.products limit: 2 %}
    - {{ product.title }}
{% endfor %}
```

### offset

If an `offset` argument is given, it should be an integer specifying how many items to skip before starting the loop.

```liquid2
{% for product in collection.products limit: 2 %}
    - {{ product.title }}
{% endfor %}
```

`offset` can also be given the special value `"continue"`, in which case the loop will start from where a previous loop with the same iterable left off.

```liquid2
{% for product in collection.products limit: 2 %}
    - {{ product.title }}
{% endfor %}

{% for product in collection.products offset: continue %}
    - {{ product.title }}!
{% endfor %}
```

### reversed

If the reversed flag is given, the target iterable will be iterated in reverse order.

```liquid2
{% for product in collection.products reversed %}
    - {{ product.title }}
{% endfor %}
```

### break

You can exit a loop early using the `break` tag.

```liquid2
{% for product in collection.products %}
    {% if product.title == "Shirt" %}
        {% break %}
    {% endif %}
    - {{ product.title }}
{% endfor %}
```

### continue

You can skip all or part of a loop iteration with the `continue` tag.

```liquid2
{% for product in collection.products %}
    {% if product.title == "Shirt" %}
        {% continue %}
    {% endif %}
    - {{ product.title }}
{% endfor %}
```

### forloop

A `forloop` object is available inside every `for` tag block.

| Property     | Description                                                          | Type    |
| ------------ | -------------------------------------------------------------------- | ------- |
| `name`       | The loop variable name and target identifier, separated by a hyphen. | string  |
| `length`     | The length of the sequence being iterated.                           | integer |
| `index`      | The 1-base index of the current iteration.                           | integer |
| `index0`     | The 0-base index of the current iteration.                           | integer |
| `rindex`     | The 1-base index of the current iteration counting from the end.     | integer |
| `rindex0`    | The 0-base index of the current iteration counting from the end.     | integer |
| `first`      | `true` if the current iteration is the first, `false` otherwise.     | bool    |
| `last`       | `true` is the current iteration is the last, `false` otherwise.      | bool    |
| `parentloop` | the `forloop` object of an enclosing `for` loop.                     | forloop |

```liquid2
{% for product in collection.products %}
    {% if forloop.first %}
      <b>{{ product.title }}</b> - {{ forloop.index0 }}
    {% else %}
      {{ product.title }} - {{ forloop.index0 }}
    {% endif %}
{% endfor %}
```

## if

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
{% if <expression> %}
  <liquid markup>
  [ {% elsif <expression> %} <liquid markup> [ {% elsif <expression> %} ... ]]
  [ {% else %} <liquid markup> ... ]
{% endif %}
```

The `if` tag conditionally renders its block if its expression evaluates to be truthy. Any number of `elsif` blocks can be given to add alternative conditions, and an `else` block is used as a default if no preceding conditions were truthy.

```liquid2
{% if product.title == "OK Hat" %}
  This hat is OK.
{% elsif product.title == "Rubbish Tie" %}
  This tie is rubbish.
{% else %}
  Not sure what this is.
{% endif %}
```

### Conditional expressions

Any primitive expression can be tested for truthiness, like `{% if some_variable %}`, or you can use a combination of the following operators. Only `false`, `nil`/`null` and the special _undefined_ object are falsy in Liquid.

| Operator                  | Description              | Example                             |
| ------------------------- | ------------------------ | ----------------------------------- |
| `==`                      | Equals                   | `product.title == "Nice Shoes"`     |
| `!=`                      | Not equals               | `user.name != "anonymous"`          |
| `>`                       | Greater than             | `product.was_price > product.price` |
| `<`                       | Less than                | `collection.products.size < 10`     |
| `>=`                      | Greater than or equal to | `user.age >= 18`                    |
| `<=`                      | Less than or equal to    | `basket.size <= 0`                  |
| `and`                     | Logical and              | `x and y`                           |
| `and`                     | Logical or               | `x or y`                            |
| `not` <!-- md:liquid2 --> | Logical not              | `not x`                             |

### Operator precedence

<!-- md:liquid2 -->

`and` binds more tightly than `or`, just like in Python. Terms can be grouped with parentheses to explicitly control logical operator precedence.

```liquid
{% if (user != empty and user.eligible and user.score > 100) or exempt %}
    user is special
{% else %}
    denied
{% endif %}
```

## include

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```liquid2
{% include <template name>
    [ ( with | for ) <expression> [ as <identifier> ]]
    [[,] <identifier>: <expression> [, [<identifier>: <expression> ... ]]]
%}
```

The `include` tag loads and renders a named template, inserting the resulting text in its place. The name of the template to include can be a string literal or a variable resolving to a string. When rendered, the included template will share the same scope as the current template.

```liquid2
{% include "snippets/header.html" %}
```

### with

Using the optional `with` syntax, we can bind a value to a variable that will be in scope for the included template. By default, that variable will be the name of the included template. Alternatively we can specify the variable to use with the `as` keyword followed by an identifier.

Here, the template named `greeting` will have access to a variable called `greeting` with the value `"Hello"`.

```liquid2
{% assign greetings = "Hello,Goodbye" | split: "," %}
{% include "greeting" with greetings.first %}
```

### for

If an array-like object it given following the `for` keyword, the named template will be rendered once for each item in the sequence and, like `with` above, the item value will be bound to a variable named after the included template.

In this example the template named `greeting` will be rendered once with the variable `greeting` set to `"Hello"` and once with the variable `greeting` set to `"Goodbye"`.

```liquid2
{% assign greetings = "Hello, Goodbye" | split: ", " %}
{% include "greeting" for greetings as greeting %}
```

### Keyword arguments

Additional keyword arguments given to the `include` tag will be added to the included template's scope, then go out of scope after the included template has been rendered.

```liquid2
{% include "partial_template" greeting: "Hello", num: 3, skip: 2 %}
```

## increment

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
{% increment <identifier> %}
```

The `increment` tag renders the next value in a named counter, increasing the count by one each time. If a counter with the given name does not already exist, it is created automatically and initialized to zero, which is output **before** adding `1`.

```liquid2
{% increment some %}
{% increment thing %}
{% increment thing %}
```

## liquid

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
{% liquid
  <tag name> [<expression>]
  [ <tag name> [<expression>]]
  ...
%}
```

The `liquid` tag encloses _line statements_, where each line starts with a tag name and is followed by the tag's expression. Expressions inside `liquid` tags **must** fit on one line as we use `\n` as a delimiter indicating the end of the expression.

Note that output statement syntax (`{{ <expression> }}`) is not allowed inside `liquid` tags, so you must use the [`echo`](#echo) tag instead.

```liquid2
{% liquid
  assign username = "Brian"

  if username
    echo "Hello, " | append: username
  else
    echo "Hello, user"
  endif

  for i in (1..3)
    echo i
  endfor
%}
```

Also, inside `liquid` tags, any line starting with a hash will be considered a comment.

```liquid2
{% liquid
  # This is a comment
  echo "Hello"
%}
```

## macro and call

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

```
{% macro <name> [[,] [ <identifier>[: <expression>]] ... ] %}
  <liquid markup>
{% endmacro %}
```

```
{% call <name> [[,] [ <identifier>[: <expression>]] ... ] %}
```

The `macro` tag defines a parameterized block that can later be called using the `call` tag.

A macro is like defining a function. You define a parameter list, possibly with default values, that are expected to be provided by a `call` tag. A macro tag's block has its own scope including its arguments and template global variables, just like the [`render`](#render) tag.

Note that argument defaults are bound late. They are evaluated when a call expression is evaluated, not when the macro is defined.

```liquid2
{% macro 'price' product, on_sale: false %}
  <div class="price-wrapper">
  {% if on_sale %}
    <p>Was {{ product.regular_price | prepend: '$' }}</p>
    <p>Now {{ product.price | prepend: '$' }}</p>
  {% else %}
    <p>{{ product.price | prepend: '$' }}</p>
  {% endif %}
  </div>
{% endmacro %}

{% call 'price' products[0], on_sale: true %}
{% call 'price' products[1] %}
```

Excess arguments passed to `call` are collected into variables called `args` and `kwargs`, so variadic macros a possible too.

```liquid2
{% macro 'foo' %}
  {% for arg in args %}
    - {{ arg }}
  {% endfor %}

  {% for arg in kwargs %}
    - {{ arg.0 }} => {{ arg.1 }}
  {% endfor %}
{% endmacro %}

{% call 'foo' 42, 43, 99, a: 3.14, b: 2.71828 %}
```

## raw

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
{% raw %} <text> {% endraw %}
```

Any text between `{% raw %}` and `{% endraw %}` will not be interpreted as Liquid markup, but output as plain text instead.

```liquid2
{% raw %}
  This will be rendered {{verbatim}}, with the curly brackets.
{% endraw %}
```

## render

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```liquid2
{% render <string>
    [ ( with | for ) <expression> [ as <identifier> ]]
    [[,] <identifier>: <expression> [, [<identifier>: <expression> ... ]]]
%}
```

The `render` tag loads and renders a named template, inserting the resulting text in its place. The name of the template to include **must** be a string literal. When rendered, the included template will have its onw scope, without variables define in the calling template.

```liquid2
{% render "snippets/header.html" %}
```

### with

Using the optional `with` syntax, we can bind a value to a variable that will be in scope for the rendered template. By default, that variable will be the name of the rendered template. Alternatively we can specify the variable to use with the `as` keyword followed by an identifier.

Here, the template named `greeting` will have access to a variable called `greeting` with the value `"Hello"`.

```liquid2
{% assign greetings = "Hello,Goodbye" | split: "," %}
{% render "greeting" with greetings.first %}
```

### for

If an array-like object it given following the `for` keyword, the named template will be rendered once for each item in the sequence and, like `with` above, the item value will be bound to a variable named after the rendered template.

In this example the template named `greeting` will be rendered once with the variable `greeting` set to `"Hello"` and once with the variable `greeting` set to `"Goodbye"`.

```liquid2
{% assign greetings = "Hello, Goodbye" | split: ", " %}
{% render "greeting" for greetings as greeting %}
```

### Keyword arguments

Additional keyword arguments given to the `render` tag will be added to the rendered template's scope, then go out of scope after the it has been rendered.

```liquid2
{% render "partial_template" greeting: "Hello", num: 3, skip: 2 %}
```

## translate

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

```
{% translate
    [context: <string>]
    [, count: <number>]
    [, <identifier>: <object> ] ... %}
  <text,variable> ...
[ {% plural %} <text,variable> ... ]
{% endtranslate %}
```

The `translate` tag defines text to be translated into another language. Said text can contain placeholders for variables. These placeholders look like Liquid output statements, but can't use dotted or bracketed property syntax or filters.

If a German translations object is found in the current render context, this example would output `Hallo Welt!`.

```liquid2
{% translate %}
  Hello, World!
{% endtranslate %}
```

If a `{% plural %}` block follows the message text and the special `count` argument is considered plural, the `{% plural %}` block will be rendered instead. Again, with a German translations object, this example would render `Hallo Welten!`.

```liquid2
{% translate count: 2 %}
  Hello, World!
{% plural %}
  Hello, Worlds!
{% endtranslate %}
```

Keyword arguments are used to add (or shadow existing) variables.

```liquid2
{% translate you: 'Sue' %}
  Hello, {{ you }}!
{% endtranslate %}
```

## unless

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```
{% unless <expression> %}
  <liquid markup>
  [ {% elsif <expression> %} <liquid markup> [ {% elsif <expression> %} ... ]]
  [ {% else %} <liquid markup> ... ]
{% endif %}
```

The `unless` tag conditionally renders its block if its expression evaluates to be falsy. Any number of elsif blocks can be given to add alternative conditions, and an else block is used as a default if none of preceding conditions were met.

```liquid2
{% unless product.title == "OK Hat" %}
  This hat is OK.
{% elsif product.title == "Rubbish Tie" %}
  This tie is rubbish.
{% else %}
  Not sure what this is.
{% endif %}
```

Otherwise `unless` behaves the same as [`if`](#if). See [Conditional expressions](#conditional-expressions).

## with

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

```
{% with <identifier>: <expression> [, <identifier>: <expression> ... ] %}
  <liquid markup>
{% endwith %}
```

The `with` tag extends the template namespace with block scoped variables. These variables have the potential to shadow global variables or variables assigned with `{% assign %}` and `{% capture %}`.

```liquid2
{% with p: collection.products.first %}
  {{ p.title }}
{% endwith %}

{% with a: 1, b: 3.4 %}
  {{ a }} + {{ b }} = {{ a | plus: b }}
{% endwith %}
```
