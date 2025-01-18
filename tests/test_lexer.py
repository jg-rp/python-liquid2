import operator
from dataclasses import dataclass

import pytest

from liquid2 import tokenize


@dataclass
class Case:
    name: str
    source: str
    want: str


TEST_CASES = [
    Case(
        name="empty template",
        source="",
        want="",
    ),
    Case(
        name="just text content",
        source="Hello",
        want="Hello",
    ),
    Case(
        name="just whitespace",
        source=" \n ",
        want=" \n ",
    ),
    Case(
        name="just output",
        source="{{ foo }}",
        want="{{ foo }}",
    ),
    Case(
        name="hello liquid",
        source="Hello, {{ you }}!",
        want="Hello, {{ you }}!",
    ),
    Case(
        name="output whitespace control",
        source=(
            "Hello, "
            "{{- you -}}, {{+ you +}}, {{~ you ~}}, "
            "{{+ you -}}, {{~ you -}}, {{- you +}}!"
        ),
        want=(
            "Hello, "
            "{{- you -}}, {{+ you +}}, {{~ you ~}}, "
            "{{+ you -}}, {{~ you -}}, {{- you +}}!"
        ),
    ),
    Case(
        name="raw tag",
        source="Hello, {% raw %}{{ you }}{% endraw %}!",
        want="Hello, {% raw %}{{ you }}{% endraw %}!",
    ),
    Case(
        name="raw tag whitespace control",
        source="Hello, {%- raw +%}{{ you }}{%~ endraw -%}!",
        want="Hello, {%- raw +%}{{ you }}{%~ endraw -%}!",
    ),
    Case(
        name="comment tag",
        source="Hello, {# some comment {{ foo }} #}{{ you }}!",
        want="Hello, {# some comment {{ foo }} #}{{ you }}!",
    ),
    Case(
        name="comment tag whitespace control",
        source="Hello, {#- some comment {{ foo }} +#}{{ you }}!",
        want="Hello, {#- some comment {{ foo }} +#}{{ you }}!",
    ),
    Case(
        name="comment tag, nested",
        source="Hello, {## some comment {# other comment #} ##}{{ you }}!",
        want="Hello, {## some comment {# other comment #} ##}{{ you }}!",
    ),
    Case(
        name="assign tag",
        source="{% assign x = true %}",
        want="{% assign x = true %}",
    ),
    Case(
        name="assign tag whitespace control",
        source="{%~ assign x = true -%}",
        want="{%~ assign x = true -%}",
    ),
    Case(
        name="assign tag, filter",
        source="{% assign x = true | default: foo %}",
        want="{% assign x = true | default: foo %}",
    ),
    Case(
        name="assign tag, filters",
        source="{% assign x = true | default: foo | upcase %}",
        want="{% assign x = true | default: foo | upcase %}",
    ),
    Case(
        name="assign tag, condition",
        source="{% assign x = true if y %}",
        want="{% assign x = true if y %}",
    ),
    Case(
        name="assign tag, condition, tail filter",
        source="{% assign x = true if y || upcase %}",
        want="{% assign x = true if y || upcase %}",
    ),
    Case(
        name="assign tag, condition, tail filters",
        source="{% assign x = true if y || upcase | join : 'foo' %}",
        want="{% assign x = true if y || upcase | join: 'foo' %}",
    ),
    Case(
        name="assign tag, condition and alternative",
        source="{% assign x = true if y else z %}",
        want="{% assign x = true if y else z %}",
    ),
    Case(
        name="assign tag, condition and alternative, filter",
        source="{% assign x = true if y else z | upcase %}",
        want="{% assign x = true if y else z | upcase %}",
    ),
    Case(
        name="assign tag, comma separated right",
        source="{% assign x = a, b %}",
        want="{% assign x = a, b %}",
    ),
    Case(
        name="if tag",
        source="{% if foo %}bar{% endif %}",
        want="{% if foo %}bar{% endif %}",
    ),
    Case(
        name="if tag, else",
        source="{% if foo %}a{% else %}b{% endif %}",
        want="{% if foo %}a{% else %}b{% endif %}",
    ),
    Case(
        name="if tag, elsif",
        source="{% if foo %}a{% elsif bar %}b{% endif %}",
        want="{% if foo %}a{% elsif bar %}b{% endif %}",
    ),
    Case(
        name="if tag, elsif, whitespace control",
        source="{%- if foo ~%}a{%+ elsif bar +%}b{%~ endif -%}",
        want="{%- if foo ~%}a{%+ elsif bar +%}b{%~ endif -%}",
    ),
    Case(
        name="liquid tag",
        source="{% liquid assign 'x' = 'y' %}",
        want="{% liquid assign 'x' = 'y' %}",
    ),
    Case(
        name="liquid tag, empty",
        source="{% liquid %}",
        want="{% liquid %}",
    ),
    Case(
        name="liquid tag, leading newline",
        source="{% liquid\nassign 'x' = 'y' %}",
        want="{% liquid\nassign 'x' = 'y' %}",
    ),
    Case(
        name="liquid tag, multiple lines",
        source="{% liquid assign 'x' = 'y'\nfor a in b\necho a\nendfor %}",
        want="{% liquid assign 'x' = 'y'\nfor a in b\necho a\nendfor %}",
    ),
    Case(
        name="liquid tag, multiple newlines",
        source="{% liquid assign 'x' = 'y'\n\nfor a in b\necho a\nendfor %}",
        want="{% liquid assign 'x' = 'y'\n\nfor a in b\necho a\nendfor %}",
    ),
    Case(
        name="liquid tag, tag without expression",
        source="{% liquid break %}",
        want="{% liquid break %}",
    ),
    Case(
        name="template string, single quote",
        source="{{ 'Hello, ${you}!' }}",
        want="{{ 'Hello, ${you}!' }}",
    ),
    Case(
        name="template string, double quote",
        source='{{ "Hello, ${you}!" }}',
        want='{{ "Hello, ${you}!" }}',
    ),
    Case(
        name="template string, with filter",
        source='{{ "Hello, ${you | upcase}!" }}',
        want='{{ "Hello, ${you | upcase}!" }}',
    ),
    Case(
        name="template string, with ternary expression",
        source='{{ "Hello, ${you if a else b}!" }}',
        want='{{ "Hello, ${you if a else b}!" }}',
    ),
    Case(
        name="template string, just a placeholder",
        source='{{ "${you}" }}',
        want='{{ "${you}" }}',
    ),
    Case(
        name="arrow expression",
        source="{% assign x | map: i => i.foo.bar %}",
        want="{% assign x | map: i => i.foo.bar %}",
    ),
    Case(
        name="arrow expression, two arguments",
        source="{% assign x | map: (item, index) => item.foo.bar %}",
        want="{% assign x | map: (item, index) => item.foo.bar %}",
    ),
    Case(
        name="range expression as filter argument",
        source="{% assign x | foo: (1..4) %}",
        want="{% assign x | foo: (1..4) %}",
    ),
]


@pytest.mark.parametrize("case", TEST_CASES, ids=operator.attrgetter("name"))
def test_lexer(case: Case) -> None:
    assert "".join(str(t) for t in tokenize(case.source)) == case.want
