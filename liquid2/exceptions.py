"""Liquid specific Exceptions and warnings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .token import ErrorToken
from .token import PathToken
from .token import TagToken
from .token import Token
from .token import TokenType

if TYPE_CHECKING:
    from .token import TokenT


class LiquidError(Exception):
    """Base class for all Liquid exceptions."""

    def __init__(
        self,
        *args: object,
        token: TokenT | None,
        template_name: str | None = None,
    ):
        super().__init__(*args)
        self.token = token
        self.template_name = template_name

    def __str__(self) -> str:
        return self.detailed_message()

    def detailed_message(self) -> str:
        """Return an error message formatted with extra context info."""
        if not self.token or self.token.start < 0:
            return super().__str__()

        lineno, col, _prev, current, _next = self._error_context(
            self.token.source, self.token.start
        )

        template_and_pos = (
            f"{self.template_name}:{lineno}:{col}"
            if self.template_name
            else f"'{current}' {lineno}:{col}"
        )
        pad = " " * len(str(lineno))

        if isinstance(self.token, (TagToken, PathToken)):
            pointer = (" " * col) + (
                "^" * min(self.token.stop - self.token.start, len(current))
            )
        elif isinstance(self.token, (Token, ErrorToken)):
            # Special case for string literal tokens so we cover quote characters
            # with the pointer.
            length = len(self.token.value)
            if self.token.type_ in (
                TokenType.SINGLE_QUOTE_STRING,
                TokenType.DOUBLE_QUOTE_STRING,
            ):
                length += 2

            pointer = (" " * col) + ("^" * max(length, 1))
        else:
            pointer = (" " * (col - 1)) + "^"

        return (
            f"{self.message}\n"
            f"{pad} -> {template_and_pos}\n"
            f"{pad} |\n"
            f"{lineno} | {current}\n"
            f"{pad} | {pointer} {self._pointer_message()}\n"
        )

    @property
    def message(self) -> object:
        """The exception's error message if one was given."""
        if self.args:
            return self.args[0]
        return None

    def _pointer_message(self) -> object:
        return self.message

    def context(self) -> tuple[int, int, str, str, str] | None:
        """Return context information for this error.

        Returns (line, col, previous line, current line, next line) or None
        if no context information is available.
        """
        if self.token is None or self.token.start < 0:
            return None
        return self._error_context(self.token.source, self.token.start)

    def _error_context(self, text: str, index: int) -> tuple[int, int, str, str, str]:
        lines = text.splitlines(keepends=True)
        cumulative_length = 0
        target_line_index = -1

        for i, line in enumerate(lines):
            cumulative_length += len(line)
            if index < cumulative_length:
                target_line_index = i
                break

        if target_line_index == -1:
            raise ValueError("index is out of bounds for the given string")

        # Line number (1-based)
        line_number = target_line_index + 1
        # Column number within the line
        column_number = index - (cumulative_length - len(lines[target_line_index]))

        previous_line = (
            lines[target_line_index - 1].rstrip() if target_line_index > 0 else ""
        )
        current_line = lines[target_line_index].rstrip()
        next_line = (
            lines[target_line_index + 1].rstrip()
            if target_line_index < len(lines) - 1
            else ""
        )

        return line_number, column_number, previous_line, current_line, next_line


class LiquidInterrupt(Exception):  # noqa: N818
    """Loop interrupt exception."""


class StopRender(Exception):  # noqa: N818
    """Template inheritance interrupt.

    An interrupt used to signal that `BoundTemplate.render_with_context` should stop
    rendering more nodes. This is used by template inheritance tags and is not an error
    condition.
    """


class LiquidEnvironmentError(LiquidError):
    """An exception raised due to a misconfigured environment."""


class LiquidSyntaxError(LiquidError):
    """Exception raised when there is a parser error."""


class TemplateInheritanceError(LiquidError):
    """An exceptions raised when template inheritance tags are used incorrectly.

    This could occur when parsing a template or at render time.
    """


class RequiredBlockError(TemplateInheritanceError):
    """An exception raised when a required block has not been overridden."""


class LiquidTypeError(LiquidError):
    """Exception raised when an error occurs at render time."""


class LiquidIndexError(LiquidError):
    """An exception raised when a sequence index is out of range."""


class LiquidNameError(LiquidError):
    """An exception raised when an unknown function extension is called."""


class DisabledTagError(LiquidError):
    """Exception raised when an attempt is made to render a disabled tag."""


class UnknownFilterError(LiquidError):  # noqa: N818
    """Exception raised when a filter lookup fails."""


class TemplateNotFoundError(LiquidError):
    """Exception raised when a template could not be found."""

    def __init__(
        self,
        *args: object,
        filename: str | None = None,
    ):
        super().__init__(*args, token=None, template_name=filename)

    def __str__(self) -> str:
        if not self.token:
            return repr(super().__str__())
        return super().__str__()

    def _pointer_message(self) -> object:
        if self.args:
            if self.token:
                return "template not found"
            return self.args[0]
        return None


class ResourceLimitError(LiquidError):
    """Base class for exceptions relating to resource limits."""


class ContextDepthError(ResourceLimitError):
    """Exception raised when the maximum context depth is reached.

    Usually indicates recursive use of `render` or `include` tags.
    """


class LoopIterationLimitError(ResourceLimitError):
    """Exception raised when the loop iteration limit has been exceeded."""


class OutputStreamLimitError(ResourceLimitError):
    """Exception raised when an output stream limit has been exceeded."""


class LocalNamespaceLimitError(ResourceLimitError):
    """Exception raised when a local namespace limit has been exceeded."""


class LiquidValueError(LiquidError):
    """Exception raised when a cast from str to int exceeds the length limit."""


class UndefinedError(LiquidError):
    """Exception raised by the StrictUndefined type."""


class BreakLoop(LiquidInterrupt):
    """Exception raised when a BreakNode is rendered."""


class ContinueLoop(LiquidInterrupt):
    """Exception raised when a ContinueNode is rendered."""


class TranslationError(LiquidError):
    """Base exception for translation errors."""


class TranslationSyntaxError(LiquidSyntaxError):
    """Exception raised when a syntax error is found within a translation block."""


class TranslationValueError(TranslationError):
    """Exception raised when message interpolation fails with a ValueError."""


class TranslationKeyError(TranslationError):
    """Exception raised when message interpolation fails with a KeyError."""
