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


def test_escaped_single_quote() -> None:
    data = {"a": {"'": "b"}}
    assert render("{{ a['\\''] }}", **data) == "b"


def test_escaped_reverse_solidus() -> None:
    data = {"a": {"\\": "b"}}
    assert render("{{ a['\\\\'] }}", **data) == "b"


def test_escaped_solidus() -> None:
    data = {"a": {"/": "b"}}
    assert render("{{ a['\\/'] }}", **data) == "b"


def test_escaped_backspace() -> None:
    data = {"a": {"\u0008": "b"}}
    assert render("{{ a['\\b'] }}", **data) == "b"


def test_escaped_line_feed() -> None:
    data = {"a": {"\n": "b"}}
    assert render("{{ a['\\n'] }}", **data) == "b"


def test_escaped_carriage_return() -> None:
    data = {"a": {"\r": "b"}}
    assert render("{{ a['\\r'] }}", **data) == "b"


def test_escaped_tab() -> None:
    data = {"a": {"\t": "b"}}
    assert render("{{ a['\\t'] }}", **data) == "b"


def test_escaped_form_feed() -> None:
    data = {"a": {"\u000c": "b"}}
    assert render("{{ a['\\f'] }}", **data) == "b"


def test_unescape_form_feed() -> None:
    data = {"a": {"\f": "b"}}
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


def test_unknown_escape_sequence() -> None:
    with pytest.raises(LiquidSyntaxError):
        parse(r"{{ a['\xc'] }}")


def test_incomplete_escape() -> None:
    with pytest.raises(LiquidSyntaxError):
        parse(r"{{ a['\'] }}")


def test_incomplete_code_point() -> None:
    with pytest.raises(LiquidSyntaxError):
        parse(r"{{ a['\u263'] }}")


def test_incomplete_surrogate_pair() -> None:
    with pytest.raises(LiquidSyntaxError):
        parse(r"{{ a['\uD83D\uDE0'] }}")


def test_two_high_surrogates() -> None:
    with pytest.raises(LiquidSyntaxError):
        parse(r"{{ a['\uD800\uD800'] }}")


def test_high_surrogate_followed_by_non_surrogate() -> None:
    with pytest.raises(LiquidSyntaxError):
        parse(r"{{ a['\uD800\u263Ac'] }}")


def test_just_a_low_surrogate() -> None:
    with pytest.raises(LiquidSyntaxError):
        parse(r"{{ a['ab\uDC00c'] }}")


def test_non_hex_digits_code_point() -> None:
    with pytest.raises(LiquidSyntaxError):
        parse(r"{{ a['ab\u263Xc'] }}")
