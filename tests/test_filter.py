"""Test filter decorators and argument helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from liquid2 import Environment
from liquid2 import Token
from liquid2 import TokenType
from liquid2.exceptions import LiquidTypeError
from liquid2.filter import int_arg
from liquid2.filter import with_context
from liquid2.query import word_to_query

if TYPE_CHECKING:
    from liquid2.context import RenderContext


@with_context
def mock_filter(val: str, arg: str, *, context: RenderContext) -> str:
    """Mock filter function making use of `with_context`."""
    dummy_token = Token(type_=TokenType.WORD, value=arg, index=-1, source="")
    query = word_to_query(dummy_token)
    return val + str(context.get(query, token=dummy_token))


def test_with_context() -> None:
    env = Environment()
    env.filters["mock"] = mock_filter
    template = env.from_string(r"{{ 'Hello, ' | mock: 'you' }}!")
    assert template.render(you="World") == "Hello, World!"


def test_int_arg_sting_value_error() -> None:
    with pytest.raises(LiquidTypeError):
        int_arg("foo")


def test_int_arg_sting_value_error_with_default() -> None:
    assert int_arg("foo", default=42) == 42  # noqa: PLR2004


# TODO: more tests following implicit conversion rules
# TODO: undefined args