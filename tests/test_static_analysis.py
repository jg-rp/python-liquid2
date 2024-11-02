"""Template static analysis test cases."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from typing import Any
from typing import Iterable
from typing import Mapping
from typing import Sequence
from typing import TypeAlias

import pytest

from liquid2 import Environment
from liquid2.builtin import DictLoader
from liquid2.exceptions import TemplateInheritanceError
from liquid2.static_analysis import Span

if TYPE_CHECKING:
    from liquid2 import Template
    from liquid2.static_analysis import TemplateAnalysis


@pytest.fixture
def env() -> Environment:  # noqa: D103
    return Environment()


class MockSpan:
    """A mock span containing the location of a variable, tag or filter."""

    __slots__ = ("template_name", "start", "end")

    def __init__(self, start: int, end: int, template_name: str = "<string>") -> None:
        self.template_name = template_name
        self.start = start
        self.end = end

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, (Span, MockSpan))
            and self.template_name == other.template_name
            and self.start == other.start
            and self.end == other.end
        )

    def __hash__(self) -> int:
        return hash((self.template_name, self.start, self.end))

    def __str__(self) -> str:
        return f"{self.template_name}[{self.start}:{self.end}]"


_Span = MockSpan
MockRefs: TypeAlias = Mapping[str, MockSpan | Sequence[MockSpan]]


def _assert(
    template: Template,
    *,
    local_refs: MockRefs,
    global_refs: MockRefs,
    all_refs: MockRefs | None = None,
    failed_visits: MockRefs | None = None,
    unloadable: MockRefs | None = None,
    raise_for_failures: bool = True,
    filters: MockRefs | None = None,
    tags: MockRefs | None = None,
) -> None:
    all_refs = {**global_refs} if all_refs is None else all_refs

    async def coro() -> TemplateAnalysis:
        return await template.analyze_async(raise_for_failures=raise_for_failures)

    def _assert_refs(refs: TemplateAnalysis) -> None:
        assert _as_strings(refs.local_variables) == _as_strings(local_refs)
        assert _as_strings(refs.global_variables) == _as_strings(global_refs)
        assert _as_strings(refs.variables) == _as_strings(all_refs)

        if failed_visits:
            assert _as_strings(refs.failed_visits) == _as_strings(failed_visits)
        else:
            assert len(refs.failed_visits) == 0

        if unloadable:
            assert _as_strings(refs.unloadable_partials) == _as_strings(unloadable)
        else:
            assert len(refs.unloadable_partials) == 0

        if filters:
            assert _as_strings(refs.filters) == _as_strings(filters)
        else:
            assert len(refs.filters) == 0

        if tags:
            assert _as_strings(refs.tags) == _as_strings(tags)
        else:
            assert len(refs.tags) == 0

    _assert_refs(template.analyze(raise_for_failures=raise_for_failures))
    _assert_refs(asyncio.run(coro()))


def _as_strings(
    refs: Mapping[Any, Any],
) -> dict[str, list[str]]:
    _refs: dict[str, list[str]] = {}
    for k, v in refs.items():
        if isinstance(v, Iterable):
            _refs[str(k)] = sorted([str(_v) for _v in v])
        else:
            _refs[str(k)] = sorted([str(v)])
    return _refs


def test_analyze_output(env: Environment) -> None:
    source = r"{{ x | default: y, allow_false: z }}"

    _assert(
        env.from_string(source),
        local_refs={},
        global_refs={
            "x": _Span(3, 4),
            "y": _Span(16, 17),
            "z": _Span(32, 33),
        },
        filters={
            "default": _Span(7, 14),
        },
    )


def test_bracketed_query_notation(env: Environment) -> None:
    source = r"{{ x['y'].title }}"

    _assert(
        env.from_string(source),
        local_refs={},
        global_refs={"x.y.title": _Span(3, 15)},
    )


def test_quoted_name_notation(env: Environment) -> None:
    source = r"{{ some['foo.bar'] }}"

    _assert(
        env.from_string(source),
        local_refs={},
        global_refs={"some['foo.bar']": _Span(3, 18)},
    )


def test_nested_queries(env: Environment) -> None:
    source = r"{{ x[y.z].title }}"

    _assert(
        env.from_string(source),
        local_refs={},
        global_refs={
            "x[y.z].title": _Span(3, 15),
            "y.z": _Span(5, 8),
        },
    )


def test_analyze_ternary(env: Environment) -> None:
    source = r"{{ a if b.c else d }}"

    _assert(
        env.from_string(source),
        local_refs={},
        global_refs={
            "a": _Span(3, 4),
            "b.c": _Span(8, 11),
            "d": _Span(17, 18),
        },
    )


def test_analyze_ternary_filters(env: Environment) -> None:
    source = r"{{ a | upcase if b.c else d | default: 'x' || append: y }}"

    _assert(
        env.from_string(source),
        local_refs={},
        global_refs={
            "a": _Span(3, 4),
            "b.c": _Span(17, 20),
            "d": _Span(26, 27),
            "y": _Span(54, 55),
        },
        filters={
            "default": _Span(30, 37),
            "append": _Span(46, 52),
        },
    )


def test_analyze_assign(env: Environment) -> None:
    source = r"{% assign x = y | append: z %}"

    _assert(
        env.from_string(source),
        local_refs={"x": _Span(10, 11)},
        global_refs={
            "y": _Span(14, 15),
            "z": _Span(26, 27),
        },
        filters={"append": _Span(18, 24)},
        tags={"assign": _Span(0, 30)},
    )


def test_analyze_capture(env: Environment) -> None:
    source = r"{% capture x %}{% if y %}z{% endif %}{% endcapture %}"

    _assert(
        env.from_string(source),
        local_refs={"x": _Span(11, 12)},
        global_refs={
            "y": _Span(21, 22),
        },
        tags={
            "capture": _Span(0, 15),
            "if": _Span(15, 25),
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
        local_refs={},
        global_refs={
            "x": _Span(8, 9),
            "y": _Span(21, 22),
            "a": _Span(31, 32),
            "z": _Span(44, 45),
            "b": _Span(54, 55),
            "c": _Span(75, 76),
        },
        tags={"case": _Span(0, 12)},
    )


def test_analyze_cycle(env: Environment) -> None:
    source = r"{% cycle x: a, b %}"

    _assert(
        env.from_string(source),
        local_refs={},
        global_refs={
            "a": _Span(12, 13),
            "b": _Span(15, 16),
        },
        tags={"cycle": _Span(0, 19)},
    )


def test_analyze_decrement(env: Environment) -> None:
    source = r"{% decrement x %}"

    _assert(
        env.from_string(source),
        local_refs={"x": _Span(13, 14)},
        global_refs={},
        tags={"decrement": _Span(0, 17)},
    )


def test_analyze_echo(env: Environment) -> None:
    source = r"{% echo x | default: y, allow_false: z %}"

    _assert(
        env.from_string(source),
        local_refs={},
        global_refs={
            "x": _Span(8, 9),
            "y": _Span(21, 22),
            "z": _Span(37, 38),
        },
        filters={
            "default": _Span(12, 19),
        },
        tags={"echo": _Span(0, 41)},
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
        local_refs={},
        global_refs={
            "y": _Span(16, 17),
            "z": _Span(60, 61),
        },
        all_refs={
            "y": _Span(16, 17),
            "x": _Span(27, 28),
            "z": _Span(60, 61),
        },
        filters={},
        tags={
            "for": _Span(0, 21),
            "break": _Span(32, 43),
            "continue": _Span(65, 79),
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
        local_refs={},
        global_refs={
            "x": _Span(6, 7),
            "a": _Span(16, 17),
            "y": _Span(30, 31),
            "b": _Span(40, 41),
            "c": _Span(61, 62),
        },
        filters={},
        tags={
            "if": _Span(0, 10),
        },
    )


def test_analyze_increment(env: Environment) -> None:
    source = r"{% increment x %}"

    _assert(
        env.from_string(source),
        local_refs={"x": _Span(13, 14)},
        global_refs={},
        tags={"increment": _Span(0, 17)},
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
        local_refs={},
        global_refs={
            "product.title": _Span(13, 26),
            "foo": _Span(36, 39),
        },
        all_refs={
            "product.title": _Span(13, 26),
            "foo": _Span(36, 39),
            "i": _Span(116, 117),
        },
        filters={"upcase": [_Span(42, 48), _Span(77, 83)]},
        tags={
            "liquid": _Span(0, 127),
            "echo": [_Span(31, 48), _Span(58, 83), _Span(111, 117)],
            "for": _Span(91, 106),
            "if": _Span(10, 26),
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
        local_refs={},
        global_refs={
            "x": _Span(10, 11),
            "a": _Span(20, 21),
            "y": _Span(34, 35),
            "b": _Span(44, 45),
            "c": _Span(65, 66),
        },
        tags={
            "unless": _Span(0, 14),
        },
    )


def test_analyze_include() -> None:
    loader = DictLoader({"a": "{{ x }}"})
    env = Environment(loader=loader)
    source = "{% include 'a' %}"

    _assert(
        env.from_string(source),
        local_refs={},
        global_refs={
            "x": _Span(3, 4, template_name="a"),
        },
        tags={
            "include": _Span(0, 17),
        },
    )


def test_analyze_included_assign() -> None:
    loader = DictLoader({"a": "{{ x }}{% assign y = 42 %}"})
    env = Environment(loader=loader)
    source = "{% include 'a' %}{{ y }}"

    _assert(
        env.from_string(source),
        local_refs={
            "y": _Span(17, 18, template_name="a"),
        },
        global_refs={
            "x": _Span(3, 4, template_name="a"),
        },
        all_refs={
            "x": _Span(3, 4, template_name="a"),
            "y": _Span(20, 21),
        },
        tags={
            "include": _Span(0, 17),
            "assign": _Span(7, 26, template_name="a"),
        },
    )


def test_analyze_include_once() -> None:
    loader = DictLoader({"a": "{{ x }}"})
    env = Environment(loader=loader)
    source = "{% include 'a' %}{% include 'a' %}"

    _assert(
        env.from_string(source),
        local_refs={},
        global_refs={
            "x": _Span(3, 4, template_name="a"),
        },
        tags={
            "include": [_Span(0, 17), _Span(17, 34)],
        },
    )


def test_analyze_include_recursive() -> None:
    loader = DictLoader({"a": "{{ x }}{% include 'a' %}"})
    env = Environment(loader=loader)
    source = "{% include 'a' %}"

    _assert(
        env.from_string(source),
        local_refs={},
        global_refs={
            "x": _Span(3, 4, template_name="a"),
        },
        tags={
            "include": [
                _Span(0, 17),
                _Span(7, 24, template_name="a"),
            ],
        },
    )


def test_analyze_include_with_bound_variable() -> None:
    loader = DictLoader({"a": "{{ x | append: y }}{{ a }}"})
    env = Environment(loader=loader)
    source = "{% include 'a' with z %}"

    _assert(
        env.from_string(source),
        local_refs={},
        global_refs={
            "z": _Span(20, 21),
            "x": _Span(3, 4, template_name="a"),
            "y": _Span(15, 16, template_name="a"),
        },
        all_refs={
            "z": _Span(20, 21),
            "x": _Span(3, 4, template_name="a"),
            "y": _Span(15, 16, template_name="a"),
            "a": _Span(22, 23, template_name="a"),
        },
        tags={"include": [_Span(0, 24)]},
        filters={"append": _Span(7, 13, template_name="a")},
    )


def test_analyze_include_with_bound_alias() -> None:
    loader = DictLoader({"a": "{{ x | append: y }}"})
    env = Environment(loader=loader)
    source = "{% include 'a' with z as y %}"

    _assert(
        env.from_string(source),
        local_refs={},
        global_refs={
            "z": _Span(20, 21),
            "x": _Span(3, 4, template_name="a"),
        },
        all_refs={
            "z": _Span(20, 21),
            "x": _Span(3, 4, template_name="a"),
            "y": _Span(15, 16, template_name="a"),
        },
        tags={"include": [_Span(0, 29)]},
        filters={"append": _Span(7, 13, template_name="a")},
    )


def test_analyze_include_with_arguments() -> None:
    loader = DictLoader({"a": "{{ x | append: y }}"})
    env = Environment(loader=loader)
    source = "{% include 'a', x:y, z:42 %}{{ x }}"

    _assert(
        env.from_string(source),
        local_refs={},
        global_refs={
            "y": [_Span(15, 16, template_name="a"), _Span(18, 19)],
            "x": _Span(31, 32),
        },
        all_refs={
            "y": [_Span(18, 19), _Span(15, 16, template_name="a")],
            "x": [_Span(31, 32), _Span(3, 4, template_name="a")],
        },
        tags={"include": [_Span(0, 28)]},
        filters={"append": _Span(7, 13, template_name="a")},
    )


def test_analyze_include_with_variable_name(env: Environment) -> None:
    source = "{% include b %}{{ x }}"

    _assert(
        env.from_string(source),
        local_refs={},
        global_refs={
            "b": _Span(11, 12),
            "x": _Span(18, 19),
        },
        tags={"include": [_Span(0, 15)]},
        unloadable={"b": _Span(11, 12)},
        raise_for_failures=False,
    )


def test_analyze_include_string_template_not_found(env: Environment) -> None:
    source = "{% include 'nosuchthing' %}{{ x }}"

    _assert(
        env.from_string(source),
        local_refs={},
        global_refs={"x": _Span(30, 31)},
        tags={"include": [_Span(0, 27)]},
        unloadable={"nosuchthing": _Span(12, 23)},
        raise_for_failures=False,
    )


def test_analyze_render_assign() -> None:
    loader = DictLoader({"a": "{{ x }}{% assign y = 42 %}"})
    env = Environment(loader=loader)
    source = "{% render 'a' %}{{ y }}"

    _assert(
        env.from_string(source),
        local_refs={
            "y": _Span(17, 18, template_name="a"),
        },
        global_refs={
            "x": _Span(3, 4, template_name="a"),
            "y": _Span(19, 20),
        },
        tags={
            "render": _Span(0, 16),
            "assign": _Span(7, 26, template_name="a"),
        },
    )


def test_analyze_render_once() -> None:
    loader = DictLoader({"a": "{{ x }}"})
    env = Environment(loader=loader)
    source = "{% render 'a' %}{% render 'a' %}"

    _assert(
        env.from_string(source),
        local_refs={},
        global_refs={
            "x": _Span(3, 4, template_name="a"),
        },
        tags={
            "render": [_Span(0, 16), _Span(16, 32)],
        },
    )


def test_analyze_render_recursive() -> None:
    loader = DictLoader({"a": "{{ x }}{% render 'a' %}"})
    env = Environment(loader=loader)
    source = "{% render 'a' %}"

    _assert(
        env.from_string(source),
        local_refs={},
        global_refs={
            "x": _Span(3, 4, template_name="a"),
        },
        tags={
            "render": [
                _Span(0, 16),
                _Span(7, 23, template_name="a"),
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
        local_refs={},
        global_refs={
            "z": _Span(19, 20),
            "x": _Span(3, 4, template_name="a"),
            "y": _Span(15, 16, template_name="a"),
        },
        all_refs={
            "z": _Span(19, 20),
            "x": _Span(3, 4, template_name="a"),
            "y": _Span(15, 16, template_name="a"),
            "a": _Span(22, 23, template_name="a"),
        },
        tags={"render": [_Span(0, 23)]},
        filters={"append": _Span(7, 13, template_name="a")},
    )


def test_analyze_render_with_bound_alias() -> None:
    loader = DictLoader({"a": "{{ x | append: y }}"})
    env = Environment(loader=loader)
    source = "{% render 'a' with z as y %}"

    _assert(
        env.from_string(source),
        local_refs={},
        global_refs={
            "z": _Span(19, 20),
            "x": _Span(3, 4, template_name="a"),
        },
        all_refs={
            "z": _Span(19, 20),
            "x": _Span(3, 4, template_name="a"),
            "y": _Span(15, 16, template_name="a"),
        },
        tags={"render": [_Span(0, 28)]},
        filters={"append": _Span(7, 13, template_name="a")},
    )


def test_analyze_render_with_arguments() -> None:
    loader = DictLoader({"a": "{{ x | append: y }}"})
    env = Environment(loader=loader)
    source = "{% render 'a', x:y, z:42 %}{{ x }}"

    _assert(
        env.from_string(source),
        local_refs={},
        global_refs={
            "y": [_Span(15, 16, template_name="a"), _Span(17, 18)],
            "x": _Span(30, 31),
        },
        all_refs={
            "y": [_Span(17, 18), _Span(15, 16, template_name="a")],
            "x": [_Span(30, 31), _Span(3, 4, template_name="a")],
        },
        tags={"render": [_Span(0, 27)]},
        filters={"append": _Span(7, 13, template_name="a")},
    )


def test_analyze_render_template_not_found(env: Environment) -> None:
    source = "{% render 'nosuchthing' %}{{ x }}"

    _assert(
        env.from_string(source),
        local_refs={},
        global_refs={"x": _Span(29, 30)},
        tags={"render": [_Span(0, 26)]},
        unloadable={"nosuchthing": _Span(11, 22)},
        raise_for_failures=False,
    )


def test_variable_parts(env: Environment) -> None:
    source = "{{ a['b.c'] }}{{ d[e.f] }}"

    _assert(
        env.from_string(source),
        local_refs={},
        global_refs={
            "a['b.c']": _Span(3, 11),
            "d[e.f]": _Span(17, 23),
            "e.f": _Span(19, 22),
        },
    )

    analysis = env.from_string(source).analyze()
    queries = list(analysis.variables.keys())
    assert len(queries) == 3  # noqa: PLR2004
    assert queries[0].as_tuple() == ("a", "b.c")
    assert queries[1].as_tuple() == ("d", ("e", "f"))
    assert queries[2].as_tuple() == ("e", "f")


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
        local_refs={
            "x": _Span(17, 18, template_name="base"),
        },
        global_refs={},
        all_refs={
            "x": _Span(42, 43, template_name="other"),
        },
        tags={
            "assign": _Span(7, 29, template_name="base"),
            "extends": [
                _Span(0, 21, template_name="some"),
                _Span(0, 20, template_name="other"),
            ],
            "block": [
                _Span(29, 48, template_name="base"),
                _Span(79, 94, template_name="base"),
                _Span(20, 39, template_name="other"),
                _Span(71, 86, template_name="other"),
                _Span(40, 55, template_name="some"),
            ],
        },
        filters={
            "downcase": _Span(46, 54, template_name="other"),
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

    with pytest.raises(TemplateInheritanceError):
        template.analyze()

    async def coro(template: Template) -> TemplateAnalysis:
        return await template.analyze_async()

    with pytest.raises(TemplateInheritanceError):
        asyncio.run(coro(template))


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
        local_refs={},
        global_refs={
            "foo": _Span(29, 32, template_name="base"),
        },
        all_refs={
            "foo": _Span(29, 32, template_name="base"),
            "block.super": _Span(42, 53, template_name="some"),
        },
        tags={
            "extends": [
                _Span(0, 20, template_name="some"),
            ],
            "block": [
                _Span(20, 39, template_name="some"),
                _Span(7, 26, template_name="base"),
            ],
        },
        filters={
            "upcase": _Span(35, 41, template_name="base"),
        },
    )
