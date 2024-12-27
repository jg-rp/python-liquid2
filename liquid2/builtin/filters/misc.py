"""Miscellaneous filter functions."""

from __future__ import annotations

import datetime
import decimal
import functools
import json
from typing import TYPE_CHECKING
from typing import Any
from typing import Callable

from dateutil import parser
from markupsafe import Markup

from liquid2.builtin import is_empty
from liquid2.exceptions import LiquidTypeError
from liquid2.filter import int_arg
from liquid2.filter import with_environment
from liquid2.undefined import is_undefined

if TYPE_CHECKING:
    from liquid2 import Environment


def size(obj: Any) -> int:
    """Return the length of _obj_.

    _obj_ could be a dict, list, string or any class implementing _len_.
    """
    try:
        return len(obj)
    except TypeError:
        return 0


def default(obj: Any, default_: object = "", *, allow_false: bool = False) -> Any:
    """Return _obj_, or _default_ if _obj_ is nil, false, or empty."""
    _obj = obj

    # Return the default value immediately if the object defines a
    # `force_liquid_default` property.
    if hasattr(obj, "force_liquid_default") and obj.force_liquid_default:
        return default_

    if hasattr(obj, "__liquid__"):
        _obj = obj.__liquid__()

    # Liquid 0, 0.0, 0b0, 0X0, 0o0 and Decimal("0") are not falsy.
    if not isinstance(obj, bool) and isinstance(obj, (int, float, decimal.Decimal)):
        return obj

    if allow_false is True and _obj is False:
        return obj

    if _obj in (None, False) or is_empty(_obj):
        return default_

    return obj


@with_environment
@functools.lru_cache(maxsize=10)
def date(  # noqa: PLR0912 PLR0911
    dat: datetime.datetime | str | int,
    fmt: str,
    *,
    environment: Environment,
) -> str:
    """Return a string representation of _dat_ using format string _fmt_."""
    if is_undefined(dat):
        return ""

    if is_undefined(fmt):
        return str(dat)

    if isinstance(dat, str):
        if dat in ("now", "today"):
            dat = datetime.datetime.now()
        elif dat.isdigit():
            dat = datetime.datetime.fromtimestamp(int(dat))
        else:
            try:
                dat = parser.parse(dat)
            except parser.ParserError:
                # Input is returned unchanged.
                return str(dat)
    elif isinstance(dat, int):
        try:
            dat = datetime.datetime.fromtimestamp(dat)
        except (OverflowError, OSError):
            # Testing on Windows shows that it can't handle some
            # negative integers.
            return str(dat)

    if not isinstance(dat, (datetime.datetime, datetime.date)):
        raise LiquidTypeError(
            f"date expected datetime.datetime, found {type(dat).__name__}",
            token=None,
        )

    try:
        rv = dat.strftime(fmt)
    except ValueError as err:
        # This is not uncommon on Windows when a format string contains
        # directives that are not officially supported by Python.

        # Handle "%s" as a special case.
        if fmt == r"%s":
            return str(dat.timestamp()).split(".")[0]
        raise LiquidTypeError(str(err), token=None) from err

    if environment.auto_escape and isinstance(fmt, Markup):
        return Markup(rv)
    return rv


class JSON:
    """Serialize an object to a JSON formatted string.

    Args:
        default: A function passed to `json.dumps`. This function is called
            in the event that the JSONEncoder does not know how to serialize an
            object. Defaults to `None`.
    """

    name = "json"

    def __init__(self, default: Callable[[Any], Any] | None = None):
        self.default = default

    def __call__(
        self,
        left: object,
        indent: object | None = None,
    ) -> str:
        """Apply this filter to _left_ and return the result."""
        indent = int_arg(indent) if indent else None
        try:
            return json.dumps(left, default=self.default, indent=indent)
        except TypeError as err:
            raise LiquidTypeError(str(err), token=None) from err
