from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import is_dataclass
from typing import Any

import pytest

from liquid2 import Environment
from liquid2 import render
from liquid2.builtin import JSON
from liquid2.exceptions import LiquidTypeError


def test_jsonify_string_literal() -> None:
    assert render("{{ 'hello' | json }}") == '"hello"'


def test_jsonify_int_literal() -> None:
    assert render("{{ 42 | json }}") == "42"


def test_jsonify_dict_and_list() -> None:
    assert render("{{ foo | json }}", foo={"foo": [1, 2, 3]}) == '{"foo": [1, 2, 3]}'


def test_jsonify_arbitrary_object() -> None:
    with pytest.raises(LiquidTypeError):
        render("{{ foo | json }}", foo=object())


def test_jsonify_with_indent() -> None:
    assert (
        render("{{ foo | json: 4}}", foo={"foo": [1, 2, 3]})
        == '{\n    "foo": [\n        1,\n        2,\n        3\n    ]\n}'
    )


@dataclass
class _MockData:
    length: int
    width: int


def _mock_json_default(obj: object) -> Any:
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    raise TypeError(f"can't serialize object {obj}")


def test_jsonify_with_custom_encoder() -> None:
    with pytest.raises(LiquidTypeError):
        render("{{ foo | json }}", foo=_MockData(3, 4))

    env = Environment()
    env.filters["json"] = JSON(default=_mock_json_default)

    assert (
        env.from_string("{{ foo | json }}").render(foo=_MockData(3, 4))
        == '{"length": 3, "width": 4}'
    )
