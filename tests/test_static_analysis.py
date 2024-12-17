"""Template static analysis test cases."""

from __future__ import annotations

import asyncio
import itertools
from typing import TYPE_CHECKING

import pytest

from liquid2 import Environment
from liquid2.builtin import DictLoader
from liquid2.exceptions import TemplateNotFoundError
from liquid2.static_analysis import Span
from liquid2.static_analysis import Variable

if TYPE_CHECKING:
    from liquid2 import Template
    from liquid2.static_analysis import TemplateAnalysis


@pytest.fixture
def env() -> Environment:  # noqa: D103
    return Environment()


def _assert(
    template: Template,
    *,
    locals: dict[str, list[Variable]],
    globals: dict[str, list[Variable]],
    variables: dict[str, list[Variable]] | None = None,
    filters: dict[str, list[Span]] | None = None,
    tags: dict[str, list[Span]] | None = None,
) -> None:
    variables = {**globals} if variables is None else variables

    async def coro() -> TemplateAnalysis:
        return await template.analyze_async()

    def _assert_refs(got: TemplateAnalysis) -> None:
        assert got.locals == locals
        assert got.globals == globals
        assert got.variables == variables

        if filters:
            assert got.filters == filters
        else:
            assert len(got.filters) == 0

        if tags:
            assert got.tags == tags
        else:
            assert len(got.tags) == 0

    _assert_refs(template.analyze())
    _assert_refs(asyncio.run(coro()))


def test_analyze_output(env: Environment) -> None:
    source = r"{{ x | default: y, allow_false: z }}"

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "x": [Variable(["x"], Span("", 3, 4))],
            "y": [Variable(["y"], Span("", 16, 17))],
            "z": [Variable(["z"], Span("", 32, 33))],
        },
        filters={
            "default": [Span("", 7, 14)],
        },
    )


def test_bracketed_query_notation(env: Environment) -> None:
    source = r"{{ x['y'].title }}"

    _assert(
        env.from_string(source),
        locals={},
        globals={"x": [Variable(["x", "y", "title"], Span("", 3, 15))]},
    )


def test_quoted_name_notation(env: Environment) -> None:
    source = r"{{ some['foo.bar'] }}"

    _assert(
        env.from_string(source),
        locals={},
        globals={"some": [Variable(["some", "foo.bar"], Span("", 3, 18))]},
    )


def test_nested_queries(env: Environment) -> None:
    source = r"{{ x[y.z].title }}"

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "x": [Variable(["x", ["y", "z"], "title"], Span("", 3, 15))],
            "y": [Variable(["y", "z"], Span("", 5, 8))],
        },
    )


def test_nested_root_query(env: Environment) -> None:
    source = r"{{ [a.b] }}"

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "a": [Variable(["a", "b"], Span("", 3, 8))],
        },
    )


def test_analyze_ternary(env: Environment) -> None:
    source = r"{{ a if b.c else d }}"

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "a": [Variable(["a"], Span("", 3, 4))],
            "b": [Variable(["b", "c"], Span("", 8, 11))],
            "d": [Variable(["d"], Span("", 17, 18))],
        },
    )


def test_analyze_ternary_filters(env: Environment) -> None:
    source = r"{{ a | upcase if b.c else d | default: 'x' || append: y }}"

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "a": [Variable(["a"], Span("", 3, 4))],
            "b": [Variable(["b", "c"], Span("", 17, 20))],
            "d": [Variable(["d"], Span("", 26, 27))],
            "y": [Variable(["y"], Span("", 54, 55))],
        },
        filters={
            "default": [Span("", 30, 37)],
            "append": [Span("", 46, 52)],
        },
    )


def test_analyze_assign(env: Environment) -> None:
    source = r"{% assign x = y | append: z %}"

    _assert(
        env.from_string(source),
        locals={"x": [Variable(["x"], Span("", 10, 11))]},
        globals={
            "y": [Variable(["y"], Span("", 14, 15))],
            "z": [Variable(["z"], Span("", 26, 27))],
        },
        filters={"append": [Span("", 18, 24)]},
        tags={"assign": [Span("", 0, 30)]},
    )


def test_analyze_capture(env: Environment) -> None:
    source = r"{% capture x %}{% if y %}z{% endif %}{% endcapture %}"

    _assert(
        env.from_string(source),
        locals={"x": [Variable(["x"], Span("", 11, 12))]},
        globals={
            "y": [Variable(["y"], Span("", 21, 22))],
        },
        tags={
            "capture": [Span("", 0, 15)],
            "if": [Span("", 15, 25)],
        },
    )


