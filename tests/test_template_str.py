"""Test that templates can be serialized back to a string."""

from liquid2 import parse


def test_content_str() -> None:
    template = parse("Hello\n")
    assert str(template) == "Hello\n"


def test_comment_str() -> None:
    template = parse("{# this is a comment #}")
    assert str(template) == "{# this is a comment #}"


def test_comment_str_wc() -> None:
    template = parse("{#- this is a comment +#}")
    assert str(template) == "{#- this is a comment +#}"


def test_output_str() -> None:
    template = parse("{{ a.b }}")
    assert str(template) == "{{ a.b }}"


def test_output_str_wc() -> None:
    template = parse("{{- a.b +}}")
    assert str(template) == "{{- a.b +}}"


def test_assign_str() -> None:
    template = parse("{% assign x = y %}")
    assert str(template) == "{% assign x = y %}"


def test_assign_str_wc() -> None:
    template = parse("{%~ assign x = y %}")
    assert str(template) == "{%~ assign x = y %}"


def test_capture_str() -> None:
    source = "{% capture foo %}Hello, {{ you }}!{% endcapture %}"
    template = parse(source)
    assert str(template) == source


def test_capture_str_wc() -> None:
    source = "{%- capture foo +%}Hello, {{ you }}!{%+ endcapture -%}"
    template = parse(source)
    assert str(template) == source


def test_case_str() -> None:
    source = "{% case 'a' %}{% when 'b', c %}c{% when 'd' %}e{% else %}f{% endcase %}"
    template = parse(source)
    assert str(template) == source


def test_case_str_whitespace() -> None:
    source = "\n".join(
        [
            "{% case x %}",
            "{% when y %}",
            "  {{ a }}",
            "{% when z %}",
            "  {{ b }}",
            "{% else %}",
            "  {{ c }}",
            "{% endcase %}",
        ]
    )
    template = parse(source)
    assert str(template) == source


def test_case_str_whitespace_wc() -> None:
    source = "\n".join(
        [
            "{%- case x +%}",
            "{% when y %}",
            "  {{ a }}",
            "{%+ when z +%}",
            "  {{ b }}",
            "{%+ else +%}",
            "  {{ c }}",
            "{% endcase %}",
        ]
    )
    template = parse(source)
    assert str(template) == source


def test_cycle_str() -> None:
    source = "{% cycle 1, 2, 3 %}"
    template = parse(source)
    assert str(template) == source


def test_cycle_str_with_name() -> None:
    source = "{% cycle foo: 1, 2, 3 %}"
    template = parse(source)
    assert str(template) == source


def test_cycle_str_wc() -> None:
    source = "{%- cycle foo: 1, 2, 3 ~%}"
    template = parse(source)
    assert str(template) == source


def test_decrement_str() -> None:
    source = "{% decrement foo %}"
    template = parse(source)
    assert str(template) == source


def test_decrement_str_wc() -> None:
    source = "{%~ decrement foo +%}"
    template = parse(source)
    assert str(template) == source


def test_increment_str() -> None:
    source = "{% increment foo %}"
    template = parse(source)
    assert str(template) == source


def test_increment_str_wc() -> None:
    source = "{%~ increment foo +%}"
    template = parse(source)
    assert str(template) == source


def test_echo_str() -> None:
    source = "{% echo foo | upcase if bar else baz %}"
    template = parse(source)
    assert str(template) == source


def test_echo_str_wc() -> None:
    source = "{%+ echo foo | upcase -%}"
    template = parse(source)
    assert str(template) == source


def test_extends_str() -> None:
    source = "{% extends 'foo' %}"
    template = parse(source)
    assert str(template) == source


def test_extends_str_wc() -> None:
    source = "{%+ extends 'foo' -%}"
    template = parse(source)
    assert str(template) == source


def test_block_str() -> None:
    template = parse("{% block b required %}{{ greeting }}, {{ x }}! {% endblock %}")
    assert (
        str(template)
        == "{% block b required %}{{ greeting }}, {{ x }}! {% endblock b %}"
    )


def test_block_wc() -> None:
    template = parse(
        "{%- block b required +%}{{ greeting }}, {{ x }}! {%+ endblock ~%}"
    )
    assert (
        str(template)
        == "{%- block b required +%}{{ greeting }}, {{ x }}! {%+ endblock b ~%}"
    )


def test_for_str() -> None:
    source = "{% for a in b %}{{ a }},{% else %}c{% endfor %}"
    template = parse(source)
    assert str(template) == source


def test_for_str_wc() -> None:
    source = "{%- for a in b +%}{{ a }},{%+ else -%}c{%~ endfor %}"
    template = parse(source)
    assert str(template) == source


def test_break_and_continue_str() -> None:
    source = (
        "{% for a in b %}"
        "{% if true %}{% continue %}{% else %}{% break %}{% endif %}"
        "{% endfor %}"
    )
    template = parse(source)
    assert str(template) == source


def test_break_and_continue_str_wc() -> None:
    source = (
        "{% for a in b %}"
        "{% if true %}{%+ continue -%}{% else %}{%- break +%}{% endif %}"
        "{% endfor %}"
    )
    template = parse(source)
    assert str(template) == source


def test_if_str() -> None:
    source = "{% if false %}a{% elsif false %}b{% else %}c{% endif %}"
    template = parse(source)
    assert str(template) == source


def test_if_str_wc() -> None:
    source = "{%- if false +%}a{%~ elsif false -%}b{%+ else -%}c{%+ endif %}"
    template = parse(source)
    assert str(template) == source


def test_unless_str() -> None:
    source = "{% unless false %}a{% elsif false %}b{% else %}c{% endunless %}"
    template = parse(source)
    assert str(template) == source


def test_unless_str_wc() -> None:
    source = "{%- unless false +%}a{%~ elsif false -%}b{% else %}c{%+ endunless %}"
    template = parse(source)
    assert str(template) == source


def test_include_str() -> None:
    source = "{% include foo %}"
    template = parse(source)
    assert str(template) == source


def test_include_str_wc() -> None:
    source = "{%- include foo +%}"
    template = parse(source)
    assert str(template) == source


def test_include_str_with_alias() -> None:
    source = "{% include 'a' with b.c[1] as x, y:42 %}"
    template = parse(source)
    assert str(template) == source


def test_render_str() -> None:
    source = "{% render 'foo' %}"
    template = parse(source)
    assert str(template) == source


def test_render_str_wc() -> None:
    source = "{%- render 'foo' +%}"
    template = parse(source)
    assert str(template) == source


def test_render_str_with_alias() -> None:
    source = "{% render 'a' for b.c[1] as x, y:42 %}"
    template = parse(source)
    assert str(template) == source


def test_liquid_str() -> None:
    template = parse("{% liquid echo 'a'\nassign b = 'c'\necho b %}")
    assert str(template) == "{% echo 'a' %}\n{% assign b = 'c' %}\n{% echo b %}"


def test_raw_str() -> None:
    source = "{% raw %}{{ a }}{% endraw %}"
    template = parse(source)
    assert str(template) == source


def test_raw_str_wc() -> None:
    source = "{%- raw +%}{{ a }}{%~ endraw -%}"
    template = parse(source)
    assert str(template) == source


# TODO: ternary expressions
# TODO: parentheses in logical expressions
# TODO: liquid tag formatting
