import asyncio
import operator
from typing import Any
from typing import NamedTuple

import pytest

from liquid2 import render
from liquid2 import render_async


class Case(NamedTuple):
    description: str
    template: str
    context: dict[str, Any]
    expect: str


TEST_CASES: list[Case] = [
    Case(
        description="output, single quoted",
        template="{{ 'Hello, ${you}!' }}",
        context={"you": "World"},
        expect="Hello, World!",
    ),
    Case(
        description="output, double quoted",
        template='{{ "Hello, ${you}!" }}',
        context={"you": "World"},
        expect="Hello, World!",
    ),
    Case(
        description="output, expression at end",
        template='{{ "Hello, ${you}" }}',
        context={"you": "World"},
        expect="Hello, World",
    ),
    Case(
        description="output, expression at start",
        template='{{ "${you}!" }}',
        context={"you": "World"},
        expect="World!",
    ),
    Case(
        description="output, just expression",
        template='{{ "${you}" }}',
        context={"you": "World"},
        expect="World",
    ),
    Case(
        description="echo, single quoted",
        template="{% echo 'Hello, ${you}!' %}",
        context={"you": "World"},
        expect="Hello, World!",
    ),
    Case(
        description="echo, double quoted",
        template='{% echo "Hello, ${you}!" %}',
        context={"you": "World"},
        expect="Hello, World!",
    ),
    Case(
        description="echo, expression at end",
        template='{% echo "Hello, ${you}" %}',
        context={"you": "World"},
        expect="Hello, World",
    ),
    Case(
        description="echo, expression at start",
        template='{% echo "${you}!" %}',
        context={"you": "World"},
        expect="World!",
    ),
    Case(
        description="echo, just expression",
        template='{% echo "${you}" %}',
        context={"you": "World"},
        expect="World",
    ),
    Case(
        description="filtered",
        template="{{ 'Hello, ${you}' | append: '!' }}",
        context={"you": "World"},
        expect="Hello, World!",
    ),
    Case(
        description="filter argument",
        template="{{ 'Hello ' | append: 'there, ${you}!' }}",
        context={"you": "World"},
        expect="Hello there, World!",
    ),
    Case(
        description="ternary alternative",
        template="{{ 'Hello' if not you else 'Hello there, ${you}!' }}",
        context={"you": "World"},
        expect="Hello there, World!",
    ),
    Case(
        description="infix expression, left",
        template="{% if 'Hello, ${you}' == 'Hello, World' %}true{% endif %}",
        context={"you": "World"},
        expect="true",
    ),
    Case(
        description="infix expression, right",
        template="{% if 'Hello, World' == 'Hello, ${you}' %}true{% endif %}",
        context={"you": "World"},
        expect="true",
    ),
    Case(
        description="output, escaped",
        template=r"{{ 'Hello, \${you}!' }}",
        context={"you": "World"},
        expect="Hello, ${you}!",
    ),
    Case(
        description="output, nested",
        template="{{ 'Hello, ${you | append: '${something}'}!' }}",
        context={"you": "World", "something": " and Liquid"},
        expect="Hello, World and Liquid!",
    ),
]


@pytest.mark.parametrize("case", TEST_CASES, ids=operator.attrgetter("description"))
def test_filter_auto_escape(case: Case) -> None:
    async def coro() -> str:
        return await render_async(case.template, **case.context)

    assert render(case.template, **case.context) == case.expect
    assert asyncio.run(coro()) == case.expect
