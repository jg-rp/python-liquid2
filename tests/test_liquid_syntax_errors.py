import operator
from typing import NamedTuple

import pytest

from liquid2 import parse
from liquid2.exceptions import LiquidSyntaxError


class Case(NamedTuple):
    description: str
    template: str
    expect_msg: str


test_cases = [
    Case(
        description="no expression",
        template="{% if %}foo{% endif %}",
        expect_msg="missing expression",
    ),
    Case(
        description="end tag mismatch",
        template="{% if true %}foo{% endunless %}",
        expect_msg="unexpected tag 'endunless'",
    ),
    Case(
        description="unexpected outer tag name",
        template="{% foo true %}foo{% endfoo %}",
        expect_msg="unexpected tag 'foo'",
    ),
    Case(
        description="missing tag name",
        template="{% %}foo{% endif %}",
        expect_msg="unexpected tag 'endif'",
    ),
    Case(
        description="missing end tag at EOF",
        template="{% if true %}foo{% assign bar = 'baz' %}",
        expect_msg="expected tag 'endif', found EOI",
    ),
    Case(
        description="orphaned break",
        template="{% break %}",
        expect_msg="unexpected 'break'",
    ),
    Case(
        description="orphaned continue",
        template="{% continue %}",
        expect_msg="unexpected 'continue'",
    ),
    Case(
        description="orphaned else",
        template="{% else %}",
        expect_msg="unexpected tag 'else'",
    ),
    Case(
        description="orphaned when",
        template="{% when %}",
        expect_msg="unexpected tag 'when'",
    ),
    Case(
        description="missing 'in' in forloop",
        template="{% for x (0..3) %}{{ x }}{% endfor %}",
        expect_msg="expected IN, found RANGE",
    ),
    Case(
        description="missing range or identifier in forloop",
        template="{% for x in %}{{ x }}foo{% endfor %}",
        expect_msg="expected a primitive expression, found EOI",
    ),
    Case(
        description="float with trailing dot in range literal",
        template="{% for x in (2...4) %}{{ x }}{% endfor %}",
        expect_msg="unexpected '.'",
    ),
    Case(
        description="chained identifier for loop variable",
        template="{% for x.y in (2...4) %}{{ x }}{% endfor %}",
        expect_msg="unexpected '.'",
    ),
    Case(
        description="missing equal in assignment tag",
        template="{% assign x 5 %}",
        expect_msg="expected ASSIGN, found INT",
    ),
    Case(
        description="invalid subscript identifier",
        template="{{ foo[1.2] }}",
        expect_msg="invalid variable path",
    ),
    Case(
        description="minus string",
        template="{{ -'foo' }}",
        expect_msg="unexpected '-'",
    ),
    Case(
        description="unknown prefix operator",
        template="{{ +5 }}",
        expect_msg=r"unexpected '\+'",
    ),
    Case(
        description="float literal without a leading zero",
        template="{{ .1 }}",
        expect_msg="unexpected '.'",
    ),
    Case(
        description="unknown infix operator",
        template="{% if 1 =! 2 %}ok{% endif %}",
        expect_msg="unexpected '!'",
    ),
    Case(
        description="bad 'unless' expression",
        template="{% unless 1 ~ 2 %}ok{% endunless %}",
        expect_msg="unexpected '~'",
    ),
    Case(
        description="bad conditional expression in unless block",
        template="{% unless true %}ok{% elsif £$! %}{% endunless %}",
        expect_msg=r"unexpected token '\$'",
    ),
    Case(
        description="unknown infix operator",
        template="{% if 1 ~ 2 %}ok{% endif %}",
        expect_msg="unexpected '~'",
    ),
    Case(
        description="bad alternative condition expression",
        template="{% if false %}ok{% elsif 1~=2 %}not ok{% endif %}",
        expect_msg="unexpected '~'",
    ),
    Case(
        description="junk in `liquid` tag",
        template="\n".join(
            [
                r"{{ 'hello' }}",
                r"{% liquid",
                r"echo 'foo'",
                r"aiu34bseu",
                r"%}",
            ]
        ),
        expect_msg="unexpected tag 'aiu34bseu'",
    ),
    Case(
        description="bad token in loop expression",
        template="{% for i$ in (1..3) %}{% endfor %}",
        expect_msg=r"unexpected token '\$'",
    ),
    Case(
        description="invalid loop argument",
        template="{% for product in collections[0]['tags'] limit:| %}{% endfor %}",
        expect_msg="unexpected '|'",
    ),
    Case(
        description="unexpected token between left value and filter",
        template=r'{{ "hello" boo | upcase }}',
        expect_msg="unexpected token 'boo'",
    ),
    Case(
        description="unexpected token after left value and no filters",
        template=r'{{ "hello" offset:2 }}',
        expect_msg="unexpected token 'offset'",
    ),
    Case(
        description="extra 'else' block",
        template=r"{% if true %}a{% else %}b{% else %}c{% endif %}",
        expect_msg="expected tag 'endif', found 'else'",
    ),
    Case(
        description="extra 'elsif' block",
        template=r"{% if true %}a{% else %}b{% elsif %}c{% endif %}",
        expect_msg="expected tag 'endif', found 'elsif'",
    ),
    Case(
        description="missing output closing bracket",
        template=r"Hello, {{you}!",
        expect_msg="missing bracket detected",
    ),
    Case(
        description="missing tag closing percent",
        template=r"{% assign x = 42 }",
        expect_msg="missing percent detected",
    ),
    Case(
        description="missing tag closing bracket",
        template=r"{% assign x = 42 %",
        expect_msg="missing bracket detected",
    ),
    Case(
        description="include, target not a path or string",
        template="{% include 42 with product['some-tags'] as foo.bar %}",
        expect_msg="expected a string or path, found INT",
    ),
    Case(
        description="include, multi-segmented alias",
        template="{% include 'feature.liquid' with product['some-tags'] as foo.bar %}",
        expect_msg="expected an identifier, found PATH",
    ),
    Case(
        description="chained keyword identifier",
        template="{% include 'product.liquid', foo.bar: 'hello' %}",
        expect_msg="expected an argument name, found PATH",
    ),
    Case(
        description="unexpected identifier character",
        template=r"{% assign foo+bar = 'hello there'%}{{ foo+bar }}",
        expect_msg=r"unexpected '\+'",
    ),
    Case(
        description="unexpected assign path",
        template=r"{% assign foo.bar = 'hello there' %}{{ foo.bar }}",
        expect_msg="expected an identifier, found PATH",
    ),
    Case(
        description="unexpected capture path",
        template=r"{% capture foo.bar %}{% endcapture %}",
        expect_msg="expected an identifier, found PATH",
    ),
    Case(
        description="consecutive commas in keyword argument list",
        template=r"{% with you='world',, some='thing' %}Hello, {{ you }}!{% endwith %}",
        expect_msg="expected an argument name, found COMMA",
    ),
    Case(
        description="consecutive commas in positional argument list",
        template=r"{% call macro a,, b %}",
        expect_msg="expected a primitive expression, found COMMA",
    ),
    Case(
        description="template string, unbalanced quotes",
        template=r'{{ "Hello, ${you["there]}!" }}',
        expect_msg="invalid variable path",
    ),
    Case(
        description="template string, missing closing bracket",
        template=r'{{ "Hello, ${you" }}',
        expect_msg="unclosed string or template string expression",
    ),
    Case(
        description="template string, missing closing quote",
        template=r'{{ "Hello, ${you} }}',
        expect_msg="unclosed string or template string expression",
    ),
    Case(
        description="path, empty brackets",
        template=r"{{ a.b[] }}",
        expect_msg="empty bracketed segment",
    ),
    Case(
        description="path, unbalanced brackets",
        template=r"{{ a.b['foo']] }}",
        expect_msg="unbalanced brackets",
    ),
]


@pytest.mark.parametrize("case", test_cases, ids=operator.attrgetter("description"))
def test_syntax_errors(case: Case) -> None:
    with pytest.raises(LiquidSyntaxError, match=case.expect_msg):
        parse(case.template).render()
