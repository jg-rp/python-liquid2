from liquid2 import parse
from liquid2.messages import extract_from_template


def test_gettext_filter() -> None:
    source = (
        "{{ 'Hello, World!' }}\n"
        "{{ 'Hello, World!' | gettext }}\n"
        "{{ 'Hello, World!' }}\n"
    )

    template = parse(source)
    messages = list(extract_from_template(template))

    assert len(messages) == 1
    message = messages[0]

    assert message.lineno == 2
    assert message.funcname == "gettext"
    assert message.message == ("Hello, World!",)
    assert message.comments == []


def test_gettext_filter_with_inline_comment() -> None:
    source = (
        "{{ 'Hello, World!' }}\n"
        "{% # Translators: greeting %}\n"
        "{{ 'Hello, World!' | gettext }}\n"
        "{{ 'Hello, World!' }}\n"
    )

    template = parse(source)
    messages = list(extract_from_template(template, comment_tags=["Translators:"]))

    assert len(messages) == 1
    message = messages[0]

    assert message.lineno == 3
    assert message.funcname == "gettext"
    assert message.message == ("Hello, World!",)
    assert message.comments == ["Translators: greeting"]


def test_gettext_filter_with_block_comment() -> None:
    source = (
        "{{ 'Hello, World!' }}\n"
        "{% comment %}Translators: greeting{% endcomment %}\n"
        "{{ 'Hello, World!' | gettext }}\n"
        "{{ 'Hello, World!' }}\n"
    )

    template = parse(source)
    messages = list(extract_from_template(template, comment_tags=["Translators:"]))

    assert len(messages) == 1
    message = messages[0]

    assert message.lineno == 3
    assert message.funcname == "gettext"
    assert message.message == ("Hello, World!",)
    assert message.comments == ["Translators: greeting"]


def test_gettext_filter_with_comment_markup() -> None:
    source = (
        "{{ 'Hello, World!' }}\n"
        "{# Translators: greeting #}\n"
        "{{ 'Hello, World!' | gettext }}\n"
        "{{ 'Hello, World!' }}\n"
    )

    template = parse(source)
    messages = list(extract_from_template(template, comment_tags=["Translators:"]))

    assert len(messages) == 1
    message = messages[0]

    assert message.lineno == 3
    assert message.funcname == "gettext"
    assert message.message == ("Hello, World!",)
    assert message.comments == ["Translators: greeting"]


def test_preceding_comments() -> None:
    source = (
        "{{ 'Hello, World!' }}\n"
        "{% # Translators: greeting %}\n"
        "\n"
        "{{ 'Hello, World!' | gettext }}\n"
        "{{ 'Hello, World!' }}\n"
    )

    template = parse(source)
    messages = list(extract_from_template(template, comment_tags=["Translators:"]))

    assert len(messages) == 1
    message = messages[0]

    assert message.lineno == 4
    assert message.funcname == "gettext"
    assert message.message == ("Hello, World!",)
    assert message.comments == []


def test_multiple_preceding_comments() -> None:
    source = (
        "{{ 'Hello, World!' }}\n"
        "{% # Translators: hello %}\n"
        "{% # Translators: greeting %}\n"
        "{{ 'Hello, World!' | gettext }}\n"
        "{{ 'Hello, World!' }}\n"
    )

    template = parse(source)
    messages = list(extract_from_template(template, comment_tags=["Translators:"]))

    assert len(messages) == 1
    message = messages[0]

    assert message.lineno == 4
    assert message.funcname == "gettext"
    assert message.message == ("Hello, World!",)
    assert message.comments == ["Translators: greeting"]


def test_comment_without_tag() -> None:
    source = (
        "{{ 'Hello, World!' }}\n"
        "{% # greeting %}\n"
        "{{ 'Hello, World!' | gettext }}\n"
        "{{ 'Hello, World!' }}\n"
    )

    template = parse(source)
    messages = list(extract_from_template(template, comment_tags=["Translators:"]))

    assert len(messages) == 1
    message = messages[0]

    assert message.lineno == 3
    assert message.funcname == "gettext"
    assert message.message == ("Hello, World!",)
    assert message.comments == []


def test_gettext_filter_ignore_excess_args() -> None:
    source = (
        "{{ 'Hello, World!' }}\n"
        "{{ 'Hello, World!' | gettext: 1 }}\n"
        "{{ 'Hello, World!' }}\n"
    )

    template = parse(source)
    messages = list(extract_from_template(template))

    assert len(messages) == 1
    message = messages[0]

    assert message.lineno == 2
    assert message.funcname == "gettext"
    assert message.message == ("Hello, World!",)
    assert message.comments == []


def test_ngettext_filter() -> None:
    source = (
        "{{ 'Hello, World!' }}\n"
        "{{ 'Hello, World!' | ngettext: 'Hello, Worlds!', 2 }}\n"
        "{{ 'Hello, World!' }}\n"
    )

    template = parse(source)
    messages = list(extract_from_template(template))

    assert len(messages) == 1
    message = messages[0]

    assert message.lineno == 2
    assert message.funcname == "ngettext"
    assert message.message == ("Hello, World!", "Hello, Worlds!")
    assert message.comments == []


def test_ngettext_filter_missing_arg() -> None:
    source = (
        "{{ 'Hello, World!' }}\n"
        "{{ 'Hello, World!' | ngettext }}\n"
        "{{ 'Hello, World!' | ngettext: 'Hello, Worlds!' }}\n"
        "{{ 'Hello, World!' }}\n"
    )

    template = parse(source)
    messages = list(extract_from_template(template))

    assert len(messages) == 1
    message = messages[0]

    assert message.lineno == 3
    assert message.funcname == "ngettext"
    assert message.message == ("Hello, World!", "Hello, Worlds!")
    assert message.comments == []


