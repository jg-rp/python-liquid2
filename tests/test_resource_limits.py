import platform

import pytest

from liquid2 import DictLoader
from liquid2 import Environment
from liquid2.exceptions import ContextDepthError
from liquid2.exceptions import LocalNamespaceLimitError
from liquid2.exceptions import LoopIterationLimitError
from liquid2.exceptions import OutputStreamLimitError


def test_recursive_render() -> None:
    env = Environment(
        loader=DictLoader(
            {
                "foo": "{% render 'bar' %}",
                "bar": "{% render 'foo' %}",
            }
        )
    )

    template = env.from_string("{% render 'foo' %}")
    with pytest.raises(ContextDepthError):
        template.render()


def test_recursive_include() -> None:
    env = Environment(
        loader=DictLoader(
            {
                "foo": "{% include 'bar' %}",
                "bar": "{% include 'foo' %}",
            }
        )
    )

    template = env.from_string("{% include 'foo' %}")
    with pytest.raises(ContextDepthError):
        template.render()


def test_set_context_depth_limit_render() -> None:
    class MockEnvironment(Environment):
        context_depth_limit = 3

    loader = DictLoader(
        {
            "foo": "{% render 'bar' %}",
            "bar": "{% render 'baz' %}",
            "baz": "Hello",
        }
    )

    env = Environment(loader=loader)
    template = env.from_string("{% render 'foo' %}")
    result = template.render()
    assert result == "Hello"

    env = MockEnvironment(loader=loader)
    template = env.from_string("{% render 'foo' %}")
    with pytest.raises(ContextDepthError):
        template.render()


def test_set_context_depth_limit_include() -> None:
    class MockEnvironment(Environment):
        context_depth_limit = 3

    loader = DictLoader(
        {
            "foo": "{% include 'bar' %}",
            "bar": "{% include 'baz' %}",
            "baz": "Hello",
        }
    )

    env = Environment(loader=loader)
    template = env.from_string("{% include 'foo' %}")
    result = template.render()
    assert result == "Hello"

    env = MockEnvironment(loader=loader)
    template = env.from_string("{% include 'foo' %}")
    with pytest.raises(ContextDepthError):
        template.render()


def test_default_loop_iteration_limit_is_reasonably_high() -> None:
    env = Environment()

    template = env.from_string(
        "{% for i in (1..100) %}"
        "{% for j in (1..100) %}"
        "x"
        "{% endfor %}"
        "{% endfor %}"
    )

    template.render()


def test_set_loop_iteration_limit() -> None:
    class MockEnv(Environment):
        loop_iteration_limit = 10000

    env = MockEnv()
    env.from_string(
        "{% for i in (1..100) %}"
        "{% for j in (1..100) %}"
        "{{ i }},{{ j }}"
        "{% endfor %}"
        "{% endfor %}"
    ).render()

    template = env.from_string(
        "{% for i in (1..101) %}"
        "{% for j in (1..100) %}"
        "{{ i }},{{ j }}"
        "{% endfor %}"
        "{% endfor %}"
    )

    with pytest.raises(LoopIterationLimitError):
        template.render()


def test_render_carries_loop_count() -> None:
    class MockEnv(Environment):
        loop_iteration_limit = 3000

    env = MockEnv(
        loader=DictLoader(
            {
                "foo": (
                    "{% for i in (1..50) %}"
                    "{% for j in (1..50) %}"
                    "{{ i }},{{ j }}"
                    "{% endfor %}"
                    "{% endfor %}"
                ),
            }
        )
    )

    template = env.from_string("{% for i in (1..10) %}{% render 'foo' %}{% endfor %}")

    with pytest.raises(LoopIterationLimitError):
        template.render()


def test_nested_renders_carry_loop_count() -> None:
    class MockEnv(Environment):
        loop_iteration_limit = 3000

    env = MockEnv(
        loader=DictLoader(
            {
                "foo": ("{% for i in (1..50) %}{% render 'bar' %}{% endfor %}"),
                "bar": ("{% for j in (1..50) %}{{ j }}{% endfor %}"),
            }
        )
    )

    template = env.from_string("{% for i in (1..10) %}{% render 'foo' %}{% endfor %}")

    with pytest.raises(LoopIterationLimitError):
        template.render()


def test_include_contributes_to_count() -> None:
    class MockEnv(Environment):
        loop_iteration_limit = 3000

    env = MockEnv(
        loader=DictLoader(
            {
                "foo": (
                    "{% for i in (1..50) %}"
                    "{% for j in (1..50) %}"
                    "{{ i }},{{ j }}"
                    "{% endfor %}"
                    "{% endfor %}"
                ),
            }
        )
    )

    template = env.from_string("{% for i in (1..10) %}{% include 'foo' %}{% endfor %}")

    with pytest.raises(LoopIterationLimitError):
        template.render()


# def test_tablerow_contributes_to_count() -> None:
#     class MockEnv(Environment):
#         loop_iteration_limit = 99

#     env = MockEnv()
#     template = env.from_string(
#         "{% for i in (1..10) %}"
#         "{% tablerow i in (1..10) cols:2 %}"
#         "{{ i }}"
#         "{% endtablerow %}"
#         "{% endfor %}"
#     )

#     with pytest.raises(LoopIterationLimitError):
#         template.render()


@pytest.mark.skipif(
    platform.python_implementation() == "PyPy", reason="no sys.getsizeof"
)
def test_set_local_namespace_limit() -> None:
    class MockEnv(Environment):
        local_namespace_limit = 140

    env = MockEnv()
    env.from_string(
        "{% assign a = 1 %}"
        "{% assign b = 2 %}"
        "{% assign c = 3 %}"
        "{% assign d = 4 %}"
        "{% assign e = 5 %}"
    ).render()

    template = env.from_string(
        "{% assign a = 1 %}"
        "{% assign b = 2 %}"
        "{% assign c = 3 %}"
        "{% assign d = 4 %}"
        "{% assign e = 5 %}"
        "{% assign f = 6 %}"
    )

    with pytest.raises(LocalNamespaceLimitError):
        template.render()


@pytest.mark.skipif(
    platform.python_implementation() == "PyPy", reason="no sys.getsizeof"
)
def test_copied_context_carries_parent_length() -> None:
    class MockEnv(Environment):
        local_namespace_limit = 5

    env = MockEnv(
        loader=DictLoader(
            {
                "foo": (
                    "{% assign a = 1 %}"
                    "{% assign b = 2 %}"
                    "{% assign c = 3 %}"
                    "{% assign d = 4 %}"
                    "{% assign e = 5 %}"
                    "{% assign e = 'five' %}"
                )
            }
        )
    )

    template = env.from_string("{% assign f = 6 %}{% render 'foo' %}")

    with pytest.raises(LocalNamespaceLimitError):
        template.render()


def test_sizeof_local_namespace_with_unhashable_values() -> None:
    class MockEnv(Environment):
        local_namespace_limit = 200

    env = MockEnv()
    env.from_string("{% assign foo = bar %}").render(bar=[1, 2, 3, 4])

    env.from_string(
        '{% assign beatles = "John, Paul, George, Ringo" | split: ", " %}'
    ).render()


def test_set_output_stream_limit() -> None:
    class MockEnv(Environment):
        output_stream_limit = 5

    env = MockEnv()
    env.from_string(
        "{% if false %}some literal that is longer then the limit{% endif %}hello"
    ).render()

    template = env.from_string(
        "{% if true %}some literal that is longer then the limit{% endif %}hello"
    )

    with pytest.raises(OutputStreamLimitError):
        template.render()
