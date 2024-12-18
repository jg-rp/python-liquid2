"""Compute Memory footprint of an object and its contents.

Adapted from the recipe by Raymond Hettinger (MIT).

https://code.activestate.com/recipes/577504-compute-memory-footprint-of-an-object-and-its-cont/?in=user-178123
"""

from collections import deque
from itertools import chain
from sys import getsizeof
from sys import stderr
from typing import Any
from typing import Callable
from typing import Iterable


def total_size(
    o: object,
    *,
    handlers: dict[Any, Any] | None = None,
    verbose: bool = False,
) -> int:
    """Returns the approximate memory footprint an object and all of its contents.

    Automatically finds the contents of the following builtin containers and
    their subclasses:  tuple, list, deque, dict, set and frozenset.
    To search other containers, add handlers to iterate over their contents:

        handlers = {SomeContainerClass: iter,
                    OtherContainerClass: OtherContainerClass.get_elements}

    """

    def dict_handler(d: dict[Any, Any]) -> Iterable[Any]:
        return chain.from_iterable(d.items())

    all_handlers: dict[Any, Callable[[Any], Any]] = {
        tuple: iter,
        list: iter,
        deque: iter,
        dict: dict_handler,
        set: iter,
        frozenset: iter,
    }

    if handlers:
        all_handlers.update(handlers)  # user handlers take precedence

    seen = set()  # track which object id's have already been seen
    default_size = getsizeof(0)  # estimate sizeof object without __sizeof__

    def sizeof(o: object) -> int:
        if id(o) in seen:  # do not double count the same object
            return 0
        seen.add(id(o))
        s = getsizeof(o, default_size)

        if verbose:
            print(s, type(o), repr(o), file=stderr)

        for typ, handler in all_handlers.items():
            if isinstance(o, typ):
                s += sum(map(sizeof, handler(o)))
                break
        return s

    return sizeof(o)
