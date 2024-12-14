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
    template = parse("{{- a.b -}}")
    assert str(template) == "{{- a.b -}}"


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