def test_analyze_case(env: Environment) -> None:
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

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "x": [Variable(["x"], Span("", 8, 9))],
            "y": [Variable(["y"], Span("", 21, 22))],
            "a": [Variable(["a"], Span("", 31, 32))],
            "z": [Variable(["z"], Span("", 44, 45))],
            "b": [Variable(["b"], Span("", 54, 55))],
            "c": [Variable(["c"], Span("", 75, 76))],
        },
        tags={"case": [Span("", 0, 12)]},
    )


def test_analyze_cycle(env: Environment) -> None:
    source = r"{% cycle x: a, b %}"

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "a": [Variable(["a"], Span("", 12, 13))],
            "b": [Variable(["b"], Span("", 15, 16))],
        },
        tags={"cycle": [Span("", 0, 19)]},
    )


def test_analyze_decrement(env: Environment) -> None:
    source = r"{% decrement x %}"

    _assert(
        env.from_string(source),
        locals={"x": [Variable(["x"], Span("", 13, 14))]},
        globals={},
        tags={"decrement": [Span("", 0, 17)]},
    )


def test_analyze_echo(env: Environment) -> None:
    source = r"{% echo x | default: y, allow_false: z %}"

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "x": [Variable(["x"], Span("", 8, 9))],
            "y": [Variable(["y"], Span("", 21, 22))],
            "z": [Variable(["z"], Span("", 37, 38))],
        },
        filters={
            "default": [Span("", 12, 19)],
        },
        tags={"echo": [Span("", 0, 41)]},
    )


def test_analyze_for(env: Environment) -> None:
    source = "\n".join(
        [
            r"{% for x in (1..y) %}",
            r"  {{ x }}",
            r"{% break %}",
            r"{% else %}",
            r"  {{ z }}",
            r"{% continue %}",
            r"{% endfor %}",
        ]
    )

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "y": [Variable(["y"], Span("", 16, 17))],
            "z": [Variable(["z"], Span("", 60, 61))],
        },
        variables={
            "y": [Variable(["y"], Span("", 16, 17))],
            "x": [Variable(["x"], Span("", 27, 28))],
            "z": [Variable(["z"], Span("", 60, 61))],
        },
        filters={},
        tags={
            "for": [Span("", 0, 21)],
            "break": [Span("", 32, 43)],
            "continue": [Span("", 65, 79)],
        },
    )


def test_analyze_if(env: Environment) -> None:
    source = "\n".join(
        [
            r"{% if x %}",
            r"  {{ a }}",
            r"{% elsif y %}",
            r"  {{ b }}",
            r"{% else %}",
            r"  {{ c }}",
            r"{% endif %}",
        ]
    )

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "x": [Variable(["x"], Span("", 6, 7))],
            "a": [Variable(["a"], Span("", 16, 17))],
            "y": [Variable(["y"], Span("", 30, 31))],
            "b": [Variable(["b"], Span("", 40, 41))],
            "c": [Variable(["c"], Span("", 61, 62))],
        },
        filters={},
        tags={
            "if": [Span("", 0, 10)],
        },
    )


def test_analyze_increment(env: Environment) -> None:
    source = r"{% increment x %}"

    _assert(
        env.from_string(source),
        locals={"x": [Variable(["x"], Span("", 13, 14))]},
        globals={},
        tags={"increment": [Span("", 0, 17)]},
    )


def test_analyze_liquid(env: Environment) -> None:
    source = """\
{% liquid
if product.title
    echo foo | upcase
else
    echo 'product-1' | upcase
endif

for i in (0..5)
    echo i
endfor %}"""

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "product": [Variable(["product", "title"], Span("", 13, 26))],
            "foo": [Variable(["foo"], Span("", 36, 39))],
        },
        variables={
            "product": [Variable(["product", "title"], Span("", 13, 26))],
            "foo": [Variable(["foo"], Span("", 36, 39))],
            "i": [Variable(["i"], Span("", 116, 117))],
        },
        filters={"upcase": [Span("", 42, 48), Span("", 77, 83)]},
        tags={
            "liquid": [Span("", 0, 127)],
            "echo": [Span("", 31, 48), Span("", 58, 83), Span("", 111, 117)],
            "for": [Span("", 91, 106)],
            "if": [Span("", 10, 26)],
        },
    )


