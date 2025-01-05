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

Inline conditional expressions can be used as an alternative to the longer form [`{% if %}` tag](#if).

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
{% echo <expression> | <filter> [| <filter> ...] %}
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

### Ternary expressions

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

```
{% echo <expression> if <expression> else <expression> %}
```

Just like output statements and the [`assign`](#assign) tag, you can use inline conditional expressions inside `echo` tags.

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

## increment

## liquid

## macro

### call

## raw

## render

## translate

## unless

## with
