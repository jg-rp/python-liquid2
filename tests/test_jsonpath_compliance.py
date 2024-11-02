"""Test JSONPath against the JSONPath Compliance Test Suite."""

import json
import operator
from dataclasses import dataclass
from dataclasses import field
from typing import Any

import pytest

from liquid2.exceptions import LiquidExtensionError
from liquid2.exceptions import LiquidNameError
from liquid2.exceptions import LiquidSyntaxError as _LiquidSyntaxError
from liquid2.exceptions import LiquidTypeError as _LiquidTypeError
from liquid2.query import JSONValue
from liquid2.query import parse_query


@dataclass
class Case:
    """Test case helper."""

    name: str
    selector: str
    document: JSONValue = None
    result: Any = None
    results: list[Any] | None = None
    invalid_selector: bool | None = None
    tags: list[str] = field(default_factory=list)


SKIP: dict[str, str] = {}

FILENAME = "python/tests/jsonpath-compliance-test-suite/cts.json"


def cases() -> list[Case]:
    with open(FILENAME, encoding="utf8") as fd:
        data = json.load(fd)
    return [Case(**case) for case in data["tests"]]


def valid_cases() -> list[Case]:
    return [case for case in cases() if not case.invalid_selector]


def invalid_cases() -> list[Case]:
    return [case for case in cases() if case.invalid_selector]


@pytest.mark.parametrize("case", valid_cases(), ids=operator.attrgetter("name"))
def test_compliance(case: Case) -> None:
    if case.name in SKIP:
        pytest.skip(reason=SKIP[case.name])  # no cov

    assert case.document is not None
    rv = find(case.selector, case.document).values()

    if case.results is not None:
        assert rv in case.results
    else:
        assert rv == case.result


@pytest.mark.parametrize("case", invalid_cases(), ids=operator.attrgetter("name"))
def test_invalid_selectors(case: Case) -> None:
    if case.name in SKIP:
        pytest.skip(reason=SKIP[case.name])  # no cov

    with pytest.raises(
        (LiquidExtensionError, LiquidNameError, _LiquidSyntaxError, _LiquidTypeError)
    ):
        compile(parse_query(case.selector))
