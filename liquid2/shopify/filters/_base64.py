"""Filter functions that operate on strings."""

from __future__ import annotations

import base64
import binascii

from liquid2.exceptions import LiquidValueError
from liquid2.filter import string_filter


@string_filter
def base64_encode(val: str) -> str:
    """Return _val_ encoded in base64."""
    return base64.b64encode(val.encode()).decode()


@string_filter
def base64_decode(val: str) -> str:
    """Return _val_ decoded as base64.

    The decoded value is assumed to be UTF-8 and will be decoded as UTF-8.
    """
    try:
        return base64.b64decode(val).decode()
    except binascii.Error as err:
        raise LiquidValueError("invalid base64-encoded string", token=None) from err


@string_filter
def base64_url_safe_encode(val: str) -> str:
    """Return _val_ encoded in URL-safe base64."""
    return base64.urlsafe_b64encode(val.encode()).decode()


@string_filter
def base64_url_safe_decode(val: str) -> str:
    """Return _val_ decoded as URL-safe base64.

    The decoded value is assumed to be UTF-8 and will be decoded as UTF-8.
    """
    try:
        return base64.urlsafe_b64decode(val).decode()
    except binascii.Error as err:
        raise LiquidValueError("invalid base64-encoded string", token=None) from err
