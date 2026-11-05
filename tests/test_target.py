"""Functional tests for target.py.

Every one of the 16 functions is tested for:
  * valid inputs (typical values),
  * boundary values (the exact edges where behaviour changes),
  * invalid values (the documented exceptions, with exact class + message),
  * wrong types (what the function really does with a bad type).

Rules followed:
  * exact equality and ``is True`` / ``is False`` wherever the result is exact;
  * ``pytest.approx`` ONLY for results that are inexact floats;
  * result *types* are asserted where they are part of the contract;
  * no skip / xfail.
"""

import math

import pytest

import target

# --------------------------------------------------------------------------- #
# 1. is_adult (integer)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (0, False),  # lower boundary of valid input
        (1, False),
        (10, False),
        (17, False),  # just below threshold
        (18, True),  # exact threshold
        (19, True),  # just above threshold
        (65, True),
        (150, True),
        (17.99, False),  # floats close to the threshold
        (18.0, True),
    ],
)
def test_is_adult_valid_and_boundaries(age, expected):
    result = target.is_adult(age)
    assert result is expected  # also proves the result is a real bool


@pytest.mark.parametrize("age", [-1, -18, -0.5, -1000])
def test_is_adult_negative_raises_value_error(age):
    with pytest.raises(ValueError, match=r"^age cannot be negative$"):
        target.is_adult(age)


@pytest.mark.parametrize("age", ["18", None, [18], {"age": 18}])
def test_is_adult_wrong_type_raises_type_error(age):
    with pytest.raises(TypeError):
        target.is_adult(age)


# --------------------------------------------------------------------------- #
# 2. celsius_to_fahrenheit (float)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("celsius", "expected"),
    [
        (0, 32.0),  # freezing point
        (100, 212.0),  # boiling point
        (-40, -40.0),  # the two scales cross here
        (37, 98.6),
        (36.6, 97.88),  # needs 2 decimals (1 decimal would give 97.9)
        (-273.15, -459.67),  # absolute zero
        (1, 33.8),
        (-17.78, -0.0),  # rounds to zero
        (0.005, 32.01),  # tiny value still visible at 2 decimals
        (1 / 3, 32.6),  # long float is rounded
        (1000, 1832.0),
    ],
)
def test_celsius_to_fahrenheit_values(celsius, expected):
    result = target.celsius_to_fahrenheit(celsius)
    # round(x, 2) is deterministic, so exact comparison is correct here
    assert result == expected
    assert isinstance(result, float)


@pytest.mark.parametrize("celsius", [0.123, 25.555, -12.3456, 1 / 7])
def test_celsius_to_fahrenheit_has_at_most_two_decimals(celsius):
    result = target.celsius_to_fahrenheit(celsius)
    assert result == round(result, 2)
    assert result == pytest.approx(celsius * 9 / 5 + 32, abs=0.005)


@pytest.mark.parametrize("celsius", ["0", None, [0]])
def test_celsius_to_fahrenheit_wrong_type_raises_type_error(celsius):
    with pytest.raises(TypeError):
        target.celsius_to_fahrenheit(celsius)


# --------------------------------------------------------------------------- #
# 3. count_vowels (string)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", 0),  # empty string
        ("a", 1),
        ("e", 1),
        ("i", 1),
        ("o", 1),
        ("u", 1),  # every vowel individually
        ("aeiou", 5),
        ("AEIOU", 5),  # upper case is counted
        ("AeIoU", 5),
        ("bcdfg", 0),  # consonants only
        ("y", 0),  # 'y' is not a vowel here
        ("Hello World", 3),
        ("Programming", 3),
        ("aaa", 3),  # repeats are each counted
        ("12345 !?", 0),  # digits / punctuation
        ("   ", 0),  # whitespace only
        ("Été", 0),  # accented letters are not plain a/e/i/o/u
        ("queue", 4),
    ],
)
def test_count_vowels_values(text, expected):
    result = target.count_vowels(text)
    assert result == expected
    assert type(result) is int


@pytest.mark.parametrize("text", [123, None, ["a", "e"], b"aeiou", 1.5, True])
def test_count_vowels_wrong_type_raises_type_error(text):
    with pytest.raises(TypeError, match=r"^text must be a string$"):
        target.count_vowels(text)


# --------------------------------------------------------------------------- #
# 4. invert (boolean)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(("flag", "expected"), [(True, False), (False, True)])
def test_invert_values(flag, expected):
    assert target.invert(flag) is expected


def test_invert_twice_returns_original():
    assert target.invert(target.invert(True)) is True
    assert target.invert(target.invert(False)) is False


