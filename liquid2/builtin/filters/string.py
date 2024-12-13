"""Filter functions that operate on strings."""

from __future__ import annotations

import html
import re
import urllib.parse
from typing import TYPE_CHECKING
from typing import Any
from typing import Sequence

from markupsafe import Markup
from markupsafe import escape as markupsafe_escape

from liquid2.exceptions import LiquidTypeError
from liquid2.filter import string_filter
from liquid2.filter import with_environment
from liquid2.limits import to_int
from liquid2.stringify import to_liquid_string
from liquid2.undefined import is_undefined
from liquid2.utils.html import strip_tags
from liquid2.utils.text import truncate_chars

if TYPE_CHECKING:
    from liquid2 import Environment


@string_filter
def append(val: str, arg: object) -> str:
    """Return a copy of _val_ concatenated with _arg_.

    If _arg_ is not a string, it will be converted to one before concatenation.
    """
    if not isinstance(arg, str):
        arg = str(arg)
    return val + arg


@string_filter
def capitalize(val: str) -> str:
    """Return _val_ with the first character in uppercase and the rest lowercase."""
    return val.capitalize()


@string_filter
def downcase(val: str) -> str:
    """Return a copy of _val_ with all characters converted to lowercase."""
    return val.lower()


@with_environment
@string_filter
def escape(val: str, *, environment: Environment) -> str:
    """Return _val_ with the characters &, < and > converted to HTML-safe sequences."""
    if environment.auto_escape:
        return markupsafe_escape(str(val))
    return html.escape(val)


@with_environment
@string_filter
def escape_once(val: str, *, environment: Environment) -> str:
    """Return _val_ with the characters &, < and > converted to HTML-safe sequences.

    It is safe to use `escape_one` on string values that already contain HTML escape
    sequences.
    """
    if environment.auto_escape:
        return Markup(val).unescape()
    return html.escape(html.unescape(val))


@string_filter
def lstrip(val: str) -> str:
    """Return a copy of _val_ with leading whitespace removed."""
    return val.lstrip()


RE_LINETERM = re.compile(r"\r?\n")


@with_environment
@string_filter
def newline_to_br(val: str, *, environment: Environment) -> str:
    """Return a copy of _val_ with LF or CRLF converted to `<br />`, plus a newline."""
    if environment.auto_escape:
        val = markupsafe_escape(val)
        return Markup(RE_LINETERM.sub("<br />\n", val))
    return RE_LINETERM.sub("<br />\n", val)


@string_filter
def prepend(val: str, arg: str) -> str:
    """Return a copy of _arg_ concatenated with _val_."""
    return to_liquid_string(arg) + val


@string_filter
def remove(val: str, arg: str) -> str:
    """Return a copy of _val_ with all occurrences of _arg_ removed."""
    return val.replace(to_liquid_string(arg), "")


@string_filter
def remove_first(val: str, arg: str) -> str:
    """Return a copy of _val_ with the first occurrence of _arg_ removed."""
    return val.replace(to_liquid_string(arg), "", 1)


@string_filter
def remove_last(val: str, arg: str) -> str:
    """Return a copy of _val_ with last occurrence of _arg_ removed."""
    try:
        before, _, after = val.rpartition(to_liquid_string(arg))
    except ValueError:
        # empty separator
        return val
    if before:
        return before + after
    return val


@string_filter
def replace(val: str, seq: str, sub: str = "") -> str:
    """Return a copy of _val_ with each occurrence of _seq_ replaced with _sub_."""
    return val.replace(to_liquid_string(seq), to_liquid_string(sub))


@string_filter
def replace_first(val: str, seq: str, sub: str = "") -> str:
    """Return a copy of _val_ with the first occurrence of _seq_ replaced with _sub_."""
    return val.replace(to_liquid_string(seq), to_liquid_string(sub), 1)


@string_filter
def replace_last(val: str, seq: str, sub: str) -> str:
    """Return a copy of _val_ with the last occurrence of _seq_ replaced with _sub_."""
    try:
        before, _, after = val.rpartition(to_liquid_string(seq))
    except ValueError:
        # empty separator
        return val + to_liquid_string(sub)
    if before:
        return before + to_liquid_string(sub) + after
    return val


@string_filter
def upcase(val: str) -> str:
    """Return a copy of _val_ with all characters converted to uppercase."""
    return val.upper()


MAX_SLICE_ARG = (1 << 63) - 1
MIN_SLICE_ARG = -(1 << 63)


