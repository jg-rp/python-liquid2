"""Test the basic API."""

from liquid2 import DEFAULT_ENVIRONMENT
from liquid2 import DictLoader
from liquid2 import Environment
from liquid2 import Template
from liquid2 import parse


def test_parse_from_string() -> None:
    template = parse("Hello, {{ you }}!")
    assert isinstance(template, Template)
    result = template.render(you="World")
    assert result == "Hello, World!"


def test_parse_from_string_with_global_data() -> None:
    template = parse("Hello, {{ you }}!", globals={"you": "World"})
    result = template.render()
    assert result == "Hello, World!"


def test_parse_from_string_using_default_environment() -> None:
    template = DEFAULT_ENVIRONMENT.from_string("Hello, {{ you }}!")
    assert isinstance(template, Template)
    result = template.render(you="World")
    assert result == "Hello, World!"


def test_parse_from_string_using_custom_environment() -> None:
    env = Environment()
    template = env.from_string("Hello, {{ you }}!")
    assert isinstance(template, Template)
    result = template.render(you="World")
    assert result == "Hello, World!"


def test_environment_loader() -> None:
    env = Environment(loader=DictLoader({"index": "Hello, {{ you }}!"}))
    template = env.from_string("{% render 'index' %}")
    assert isinstance(template, Template)
    result = template.render(you="World")
    assert result == "Hello, World!"


def test_load_template() -> None:
    env = Environment(
        loader=DictLoader(
            {
                "layout": "{% include 'index' %}",
                "index": "Hello, {{ you }}!",
            }
        )
    )

    template = env.get_template("layout")
    assert isinstance(template, Template)
    result = template.render(you="World")
    assert result == "Hello, World!"


def test_environment_globals() -> None:
    env = Environment(
        loader=DictLoader({"index": "Hello, {{ you }}!"}),
        globals={"you": "World"},
    )

    template = env.from_string("{% render 'index' %}")
    assert isinstance(template, Template)
    result = template.render()
    assert result == "Hello, World!"


def test_template_globals_take_priority_over_environment_globals() -> None:
    env = Environment(
        loader=DictLoader({"index": "Hello, {{ you }}!"}),
        globals={"you": "World"},
    )

    template = env.from_string(
        "{% render 'index' %}",
        globals={"you": "there"},
    )

    assert isinstance(template, Template)
    result = template.render()
    assert result == "Hello, there!"