@pytest.mark.parametrize("flag", [0, 1, None, "True", "", [], 1.0])
def test_invert_non_bool_raises_type_error(flag):
    with pytest.raises(TypeError, match=r"^flag must be True or False$"):
        target.invert(flag)


# --------------------------------------------------------------------------- #
# 5. greet (None)
# --------------------------------------------------------------------------- #


def test_greet_without_argument_greets_guest():
    assert target.greet() == "Hello, Guest!"


@pytest.mark.parametrize("name", [None, "", " ", "    ", "\t", "\n", " \t\n "])
def test_greet_none_empty_or_blank_greets_guest(name):
    assert target.greet(name) == "Hello, Guest!"


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Alice", "Hello, Alice!"),
        ("  Bob  ", "Hello, Bob!"),  # surrounding spaces are stripped
        ("\tCarol\n", "Hello, Carol!"),
        ("Mary Ann", "Hello, Mary Ann!"),  # inner space is kept
        ("A", "Hello, A!"),  # single character
        ("guest", "Hello, guest!"),
        ("None", "Hello, None!"),  # the *string* "None" is a real name
    ],
)
def test_greet_with_name(name, expected):
    result = target.greet(name)
    assert result == expected
    assert type(result) is str


@pytest.mark.parametrize("name", [123, 4.5, ["Alice"]])
def test_greet_non_string_raises_attribute_error(name):
    # Documents current behaviour (see "Suspected bugs" in README):
    # non-strings reach .strip() and fail with AttributeError.
    with pytest.raises(AttributeError):
        target.greet(name)


# --------------------------------------------------------------------------- #
# 6. find_max (list)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("numbers", "expected"),
    [
        ([1, 2, 3], 3),  # max at end
        ([3, 2, 1], 3),  # max at start
        ([1, 5, 2], 5),  # max in middle
        ([7], 7),  # single element
        ([-5, -2, -9], -2),  # all negative
        ([0, -1], 0),
        ([2, 2, 2], 2),  # duplicates
        ([1.5, 2.5, 0.5], 2.5),
        ([1, 2.5, 2], 2.5),  # mixed int / float
        ([10**20, 1], 10**20),  # very large int
    ],
)
def test_find_max_values(numbers, expected):
    result = target.find_max(numbers)
    assert result == expected
    assert type(result) is type(expected)


def test_find_max_does_not_modify_input():
    numbers = [3, 1, 2]
    target.find_max(numbers)
    assert numbers == [3, 1, 2]


def test_find_max_accepts_tuple():
    assert target.find_max((4, 9, 1)) == 9


@pytest.mark.parametrize("numbers", [[], ()])
def test_find_max_empty_raises_value_error(numbers):
    with pytest.raises(ValueError, match=r"^list is empty$"):
        target.find_max(numbers)


@pytest.mark.parametrize("numbers", [None, 5, [1, "a"]])
def test_find_max_wrong_type_raises_type_error(numbers):
    with pytest.raises(TypeError):
        target.find_max(numbers)


# --------------------------------------------------------------------------- #
# 7. get_price (dictionary)
# --------------------------------------------------------------------------- #

PRICES = {"apple": 1.5, "bread": 2, "free sample": 0, "water": 0.0}


@pytest.mark.parametrize(
    ("item", "expected"),
    [("apple", 1.5), ("bread", 2), ("free sample", 0), ("water", 0.0)],
)
def test_get_price_existing_item(item, expected):
    result = target.get_price(PRICES, item)
    assert result == expected
    assert type(result) is type(expected)


def test_get_price_falsy_value_is_returned_not_treated_as_missing():
    assert target.get_price({"x": None}, "x") is None
    assert target.get_price({"x": 0}, "x") == 0


def test_get_price_does_not_modify_dict():
    prices = {"apple": 1}
    target.get_price(prices, "apple")
    assert prices == {"apple": 1}


@pytest.mark.parametrize(
    ("prices", "item"),
    [
        (PRICES, "banana"),
        (PRICES, "Apple"),  # keys are case sensitive
        (PRICES, "apple "),  # no stripping
        ({}, "apple"),  # empty dictionary
    ],
)
def test_get_price_missing_item_raises_key_error(prices, item):
    with pytest.raises(KeyError, match=rf"{item} not found"):
        target.get_price(prices, item)


def test_get_price_missing_key_error_exact_message():
    with pytest.raises(KeyError) as excinfo:
        target.get_price({}, "milk")
    assert excinfo.value.args == ("milk not found",)


def test_get_price_unhashable_item_raises_type_error():
    with pytest.raises(TypeError):
        target.get_price(PRICES, ["apple"])


def test_get_price_none_prices_raises_type_error():
    with pytest.raises(TypeError):
        target.get_price(None, "apple")


