"""Filter functions that operate on arrays."""

from __future__ import annotations

import math
import re
from decimal import Decimal
from functools import partial
from itertools import chain
from itertools import islice
from operator import getitem
from typing import TYPE_CHECKING
from typing import Any
from typing import Iterable
from typing import Sequence

from markupsafe import Markup

from liquid2.builtin import Null
from liquid2.exceptions import LiquidTypeError
from liquid2.filter import decimal_arg
from liquid2.filter import sequence_filter
from liquid2.filter import with_environment
from liquid2.limits import to_int
from liquid2.stringify import to_liquid_string
from liquid2.undefined import is_undefined

if TYPE_CHECKING:
    from ...environment import Environment  # noqa: TID252


class _Null:
    """A null without a token for use in the map filter."""

    def __eq__(self, other: object) -> bool:
        return other is None or isinstance(other, (_Null, Null))

    def __str__(self) -> str:  # pragma: no cover
        return ""


_NULL = _Null()

# Send objects with missing keys to the end when sorting a list.
MAX_CH = chr(0x10FFFF)

# Unique object for use with the uniq filter.
MISSING = object()


def _getitem(sequence: Any, key: object, default: object = None) -> Any:
    """Helper for the map filter.

    Same as sequence[key], but returns a default value if key does not exist
    in sequence.
    """
    try:
        return getitem(sequence, key)
    except (KeyError, IndexError):
        return default
    except TypeError:
        if not hasattr(sequence, "__getitem__"):
            raise
        return default


def _lower(obj: Any) -> str:
    """Helper for the sort filter."""
    try:
        return str(obj).lower()
    except AttributeError:
        return ""


@with_environment
@sequence_filter
def join(
    sequence: Iterable[object],
    separator: object = " ",
    *,
    environment: Environment,
) -> str:
    """Return a string by joining items in _sequence_, separated by _separator_."""
    if not isinstance(separator, str):
        separator = str(separator)

    if environment.auto_escape and separator == " ":
        separator = Markup(" ")

    return separator.join(to_liquid_string(item) for item in sequence)


def first(obj: Any) -> object:
    """Return the first item of collection _obj_."""
    if isinstance(obj, str):
        return None

    if isinstance(obj, dict):
        obj = list(islice(obj.items(), 1))

    try:
        return getitem(obj, 0)
    except (TypeError, KeyError, IndexError):
        return None


def last(obj: Sequence[Any]) -> object:
    """Return the last item of array-like object _obj_."""
    if isinstance(obj, str):
        return None

    try:
        return getitem(obj, -1)
    except (TypeError, KeyError, IndexError):
        return None


@sequence_filter
def concat(sequence: Sequence[object], other: Sequence[object]) -> list[object]:
    """Return the concatenation of _sequence_ and _second_array_."""
    if not isinstance(other, (list, tuple)):
        raise LiquidTypeError(
            f"concat expected an array, found {type(other).__name__}",
            token=None,
        )

    if is_undefined(sequence):
        return list(other)

    return list(chain(sequence, other))


@sequence_filter
def map_(sequence: Sequence[object], key: object) -> list[object]:
    """Return an array/list of items in _sequence_ selected by _key_."""
    try:
        return [_getitem(itm, str(key), default=_NULL) for itm in sequence]
    except TypeError as err:
        raise LiquidTypeError("can't map sequence", token=None) from err


@sequence_filter
def reverse(array: Sequence[object]) -> list[object]:
    """Reverses the order of the items in an array."""
    return list(reversed(array))


@sequence_filter
def sort(sequence: Sequence[Any], key: object = None) -> list[object]:
    """Return a copy of _sequence_ in ascending order.

    When a key string is provided, objects without the key property will
    be at the end of the output list/array.
    """
    if key:
        key_func = partial(_getitem, key=str(key), default=MAX_CH)
        return sorted(sequence, key=key_func)

    try:
        return sorted(sequence)
    except TypeError as err:
        raise LiquidTypeError("can't sort sequence", token=None) from err


@sequence_filter
def sort_natural(sequence: Sequence[object], key: object = None) -> list[object]:
    """Return a copy of _sequence_ in ascending order, with case-insensitive comparison.

    When a key string is provided, objects without the key property will
    be at the end of the output list/array.
    """
    if key:
        item_getter = partial(_getitem, key=str(key), default=MAX_CH)
        return sorted(sequence, key=lambda obj: _lower(item_getter(obj)))

    return sorted(sequence, key=_lower)


@sequence_filter
def where(
    sequence: Sequence[object], attr: object, value: object = None
) -> list[object]:
    """Return a list of items from _sequence_ where _attr_ equals _value_."""
    if value is not None and not is_undefined(value):
        return [itm for itm in sequence if _getitem(itm, attr) == value]

    return [itm for itm in sequence if _getitem(itm, attr) not in (False, None)]


@sequence_filter
def uniq(sequence: Sequence[Any], key: object = None) -> list[object]:
    """Return a copy of _sequence_ with duplicate elements removed."""
    # Note that we're not using a dict or set for deduplication because we need
    # to handle sequences containing unhashable objects, like dictionaries.

    # This is probably quite slow.
    if key is not None:
        keys = []
        result = []
        for obj in sequence:
            try:
                item = obj[key]
            except KeyError:
                item = MISSING
            except TypeError as err:
                raise LiquidTypeError(
                    f"can't read property '{key}' of {obj}",
                    token=None,
                ) from err

            if item not in keys:
                keys.append(item)
                result.append(obj)

        return result

    return [obj for i, obj in enumerate(sequence) if sequence.index(obj) == i]


@sequence_filter
def compact(sequence: Sequence[Any], key: object = None) -> list[object]:
    """Return a copy of _sequence_ with any NULL values removed."""
    if key is not None:
        try:
            return [itm for itm in sequence if itm[key] is not None]
        except TypeError as err:
            raise LiquidTypeError(f"can't read property '{key}'", token=None) from err
    return [itm for itm in sequence if itm is not None]


@sequence_filter
def sum_(sequence: Sequence[object], key: object = None) -> float | int | Decimal:
    """Return the sum of all numeric elements in _sequence_.

    If _key_ is given, it is assumed that sequence items are mapping-like,
    and the values at _item[key]_ will be summed instead.
    """
    if key is not None and not is_undefined(key):
        rv = sum(decimal_arg(_getitem(elem, key, 0), 0) for elem in sequence)
    else:
        rv = sum(decimal_arg(elem, 0) for elem in sequence)
    if isinstance(rv, Decimal):
        return float(rv)
    return rv


RE_NUMERIC = re.compile(r"-?\d+")


@sequence_filter
def sort_numeric(left: Sequence[object], key: object = None) -> list[object]:
    """Return a copy of `left` sorted by numeric values found in `left`'s items."""
    if key:
        _key = str(key)
        return sorted(left, key=lambda item: _ints(_get_numeric_item(item, _key)))
    return sorted(left, key=_ints)


def _get_numeric_item(sequence: Any, key: object, default: object = None) -> Any:
    """Item getter for the `sort_numeric` filter."""
    try:
        return getitem(sequence, key)
    except (KeyError, IndexError, TypeError):
        return default


def _ints(obj: object) -> tuple[int | float | Decimal, ...]:
    """Key function for the `sort_numeric` filter."""
    if isinstance(obj, bool):
        # isinstance(False, int) == True
        return (math.inf,)
    if isinstance(obj, (int, float, Decimal)):
        return (obj,)

    ints = tuple(to_int(n) for n in RE_NUMERIC.findall(str(obj)))

    if not ints:
        return (math.inf,)
    return ints
