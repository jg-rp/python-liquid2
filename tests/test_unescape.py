import pytest

from liquid2 import parse
from liquid2 import render
from liquid2.exceptions import LiquidSyntaxError


def test_unescape_u0020() -> None:
    assert render("{{ '\\u0020' }}") == " "


def test_unescape_code_point() -> None:
    assert render("{{ '\\u263A' }}") == "☺"


def test_unescape_surrogate_pair() -> None:
    assert render("{{ '\\uD834\\uDD1E' }}") == "𝄞"


def test_escaped_double_quote() -> None:
    data = {"a": {'"': "b"}}
    assert render('{{ a["\\""] }}', **data) == "b"


def test_unescape_form_feed() -> None:
    data = {"a": {"\u000c": "b"}}
    assert render("{{ a['\\u000c'] }}", **data) == "b"


def test_escaped_code_point() -> None:
    data = {"a": {"☺": "b"}}
    assert render('{{ a["\\u263A"] }}', **data) == "b"


def test_unicode_identifier() -> None:
    assert render("{% assign ☺ = 'smiley' %}{{ ☺ }}") == "smiley"


def test_escaped_surrogate_pair() -> None:
    data = {"a": {"𝄞": "b"}}
    assert render('{{ a["\\uD834\\uDD1E"] }}', **data) == "b"


def test_escaped_double_quote_in_single_quote_string() -> None:
    with pytest.raises(LiquidSyntaxError):
        parse("{{ a['\\\"'] }}")
