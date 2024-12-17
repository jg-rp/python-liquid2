import asyncio
import tempfile
import time
from pathlib import Path

import pytest

from liquid2 import CachingFileSystemLoader
from liquid2 import Environment
from liquid2 import FileSystemLoader
from liquid2 import Template
from liquid2 import TemplateNotFoundError


def test_load_template() -> None:
    env = Environment(loader=FileSystemLoader("tests/fixtures/001/"))
    template = env.get_template("main.html")
    assert isinstance(template, Template)
    assert template.name == "main.html"
    assert str(template.path) == "tests/fixtures/001/main.html"


def test_load_template_async() -> None:
    env = Environment(loader=FileSystemLoader("tests/fixtures/001/"))

    async def coro() -> Template:
        return await env.get_template_async("main.html")

    template = asyncio.run(coro())
    assert isinstance(template, Template)
    assert template.name == "main.html"
    assert str(template.path) == "tests/fixtures/001/main.html"


def test_template_not_found() -> None:
    env = Environment(loader=FileSystemLoader("tests/fixtures/001/"))
    with pytest.raises(TemplateNotFoundError):
        env.get_template("nosuchthing.html")


def test_template_not_found_async() -> None:
    env = Environment(loader=FileSystemLoader("tests/fixtures/001/"))

    async def coro() -> Template:
        return await env.get_template_async("nosuchthing.html")

    with pytest.raises(TemplateNotFoundError):
        asyncio.run(coro())


def test_no_such_search_path() -> None:
    env = Environment(loader=FileSystemLoader("no/such/thing/"))
    with pytest.raises(TemplateNotFoundError):
        env.get_template("main.html")


def test_list_of_search_paths() -> None:
    env = Environment(
        loader=FileSystemLoader(
            [
                "tests/fixtures/001/",
                "tests/fixtures/001/snippets",
            ]
        )
    )

    template = env.get_template("main.html")
    assert isinstance(template, Template)
    assert template.name == "main.html"
    assert str(template.path) == "tests/fixtures/001/main.html"

    template = env.get_template("featured_content.html")
    assert isinstance(template, Template)
    assert template.name == "featured_content.html"
    assert str(template.path) == "tests/fixtures/001/snippets/featured_content.html"


def test_default_file_extension() -> None:
    env = Environment(loader=FileSystemLoader("tests/fixtures/001/"))
    template = env.get_template("main.html")
    assert isinstance(template, Template)
    assert template.name == "main.html"
    assert str(template.path) == "tests/fixtures/001/main.html"

    with pytest.raises(TemplateNotFoundError):
        env.get_template("main")


def test_set_default_file_extension() -> None:
    env = Environment(loader=FileSystemLoader("tests/fixtures/001/", ext=".html"))
    template = env.get_template("main.html")
    assert isinstance(template, Template)
    assert template.name == "main.html"
    assert str(template.path) == "tests/fixtures/001/main.html"

    template = env.get_template("main")
    assert isinstance(template, Template)
    assert template.name == "main.html"
    assert str(template.path) == "tests/fixtures/001/main.html"


def test_stay_in_search_path() -> None:
    env = Environment(loader=FileSystemLoader("tests/fixtures/001/snippets"))
    with pytest.raises(TemplateNotFoundError):
        env.get_template("../main.html")


def test_dont_cache_templates() -> None:
    env = Environment(loader=FileSystemLoader("tests/fixtures/001/"))
    template = env.get_template("main.html")
    assert isinstance(template, Template)
    assert template.name == "main.html"
    assert str(template.path) == "tests/fixtures/001/main.html"
    assert template.is_up_to_date() is True

    another_template = env.get_template("main.html")
    assert template is not another_template


def test_cache_templates() -> None:
    env = Environment(loader=CachingFileSystemLoader("tests/fixtures/001/"))
    template = env.get_template("main.html")
    assert isinstance(template, Template)
    assert template.name == "main.html"
    assert str(template.path) == "tests/fixtures/001/main.html"
    assert template.is_up_to_date() is True

    another_template = env.get_template("main.html")
    assert template is another_template


def test_auto_reload_cached_templates() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "some.txt"

        # Write some content to temporary file
        with path.open("w", encoding="UTF-8") as fd:
            fd.write("Hello, {{ you }}!")

        env = Environment(loader=CachingFileSystemLoader(tmp))
        template = env.get_template("some.txt")
        assert template.is_up_to_date()

        same_template = env.get_template("some.txt")
        assert same_template.is_up_to_date()
        assert same_template is template

        # Update template source
        time.sleep(0.01)
        path.touch()

        assert template.is_up_to_date() is False
        updated_template = env.get_template("some.txt")
        assert updated_template is not template


def test_auto_reload_cached_templates_async() -> None:
    async def coro() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "some.txt"

            # Write some content to temporary file
            with path.open("w", encoding="UTF-8") as fd:
                fd.write("Hello, {{ you }}!")

            env = Environment(loader=CachingFileSystemLoader(tmp))
            template = await env.get_template_async("some.txt")
            assert await template.is_up_to_date_async()

            same_template = await env.get_template_async("some.txt")
            assert await same_template.is_up_to_date_async()
            assert same_template is template

            # Update template source
            time.sleep(0.01)
            path.touch()

            assert await template.is_up_to_date_async() is False
            updated_template = await env.get_template_async("some.txt")
            assert updated_template is not template

    asyncio.run(coro())


def test_dont_auto_reload_cached_templates() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "some.txt"

        # Write some content to temporary file
        with path.open("w", encoding="UTF-8") as fd:
            fd.write("Hello, {{ you }}!")

        env = Environment(loader=CachingFileSystemLoader(tmp, auto_reload=False))
        template = env.get_template("some.txt")
        assert template.is_up_to_date()

        same_template = env.get_template("some.txt")
        assert same_template.is_up_to_date()
        assert same_template is template

        # Update template source
        time.sleep(0.01)
        path.touch()

        assert template.is_up_to_date() is False
        updated_template = env.get_template("some.txt")
        assert updated_template is template


def test_dont_auto_reload_cached_templates_async() -> None:
    async def coro() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "some.txt"

            # Write some content to temporary file
            with path.open("w", encoding="UTF-8") as fd:
                fd.write("Hello, {{ you }}!")

            env = Environment(loader=CachingFileSystemLoader(tmp, auto_reload=False))
            template = await env.get_template_async("some.txt")
            assert await template.is_up_to_date_async()

            same_template = await env.get_template_async("some.txt")
            assert await same_template.is_up_to_date_async()
            assert same_template is template

            # Update template source
            time.sleep(0.01)
            path.touch()

            assert await template.is_up_to_date_async() is False
            updated_template = await env.get_template_async("some.txt")
            assert updated_template is template

    asyncio.run(coro())


def test_cache_capacity() -> None:
    loader = CachingFileSystemLoader("tests/fixtures/001/", capacity=2)
    env = Environment(loader=loader)
    assert len(loader.cache) == 0
    _template = env.get_template("main.html")
    assert len(loader.cache) == 1
    _template = env.get_template("main.html")
    assert len(loader.cache) == 1
    _template = env.get_template("header.html")
    assert len(loader.cache) == 2
    assert list(loader.cache.keys()) == ["header.html", "main.html"]
    _template = env.get_template("footer.html")
    assert len(loader.cache) == 2
    assert list(loader.cache.keys()) == ["footer.html", "header.html"]
