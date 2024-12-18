from typing import Iterator

from liquid2 import Node
from liquid2 import RenderContext
from liquid2 import Template
from liquid2 import parse
from liquid2.builtin.comment import CommentNode


def _find_comment_nodes(template: Template) -> Iterator[CommentNode]:
    context = RenderContext(template)

    def _visit(node: Node) -> Iterator[CommentNode]:
        if isinstance(node, CommentNode):
            yield node
        for child in node.children(context, include_partials=False):
            yield from _visit(child)

    for node in template.nodes:
        yield from _visit(node)


def test_find_block_comment_text() -> None:
    template = parse(
        "\n".join(
            (
                "{% comment %}hello{% endcomment %}",
                "{% if false %}",
                "{% comment %}",
                "foo bar",
                "{% endcomment %}",
                "{% endif %}",
                "{% for x in (1..3) %}",
                "{% if true %}",
                "{% comment %}goodbye{% endcomment %}",
                "{% endif %}",
                "{% endfor %}",
                "{% comment %}world{% endcomment %}",
            )
        )
    )

    nodes = list(_find_comment_nodes(template))
    assert len(nodes) == 4
    text = [node.text for node in nodes]
    assert text == ["hello", "\nfoo bar\n", "goodbye", "world"]


def test_find_inline_comment_text() -> None:
    template = parse(
        "\n".join(
            (
                "{% # hello %}",
                "{% if false %}",
                "{% #",
                "# foo bar",
                "# foo bar",
                "%}",
                "{% endif %}",
                "{% for x in (1..3) %}",
                "{% if true %}",
                "{% # goodbye %}",
                "{% endif %}",
                "{% endfor %}",
                "{% # world %}",
            )
        )
    )

    nodes = list(_find_comment_nodes(template))
    assert len(nodes) == 4
    text = [node.text for node in nodes]
    assert text == [" hello ", "\n# foo bar\n# foo bar\n", " goodbye ", " world "]