def test_analyze_unless(env: Environment) -> None:
    source = """\
{% unless x %}
  {{ a }}
{% elsif y %}
  {{ b }}
{% else %}
  {{ c }}
{% endunless %}"""

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "x": [Variable(["x"], Span("", 10, 11))],
            "a": [Variable(["a"], Span("", 20, 21))],
            "y": [Variable(["y"], Span("", 34, 35))],
            "b": [Variable(["b"], Span("", 44, 45))],
            "c": [Variable(["c"], Span("", 65, 66))],
        },
        tags={
            "unless": [Span("", 0, 14)],
        },
    )


def test_analyze_include() -> None:
    loader = DictLoader({"a": "{{ x }}"})
    env = Environment(loader=loader)
    source = "{% include 'a' %}"

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "x": [Variable(["x"], Span("a", 3, 4))],
        },
        tags={
            "include": [Span("", 0, 17)],
        },
    )


def test_analyze_included_assign() -> None:
    loader = DictLoader({"a": "{{ x }}{% assign y = 42 %}"})
    env = Environment(loader=loader)
    source = "{% include 'a' %}{{ y }}"

    _assert(
        env.from_string(source),
        locals={
            "y": [Variable(["y"], Span("a", 17, 18))],
        },
        globals={
            "x": [Variable(["x"], Span("a", 3, 4))],
        },
        variables={
            "x": [Variable(["x"], Span("a", 3, 4))],
            "y": [Variable(["y"], Span("", 20, 21))],
        },
        tags={
            "include": [Span("", 0, 17)],
            "assign": [Span("a", 7, 26)],
        },
    )


def test_analyze_include_once() -> None:
    loader = DictLoader({"a": "{{ x }}"})
    env = Environment(loader=loader)
    source = "{% include 'a' %}{% include 'a' %}"

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "x": [Variable(["x"], Span("a", 3, 4))],
        },
        tags={
            "include": [Span("", 0, 17), Span("", 17, 34)],
        },
    )


def test_analyze_include_recursive() -> None:
    loader = DictLoader({"a": "{{ x }}{% include 'a' %}"})
    env = Environment(loader=loader)
    source = "{% include 'a' %}"

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "x": [Variable(["x"], Span("a", 3, 4))],
        },
        tags={
            "include": [
                Span("", 0, 17),
                Span("a", 7, 24),
            ],
        },
    )


def test_analyze_include_with_bound_variable() -> None:
    loader = DictLoader({"a": "{{ x | append: y }}{{ a }}"})
    env = Environment(loader=loader)
    source = "{% include 'a' with z %}"

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "z": [Variable(["z"], Span("", 20, 21))],
            "x": [Variable(["x"], Span("a", 3, 4))],
            "y": [Variable(["y"], Span("a", 15, 16))],
        },
        variables={
            "z": [Variable(["z"], Span("", 20, 21))],
            "x": [Variable(["x"], Span("a", 3, 4))],
            "y": [Variable(["y"], Span("a", 15, 16))],
            "a": [Variable(["a"], Span("a", 22, 23))],
        },
        tags={"include": [Span("", 0, 24)]},
        filters={"append": [Span("a", 7, 13)]},
    )


def test_analyze_include_with_bound_alias() -> None:
    loader = DictLoader({"a": "{{ x | append: y }}"})
    env = Environment(loader=loader)
    source = "{% include 'a' with z as y %}"

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "z": [Variable(["z"], Span("", 20, 21))],
            "x": [Variable(["x"], Span("a", 3, 4))],
        },
        variables={
            "z": [Variable(["z"], Span("", 20, 21))],
            "x": [Variable(["x"], Span("a", 3, 4))],
            "y": [Variable(["y"], Span("a", 15, 16))],
        },
        tags={"include": [Span("", 0, 29)]},
        filters={"append": [Span("a", 7, 13)]},
    )


def test_analyze_include_with_arguments() -> None:
    loader = DictLoader({"a": "{{ x | append: y }}"})
    env = Environment(loader=loader)
    source = "{% include 'a', x:y, z:42 %}{{ x }}"

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "y": [
                Variable(["y"], Span("", 18, 19)),
                Variable(["y"], Span("a", 15, 16)),
            ],
            "x": [Variable(["x"], Span("", 31, 32))],
        },
        variables={
            "y": [
                Variable(["y"], Span("", 18, 19)),
                Variable(["y"], Span("a", 15, 16)),
            ],
            "x": [
                Variable(["x"], Span("a", 3, 4)),
                Variable(["x"], Span("", 31, 32)),
            ],
        },
        tags={"include": [Span("", 0, 28)]},
        filters={"append": [Span("a", 7, 13)]},
    )


