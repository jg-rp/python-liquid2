import io

import pytest
from babel.messages import Catalog
from babel.messages.extract import extract as babel_extract

from liquid2 import Environment
from liquid2 import Template
from liquid2 import parse
from liquid2.messages import extract_from_template
from liquid2.messages import extract_from_templates


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
