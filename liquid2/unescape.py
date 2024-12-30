"""Replace escape sequences with their Unicode equivalents."""

from .exceptions import LiquidSyntaxError
from .token import TokenT


def unescape(value: str, token: TokenT) -> str:
    """Return _value_ with escape sequences replaced with their Unicode equivalents."""
    unescaped: list[str] = []
    index = 0

    while index < len(value):
        ch = value[index]
        if ch == "\\":
            index += 1
            _ch, index = _decode_escape_sequence(value, index, token)
            unescaped.append(_ch)
        else:
            _string_from_code_point(ord(ch), token)
            unescaped.append(ch)
        index += 1

    return "".join(unescaped)


def _decode_escape_sequence(  # noqa: PLR0911
    value: str, index: int, token: TokenT
) -> tuple[str, int]:
    ch = value[index]
    if ch == '"':
        return '"', index
    if ch == "$":
        # For escaping string interpolation.
        return "$", index
    if ch == "\\":
        return "\\", index
    if ch == "/":
        return "/", index
    if ch == "b":
        return "\x08", index
    if ch == "f":
        return "\x0c", index
    if ch == "n":
        return "\n", index
    if ch == "r":
        return "\r", index
    if ch == "t":
        return "\t", index
    if ch == "u":
        code_point, index = _decode_hex_char(value, index, token)
        return _string_from_code_point(code_point, token), index

    raise LiquidSyntaxError(
        f"unknown escape sequence at index {token.start + index - 1}",
        token=token,
    )


def _decode_hex_char(value: str, index: int, token: TokenT) -> tuple[int, int]:
    length = len(value)

    if index + 4 >= length:
        raise LiquidSyntaxError(
            f"incomplete escape sequence at index {token.start + index - 1}",
            token=token,
        )

    index += 1  # move past 'u'
    code_point = _parse_hex_digits(value[index : index + 4], token)

    if _is_low_surrogate(code_point):
        raise LiquidSyntaxError(
            f"unexpected low surrogate at index {token.start + index - 1}",
            token=token,
        )

    if _is_high_surrogate(code_point):
        # expect a surrogate pair
        if not (
            index + 9 < length and value[index + 4] == "\\" and value[index + 5] == "u"
        ):
            raise LiquidSyntaxError(
                f"incomplete escape sequence at index {token.start + index - 2}",
                token=token,
            )

        low_surrogate = _parse_hex_digits(value[index + 6 : index + 10], token)

        if not _is_low_surrogate(low_surrogate):
            raise LiquidSyntaxError(
                f"unexpected code_point at index {token.start + index + 4}",
                token=token,
            )

        code_point = 0x10000 + (
            ((code_point & 0x03FF) << 10) | (low_surrogate & 0x03FF)
        )

        return (code_point, index + 9)

    return (code_point, index + 3)


def _parse_hex_digits(digits: str, token: TokenT) -> int:
    code_point = 0
    for digit in digits.encode():
        code_point <<= 4
        if digit >= 48 and digit <= 57:
            code_point |= digit - 48
        elif digit >= 65 and digit <= 70:
            code_point |= digit - 65 + 10
        elif digit >= 97 and digit <= 102:
            code_point |= digit - 97 + 10
        else:
            raise LiquidSyntaxError(
                "invalid \\uXXXX escape sequence",
                token=token,
            )
    return code_point


def _string_from_code_point(code_point: int, token: TokenT) -> str:
    if code_point < 8:
        raise LiquidSyntaxError("invalid character", token=token)
    return chr(code_point)


def _is_high_surrogate(code_point: int) -> bool:
    return code_point >= 0xD800 and code_point <= 0xDBFF


def _is_low_surrogate(code_point: int) -> bool:
    return code_point >= 0xDC00 and code_point <= 0xDFFF
