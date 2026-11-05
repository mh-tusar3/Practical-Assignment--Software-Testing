"""target.py - simple functions for practising functional testing."""

import math


# 1. Integer: True if age is 18 or more. Negative age raises ValueError.
def is_adult(age):
    if age < 0:
        raise ValueError("age cannot be negative")
    return age >= 18


# 2. Float: convert Celsius to Fahrenheit, rounded to 2 decimals.
def celsius_to_fahrenheit(celsius):
    return round(celsius * 9 / 5 + 32, 2)


# 3. String: count vowels (a, e, i, o, u), ignoring case. Non-string raises TypeError.
def count_vowels(text):
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return sum(1 for letter in text.lower() if letter in "aeiou")


# 4. Boolean: return the opposite of flag. Non-bool raises TypeError.
def invert(flag):
    if not isinstance(flag, bool):
        raise TypeError("flag must be True or False")
    return not flag


# 5. None: greet by name, or greet "Guest" if name is None, empty or only spaces.
def greet(name=None):
    if name is None or name.strip() == "":
        return "Hello, Guest!"
    return f"Hello, {name.strip()}!"


# 6. List: return the largest number. Empty list raises ValueError.
def find_max(numbers):
    if len(numbers) == 0:
        raise ValueError("list is empty")
    return max(numbers)


# 7. Dictionary: return the price of item. Missing item raises KeyError.
def get_price(prices, item):
    if item not in prices:
        raise KeyError(f"{item} not found")
    return prices[item]


# 8. Tuple: return the two values swapped. Not exactly 2 values raises ValueError.
def swap(pair):
    if len(pair) != 2:
        raise ValueError("pair must have exactly 2 values")
    return (pair[1], pair[0])


# 9. Set: return the items found in both sets.
def common_items(set_a, set_b):
    return set_a & set_b


# 10. Date: True if year is a leap year. Year below 1 raises ValueError.
def is_leap_year(year):
    if year < 1:
        raise ValueError("year must be 1 or more")
    return (year % 4 == 0 and year % 100 != 0) or year % 400 == 0


# 11. Type conversion: convert value to int. A bool raises TypeError.
def to_int(value):
    if isinstance(value, bool):
        raise TypeError("bool is not allowed")
    return int(value)


# 12. Math: return a / b. Dividing by zero raises ZeroDivisionError.
def divide(a, b):
    if b == 0:
        raise ZeroDivisionError("cannot divide by zero")
    return a / b


# 13. Math: return base raised to exponent.
def power(base, exponent):
    return base ** exponent


# 14. Math: return the square root of x. Negative x raises ValueError.
def square_root(x):
    if x < 0:
        raise ValueError("cannot take the square root of a negative number")
    return math.sqrt(x)


# 15. Math: return n factorial. Negative n raises ValueError.
def factorial(n):
    if n < 0:
        raise ValueError("factorial is not defined for negative numbers")
    return math.prod(range(1, n + 1))


# 16. Math: return the average of a list. Empty list raises ValueError.
def average(numbers):
    if len(numbers) == 0:
        raise ValueError("list is empty")
    return sum(numbers) / len(numbers)
