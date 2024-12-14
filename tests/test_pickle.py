import asyncio
import pickle

from liquid2 import Environment
from liquid2 import FileSystemLoader


def test_pickle_template() -> None:
    env = Environment(loader=FileSystemLoader("tests/fixtures/001/"))
    template = env.get_template("main.html")
    pickle.dumps(template)

    async def coro() -> None:
        template = await env.get_template_async("main.html")
        pickle.dumps(template)

    asyncio.run(coro())
