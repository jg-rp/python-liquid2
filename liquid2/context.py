"""Template render context."""

from __future__ import annotations

import datetime
import sys
from collections import defaultdict
from contextlib import contextmanager
from functools import partial
from functools import reduce
from io import StringIO
from itertools import cycle
from operator import mul
from typing import TYPE_CHECKING
from typing import Any
from typing import Callable
from typing import Iterator
from typing import Mapping
from typing import TextIO

from markupsafe import Markup

from .exceptions import ContextDepthError
from .exceptions import NoSuchFilterFunc
from .undefined import UNDEFINED
from .utils import ReadOnlyChainMap

if TYPE_CHECKING:
    from liquid2 import TokenT
    from liquid2.builtin.tags.for_tag import ForLoop

    from .query import Query
    from .template import Template
    from .undefined import Undefined


class RenderContext:
    """Template render state."""

    __slots__ = (
        "template",
        "globals",
        "disabled_tags",
        "parent",
        "_copy_depth",
        "loop_iteration_carry",
        "local_namespace_carry",
        "locals",
        "counters",
        "scope",
        "auto_escape",
        "env",
        "tag_namespace",
        "loops",
    )

    def __init__(
        self,
        template: Template,
        *,
        global_data: Mapping[str, object] | None = None,
        disabled_tags: set[str] | None = None,
        parent: RenderContext | None = None,
        copy_depth: int = 0,
        loop_iteration_carry: int = 1,
        local_namespace_carry: int = 0,
    ) -> None:
        self.template = template
        self.globals = global_data or {}
        self.disabled_tags = disabled_tags or set()
        self.parent = parent
        self._copy_depth = copy_depth
        self.loop_iteration_carry = loop_iteration_carry
        self.local_namespace_carry = local_namespace_carry

        self.locals: dict[str, object] = {}
        self.counters: dict[str, int] = {}
        self.scope = ReadOnlyChainMap(
            self.locals,
            self.globals,
            builtin,
            self.counters,
        )

        self.env = template.env
        self.auto_escape = self.env.auto_escape

        # A namespace supporting stateful tags. Such as `cycle`, `increment`,
        # `decrement` and `ifchanged`.
        self.tag_namespace: dict[str, Any] = {
            "cycles": {},
            "stopindex": {},
            "extends": defaultdict(list),
        }

        # As stack of forloop objects. Used for populating forloop.parentloop.
        self.loops: list[ForLoop] = []

    def assign(self, key: str, val: object) -> None:
        """Add _key_ to the local namespace with value _val_."""
        self.locals[key] = val
        # TODO: namespace limit

    def get(self, path: Query, *, token: TokenT, default: object = UNDEFINED) -> object:
        """Resolve the variable _path_ in the current namespace."""
        nodes = path.find(self.scope)

        if not nodes:
            if default == UNDEFINED:
                return self.template.env.undefined(path, token=token)
            return default

        if len(nodes) == 1:
            return nodes[0].value

        return nodes.values()

    def filter(self, name: str, *, token: TokenT) -> Callable[..., object]:
        """Return the filter callable for _name_."""
        try:
            filter_func = self.env.filters[name]
        except KeyError as err:
            raise NoSuchFilterFunc(f"unknown filter '{name}'", token=token) from err

        kwargs: dict[str, Any] = {}

        if getattr(filter_func, "with_context", False):
            kwargs["context"] = self

        if getattr(filter_func, "with_environment", False):
            kwargs["environment"] = self.env

        if kwargs:
            if hasattr(filter_func, "filter_async"):
                _filter_func = partial(filter_func, **kwargs)
                _filter_func.filter_async = partial(  # type: ignore
                    filter_func.filter_async,
                    **kwargs,
                )
                return _filter_func
            return partial(filter_func, **kwargs)

        return filter_func

    def get_size_of_locals(self) -> int:
        """Return the "size" or a "score" for the current local namespace.

        This is used by the optional local namespace resource limit. Override
        `get_size_of_locals` to customize how the limit is calculated. Be sure
        to consider `self.local_namespace_size_carry` when writing a custom
        implementation of `get_size_of_locals`.

        The default implementation uses `sys.getsizeof()` on each of the local
        namespace's values. It is not a reliable measure of size in bytes.
        """
        if not self.env.local_namespace_limit:
            return 0
        return (
            sum(sys.getsizeof(obj, default=1) for obj in self.locals.values())
            + self.local_namespace_carry
        )

    @contextmanager
    def extend(
        self, namespace: Mapping[str, object], template: Template | None = None
    ) -> Iterator[RenderContext]:
        """Extend this context with the given read-only namespace."""
        if self.scope.size() > self.env.context_depth_limit:
            raise ContextDepthError(
                "maximum context depth reached, possible recursive include",
                token=None,
            )

        _template = self.template
        if template:
            self.template = template

        self.scope.push(namespace)

        try:
            yield self
        finally:
            if template:
                self.template = _template
            self.scope.pop()

    def copy(
        self,
        token: TokenT,
        *,
        namespace: Mapping[str, object],
        template: Template | None = None,
        disabled_tags: set[str] | None = None,
        carry_loop_iterations: bool = False,
        block_scope: bool = False,
    ) -> RenderContext:
        """Return a copy of this render context with a new scope."""
        if self._copy_depth > self.env.context_depth_limit:
            raise ContextDepthError(
                "maximum context depth reached, possible recursive render",
                token=token,
            )

        if carry_loop_iterations:
            loop_iteration_carry = reduce(
                mul,
                (loop.length for loop in self.loops),
                self.loop_iteration_carry,
            )
        else:
            loop_iteration_carry = 1

        if block_scope:
            ctx = self.__class__(
                template or self.template,
                global_data=ReadOnlyChainMap(namespace, self.scope),
                disabled_tags=disabled_tags,
                copy_depth=self._copy_depth + 1,
                parent=self,
                loop_iteration_carry=loop_iteration_carry,
                local_namespace_carry=self.get_size_of_locals(),
            )
            # This might need to be generalized so the caller can specify which
            # tag namespaces need to be copied.
            ctx.tag_namespace["extends"] = self.tag_namespace["extends"]
        else:
            ctx = self.__class__(
                template or self.template,
                global_data=ReadOnlyChainMap(namespace, self.globals),
                disabled_tags=disabled_tags,
                copy_depth=self._copy_depth + 1,
                parent=self,
                loop_iteration_carry=loop_iteration_carry,
                local_namespace_carry=self.get_size_of_locals(),
            )

        ctx.template = template or self.template
        return ctx

    def stopindex(self, key: str, index: int | None = None) -> int:
        """Set or return the stop index of a for loop."""
        if index is not None:
            self.tag_namespace["stopindex"][key] = index
            return index

        idx: int = self.tag_namespace["stopindex"].get(key, 0)
        return idx

    @contextmanager
    def loop(
        self, namespace: Mapping[str, object], forloop: ForLoop
    ) -> Iterator[RenderContext]:
        """Just like `Context.extend`, but keeps track of ForLoop objects too."""
        # TODO: self.raise_for_loop_limit(forloop.length)
        self.loops.append(forloop)
        with self.extend(namespace) as context:
            try:
                yield context
            finally:
                self.loops.pop()

    def parentloop(self, token: TokenT) -> Undefined | object:
        """Return the last ForLoop object from the loop stack."""
        try:
            return self.loops[-1]
        except IndexError:
            return self.env.undefined("parentloop", token=token)

    def get_output_buffer(self, parent_buffer: TextIO | None) -> StringIO:
        """Return a new output buffer respecting any limits set on the environment."""
        # TODO
        return StringIO()

    def markup(self, s: str) -> str | Markup:
        """Return a _safe_ string if auto escape is enabled."""
        return Markup(s) if self.auto_escape else s

    def cycle(self, cycle_hash: int, length: int) -> int:
        """Return the index of the next item in the named cycle."""
        namespace = self.tag_namespace["cycles"]
        if cycle_hash not in namespace:
            namespace[cycle_hash] = cycle(
                range(length)
            )  # TODO: benchmark without cycle
        return next(namespace[cycle_hash])  # type: ignore

    def increment(self, name: str) -> int:
        """Increment the named counter and return its value."""
        val: int = self.counters.get(name, 0)
        self.counters[name] = val + 1
        return val

    def decrement(self, name: str) -> int:
        """Decrement the named counter and return its value."""
        val: int = self.counters.get(name, 0) - 1
        self.counters[name] = val
        return val


class BuiltIn(Mapping[str, object]):
    """Mapping-like object for resolving built-in, dynamic objects."""

    def __contains__(self, item: object) -> bool:
        return item in ("now", "today")

    def __getitem__(self, key: str) -> object:
        if key == "now":
            return datetime.datetime.now()
        if key == "today":
            return datetime.date.today()
        raise KeyError(str(key))

    def __len__(self) -> int:
        return 2

    def __iter__(self) -> Iterator[str]:
        return iter(["now", "today"])


builtin = BuiltIn()