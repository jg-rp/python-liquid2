import pytest

from liquid2 import Environment
from liquid2 import parse


def test_suppress_empty_if_block() -> None:
    template = parse("!{% if true %}\n \t\r{% endif %}!")
    assert template.render() == "!!"


def test_suppress_empty_else_block() -> None:
    template = parse("!{% if false %}foo{% else %}\n \r\t{% endif %}!")
    assert template.render() == "!!"


def test_suppress_empty_unless_block() -> None:
    template = parse("!{% unless false %}\n \t\r{% endunless %}!")
    assert template.render() == "!!"


def test_suppress_empty_case_block() -> None:
    template = parse("!{% assign x = 1 %}{% case x %}{% when 1 %}\n \t\r{% endcase %}!")
    assert template.render() == "!!"


def test_suppress_empty_for_block() -> None:
    template = parse("!{% for x in (1..3) %}\n \t\r{% endfor %}!")
    assert template.render() == "!!"


class MockEnvironment(Environment):
    suppress_blank_control_flow_blocks = False


@pytest.fixture
def env() -> Environment:
    return MockEnvironment()


def test_output_empty_if_block(env: Environment) -> None:
    template = env.from_string("!{% if true %}\n \t\r{% endif %}!")
    assert template.render() == "!\n \t\r!"


def test_output_empty_else_block(env: Environment) -> None:
    template = env.from_string("!{% if false %}foo{% else %}\n \r\t{% endif %}!")
    assert template.render() == "!\n \r\t!"


def test_output_empty_unless_block(env: Environment) -> None:
    template = env.from_string("!{% unless false %}\n \t\r{% endunless %}!")
    assert template.render() == "!\n \t\r!"


def test_output_empty_case_block(env: Environment) -> None:
    template = env.from_string(
        "!{% assign x = 1 %}{% case x %}{% when 1 %}\n \t\r{% endcase %}!"
    )
    assert template.render() == "!\n \t\r!"


def test_output_empty_for_block(env: Environment) -> None:
    template = env.from_string("!{% for x in (1..3) %}\n{% endfor %}!")
    assert template.render() == "!\n\n\n!"


def test_old_issue127_example(env: Environment) -> None:
    # This is issue #127 from Python Liquid version 1
    template = env.from_string(
        "{% for x in (1..3) %}{{ x }}"
        "{% unless forloop.last %}\n{% endunless %}{% endfor %}"
    )
    assert template.render() == "1\n2\n3"
