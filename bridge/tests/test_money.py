from decimal import Decimal

import pytest

from core.money import MoneyError, format_inr, to_decimal_string, to_paise


@pytest.mark.parametrize(
    "value,expected",
    [
        ("1234.50", 123450),
        ("1,23,456.78", 12345678),
        ("180", 18000),
        ("180.5", 18050),
        ("0.01", 1),
        ("-250.00", -25000),
        (" 99.90 ", 9990),
        ("12.500000000000", 1250),  # Firefly pads balances like this
        (Decimal("0.10"), 10),
        (7, 700),
    ],
)
def test_to_paise(value, expected):
    assert to_paise(value) == expected


@pytest.mark.parametrize("value", [12.5, 0.1, True, None, "", "abc", "1.005", "NaN", "Infinity", Decimal("0.001")])
def test_to_paise_rejects(value):
    with pytest.raises(MoneyError):
        to_paise(value)


def test_no_float_drift():
    # 0.1 + 0.2 != 0.3 in floats; in paise it is exact.
    assert to_paise("0.10") + to_paise("0.20") == to_paise("0.30")


@pytest.mark.parametrize(
    "paise,expected",
    [(123450, "1234.50"), (1, "0.01"), (0, "0.00"), (-25000, "-250.00"), (-5, "-0.05"), (10**12 + 7, "10000000000.07")],
)
def test_to_decimal_string(paise, expected):
    assert to_decimal_string(paise) == expected
    assert to_paise(expected) == paise  # round trip


@pytest.mark.parametrize("value", [1.0, "100", True, None])
def test_to_decimal_string_rejects(value):
    with pytest.raises(MoneyError):
        to_decimal_string(value)


@pytest.mark.parametrize(
    "paise,expected",
    [
        (0, "₹0.00"),
        (99900, "₹999.00"),
        (100000, "₹1,000.00"),
        (10000000, "₹1,00,000.00"),  # one lakh
        (1000000000, "₹1,00,00,000.00"),  # one crore
        (123456789, "₹12,34,567.89"),
        (-12345678, "-₹1,23,456.78"),
    ],
)
def test_format_inr(paise, expected):
    assert format_inr(paise) == expected