def test_analyze_include_with_variable_name(env: Environment) -> None:
    source = "{% include b %}{{ x }}"
    template = env.from_string(source)

    with pytest.raises(TemplateNotFoundError):
        template.analyze()


def test_analyze_include_string_template_not_found(env: Environment) -> None:
    source = "{% include 'nosuchthing' %}{{ x }}"
    template = env.from_string(source)

    with pytest.raises(TemplateNotFoundError):
        template.analyze()


def test_analyze_render_assign() -> None:
    loader = DictLoader({"a": "{{ x }}{% assign y = 42 %}"})
    env = Environment(loader=loader)
    source = "{% render 'a' %}{{ y }}"

    _assert(
        env.from_string(source),
        locals={
            "y": [Variable(["y"], Span("a", 17, 18))],
        },
        globals={
            "x": [Variable(["x"], Span("a", 3, 4))],
            "y": [Variable(["y"], Span("", 19, 20))],
        },
        tags={
            "render": [Span("", 0, 16)],
            "assign": [Span("a", 7, 26)],
        },
    )


def test_analyze_render_once() -> None:
    loader = DictLoader({"a": "{{ x }}"})
    env = Environment(loader=loader)
    source = "{% render 'a' %}{% render 'a' %}"

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "x": [Variable(["x"], Span("a", 3, 4))],
        },
        tags={
            "render": [Span("", 0, 16), Span("", 16, 32)],
        },
    )


def test_analyze_render_recursive() -> None:
    loader = DictLoader({"a": "{{ x }}{% render 'a' %}"})
    env = Environment(loader=loader)
    source = "{% render 'a' %}"

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "x": [Variable(["x"], Span("a", 3, 4))],
        },
        tags={
            "render": [
                Span("", 0, 16),
                Span("a", 7, 23),
            ],
        },
    )


def test_analyze_render_with_bound_variable() -> None:
    loader = DictLoader({"a": "{{ x | append: y }}{{ a }}"})
    env = Environment(loader=loader)
    source = "{% render 'a' with z %}"

    # Defaults to binding the value at `z` to the rendered template's name.

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "z": [Variable(["z"], Span("", 19, 20))],
            "x": [Variable(["x"], Span("a", 3, 4))],
            "y": [Variable(["y"], Span("a", 15, 16))],
        },
        variables={
            "z": [Variable(["z"], Span("", 19, 20))],
            "x": [Variable(["x"], Span("a", 3, 4))],
            "y": [Variable(["y"], Span("a", 15, 16))],
            "a": [Variable(["a"], Span("a", 22, 23))],
        },
        tags={"render": [Span("", 0, 23)]},
        filters={"append": [Span("a", 7, 13)]},
    )


def test_analyze_render_with_bound_alias() -> None:
    loader = DictLoader({"a": "{{ x | append: y }}"})
    env = Environment(loader=loader)
    source = "{% render 'a' with z as y %}"

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "z": [Variable(["z"], Span("", 19, 20))],
            "x": [Variable(["x"], Span("a", 3, 4))],
        },
        variables={
            "z": [Variable(["z"], Span("", 19, 20))],
            "x": [Variable(["x"], Span("a", 3, 4))],
            "y": [Variable(["y"], Span("a", 15, 16))],
        },
        tags={"render": [Span("", 0, 28)]},
        filters={"append": [Span("a", 7, 13)]},
    )


def test_analyze_render_with_arguments() -> None:
    loader = DictLoader({"a": "{{ x | append: y }}"})
    env = Environment(loader=loader)
    source = "{% render 'a', x:y, z:42 %}{{ x }}"

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "x": [Variable(["x"], Span("", 30, 31))],
            "y": [
                Variable(["y"], Span("", 17, 18)),
                Variable(["y"], Span("a", 15, 16)),
            ],
        },
        variables={
            "x": [
                Variable(["x"], Span("a", 3, 4)),
                Variable(["x"], Span("", 30, 31)),
            ],
            "y": [
                Variable(["y"], Span("", 17, 18)),
                Variable(["y"], Span("a", 15, 16)),
            ],
        },
        tags={"render": [Span("", 0, 27)]},
        filters={"append": [Span("a", 7, 13)]},
    )


