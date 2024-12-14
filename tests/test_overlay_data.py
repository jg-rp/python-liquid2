"""Test that template loaders can add to render context globals."""

from liquid2 import DictLoader
from liquid2 import Environment
from liquid2 import RenderContext
from liquid2 import TemplateNotFound
from liquid2.loader import TemplateSource


class MockFrontMatterLoader(DictLoader):
    def __init__(
        self,
        templates: dict[str, str],
        matter: dict[str, dict[str, object]],
    ):
        super().__init__(templates)
        self.matter = matter

    def get_source(
        self,
        env: Environment,  # noqa: ARG002
        template_name: str,
        *,
        context: RenderContext | None = None,  # noqa: ARG002
        **kwargs: object,  # noqa: ARG002
    ) -> TemplateSource:
        """Return template source info."""
        try:
            source = self.templates[template_name]
        except KeyError as err:
            raise TemplateNotFound(template_name) from err

        return TemplateSource(
            source=source,
            name=template_name,
            uptodate=None,
            matter=self.matter.get(template_name),
        )


def test_front_matter_loader() -> None:
    loader = MockFrontMatterLoader(
        templates={
            "some": "Hello, {{ you }}{{ username }}!",
            "other": "Goodbye, {{ you }}{{ username }}.",
            "thing": "{{ you }}{{ username }}",
        },
        matter={
            "some": {"you": "World"},
            "other": {"username": "Smith"},
        },
    )

    env = Environment(loader=loader)
    template = env.get_template("some")
    assert template.render() == "Hello, World!"

    template = env.get_template("other")
    assert template.render() == "Goodbye, Smith."

    template = env.get_template("thing")
    assert template.render() == ""


def test_overlay_data_takes_priority_over_globals() -> None:
    loader = MockFrontMatterLoader(
        templates={"some": "Hello, {{ you }}{{ username }}!"},
        matter={"some": {"you": "World"}},
    )

    env = Environment(loader=loader, globals={"you": "Liquid"})
    template = env.get_template("some", globals={"you": "Jinja"})
    assert template.render() == "Hello, World!"


def test_render_args_take_priority_over_overlay_data() -> None:
    loader = MockFrontMatterLoader(
        templates={"some": "Hello, {{ you }}{{ username }}!"},
        matter={"some": {"you": "World"}},
    )

    env = Environment(loader=loader)
    template = env.get_template("some")
    assert template.render(you="Liquid") == "Hello, Liquid!"
