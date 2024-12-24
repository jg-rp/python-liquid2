import datetime

import pytest
import pytz
from babel import UnknownLocaleError

from liquid2 import Environment
from liquid2 import render
from liquid2.builtin import DateTime

DT = dt = datetime.datetime(2007, 4, 1, 15, 30)


def test_default_options() -> None:
    assert (
        render("{{ dt | datetime }}", dt=DT)
        == "Apr 1, 2007, 3:30:00\N{NARROW NO-BREAK SPACE}PM"
    )


def test_short_format() -> None:
    assert (
        render("{{ dt | datetime: format='short' }}", dt=DT)
        == "4/1/07, 3:30\N{NARROW NO-BREAK SPACE}PM"
    )


def test_medium_format() -> None:
    assert (
        render("{{ dt | datetime: format='medium' }}", dt=DT)
        == "Apr 1, 2007, 3:30:00\N{NARROW NO-BREAK SPACE}PM"
    )


def test_long_format() -> None:
    assert (
        render("{{ dt | datetime: format='long' }}", dt=DT)
        == "April 1, 2007, 3:30:00\N{NARROW NO-BREAK SPACE}PM UTC"
    )


def test_full_format() -> None:
    assert (
        render("{{ dt | datetime: format='full' }}", dt=DT)
        == "Sunday, April 1, 2007, 3:30:00\N{NARROW NO-BREAK SPACE}PM Coordinated Universal Time"  # noqa: E501
    )


def test_custom_format() -> None:
    assert (
        render("{{ dt | datetime: format: 'EEEE, d.M.yyyy' }}", dt=DT)
        == "Sunday, 1.4.2007"
    )


def test_format_from_context() -> None:
    assert (
        render("{{ dt | datetime }}", dt=DT, datetime_format="EEEE, d.M.yyyy")
        == "Sunday, 1.4.2007"
    )


def test_set_default_timezone() -> None:
    env = Environment()
    # Choose a static timezone so tests wont fail as we go in and out of daylight
    # saving. Etc/GMT reverses the meaning of '+' and '-' compared to UTC or GMT.
    env.filters["datetime"] = DateTime(default_timezone="Etc/GMT-1")
    assert (
        env.from_string("{{ dt | datetime }}").render(dt=DT)
        == "Apr 1, 2007, 4:30:00\N{NARROW NO-BREAK SPACE}PM"
    )


def test_get_timezone_from_context() -> None:
    assert (
        render("{{ dt | datetime }}", dt=DT, timezone="Etc/GMT-1")
        == "Apr 1, 2007, 4:30:00\N{NARROW NO-BREAK SPACE}PM"
    )


def test_unknown_timezone_falls_back_to_default() -> None:
    assert (
        render("{{ dt | datetime }}", dt=DT, timezone="foo")
        == "Apr 1, 2007, 3:30:00\N{NARROW NO-BREAK SPACE}PM"
    )


def test_unknown_default_timezone() -> None:
    env = Environment()
    with pytest.raises(pytz.UnknownTimeZoneError):
        env.filters["datetime"] = DateTime(default_timezone="foo")


def test_set_default_locale() -> None:
    env = Environment()
    env.filters["datetime"] = DateTime(default_locale="en_GB")
    assert (
        env.from_string("{{ dt | datetime }}").render(dt=DT) == "1 Apr 2007, 15:30:00"
    )


def test_get_locale_from_context() -> None:
    assert (
        render("{{ dt | datetime }}", dt=DT, locale="en_GB") == "1 Apr 2007, 15:30:00"
    )


def test_unknown_default_locale() -> None:
    env = Environment()
    with pytest.raises(UnknownLocaleError):
        env.filters["datetime"] = DateTime(default_locale="nosuchthing")


def test_unknown_locale_falls_back_to_default() -> None:
    assert (
        render("{{ dt | datetime }}", dt=DT, locale="nosuchthing")
        == "Apr 1, 2007, 3:30:00\N{NARROW NO-BREAK SPACE}PM"
    )
