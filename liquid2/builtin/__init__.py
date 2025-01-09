"""Filters, tags and expressions built-in to Liquid."""

from __future__ import annotations

from gettext import NullTranslations
from typing import TYPE_CHECKING

from .comment import Comment
from .content import Content
from .expressions import Blank
from .expressions import BooleanExpression
from .expressions import Continue
from .expressions import Empty
from .expressions import EqExpression
from .expressions import FalseLiteral
from .expressions import Filter
from .expressions import FilteredExpression
from .expressions import FloatLiteral
from .expressions import Identifier
from .expressions import IntegerLiteral
from .expressions import KeywordArgument
from .expressions import Literal
from .expressions import LogicalAndExpression
from .expressions import LogicalNotExpression
from .expressions import LogicalOrExpression
from .expressions import LoopExpression
from .expressions import Null
from .expressions import Parameter
from .expressions import Path
from .expressions import PositionalArgument
from .expressions import RangeLiteral
from .expressions import StringLiteral
from .expressions import TernaryFilteredExpression
from .expressions import TrueLiteral
from .expressions import is_blank
from .expressions import is_empty
from .expressions import is_truthy
from .expressions import parse_identifier
from .expressions import parse_keyword_arguments
from .expressions import parse_parameters
from .expressions import parse_positional_and_keyword_arguments
from .expressions import parse_primitive
from .expressions import parse_string_or_identifier
from .expressions import parse_string_or_path
from .filters.array import compact
from .filters.array import concat
from .filters.array import first
from .filters.array import join
from .filters.array import last
from .filters.array import map_
from .filters.array import reverse
from .filters.array import sort
from .filters.array import sort_natural
from .filters.array import sort_numeric
from .filters.array import sum_
from .filters.array import uniq
from .filters.array import where
from .filters.babel import Currency
from .filters.babel import DateTime
from .filters.babel import Number
from .filters.babel import Unit
from .filters.math import abs_
from .filters.math import at_least
from .filters.math import at_most
from .filters.math import ceil
from .filters.math import divided_by
from .filters.math import floor
from .filters.math import minus
from .filters.math import modulo
from .filters.math import plus
from .filters.math import round_
from .filters.math import times
from .filters.misc import JSON
from .filters.misc import date
from .filters.misc import default
from .filters.misc import size
from .filters.string import append
from .filters.string import capitalize
from .filters.string import downcase
from .filters.string import escape
from .filters.string import escape_once
from .filters.string import lstrip
from .filters.string import newline_to_br
from .filters.string import prepend
from .filters.string import remove
from .filters.string import remove_first
from .filters.string import remove_last
from .filters.string import replace
from .filters.string import replace_first
from .filters.string import replace_last
from .filters.string import rstrip
from .filters.string import safe
from .filters.string import slice_
from .filters.string import split
from .filters.string import strip
from .filters.string import strip_html
from .filters.string import strip_newlines
from .filters.string import truncate
from .filters.string import truncatewords
from .filters.string import upcase
from .filters.string import url_decode
from .filters.string import url_encode
from .filters.translate import BaseTranslateFilter
from .filters.translate import GetText
from .filters.translate import NGetText
from .filters.translate import NPGetText
from .filters.translate import PGetText
from .filters.translate import Translate
from .loaders.caching_file_system_loader import CachingFileSystemLoader
from .loaders.choice_loader import CachingChoiceLoader
from .loaders.choice_loader import ChoiceLoader
from .loaders.dict_loader import CachingDictLoader
from .loaders.dict_loader import DictLoader
from .loaders.file_system_loader import FileSystemLoader
from .loaders.mixins import CachingLoaderMixin
from .loaders.package_loader import PackageLoader
from .output import Output
from .tags.assign_tag import AssignTag
from .tags.capture_tag import CaptureTag
from .tags.case_tag import CaseTag
from .tags.cycle_tag import CycleTag
from .tags.decrement_tag import DecrementTag
from .tags.echo_tag import EchoTag
from .tags.extends_tag import BlockTag
from .tags.extends_tag import ExtendsTag
from .tags.for_tag import BreakTag
from .tags.for_tag import ContinueTag
from .tags.for_tag import ForTag
from .tags.if_tag import IfTag
from .tags.include_tag import IncludeTag
from .tags.increment_tag import IncrementTag
from .tags.liquid_tag import LiquidTag
from .tags.macro_tag import CallTag
from .tags.macro_tag import MacroTag
from .tags.raw_tag import RawTag
from .tags.render_tag import RenderTag
from .tags.translate_tag import TranslateTag
from .tags.unless_tag import UnlessTag
from .tags.with_tag import WithTag

