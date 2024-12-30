"""Stringify a Python object ready for output in a Liquid template."""

from typing import Any
from typing import Sequence

from markupsafe import Markup
from markupsafe import escape

from liquid2.builtin import Blank
from liquid2.builtin import Empty

# NOTE: liquid2.builtin.expressions has a version of this too.


def to_liquid_string(val: Any, *, auto_escape: bool = False) -> str:
    """Stringify a Python object ready for output in a Liquid template."""
    if isinstance(val, str) or (auto_escape and hasattr(val, "__html__")):
        pass
    elif isinstance(val, bool):
        val = str(val).lower()
    elif val is None:
        val = ""
    elif isinstance(val, range):
        val = f"{val.start}..{val.stop - 1}"
    elif isinstance(val, Sequence):
        if auto_escape:
            val = Markup("").join(
                to_liquid_string(itm, auto_escape=auto_escape) for itm in val
            )
        else:
            val = "".join(to_liquid_string(itm, auto_escape=auto_escape) for itm in val)
    elif isinstance(val, (Empty, Blank)):
        val = ""
    else:
        val = str(val)

    if auto_escape:
        val = escape(val)

    assert isinstance(val, str)
    return val
