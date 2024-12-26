"""Translation filters."""

import re
from gettext import NullTranslations
from typing import Any
from typing import cast

from markupsafe import Markup

from liquid2 import Expression
from liquid2 import RenderContext
from liquid2.builtin import Filter
from liquid2.builtin import KeywordArgument
from liquid2.builtin import PositionalArgument
from liquid2.builtin import StringLiteral
from liquid2.filter import int_arg
from liquid2.messages import MESSAGES
from liquid2.messages import MessageText
from liquid2.messages import TranslatableFilter
from liquid2.messages import Translations
from liquid2.stringify import to_liquid_string

__all__ = [
    "Translate",
    "GetText",
    "NGetText",
    "PGetText",
    "NPGetText",
]


class BaseTranslateFilter:
    """Base class for the default translation filters.

    Args:
        translations_var: The name of a render context variable that resolves to a
            gettext `Translations` class. Defaults to `"translations"`.
        default_translations: A fallback translations class to use if
            `translations_var` can not be resolves. Defaults to `NullTranslations`.
        message_interpolation: If `True` (default), perform printf-style string
            interpolation on the translated message, using keyword arguments passed to
            the filter function.
        auto_escape_message: If `True` and the current environment has `auto_escape`
            set to `True`, the filter's left value will be escaped before translation.
            Defaults to `False`.
    """

    name = "base"
    re_vars = re.compile(r"(?<!%)%\((\w+)\)s")
    with_context = True

    def __init__(
        self,
        *,
        translations_var: str = "translations",
        default_translations: Translations | None = None,
        message_interpolation: bool = True,
        auto_escape_message: bool = False,
    ) -> None:
        self.translations_var = translations_var
        self.default_translations = default_translations or NullTranslations()
        self.message_interpolation = message_interpolation
        self.auto_escape_message = auto_escape_message

    def format_message(
        self, context: RenderContext, message_text: str, message_vars: dict[str, Any]
    ) -> str:
        """Return the message string formatted with the given message variables."""
        with context.extend(namespace=message_vars):
            _vars = {
                k: to_liquid_string(
                    context.resolve(k), auto_escape=context.env.auto_escape
                )
                for k in self.re_vars.findall(message_text)
            }

        # Missing variables get replaced by the current `Undefined` type and we're
        # converting all values to a string, so a KeyError or a ValueError should
        # be impossible.
        return message_text % _vars

    def _resolve_translations(self, context: RenderContext) -> Translations:
        return cast(
            Translations,
            context.resolve(self.translations_var, self.default_translations),
        )


class Translate(BaseTranslateFilter, TranslatableFilter):
    """A Liquid filter for translating strings to other languages.

    Depending on the keyword arguments provided when the resulting filter
    is called, it could behave like gettext, ngettext, pgettext or npgettext.
    """

    name = "t"

    def __call__(
        self,
        __left: object,
        __message_context: object = None,
        *,
        context: RenderContext,
        **kwargs: Any,
    ) -> str:
        """Apply the filter and return the result."""
        auto_escape = context.env.auto_escape
        __left = to_liquid_string(
            __left,
            auto_escape=auto_escape and self.auto_escape_message,
        )

        translations = self._resolve_translations(context)

        plural = kwargs.pop("plural", None)
        n = _count(kwargs.get("count"))

        if plural is not None and n is not None:
            plural = to_liquid_string(
                plural,
                auto_escape=auto_escape and self.auto_escape_message,
            )

            if __message_context is not None:
                text = translations.npgettext(
                    to_liquid_string(
                        __message_context,
                        auto_escape=auto_escape and self.auto_escape_message,
                    ),
                    __left,
                    plural,
                    n,
                )
            else:
                text = translations.ngettext(__left, plural, n)
        elif __message_context is not None:
            text = translations.pgettext(
                to_liquid_string(
                    __message_context,
                    auto_escape=auto_escape and self.auto_escape_message,
                ),
                __left,
            )
        else:
            text = translations.gettext(__left)

        if auto_escape:
            text = Markup(text)

        if self.message_interpolation:
            text = self.format_message(context, text, kwargs)

        return text

    def message(  # noqa: D102
        self,
        left: Expression,
        _filter: Filter,
        lineno: int,
    ) -> MessageText | None:
        if not isinstance(left, StringLiteral):
            return None

        if not _filter.args:
            return MessageText(
                lineno=lineno,
                funcname="gettext",
                message=(left.value,),
            )

        if isinstance(_filter.args[0], PositionalArgument):
            _context: Expression | None = _filter.args[0].value
        else:
            _context = None

        plural: Expression | None = None
        for arg in _filter.args:
            if isinstance(arg, KeywordArgument) and arg.name == "plural":
                plural = arg.value

        # Translate our filters into standard *gettext argument specs.

        if isinstance(plural, StringLiteral):
            if isinstance(_context, StringLiteral):
                funcname = "npgettext"
                message: MESSAGES = ((_context.value, "c"), left.value, plural.value)
            else:
                funcname = "ngettext"
                message = (left.value, plural.value)
        elif plural is not None:
            # Don't attempt to extract any messages if plural is given
            # but not a string literal
            return None
        elif isinstance(_context, StringLiteral):
            funcname = "pgettext"
            message = ((_context.value, "c"), left.value)
        else:
            funcname = "gettext"
            message = (left.value,)

        return MessageText(
            lineno=lineno,
            funcname=funcname,
            message=message,
        )