if TYPE_CHECKING:
    from ..environment import Environment  # noqa: TID252
    from ..messages import Translations  # noqa: TID252


__all__ = (
    "abs_",
    "AssignTag",
    "at_least",
    "at_most",
    "Blank",
    "BlockTag",
    "Boolean",
    "BooleanExpression",
    "BreakTag",
    "CachingChoiceLoader",
    "CachingDictLoader",
    "CachingFileSystemLoader",
    "CaptureTag",
    "CaseTag",
    "ceil",
    "ChoiceLoader",
    "Comment",
    "Content",
    "Continue",
    "ContinueTag",
    "CycleTag",
    "date",
    "DecrementTag",
    "default",
    "DictLoader",
    "divided_by",
    "EchoTag",
    "Empty",
    "EqExpression",
    "ExtendsTag",
    "FalseLiteral",
    "FileSystemLoader",
    "Filter",
    "FilteredExpression",
    "FilteredExpression",
    "FloatLiteral",
    "floor",
    "ForTag",
    "Identifier",
    "IfTag",
    "IncludeTag",
    "IncrementTag",
    "IntegerLiteral",
    "is_blank",
    "is_empty",
    "is_truthy",
    "KeywordArgument",
    "LiquidTag",
    "Literal",
    "LogicalAndExpression",
    "LogicalNotExpression",
    "LogicalOrExpression",
    "LoopExpression",
    "minus",
    "modulo",
    "Null",
    "Output",
    "PackageLoader",
    "parse_identifier",
    "parse_keyword_arguments",
    "parse_positional_and_keyword_arguments",
    "parse_primitive",
    "parse_string_or_identifier",
    "Path",
    "plus",
    "PositionalArgument",
    "RangeLiteral",
    "RawTag",
    "register_default_tags_and_filters",
    "RenderTag",
    "round_",
    "safe",
    "size",
    "StringLiteral",
    "TernaryFilteredExpression",
    "times",
    "TrueLiteral",
    "UnlessTag",
    "parse_string_or_path",
    "register_translation_filters",
    "Currency",
    "GetText",
    "NGetText",
    "NPGetText",
    "PGetText",
    "Translate",
    "DataTime",
    "Number",
    "Unit",
    "DateTime",
    "parse_parameters",
    "Parameter",
    "WithTag",
    "JSON",
    "CachingLoaderMixin",
    "BaseTranslateFilter",
)


