"""Manage undefined template variables.

When rendering a Liquid template, if a variable name can not be resolved, an instance of
liquid.Undefined, or a subclass, is used instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import Iterable
from typing import Iterator
from typing import Mapping
from typing import TypeGuard

from .exceptions import UndefinedError

if TYPE_CHECKING:
    from .token import TokenT

UNDEFINED = object()


class Undefined(Mapping[Any, object]):
    """The default undefined type.

    Always evaluates to an empty string. Can be iterated over and indexed without error.
    """

    __slots__ = ("path", "obj", "hint", "token")

    def __init__(
        self,
        path: str,
        *,
        token: TokenT | None,
        obj: object = UNDEFINED,
        hint: str | None = None,
    ):
        self.path = path
        self.token = token
        self.obj = obj
        self.hint = hint

    def __contains__(self, item: object) -> bool:
        return False

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Undefined) or other is None

    def __getitem__(self, key: str) -> object:
        return self

    def __len__(self) -> int:
        return 0

    def __iter__(self) -> Iterator[Any]:
        return iter([])

    def __str__(self) -> str:
        return ""

    def __repr__(self) -> str:  # pragma: no cover
        return f"Undefined({self.path})"

    def __int__(self) -> int:
        return 0

    def __hash__(self) -> int:
        return hash(self.path)

    def __reversed__(self) -> Iterable[Any]:
        return []

    def __liquid__(self) -> object:
        return None

    def poke(self) -> bool:
        """Prod the type, giving it the opertunity to raise an exception."""
        return True


class DebugUndefined(Undefined):
    """An undefined that returns debug information when rendered."""

    __slots__ = ()

    def __str__(self) -> str:
        if self.hint:
            return f"undefined: {self.hint}"
        if self.obj is not UNDEFINED:
            return f"{type(self.obj).__name__} has no attribute '{self.path}'"
        return f"'{self.path}' is undefined"

    def __repr__(self) -> str:  # pragma: no cover
        return f"Undefined({self.path})"


class StrictUndefined(Undefined):
    """An undefined that raises an exception for everything other than `repr`."""

    __slots__ = ("msg",)

    # Force the `default` filter to return its default value
    # without inspecting this class type.
    force_liquid_default = True

    # Properties that don't raise an UndefinedError.
    allowed_properties = frozenset(
        [
            "__repr__",
            "force_liquid_default",
            "name",
            "hint",
            "obj",
            "msg",
            "path",
            "token",
        ]
    )

    def __init__(
        self,
        path: str,
        *,
        token: TokenT | None,
        obj: object = UNDEFINED,
        hint: str | None = None,
    ):
        super().__init__(path, token=token, obj=obj, hint=hint)
        self.msg = self.hint if self.hint else f"'{self.path}' is undefined"

    def __getattribute__(self, name: str) -> object:
        if name in object.__getattribute__(self, "allowed_properties"):
            return object.__getattribute__(self, name)
        raise UndefinedError(object.__getattribute__(self, "msg"), token=self.token)

    def __contains__(self, item: object) -> bool:
        raise UndefinedError(self.msg, token=self.token)

    def __eq__(self, other: object) -> bool:
        raise UndefinedError(self.msg, token=self.token)

    def __getitem__(self, key: str) -> object:
        raise UndefinedError(self.msg, token=self.token)

    def __len__(self) -> int:
        raise UndefinedError(self.msg, token=self.token)

    def __iter__(self) -> Iterator[Any]:
        raise UndefinedError(self.msg, token=self.token)

    def __str__(self) -> str:
        raise UndefinedError(self.msg, token=self.token)

    def __repr__(self) -> str:
        return f"StrictUndefined({self.path})"

    def __bool__(self) -> bool:
        raise UndefinedError(self.msg, token=self.token)

    def __int__(self) -> int:
        raise UndefinedError(self.msg, token=self.token)

    def __hash__(self) -> int:
        raise UndefinedError(self.msg, token=self.token)

    def __reversed__(self) -> Iterable[Any]:
        raise UndefinedError(self.msg, token=self.token)


class FalsyStrictUndefined(StrictUndefined):
    """An strict undefined type that can be tested for truthiness."""

    allowed_properties = frozenset(
        [
            "__repr__",
            "__bool__",
            "__eq__",
            "__liquid__",
            "__class__",
            "name",
            "hint",
            "obj",
            "msg",
            "force_liquid_default",
            "path",
            "token",
        ]
    )

    def __bool__(self) -> bool:
        return False

    def __eq__(self, other: object) -> bool:
        return other is False


def is_undefined(obj: object) -> TypeGuard[Undefined]:
    """Return `True` if `obj` is undefined. `False` otherwise."""
    return isinstance(obj, Undefined)
