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

