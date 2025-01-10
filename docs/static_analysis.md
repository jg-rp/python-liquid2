Instances of [`Template`](api/template.md), as returned by [`parse()`](api/convenience.md#liquid2.parse), [`from_string()`](api/environment.md#liquid2.Environment.from_string) and [`get_template()`](api/environment.md#liquid2.Environment.get_template), include several methods for inspecting a template's variable, tag a filter usage, without rendering the template.

By default, all of these methods will try to load and analyze [included](tag_reference.md#include), [rendered](tag_reference.md#render) and [extended](tag_reference.md#extends) templates too. Set the `include_partials` keyword only argument to `False` to disable automatic loading and analysis of partial/parent templates.

## Variables

[`variables()`](api/template.md#liquid2.Template.variables) and [`variables_async()`](api/template.md#liquid2.Template.variables_async) return a list of distinct variables used in the template, without [path segments](variables_and_drops.md#paths-to-variables). The list will include variables that are _local_ to the template, like those crated with `{% assign %}` and `{% capture %}`, or are in scope from `{% for %}` tags.

```python
from liquid2 import parse

source = """\
Hello, {{ you }}!
{% assign x = 'foo' | upcase %}

{% for ch in x %}
    - {{ ch }}
{% endfor %}

Goodbye, {{ you.first_name | capitalize }} {{ you.last_name }}
Goodbye, {{ you.first_name }} {{ you.last_name }}
"""

template = parse(source)
print(template.variables())
```

```plain title="output"
['you', 'x', 'ch']
```

## Variable paths

[`variable_paths()`](api/template.md#liquid2.Template.variable_paths) and [`variable_paths_async()`](api/template.md#liquid2.Template.variable_paths_async) return a list of variables used in the template, including all path segments. The list will include variables that are _local_ to the template, like those crated with `{% assign %}` and `{% capture %}`, or are in scope from `{% for %}` tags.

```python
# ... continued from above

print(template.variable_paths())
```

```plain title="output"
['you.first_name', 'you', 'you.last_name', 'x', 'ch']
```

## Variable segments

[`variable_segments()`](api/template.md#liquid2.Template.variable_segments) and [`variable_segments_async()`](api/template.md#liquid2.Template.variable_segments_async) return a list of variables used in the template, each as a list of segments. The list will include variables that are _local_ to the template, like those crated with `{% assign %}` and `{% capture %}`, or are in scope from `{% for %}` tags.

```python
# ... continued from above

print(template.variable_segments())
```

```plain title="output"
[
    ["you", "last_name"],
    ["you"],
    ["you", "first_name"],
    ["ch"],
    ["x"],
]
```

## Global variables

[`global_variables()`](api/template.md#liquid2.Template.global_variables) and [`global_variables_async()`](api/template.md#liquid2.Template.global_variables_async) return a list of variables used in the template, without path segments and excluding variables that are local to the template.

```python
# ... continued from above

print(template.global_variables())
```

```plain title="output"
['you']
```

## Global variable paths

[`global_variable_paths()`](api/template.md#liquid2.Template.global_variable_paths) and [`global_variable_paths_async()`](api/template.md#liquid2.Template.global_variable_paths_async) return a list of variables used in the template, with path segments and excluding variables that are local to the template.

```python
# ... continued from above

print(template.global_variable_paths())
```

```plain title="output"
['you', 'you.first_name', 'you.last_name']
```

## Global variable segments

[`global_variable_segments()`](api/template.md#liquid2.Template.global_variable_segments) and [`global_variable_segments_async()`](api/template.md#liquid2.Template.global_variable_segments_async) return a list of variables used in the template, each as a list of segments, excluding variables that are local to the template.

```python
# ... continued from above

print(template.global_variable_segments())
```

```plain title="output"
[
    ['you', 'last_name'],
    ['you', 'first_name'],
    ['you'],
]
```

## Filter names

[`filter_names()`](api/template.md#liquid2.Template.filter_names) and [`filter_names_async()`](api/template.md#liquid2.Template.filter_names_async) return names of filters used in the template.

```python
# ... continued from above

print(template.filter_names())
```

```plain title="output"
['upcase', 'capitalize']
```

## Tag names

[`tag_names()`](api/template.md#liquid2.Template.tag_names) and [`tag_names_async()`](api/template.md#liquid2.Template.tag_names_async) return the names of tags used in the template.

```python
# ... continued from above

print(template.tag_names())
```

```plain title="output"
['assign', 'for']
```

## Variable, tag and filter locations

[`analyze()`](api/template.md#liquid2.Template.analyze) and [`analyze_async()`](api/template.md#liquid2.Template.analyze_async) return an instance of [`TemplateAnalysis`](api/template.md#liquid2.static_analysis.TemplateAnalysis). It contains all of the information provided by the methods described above, but includes the location of each variable, tag and filter, each of which can appear many times across many templates.

Using the same example template show at the top of this page, pretty printing `template.analyze()` gives us the following output.

```plain
TemplateAnalysis(variables={'ch': [Variable(segments=['ch'],
                                            span=Span(template_name='',
                                                      start=78,
                                                      end=80))],
                            'x': [Variable(segments=['x'],
                                           span=Span(template_name='',
                                                     start=64,
                                                     end=65))],
                            'you': [Variable(segments=['you'],
                                             span=Span(template_name='',
                                                       start=10,
                                                       end=13)),
                                    Variable(segments=['you', 'first_name'],
                                             span=Span(template_name='',
                                                       start=110,
                                                       end=124)),
                                    Variable(segments=['you', 'last_name'],
                                             span=Span(template_name='',
                                                       start=144,
                                                       end=157)),
                                    Variable(segments=['you', 'first_name'],
                                             span=Span(template_name='',
                                                       start=173,
                                                       end=187)),
                                    Variable(segments=['you', 'last_name'],
                                             span=Span(template_name='',
                                                       start=194,
                                                       end=207))]},
                 globals={'you': [Variable(segments=['you'],
                                           span=Span(template_name='',
                                                     start=10,
                                                     end=13)),
                                  Variable(segments=['you', 'first_name'],
                                           span=Span(template_name='',
                                                     start=110,
                                                     end=124)),
                                  Variable(segments=['you', 'last_name'],
                                           span=Span(template_name='',
                                                     start=144,
                                                     end=157)),
                                  Variable(segments=['you', 'first_name'],
                                           span=Span(template_name='',
                                                     start=173,
                                                     end=187)),
                                  Variable(segments=['you', 'last_name'],
                                           span=Span(template_name='',
                                                     start=194,
                                                     end=207))]},
                 locals={'x': [Variable(segments=['x'],
                                        span=Span(template_name='',
                                                  start=28,
                                                  end=29))]},
                 filters={'capitalize': [Span(template_name='',
                                              start=127,
                                              end=137)],
                          'upcase': [Span(template_name='', start=40, end=46)]},
                 tags={'assign': [Span(template_name='', start=18, end=49)],
                       'for': [Span(template_name='', start=51, end=68)]})
```
