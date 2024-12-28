from liquid2 import render


def test_integer_literal_with_exponent() -> None:
    assert render("{{ 1e2 }}") == "100"


def test_integer_literal_with_exponent_upper_case_e() -> None:
    assert render("{{ 1E2 }}") == "100"


def test_integer_literal_with_zero_exponent() -> None:
    assert render("{{ 1e0 }}") == "1"


def test_integer_literal_with_positive_exponent() -> None:
    assert render("{{ 1e+2 }}") == "100"


def test_integer_literal_with_negative_exponent() -> None:
    assert render("{{ 1e-2 }}") == "0.01"


def test_integer_literal_with_negative_zero_exponent() -> None:
    assert render("{{ 1e-0 }}") == "1.0"


def test_float_literal_with_exponent() -> None:
    assert render("{{ 1.2e2 }}") == "120.0"


def test_float_literal_with_negative_exponent() -> None:
    assert render("{{ 1.2e-2 }}") == "0.012"