# --------------------------------------------------------------------------- #
# 8. swap (tuple)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("pair", "expected"),
    [
        ((1, 2), (2, 1)),
        (("a", "b"), ("b", "a")),
        ((1, 1), (1, 1)),  # equal values
        ((None, 0), (0, None)),
        ((1, "x"), ("x", 1)),  # mixed types
        ([1, 2], (2, 1)),  # list input still gives a tuple
    ],
)
def test_swap_values(pair, expected):
    result = target.swap(pair)
    assert result == expected
    assert type(result) is tuple


def test_swap_twice_returns_original():
    assert target.swap(target.swap((3, 4))) == (3, 4)


@pytest.mark.parametrize("pair", [(), (1,), (1, 2, 3), [], [1, 2, 3, 4]])
def test_swap_wrong_length_raises_value_error(pair):
    with pytest.raises(ValueError, match=r"^pair must have exactly 2 values$"):
        target.swap(pair)


@pytest.mark.parametrize("pair", [None, 12])
def test_swap_wrong_type_raises_type_error(pair):
    with pytest.raises(TypeError):
        target.swap(pair)


# --------------------------------------------------------------------------- #
# 9. common_items (set)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("set_a", "set_b", "expected"),
    [
        ({1, 2, 3}, {2, 3, 4}, {2, 3}),  # partial overlap
        ({1, 2}, {3, 4}, set()),  # disjoint
        ({1, 2}, {1, 2}, {1, 2}),  # identical
        ({1, 2, 3}, {2}, {2}),  # subset
        (set(), {1, 2}, set()),  # one empty
        (set(), set(), set()),  # both empty
        ({"a", "b"}, {"B", "a"}, {"a"}),  # strings, case sensitive
    ],
)
def test_common_items_values(set_a, set_b, expected):
    result = target.common_items(set_a, set_b)
    assert result == expected
    assert type(result) is set


def test_common_items_is_symmetric():
    a, b = {1, 2, 3}, {3, 4}
    assert target.common_items(a, b) == target.common_items(b, a) == {3}


def test_common_items_does_not_modify_inputs():
    a, b = {1, 2}, {2, 3}
    target.common_items(a, b)
    assert a == {1, 2}
    assert b == {2, 3}


@pytest.mark.parametrize(("set_a", "set_b"), [([1, 2], {1}), ({1}, [1]), (None, {1})])
def test_common_items_wrong_type_raises_type_error(set_a, set_b):
    with pytest.raises(TypeError):
        target.common_items(set_a, set_b)


# --------------------------------------------------------------------------- #
# 10. is_leap_year (date)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("year", "expected"),
    [
        (1, False),  # lowest valid year
        (4, True),  # first leap year
        (100, False),  # century, not / 400
        (400, True),  # / 400
        (1600, True),
        (1900, False),
        (1996, True),
        (1999, False),
        (2000, True),
        (2023, False),
        (2024, True),
        (2100, False),
        (2400, True),
    ],
)
def test_is_leap_year_values(year, expected):
    assert target.is_leap_year(year) is expected


@pytest.mark.parametrize("year", [0, -1, -4, -400])
def test_is_leap_year_below_one_raises_value_error(year):
    with pytest.raises(ValueError, match=r"^year must be 1 or more$"):
        target.is_leap_year(year)


@pytest.mark.parametrize("year", ["2024", None])
def test_is_leap_year_wrong_type_raises_type_error(year):
    with pytest.raises(TypeError):
        target.is_leap_year(year)


# --------------------------------------------------------------------------- #
# 11. to_int (type conversion)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (42, 42),
        (0, 0),
        (-7, -7),
        ("42", 42),
        ("-5", -5),
        ("+8", 8),
        ("  7  ", 7),  # surrounding whitespace allowed by int()
        ("007", 7),
        (3.9, 3),  # truncates toward zero, does NOT round
        (-3.9, -3),
        (0.0, 0),
        (10**20, 10**20),
    ],
)
def test_to_int_values(value, expected):
    result = target.to_int(value)
    assert result == expected
    assert type(result) is int


@pytest.mark.parametrize("value", [True, False])
def test_to_int_bool_raises_type_error(value):
    with pytest.raises(TypeError, match=r"^bool is not allowed$"):
        target.to_int(value)


@pytest.mark.parametrize("value", ["abc", "", "3.5", "1e3", "  "])
def test_to_int_bad_string_raises_value_error(value):
    with pytest.raises(ValueError):
        target.to_int(value)


@pytest.mark.parametrize("value", [None, [1], {"a": 1}])
def test_to_int_wrong_type_raises_type_error(value):
    with pytest.raises(TypeError):
        target.to_int(value)


def test_to_int_infinity_raises_overflow_error():
    with pytest.raises(OverflowError):
        target.to_int(float("inf"))