def test_ngettext_filter_excess_args() -> None:
    source = (
        "{{ 'Hello, World!' }}\n"
        "{{ 'Hello, World!' | ngettext: 'Hello, Worlds!', 2, foo }}\n"
        "{{ 'Hello, World!' }}\n"
    )

    template = parse(source)
    messages = list(extract_from_template(template))

    assert len(messages) == 1
    message = messages[0]

    assert message.lineno == 2
    assert message.funcname == "ngettext"
    assert message.message == ("Hello, World!", "Hello, Worlds!")
    assert message.comments == []


def test_pgettext_filter() -> None:
    source = (
        "{{ 'Hello, World!' }}\n"
        "{{ 'Hello, World!' | pgettext: 'greeting' }}\n"
        "{{ 'Hello, World!' }}\n"
    )

    template = parse(source)
    messages = list(extract_from_template(template))

    assert len(messages) == 1
    message = messages[0]

    assert message.lineno == 2
    assert message.funcname == "pgettext"
    assert message.message == (("greeting", "c"), "Hello, World!")
    assert message.comments == []


def test_npgettext_filter() -> None:
    source = (
        "{{ 'Hello, World!' }}\n"
        "{{ 'Hello, World!' | npgettext: 'greeting', 'Hello, Worlds!', 2 }}\n"
        "{{ 'Hello, World!' }}\n"
    )

    template = parse(source)
    messages = list(extract_from_template(template))

    assert len(messages) == 1
    message = messages[0]

    assert message.lineno == 2
    assert message.funcname == "npgettext"
    assert message.message == (("greeting", "c"), "Hello, World!", "Hello, Worlds!")
    assert message.comments == []


def test_t_filter_gettext() -> None:
    source = (
        "{{ 'Hello, World!' }}\n"
        "{{ 'Hello, World!' | t }}\n"
        "{{ 'Hello, World!' }}\n"
    )

    template = parse(source)
    messages = list(extract_from_template(template))

    assert len(messages) == 1
    message = messages[0]

    assert message.lineno == 2
    assert message.funcname == "gettext"
    assert message.message == ("Hello, World!",)
    assert message.comments == []


def test_t_filter_ngettext() -> None:
    source = (
        "{{ 'Hello, World!' }}\n"
        "{{ 'Hello, World!' | t: plural: 'Hello, Worlds!' }}\n"
        "{{ 'Hello, World!' }}\n"
    )

    template = parse(source)
    messages = list(extract_from_template(template))

    assert len(messages) == 1
    message = messages[0]

    assert message.lineno == 2
    assert message.funcname == "ngettext"
    assert message.message == ("Hello, World!", "Hello, Worlds!")
    assert message.comments == []


def test_t_filter_pgettext() -> None:
    source = (
        "{{ 'Hello, World!' }}\n"
        "{{ 'Hello, World!' | t: 'greeting' }}\n"
        "{{ 'Hello, World!' }}\n"
    )

    template = parse(source)
    messages = list(extract_from_template(template))

    assert len(messages) == 1
    message = messages[0]

    assert message.lineno == 2
    assert message.funcname == "pgettext"
    assert message.message == (("greeting", "c"), "Hello, World!")
    assert message.comments == []


def test_t_filter_npgettext() -> None:
    source = (
        "{{ 'Hello, World!' }}\n"
        "{{ 'Hello, World!' | t: 'greeting', plural: 'Hello, Worlds!' }}\n"
        "{{ 'Hello, World!' }}\n"
    )

    template = parse(source)
    messages = list(extract_from_template(template))

    assert len(messages) == 1
    message = messages[0]

    assert message.lineno == 2
    assert message.funcname == "npgettext"
    assert message.message == (("greeting", "c"), "Hello, World!", "Hello, Worlds!")
    assert message.comments == []


def test_translate_tag_gettext() -> None:
    source = "{% translate %}Hello, World!{% endtranslate %}"
    template = parse(source)
    messages = list(extract_from_template(template))

    assert len(messages) == 1
    message = messages[0]

    assert message.lineno == 1
    assert message.funcname == "gettext"
    assert message.message == ("Hello, World!",)
    assert message.comments == []


def test_translate_tag_pgettext() -> None:
    source = (
        "{% translate context: 'greetings everyone' %}"
        "Hello, World!"
        "{% endtranslate %}"
    )

    template = parse(source)
    messages = list(extract_from_template(template))

    assert len(messages) == 1
    message = messages[0]

    assert message.lineno == 1
    assert message.funcname == "pgettext"
    assert message.message == (("greetings everyone", "c"), "Hello, World!")
    assert message.comments == []


def test_translate_tag_ngettext() -> None:
    source = (
        "{% translate %}"
        "Hello, World!"
        "{% plural %}"
        "Hello, Worlds!"
        "{% endtranslate %}"
    )

    template = parse(source)
    messages = list(extract_from_template(template))

    assert len(messages) == 1
    message = messages[0]

    assert message.lineno == 1
    assert message.funcname == "ngettext"
    assert message.message == ("Hello, World!", "Hello, Worlds!")
    assert message.comments == []


def test_translate_tag_npgettext() -> None:
    source = (
        "{% translate context: 'greetings everyone' %}"
        "Hello, World!"
        "{% plural %}"
        "Hello, Worlds!"
        "{% endtranslate %}"
    )

    template = parse(source)
    messages = list(extract_from_template(template))

    assert len(messages) == 1
    message = messages[0]

    assert message.lineno == 1
    assert message.funcname == "npgettext"
    assert message.message == (
        ("greetings everyone", "c"),
        "Hello, World!",
        "Hello, Worlds!",
    )
    assert message.comments == []
