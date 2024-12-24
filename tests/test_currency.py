import pytest
from babel import UnknownLocaleError

from liquid2 import Environment
from liquid2 import render
from liquid2.builtin import Currency


def test_default_currency_code_and_locale() -> None:
    assert render("{{ 1.99 | currency }}") == "$1.99"


def test_set_default_currency_code() -> None:
    env = Environment()
    env.filters["currency"] = Currency(default_currency_code="GBP")
    assert env.from_string("{{ 1.99 | currency }}").render() == "£1.99"


def test_currency_code_from_context() -> None:
    assert render("{{ 1.99 | currency }}", currency_code="GBP") == "£1.99"


def test_prefix_unknown_currency_code() -> None:
    assert (
        render("{{ 1.99 | currency }}", currency_code="nosuchthing")
        == "nosuchthing1.99"
    )


def test_set_default_locale() -> None:
    env = Environment()
    env.filters["currency"] = Currency(default_locale="de")
    assert env.from_string("{{ 1.99 | currency }}").render() == "1,99\xa0$"


def test_locale_from_context() -> None:
    assert render("{{ 1.99 | currency }}", locale="de") == "1,99\xa0$"


def test_unknown_default_locale() -> None:
    env = Environment()
    with pytest.raises(UnknownLocaleError):
        env.filters["currency"] = Currency(default_locale="nosuchthing")


def test_unknown_locale_from_context() -> None:
    # Falls back to default
    assert render("{{ 1.99 | currency }}", locale="nosuchthing") == "$1.99"
