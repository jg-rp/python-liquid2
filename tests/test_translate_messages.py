import re

from markupsafe import Markup

from liquid2 import parse


class MockTranslations:
    """A mock translations class that returns all messages in upper case."""

    RE_VARS = re.compile(r"%\(\w+\)s")

    def gettext(self, message: str) -> str:
        return self._upper(message)

    def ngettext(self, singular: str, plural: str, n: int) -> str:
        if n > 1:
            return self._upper(plural)
        return self._upper(singular)

    def pgettext(self, message_context: str, message: str) -> str:
        return message_context + "::" + self._upper(message)

    def npgettext(
        self, message_context: str, singular: str, plural: str, n: int
    ) -> str:
        if n > 1:
            return message_context + "::" + self._upper(plural)
        return message_context + "::" + self._upper(singular)

    def _upper(self, message: str) -> str:
        start = 0
        parts: list[str] = []
        for match in self.RE_VARS.finditer(message):
            parts.append(message[start : match.start()].upper())
            parts.append(match.group())
            start = match.end()

        parts.append(message[start:].upper())
        return Markup("").join(parts)


MOCK_TRANSLATIONS = MockTranslations()


def test_gettext_filter() -> None:
    source = "{{ 'Hello, World!' | gettext }}"
    template = parse(source)
    # Default null translation
    assert template.render() == "Hello, World!"
    # Mock translation
    assert template.render(translations=MOCK_TRANSLATIONS) == "HELLO, WORLD!"


def test_gettext_from_context() -> None:
    source = "{{ foo | gettext }}"
    template = parse(source)
    # Default null translation
    assert template.render(foo="Hello, World!") == "Hello, World!"
    # Mock translation
    assert (
        template.render(
            translations=MOCK_TRANSLATIONS,
            foo="Hello, World!",
        )
        == "HELLO, WORLD!"
    )


def test_gettext_filter_with_variable() -> None:
    source = "{{ 'Hello, %(you)s!' | gettext: you: 'World' }}"
    template = parse(source)
    # Default null translation
    assert template.render() == "Hello, World!"
    # Mock translation
    assert template.render(translations=MOCK_TRANSLATIONS) == "HELLO, World!"


def test_ngettext_filter() -> None:
    source = "{{ 'Hello, World!' | ngettext: 'Hello, Worlds!', 2 }}"
    template = parse(source)
    # Default null translation
    assert template.render() == "Hello, Worlds!"
    # Mock translation
    assert template.render(translations=MOCK_TRANSLATIONS) == "HELLO, WORLDS!"


def test_pgettext_filter() -> None:
    source = "{{ 'Hello, World!' | pgettext: 'greeting' }}"
    template = parse(source)
    # Default null translation
    assert template.render() == "Hello, World!"
    # Mock translation
    assert template.render(translations=MOCK_TRANSLATIONS) == "greeting::HELLO, WORLD!"


def test_npgettext_filter() -> None:
    source = "{{ 'Hello, World!' | npgettext: 'greeting', 'Hello, Worlds!', 2 }}"
    template = parse(source)
    # Default null translation
    assert template.render() == "Hello, Worlds!"
    # Mock translation
    assert template.render(translations=MOCK_TRANSLATIONS) == "greeting::HELLO, WORLDS!"


def test_t_filter_gettext() -> None:
    source = "{{ 'Hello, World!' | t }}"
    template = parse(source)
    # Default null translation
    assert template.render() == "Hello, World!"
    # Mock translation
    assert template.render(translations=MOCK_TRANSLATIONS) == "HELLO, WORLD!"


def test_t_filter_ngettext() -> None:
    source = "{{ 'Hello, World!' | t: plural: 'Hello, Worlds!', count: 2 }}"
    template = parse(source)
    # Default null translation
    assert template.render() == "Hello, Worlds!"
    # Mock translation
    assert template.render(translations=MOCK_TRANSLATIONS) == "HELLO, WORLDS!"


def test_t_filter_pgettext() -> None:
    source = "{{ 'Hello, %(you)s!' | t: 'greeting', you: 'World' }}"
    template = parse(source)
    # Default null translation
    assert template.render() == "Hello, World!"
    # Mock translation
    assert template.render(translations=MOCK_TRANSLATIONS) == "greeting::HELLO, World!"


def test_t_filter_npgettext() -> None:
    source = """
        {{-
            'Hello, %(you)s!' | t:
                'greeting',
                plural: 'Hello, %(you)ss!',
                count: 2,
                you: 'World'
        -}}
    """

    template = parse(source)
    # Default null translation
    assert template.render() == "Hello, Worlds!"
    # Mock translation
    assert template.render(translations=MOCK_TRANSLATIONS) == "greeting::HELLO, WorldS!"
