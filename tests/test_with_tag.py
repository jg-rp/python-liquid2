import asyncio

from liquid2 import render
from liquid2 import render_async


def test_block_scoped_literal() -> None:
    source = "{{ x }}{% with x: 'foo' %}{{ x }}{% endwith %}{{ x }}"
    want = "foo"

    async def coro() -> str:
        return await render_async(source)

    assert render(source) == want
    assert asyncio.run(coro()) == want


def test_block_scoped_variable() -> None:
    source = (
        r"{% with p: collection.products.first %}"
        r"{{ p.title }}"
        r"{% endwith %}"
        r"{{ p.title }}"
        r"{{ collection.products.first.title }}"
    )

    want = "A ShoeA Shoe"
    data = {"collection": {"products": [{"title": "A Shoe"}]}}

    async def coro() -> str:
        return await render_async(source, **data)

    assert render(source, **data) == want
    assert asyncio.run(coro()) == want


def test_argument_list() -> None:
    source = (
        r"{% with a: 1, b: 3.4 %}"
        r"{{ a }} + {{ b }} = {{ a | plus: b }}"
        r"{% endwith %}"
    )

    want = "1 + 3.4 = 4.4"

    async def coro() -> str:
        return await render_async(source)

    assert render(source) == want
    assert asyncio.run(coro()) == want
