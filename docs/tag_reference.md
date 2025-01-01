## Comments

<!-- md:version 0.1.0 -->
<!-- md:liquid2 -->

Comments can be used to add documentation to your templates or "comment out" chunks of Liquid markup so that it wont be rendered. The recommended comment syntax is to surround comment text with `{#` and `#}`.

```liquid
{# This is a comment #}
{#
    Comments can
    span
    multiple lines
#}
```

We can safely comment-out Liquid markup, and add hashes so as not to conflict with existing comments.

```liquid
{## comment this out for now
{% for x in y %}
    {# x could be empty #}
    {{ x | default: TODO}}
{% endfor %}
##}
```

Inside [liquid tags](#liquid), any line starting with a hash will be considered a comment.

```liquid
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

```liquid
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

```liquid
{% # This is a comment %}
{%-
  # Comments can span multiple lines,
  # but every line must start with a hash.
-%}
```

## assign

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

## block

## break

## call

## capture

## case

## continue

## cycle

## decrement

## echo

## extends

## for

## if

## include

## increment

## liquid

## macro

## raw

## render

## translate

## unless

## with
