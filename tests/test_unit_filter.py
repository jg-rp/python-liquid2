from liquid2 import Environment
from liquid2 import render
from liquid2.builtin import Unit


def test_defaults() -> None:
    assert render("{{ 12 | unit: 'length-meter' }}") == "12 meters"


def test_set_default_locale() -> None:
    env = Environment()
    env.filters["unit"] = Unit(default_locale="de")
    assert env.from_string("{{ 12 | unit: 'length-meter' }}").render() == "12 Meter"


def test_get_locale_from_context() -> None:
    assert render("{{ 12 | unit: 'length-meter' }}", locale="de") == "12 Meter"