def test_analyze_render_template_not_found(env: Environment) -> None:
    source = "{% render 'nosuchthing' %}{{ x }}"
    template = env.from_string(source)

    with pytest.raises(TemplateNotFoundError):
        template.analyze()


def test_variable_segments(env: Environment) -> None:
    source = "{{ a['b.c'] }}{{ d[e.f][4] }}"

    _assert(
        env.from_string(source),
        locals={},
        globals={
            "a": [Variable(["a", "b.c"], Span("", 3, 11))],
            "d": [Variable(["d", ["e", "f"], 4], Span("", 17, 26))],
            "e": [Variable(["e", "f"], Span("", 19, 22))],
        },
    )

    analysis = env.from_string(source).analyze()
    variables = list(itertools.chain.from_iterable(analysis.variables.values()))
    assert len(variables) == 3  # noqa: PLR2004
    assert variables[0].segments == ["a", "b.c"]
    assert variables[1].segments == ["d", ["e", "f"], 4]
    assert variables[2].segments == ["e", "f"]
    assert str(analysis.globals["a"][0]) == "a['b.c']"
    assert str(analysis.globals["d"][0]) == "d[e.f][4]"


def test_analyze_inheritance_chain() -> None:
    loader = DictLoader(
        {
            "base": (
                "Hello, "
                "{% assign x = 'foo' %}"
                "{% block content %}{{ x | upcase }}{% endblock %}!"
                "{% block foo %}{% endblock %}!"
            ),
            "other": (
                "{% extends 'base' %}"
                "{% block content %}{{ x | downcase }}{% endblock %}"
                "{% block foo %}{% assign z = 7 %}{% endblock %}"
            ),
            "some": (
                "{% extends 'other' %}{{ y | append: x }}"
                "{% block foo %}{% endblock %}"
            ),
        }
    )

    env = Environment(loader=loader)

    _assert(
        env.get_template("some"),
        locals={
            "x": [Variable(["x"], Span("base", 17, 18))],
            "z": [Variable(["z"], Span("other", 96, 97))],
        },
        globals={
            "y": [Variable(["y"], Span("some", 24, 25))],
        },
        variables={
            "x": [
                Variable(["x"], Span("base", 51, 52)),
                Variable(["x"], Span("other", 42, 43)),
                Variable(["x"], Span("some", 36, 37)),
            ],
            "y": [Variable(["y"], Span("some", 24, 25))],
        },
        tags={
            "assign": [
                Span("base", 7, 29),
                Span("other", 86, 104),
            ],
            "extends": [
                Span("some", 0, 21),
                Span("other", 0, 20),
            ],
            "block": [
                Span("base", 29, 48),
                Span("base", 79, 94),
                Span("other", 20, 39),
                Span("other", 71, 86),
                Span("some", 40, 55),
            ],
        },
        filters={
            "append": [Span("some", 28, 34)],
            "downcase": [Span("other", 46, 54)],
            "upcase": [Span("base", 55, 61)],
        },
    )


def test_analyze_recursive_extends() -> None:
    loader = DictLoader(
        {
            "some": "{% extends 'other' %}",
            "other": "{% extends 'some' %}",
        }
    )
    env = Environment(loader=loader)
    template = env.get_template("some")

    _assert(
        template,
        locals={},
        globals={},
        tags={
            "extends": [
                Span("some", 0, 21),
                Span("other", 0, 20),
            ],
        },
    )


def test_analyze_super() -> None:
    loader = DictLoader(
        {
            "base": "Hello, {% block content %}{{ foo | upcase }}{% endblock %}!",
            "some": (
                "{% extends 'base' %}"
                "{% block content %}{{ block.super }}!{% endblock %}"
            ),
        }
    )

    env = Environment(loader=loader)

    _assert(
        env.get_template("some"),
        locals={},
        globals={
            "foo": [Variable(["foo"], Span("base", 29, 32))],
        },
        variables={
            "foo": [Variable(["foo"], Span("base", 29, 32))],
            "block": [Variable(["block", "super"], Span("some", 42, 53))],
        },
        tags={
            "extends": [
                Span("some", 0, 20),
            ],
            "block": [
                Span("base", 7, 26),
                Span("some", 20, 39),
            ],
        },
        filters={
            "upcase": [Span("base", 35, 41)],
        },
    )