def _slice_arg(val: Any) -> int:
    if isinstance(val, float):
        raise LiquidTypeError(
            f"slice expected an integer, found {type(val).__name__}",
            token=None,
        )

    try:
        rv = to_int(val)
    except (ValueError, TypeError) as err:
        raise LiquidTypeError(
            f"slice expected an integer, found {type(val).__name__}",
            token=None,
        ) from err

    rv = min(rv, MAX_SLICE_ARG)
    return max(rv, MIN_SLICE_ARG)


def slice_(val: Any, start: Any, length: Any = 1) -> str | list[object]:
    """Return the subsequence of _val_ starting at _start_ with up to _length_ chars.

    Array-like objects return a list, strings return a substring, all other objects are
    cast to a string before returning a substring.
    """
    if not isinstance(val, Sequence):
        val = str(val)

    if is_undefined(start):
        raise LiquidTypeError(
            "slice expected an integer, found Undefined",
            token=None,
        )

    if is_undefined(length):
        length = 1

    _start = _slice_arg(start)
    _length = _slice_arg(length)
    end: int | None = _start + _length

    # A negative start index and a length that exceeds the theoretical length
    # of the sequence.
    if isinstance(end, int) and _start < 0 <= end:
        end = None

    if isinstance(val, str):
        return val[_start:end]
    return list(val[_start:end])


@string_filter
def split(val: str, sep: str) -> list[str]:
    """Split string _val_ on delimiter _sep_.

    If _sep_ is empty or _undefined_, _val_ is split into a list of single
    characters. If _val_ is empty or equal to _sep_, an empty list is returned.
    """
    if not sep:
        return list(val)

    sep = to_liquid_string(sep)
    if not val or val == sep:
        return []

    return val.split(sep)


@string_filter
def strip(val: str) -> str:
    """Return a copy of _val_ with leading and trailing whitespace removed."""
    return val.strip()


@string_filter
def rstrip(val: str) -> str:
    """Return a copy of _val_ with trailing whitespace removed."""
    return val.rstrip()


@with_environment
@string_filter
def strip_html(val: str, *, environment: Environment) -> str:
    """Return a copy of _val_ with all HTML tags removed."""
    stripped = strip_tags(val)
    if environment.auto_escape and isinstance(val, Markup):
        return Markup(stripped)
    return stripped


@with_environment
@string_filter
def strip_newlines(val: str, *, environment: Environment) -> str:
    """Return ta copy of _val_ with all newline characters removed."""
    if environment.auto_escape:
        val = markupsafe_escape(val)
        return Markup(RE_LINETERM.sub("", val))
    return RE_LINETERM.sub("", val)


@string_filter
def truncate(val: str, num: Any = 50, end: str = "...") -> str:
    """Return a copy of _val_ truncated to _num_ characters."""
    if is_undefined(num):
        raise LiquidTypeError(
            "truncate expected an integer, found Undefined", token=None
        )

    try:
        num = to_int(num)
    except ValueError as err:
        raise LiquidTypeError(
            f"truncate expected an integer, found {type(num).__name__}",
            token=None,
        ) from err

    end = str(end)
    return truncate_chars(val, num, end)


# Limit to the number of words that can be truncated.
MAX_TRUNC_WORDS = (1 << 31) - 1


@string_filter
def truncatewords(val: str, num: Any = 15, end: str = "...") -> str:
    """Return a copy of _val_ truncated to at most _num_ words."""
    if is_undefined(num):
        raise LiquidTypeError(
            "truncate expected an integer, found Undefined", token=None
        )

    try:
        num = to_int(num)
    except ValueError as err:
        raise LiquidTypeError(
            f"truncate expected an integer, found {type(num).__name__}",
            token=None,
        ) from err

    end = str(end)

    # Force a minimum `num` of 1.
    if num <= 0:
        num = 1

    # Replaces consecutive whitespace with a single newline.
    words = val.split()

    if num >= MAX_TRUNC_WORDS:
        return val

    if len(words) < num:
        return " ".join(words)

    return " ".join(words[:num]) + end


@with_environment
@string_filter
def url_encode(val: str, *, environment: Environment) -> str:
    """Return a percent-encoded copy of _val_ so it is useable in a URL."""
    if environment.auto_escape:
        return Markup(urllib.parse.quote_plus(val))
    return urllib.parse.quote_plus(val)


@string_filter
def url_decode(val: str) -> str:
    """Return a copy of _val_ after decoding percent-encoded sequences."""
    # Assuming URL decoded strings are all unsafe.
    return urllib.parse.unquote_plus(val)


@with_environment
@string_filter
def safe(val: str, *, environment: Environment) -> str:
    """Return a copy of _val_ that will not be automatically HTML escaped on output."""
    if environment.auto_escape:
        return Markup(val)
    return val
