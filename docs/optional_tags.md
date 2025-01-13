The tags described here are **not** enabled by default in Python Liquid2.

## tablerow

<!-- md:version 0.1.0 -->
<!-- md:shopify -->

```plain
{% tablerow <identifier> in <expression>
    [ cols: <expression> ] [ limit: <expression> ] [ offset: <expression> ] %}
  <liquid markup>
{% endtablerow %}
```

The `tablerow` tag renders HTML `<tr>` and `<td>` elements for each item in an iterable. Text inside `<td>` elements will be the result of rendering the tag's block.

```json title="data"
{
  "collection": {
    "products": [
      { "title": "Cool Shirt" },
      { "title": "Alien Poster" },
      { "title": "Batman Poster" },
      { "title": "Bullseye Shirt" },
      { "title": "Another Classic Vinyl" },
      { "title": "Awesome Jeans" }
    ]
  }
}
```

```liquid2 title="template"
<table>
{% tablerow product in collection.products %}
  {{ product.title }}
{% endtablerow %}
</table>
```

```html title="output"
<table>
  <tr class="row1">
    <td class="col1">Cool Shirt</td>
    <td class="col2">Alien Poster</td>
    <td class="col3">Batman Poster</td>
    <td class="col4">Bullseye Shirt</td>
    <td class="col5">Another Classic Vinyl</td>
    <td class="col6">Awesome Jeans</td>
  </tr>
</table>
```

### cols

By default, `tablerow` will output one row with one column for each item in the sequence. Use the `cols` parameter to set the number of columns.

```liquid2 title="template"
{% tablerow product in collection.products cols:2 %}
  {{ product.title }}
{% endtablerow %}
```

```html title="output"
<table>
  <tr class="row1">
    <td class="col1">Cool Shirt</td>
    <td class="col2">Alien Poster</td>
  </tr>
  <tr class="row2">
    <td class="col1">Batman Poster</td>
    <td class="col2">Bullseye Shirt</td>
  </tr>
  <tr class="row3">
    <td class="col1">Another Classic Vinyl</td>
    <td class="col2">Awesome Jeans</td>
  </tr>
</table>
```

### limit

If `limit` is specified, the `tablerow` loop will stop after the given number of iterations.

```liquid2 title="template"
<table>
{% tablerow product in collection.products limit:2 %}
  {{ product.title }}
{% endtablerow %}
</table>
```

```html title="output"
<table>
  <tr class="row1">
    <td class="col1">Cool Shirt</td>
    <td class="col2">Alien Poster</td>
  </tr>
</table>
```

### offset

If `offset` is specified, the `tablerow` loop will start at the given index in the sequence.

```liquid2 title="template"
<table>
{% tablerow product in collection.products offset:4 %}
  {{ product.title }}
{% endtablerow %}
</table>
```

```html title="output"
<table>
  <tr class="row1">
    <td class="col1">Another Classic Vinyl</td>
    <td class="col2">Awesome Jeans</td>
  </tr>
</table>
```

### tablerowloop

A `tablerowloop` object is available inside every `tablerow` block.

| Property    | Description                                                         | Type    |
| ----------- | ------------------------------------------------------------------- | ------- |
| `length`    | The length of the sequence being iterated                           | integer |
| `index`     | The 1-base index of the current iteration                           | integer |
| `index0`    | The 0-base index of the current iteration                           | integer |
| `rindex`    | The 1-base index of the current iteration counting from the end     | integer |
| `rindex0`   | The 0-base index of the current iteration counting from the end     | integer |
| `first`     | `true` if the current iteration is the first, `false` otherwise     | bool    |
| `last`      | `true` is the current iteration is the last, `false` otherwise      | bool    |
| `col`       | The 1-based column number                                           | integer |
| `col0`      | The 0-based column number                                           | integer |
| `col_first` | `true` if the current column is the first column, `false` otherwise | integer |
| `col_last`  | `true` if the current column is the last column, `false` otherwise  | integer |
| `row`       | The current row number of the table                                 | integer |

```liquid2 title="template"
{% tablerow product in collection.products cols:2 %}
  {{ product.title }} - {{ tablerowloop.col0 }}
{% endtablerow %}
```

```html title="output"
<table>
  <tr class="row1">
    <td class="col1">Cool Shirt - 0</td>
    <td class="col2">Alien Poster - 1</td>
  </tr>
  <tr class="row2">
    <td class="col1">Batman Poster - 0</td>
    <td class="col2">Bullseye Shirt< - 1/td></td>
  </tr>
  <tr class="row3">
    <td class="col1">Another Classic Vinyl - 0</td>
    <td class="col2">Awesome Jeans - 1</td>
  </tr>
</table>
```
