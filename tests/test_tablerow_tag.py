"""Test the tablerow tag using cases from CTS extra."""

import asyncio
import json
import operator
from dataclasses import dataclass
from dataclasses import field
from typing import Any

import pytest

from liquid2.builtin import DictLoader
from liquid2.exceptions import LiquidError
from liquid2.shopify import Environment


@dataclass
class Case:
    """Test helper class."""

    name: str
    template: str
    data: dict[str, Any] = field(default_factory=dict)
    templates: dict[str, str] | None = None
    result: str | None = None
    invalid: bool | None = None
    tags: list[str] = field(default_factory=list)


FILENAME = "tests/liquid2-compliance-test-suite/extra/tablerow.json"


def cases() -> list[Case]:
    with open(FILENAME, encoding="utf8") as fd:
        data = json.load(fd)
    return [Case(**case) for case in data["tests"]]


def valid_cases() -> list[Case]:
    return [case for case in cases() if not case.invalid]


def invalid_cases() -> list[Case]:
    return [case for case in cases() if case.invalid]


@pytest.mark.parametrize("case", valid_cases(), ids=operator.attrgetter("name"))
def test_tablerow(case: Case) -> None:
    env = Environment(loader=DictLoader(case.templates or {}))
    assert env.from_string(case.template).render(**case.data) == case.result


@pytest.mark.parametrize("case", valid_cases(), ids=operator.attrgetter("name"))
def test_tablerow_async(case: Case) -> None:
    env = Environment(loader=DictLoader(case.templates or {}))
    template = env.from_string(case.template)

    async def coro() -> str:
        return await template.render_async(**case.data)

    assert asyncio.run(coro()) == case.result


@pytest.mark.parametrize("case", invalid_cases(), ids=operator.attrgetter("name"))
def test_invalid_tablerow(case: Case) -> None:
    env = Environment(loader=DictLoader(case.templates or {}))
    with pytest.raises(LiquidError):
        env.from_string(case.template).render(**case.data)


@pytest.mark.parametrize("case", invalid_cases(), ids=operator.attrgetter("name"))
def test_invalid_tablerow_async(case: Case) -> None:
    env = Environment(loader=DictLoader(case.templates or {}))

    async def coro() -> str:
        template = env.from_string(case.template)
        return await template.render_async(**case.data)

    with pytest.raises(LiquidError):
        asyncio.run(coro())
