"""Test that we can pass a render context to template loaders."""

from liquid2 import DictLoader
from liquid2 import Environment
from liquid2 import RenderContext
from liquid2.builtin.loaders.mixins import CachingLoaderMixin
from liquid2.loader import TemplateSource


class MockContextLoader(CachingLoaderMixin, DictLoader):
    def __init__(
        self,
        templates: dict[str, str],
        *,
        auto_reload: bool = True,
        namespace_key: str = "",
        capacity: int = 300,
    ):
        super().__init__(
            auto_reload=auto_reload,
            namespace_key=namespace_key,
            capacity=capacity,
        )

        DictLoader.__init__(self, templates)
        self.args: dict[str, object] = {}

    def get_source(
        self,
        env: Environment,
        template_name: str,
        *,
        context: RenderContext | None = None,
        **kwargs: object,
    ) -> TemplateSource:
        """Return template source info."""
        self.args.update(kwargs)
        if context:
            self.args["uid"] = context.resolve("uid")
        return super().get_source(env, template_name)

    async def get_source_async(
        self,
        env: Environment,
        template_name: str,
        *,
        context: RenderContext | None = None,
        **kwargs: object,
    ) -> TemplateSource:
        """Return template source info."""
        self.args.update(kwargs)
        if context:
            self.args["uid"] = context.resolve("uid")
        return await super().get_source_async(env, template_name)


def test_load_with_kwargs() -> None:
    loader = MockContextLoader({"snippet": "Hello, {{ you }}!"}, namespace_key="tag")
    env = Environment(loader=loader)
    template = env.from_string("{% include 'snippet' %}")
    template.render()
    assert "tag" in loader.args
    assert loader.args["tag"] == "include"
    assert "include/snippet" in loader.cache


def test_load_with_context() -> None:
    loader = MockContextLoader({"snippet": "Hello, {{ you }}!"}, namespace_key="uid")
    env = Environment(loader=loader)
    template = env.from_string("{% include 'snippet' %}", globals={"uid": 1234})
    template.render()
    assert "uid" in loader.args
    assert loader.args["uid"] == 1234
    assert "1234/snippet" in loader.cache
