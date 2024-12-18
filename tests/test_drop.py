import operator
from typing import Generic
from typing import NamedTuple
from typing import TypeVar

import pytest

from liquid2 import parse

T = TypeVar("T")


class Case(NamedTuple):
    description: str
    template: str
    context: dict[str, object]
    expect: str


class MockDrop(Generic[T]):
    """Generic drop that wraps a primitive value."""

    def __init__(self, val: T):
        self.val = val

    def __liquid__(self) -> T:
        return self.val

    def __str__(self) -> str:
        return str(self.val)


class MockIntDrop:
    """Mock drop that wraps an integer value."""

    def __init__(self, val: int):
        self.val = val

    def __int__(self) -> int:
        return self.val

    def __str__(self) -> str:
        return "one"

    def __liquid__(self) -> int:
        return int(self)


class MockConfusedDrop:
    def __init__(self, val: bool):  # noqa: FBT001
        self.val = val

    def __liquid__(self) -> bool:
        return self.val

    def __str__(self) -> str:
        return "yay" if self.val else "nay"


test_cases = [
    Case(
        description="int drop",
        template=r"{{ drop }}",
        context={"drop": MockIntDrop(1)},
        expect="one",
    ),
    Case(
        description="int drop as array index",
        template=r"{{ foo[drop] }}",
        context={"foo": ["a", "b", "c"], "drop": MockIntDrop(1)},
        expect="b",
    ),
    Case(
        description="int drop as hash key",
        template=r"{{ foo[drop] }}",
        context={"foo": {1: "a", 2: "b"}, "drop": MockIntDrop(1)},
        expect="a",
    ),
    Case(
        description="int drop as filter left value",
        template=r"{{ drop | plus: 1 }}",
        context={"drop": MockIntDrop(1)},
        expect="1",
    ),
    Case(
        description="int drop in boolean expression",
        template=r"{% if drop == 1 %}one{% endif %}",
        context={"drop": MockIntDrop(1)},
        expect="one",
    ),
    Case(
        description="int drop is less than int drop",
        template=r"{% if some < other %}hello{% endif %}",
        context={"some": MockIntDrop(1), "other": MockIntDrop(2)},
        expect="hello",
    ),
    Case(
        description="int drop in case expression",
        template=r"{% case drop %}{% when 1 %}one{% endcase %}",
        context={"drop": MockIntDrop(1)},
        expect="one",
    ),
    Case(
        description="boolean drop",
        template=r"{{ drop }}",
        context={"drop": MockDrop[bool](False)},
        expect="False",
    ),
    Case(
        description="bool drop in boolean expression",
        template=r"{% if drop == true %}one{% endif %}",
        context={"drop": MockDrop[bool](True)},
        expect="one",
    ),
    Case(
        description="false bool drop in boolean expression",
        template=r"{% if drop == true %}one{% endif %}",
        context={"drop": MockDrop[bool](False)},
        expect="",
    ),
    Case(
        description="false bool drop is False",
        template=r"{% if drop %}one{% endif %}",
        context={"drop": MockDrop[bool](False)},
        expect="",
    ),
    Case(
        description="bool drop in unless expression",
        template=r"{% unless drop %}hello{% endunless %}",
        context={"drop": MockDrop[bool](True)},
        expect="",
    ),
    Case(
        description="confused drop",
        template=r"{{ drop }}",
        context={"drop": MockConfusedDrop(False)},
        expect="nay",
    ),
    Case(
        description="filtered confused drop",
        template=r"{{ drop | upcase }}",
        context={"drop": MockConfusedDrop(False)},
        expect="NAY",
    ),
    Case(
        description="compare confused drop",
        template=r"{% if drop %}{{ drop | upcase }}{% endif %}",
        context={"drop": MockConfusedDrop(False)},
        expect="",
    ),
]


@pytest.mark.parametrize("case", test_cases, ids=operator.attrgetter("description"))
def test_drop(case: Case) -> None:
    template = parse(case.template)
    result = template.render(**case.context)
    assert result == case.expect