def register_default_tags_and_filters(env: Environment) -> None:  # noqa: PLR0915
    """Register standard tags and filters with an environment."""
    env.filters["join"] = join
    env.filters["first"] = first
    env.filters["last"] = last
    env.filters["concat"] = concat
    env.filters["map"] = map_
    env.filters["reverse"] = reverse
    env.filters["sort"] = sort
    env.filters["sort_natural"] = sort_natural
    env.filters["sort_numeric"] = sort_numeric
    env.filters["sum"] = sum_
    env.filters["where"] = where
    env.filters["uniq"] = uniq
    env.filters["compact"] = compact

    env.filters["abs"] = abs_
    env.filters["at_least"] = at_least
    env.filters["at_most"] = at_most
    env.filters["ceil"] = ceil
    env.filters["divided_by"] = divided_by
    env.filters["floor"] = floor
    env.filters["minus"] = minus
    env.filters["modulo"] = modulo
    env.filters["plus"] = plus
    env.filters["round"] = round_
    env.filters["times"] = times

    env.filters["date"] = date
    env.filters["default"] = default
    env.filters["size"] = size
    env.filters["json"] = JSON()

    env.filters["capitalize"] = capitalize
    env.filters["append"] = append
    env.filters["downcase"] = downcase
    env.filters["escape"] = escape
    env.filters["escape_once"] = escape_once
    env.filters["lstrip"] = lstrip
    env.filters["newline_to_br"] = newline_to_br
    env.filters["prepend"] = prepend
    env.filters["remove"] = remove
    env.filters["remove_first"] = remove_first
    env.filters["remove_last"] = remove_last
    env.filters["replace"] = replace
    env.filters["replace_first"] = replace_first
    env.filters["replace_last"] = replace_last
    env.filters["safe"] = safe
    env.filters["slice"] = slice_
    env.filters["split"] = split
    env.filters["upcase"] = upcase
    env.filters["strip"] = strip
    env.filters["rstrip"] = rstrip
    env.filters["safe"] = safe
    env.filters["strip_html"] = strip_html
    env.filters["strip_newlines"] = strip_newlines
    env.filters["truncate"] = truncate
    env.filters["truncatewords"] = truncatewords
    env.filters["url_encode"] = url_encode
    env.filters["url_decode"] = url_decode

    env.filters[GetText.name] = GetText(auto_escape_message=env.auto_escape)
    env.filters[NGetText.name] = NGetText(auto_escape_message=env.auto_escape)
    env.filters[NPGetText.name] = NPGetText(auto_escape_message=env.auto_escape)
    env.filters[PGetText.name] = PGetText(auto_escape_message=env.auto_escape)
    env.filters[Translate.name] = Translate(auto_escape_message=env.auto_escape)
    env.filters["currency"] = Currency()
    env.filters["money"] = Currency()
    env.filters["money_with_currency"] = Currency(default_format="¤#,##0.00 ¤¤")
    env.filters["money_without_currency"] = Currency(default_format="#,##0.00")
    env.filters["money_without_trailing_zeros"] = Currency(
        default_format="¤#,###",
        currency_digits=False,
    )
    env.filters["datetime"] = DateTime()
    env.filters["decimal"] = Number()
    env.filters["unit"] = Unit()

    env.tags["__COMMENT"] = Comment(env)
    env.tags["__CONTENT"] = Content(env)
    env.tags["__OUTPUT"] = Output(env)
    env.tags["__RAW"] = RawTag(env)
    env.tags["assign"] = AssignTag(env)
    env.tags["if"] = IfTag(env)
    env.tags["unless"] = UnlessTag(env)
    env.tags["for"] = ForTag(env)
    env.tags["break"] = BreakTag(env)
    env.tags["continue"] = ContinueTag(env)
    env.tags["capture"] = CaptureTag(env)
    env.tags["case"] = CaseTag(env)
    env.tags["cycle"] = CycleTag(env)
    env.tags["decrement"] = DecrementTag(env)
    env.tags["increment"] = IncrementTag(env)
    env.tags["echo"] = EchoTag(env)
    env.tags["include"] = IncludeTag(env)
    env.tags["render"] = RenderTag(env)
    env.tags["__LINES"] = LiquidTag(env)
    env.tags["block"] = BlockTag(env)
    env.tags["extends"] = ExtendsTag(env)
    env.tags["translate"] = TranslateTag(env)
    env.tags["macro"] = MacroTag(env)
    env.tags["call"] = CallTag(env)
    env.tags["with"] = WithTag(env)


def register_translation_filters(
    env: Environment,
    *,
    replace: bool = True,
    translations_var: str = "translations",
    default_translations: Translations | None = None,
    message_interpolation: bool = True,
    autoescape_message: bool = False,
) -> None:
    """Add gettext-style translation filters to a Liquid environment.

    Args:
        env: The liquid.Environment to add translation filters to.
        replace: If True, existing filters with conflicting names will
            be replaced. Defaults to False.
        translations_var: The name of a render context variable that
            resolves to a gettext `Translations` class. Defaults to
            `"translations"`.
        default_translations: A fallback translations class to use if
            `translations_var` can not be resolves. Defaults to
            `NullTranslations`.
        message_interpolation: If `True` (default), perform printf-style
            string interpolation on the translated message, using keyword arguments
            passed to the filter function.
        autoescape_message: If `True` and the current environment has
            `autoescape` set to `True`, the filter's left value will be escaped
            before translation. Defaults to `False`.
    """
    default_translations = default_translations or NullTranslations()
    default_filters = (
        Translate,
        GetText,
        NGetText,
        PGetText,
        NPGetText,
    )
    for _filter in default_filters:
        if replace or _filter.name not in env.filters:
            env.filters[_filter.name] = _filter(
                translations_var=translations_var,
                default_translations=default_translations,
                message_interpolation=message_interpolation,
                auto_escape_message=autoescape_message,
            )
