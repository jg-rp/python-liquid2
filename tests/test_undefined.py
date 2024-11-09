"""Test cases for built in _undefined_ types."""

import operator
from dataclasses import dataclass
from dataclasses import field

import pytest

from liquid2 import Environment
from liquid2 import StrictUndefined
from liquid2.exceptions import UndefinedError


@dataclass(kw_only=True)
class Case:
    """Table driven test case helper."""

    description: str
    template: str
    expect: str
    context: dict[str, object] = field(default_factory=dict)


default_undefined_test_cases: list[Case] = [
    Case(
        description="undefined in output statement",
        template=r"{{ nosuchthing }}",
        expect="",
    ),
    Case(
        description="undefined in loop expression",
        template=r"{% for tag in nosuchthing %}{tag}{% endfor %}",
        expect="",
    ),
    Case(
        description="index undefined",
        template=r"{{ nosuchthing[0] }}",
        expect="",
    ),
    Case(
        description="test undefined for truthy-ness",
        template=r"{% if nosuchthing %}hello{% endif %}",
        expect="",
    ),
    Case(
        description="compare undefined",
        template=r"{% if nosuchthing == 'hello' %}hello{% endif %}",
        expect="",
    ),
    Case(
        description="undefined equals undefined",
        template=r"{% if nosuchthing == noway %}hello{% endif %}",
        expect="hello",
    ),
    Case(
        description="undefined contains string",
        template=r"{% if nosuchthing contains 'hello' %}hello{% endif %}",
        expect="",
    ),
    Case(
        description="access `last` from undefined",
        template=r"{{ nosuchthing.last }}",
        expect="",
    ),
    Case(
        description="access `size` from undefined",
        template=r"{{ nosuchthing.size }}",
        expect="",
    ),
    Case(
        description="filtered undefined",
        template=r"hello {{ nosuchthing | last }} there",
        expect="hello  there",
    ),
    Case(
        description="math filter undefined",
        template=r"hello {{ nosuchthing | abs }} there",
        expect="hello 0 there",
    ),
    Case(
        description="undefined filter argument",
        template=r"hello {{ '1,2,3' | split: nosuchthing }} there",
        expect="hello 1,2,3 there",
    ),
    Case(
        description="filter undefined through date",
        template=r"hello {{ nosuchthing | date: '%b %d, %y' }} there",
        expect="hello  there",
    ),
    Case(
        description="array index out or range",
        template=r"{% assign a = '1,2,3,4,5' | split: ',' %}{{ a[100] }}",
        expect="",
    ),
    Case(
        description="negative array index out or range",
        template=r"{% assign a = '1,2,3,4,5' | split: ',' %}{{ a[-100] }}",
        expect="",
    ),
]


@pytest.mark.parametrize(
    "case", default_undefined_test_cases, ids=operator.attrgetter("description")
)
def test_default_undefined(case: Case) -> None:
    env = Environment()
    assert env.from_string(case.template).render(**case.context) == case.expect


# TODO: update and test error messages

strict_undefined_test_cases: list[Case] = [
    Case(
        description="undefined in output statement",
        template=r"{{ nosuchthing }}",
        expect="'nosuchthing' is undefined, on line 1",
    ),
    Case(
        description="undefined in loop expression",
        template=r"{% for tag in nosuchthing %}{tag}{% endfor %}",
        expect="'nosuchthing' is undefined, on line 1",
    ),
    Case(
        description="index undefined",
        template=r"{{ nosuchthing[0] }}",
        expect="'nosuchthing' is undefined, on line 1",
    ),
    Case(
        description="test undefined for truthy-ness",
        template=r"{% if nosuchthing %}hello{% endif %}",
        expect="'nosuchthing' is undefined, on line 1",
    ),
    Case(
        description="compare undefined",
        template=r"{% if nosuchthing == 'hello' %}hello{% endif %}",
        expect="'nosuchthing' is undefined, on line 1",
    ),
    Case(
        description="undefined equals undefined",
        template=r"{% if nosuchthing == noway %}hello{% endif %}",
        expect="'nosuchthing' is undefined, on line 1",
    ),
    Case(
        description="undefined contains string",
        template=r"{% if nosuchthing contains 'hello' %}hello{% endif %}",
        expect="'nosuchthing' is undefined, on line 1",
    ),
    Case(
        description="access `last` from undefined",
        template=r"{{ nosuchthing.last }}",
        expect="'nosuchthing' is undefined, on line 1",
    ),
    Case(
        description="access `size` from undefined",
        template=r"{{ nosuchthing.size }}",
        expect="'nosuchthing' is undefined, on line 1",
    ),
    Case(
        description="filtered undefined",
        template=r"hello {{ nosuchthing | last }} there",
        expect="'nosuchthing' is undefined, on line 1",
    ),
    Case(
        description="undefined filter argument",
        template=r"hello {{ '1,2,3' | split: nosuchthing }} there",
        expect="'nosuchthing' is undefined, on line 1",
    ),
    Case(
        description="math filter undefined",
        template=r"hello {{ nosuchthing | abs }} there",
        expect="'nosuchthing' is undefined, on line 1",
    ),
    Case(
        description="array index out of range",
        template=r"{% assign a = '1,2,3,4,5' | split: ',' %}{{ a[100] }}",
        expect="list index out of range: a[100], on line 1",
    ),
    Case(
        description="negative array index out of range",
        template=r"{% assign a = '1,2,3,4,5' | split: ',' %}{{ a[-100] }}",
        expect="list index out of range: a[-100], on line 1",
    ),
    Case(
        description="key error",
        template=r"{{ obj['bar'] }}",
        expect="key error: 'bar', obj[bar], on line 1",
        context={"obj": {"foo": 1}},
    ),
]


@pytest.mark.parametrize(
    "case", strict_undefined_test_cases, ids=operator.attrgetter("description")
)
def test_strict_undefined(case: Case) -> None:
    env = Environment(undefined=StrictUndefined)
    template = env.from_string(case.template)

    with pytest.raises(UndefinedError):
        template.render(**case.context)


def test_strict_undefined_with_default() -> None:
    env = Environment(undefined=StrictUndefined)
    template = env.from_string(r"{{ nosuchthing | default: 'hello' }}")
    assert template.render() == "hello"


def test_strict_undefined_magic() -> None:
    undefined = StrictUndefined("test", token=None)

    with pytest.raises(UndefinedError):
        "foo" in undefined  # noqa: B015

    with pytest.raises(UndefinedError):
        int(undefined)

    with pytest.raises(UndefinedError):
        list(undefined)

    with pytest.raises(UndefinedError):
        len(undefined)

    with pytest.raises(UndefinedError):
        str(undefined)

    assert repr(undefined) == "StrictUndefined(test)"

    with pytest.raises(UndefinedError):
        bool(undefined)

    with pytest.raises(UndefinedError):
        hash(undefined)

    with pytest.raises(UndefinedError):
        reversed(undefined)  # type: ignore