class GetText(BaseTranslateFilter, TranslatableFilter):
    """A Liquid filter equivalent of `gettext.gettext`."""

    name = "gettext"

    def __call__(  # noqa: D102
        self,
        __left: object,
        *,
        context: RenderContext,
        **kwargs: Any,
    ) -> str:
        auto_escape = context.env.auto_escape
        __left = to_liquid_string(
            __left,
            auto_escape=auto_escape and self.auto_escape_message,
        )

        translations = self._resolve_translations(context)
        text = translations.gettext(__left)

        if auto_escape:
            text = Markup(text)

        if self.message_interpolation:
            text = self.format_message(context, text, kwargs)

        return text

    def message(  # noqa: D102
        self,
        left: Expression,
        _filter: Filter,
        lineno: int,
    ) -> MessageText | None:
        if not isinstance(left, StringLiteral):
            return None

        return MessageText(
            lineno=lineno,
            funcname=self.name,
            message=(left.value,),
        )


class NGetText(BaseTranslateFilter, TranslatableFilter):
    """A Liquid filter equivalent of `gettext.ngettext`."""

    name = "ngettext"

    def __call__(
        self,
        __left: object,
        __plural: str,
        __count: object,
        *,
        context: RenderContext,
        **kwargs: Any,
    ) -> str:
        """Apply the filter and return the result."""
        auto_escape = context.env.auto_escape
        __left = to_liquid_string(
            __left,
            auto_escape=auto_escape and self.auto_escape_message,
        )

        __plural = to_liquid_string(
            __plural,
            auto_escape=auto_escape and self.auto_escape_message,
        )

        __count = int_arg(__count, default=1)

        translations = self._resolve_translations(context)
        text = translations.ngettext(__left, __plural, __count)

        if auto_escape:
            text = Markup(text)

        if self.message_interpolation:
            text = self.format_message(context, text, kwargs)

        return text

    def message(  # noqa: D102
        self,
        left: Expression,
        _filter: Filter,
        lineno: int,
    ) -> MessageText | None:
        if len(_filter.args) < 1:
            return None

        plural = _filter.args[0].value

        if not isinstance(left, StringLiteral) or not isinstance(plural, StringLiteral):
            return None

        return MessageText(
            lineno=lineno,
            funcname=self.name,
            message=(left.value, plural.value),
        )


class PGetText(BaseTranslateFilter, TranslatableFilter):
    """A Liquid filter equivalent of `gettext.pgettext`."""

    name = "pgettext"

    def __call__(  # noqa: D102
        self,
        __left: object,
        __message_context: str,
        *,
        context: RenderContext,
        **kwargs: Any,
    ) -> str:
        auto_escape = context.env.auto_escape
        __left = to_liquid_string(
            __left,
            auto_escape=auto_escape and self.auto_escape_message,
        )

        __message_context = to_liquid_string(
            __message_context,
            auto_escape=auto_escape and self.auto_escape_message,
        )

        translations = self._resolve_translations(context)
        text = translations.pgettext(__message_context, __left)

        if auto_escape:
            text = Markup(text)

        if self.message_interpolation:
            text = self.format_message(context, text, kwargs)

        return text

    def message(  # noqa: D102
        self, left: Expression, _filter: Filter, lineno: int
    ) -> MessageText | None:
        if len(_filter.args) < 1:
            return None

        ctx = _filter.args[0].value

        if not isinstance(left, StringLiteral) or not isinstance(ctx, StringLiteral):
            return None

        return MessageText(
            lineno=lineno,
            funcname=self.name,
            message=((ctx.value, "c"), left.value),
        )


class NPGetText(BaseTranslateFilter, TranslatableFilter):
    """A Liquid filter equivalent of `gettext.npgettext`."""

    name = "npgettext"

    def __call__(  # noqa: D102
        self,
        __left: object,
        __message_context: str,
        __plural: str,
        __count: object,
        *,
        context: RenderContext,
        **kwargs: Any,
    ) -> str:
        auto_escape = context.env.auto_escape
        __left = to_liquid_string(
            __left,
            auto_escape=auto_escape and self.auto_escape_message,
        )

        __message_context = to_liquid_string(
            __message_context,
            auto_escape=auto_escape and self.auto_escape_message,
        )

        __plural = to_liquid_string(
            __plural,
            auto_escape=auto_escape and self.auto_escape_message,
        )

        __count = int_arg(__count, default=1)

        translations = self._resolve_translations(context)
        text = translations.npgettext(
            __message_context,
            __left,
            __plural,
            __count,
        )

        if auto_escape:
            text = Markup(text)

        if self.message_interpolation:
            text = self.format_message(context, text, kwargs)

        return text

    def message(  # noqa: D102
        self,
        left: Expression,
        _filter: Filter,
        lineno: int,
    ) -> MessageText | None:
        if len(_filter.args) < 2:  # noqa: PLR2004
            return None

        ctx = _filter.args[0].value
        plural = _filter.args[1].value

        if (
            not isinstance(left, StringLiteral)
            or not isinstance(plural, StringLiteral)
            or not isinstance(ctx, StringLiteral)
        ):
            return None

        return MessageText(
            lineno=lineno,
            funcname=self.name,
            message=((ctx.value, "c"), left.value, plural.value),
        )


def _count(val: Any) -> int | None:
    if val in (None, False, True):
        return None
    try:
        return int(val)
    except ValueError:
        return None
