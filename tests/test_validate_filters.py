import pytest

from liquid2 import Environment
from liquid2 import TokenT
from liquid2.builtin import KeywordArgument
from liquid2.builtin import PositionalArgument
from liquid2.exceptions import LiquidSyntaxError
from liquid2.exceptions import UnknownFilterError


def test_unknown_filter_without_validation() -> None:
    env = Environment(validate_filter_arguments=False)
    # No exception at parse time
    template = env.from_string("{{ x | nosuchthing }}")

    with pytest.raises(UnknownFilterError):
        template.render(x="foo")


def test_unknown_filter_with_validation() -> None:
    env = Environment(validate_filter_arguments=True)
    # Exception is raised at parse time
    with pytest.raises(UnknownFilterError):
        env.from_string("{{ x | nosuchthing }}")


class MockInvalidFilter:
    def __call__(self, _left: object) -> str:
        return self.__class__.__name__

    def validate(
        self,
        _env: Environment,
        token: TokenT,
        name: str,
        _args: list[KeywordArgument | PositionalArgument],
    ) -> None:
        raise LiquidSyntaxError(f"{name!r} is invalid", token=token)


def test_invalid_filter_without_validation() -> None:
    env = Environment(validate_filter_arguments=False)
    env.filters["mock"] = MockInvalidFilter()
    template = env.from_string("{{ x | mock }}")
    assert template.render(x="foo") == "MockInvalidFilter"


def test_invalid_filter_with_validation() -> None:
    env = Environment(validate_filter_arguments=True)
    env.filters["mock"] = MockInvalidFilter()

    with pytest.raises(LiquidSyntaxError, match=r"'mock' is invalid"):
        env.from_string("{{ x | mock }}")
