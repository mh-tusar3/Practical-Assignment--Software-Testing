"""Cross-validation: run the test-suite against deliberately faulty copies of
target.py ("mutants"). Every mutant must be KILLED (at least one test fails).

Usage:  python tools/mutation_check.py
The original target.py is never modified; mutants live in a temp directory.
"""

import concurrent.futures
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = (ROOT / "target.py").read_text(encoding="utf-8")

LEAP = "return (year % 4 == 0 and year % 100 != 0) or year % 400 == 0"
SQRT_MSG = 'raise ValueError("cannot take the square root of a negative number")'

MUTANTS = [
    # is_adult
    ("is_adult: >= -> >", "return age >= 18", "return age > 18"),
    ("is_adult: threshold 17", "return age >= 18", "return age >= 17"),
    ("is_adult: threshold 19", "return age >= 18", "return age >= 19"),
    ("is_adult: < 0 -> <= 0", "if age < 0:", "if age <= 0:"),
    ("is_adult: no negative check", 'raise ValueError("age cannot be negative")', "pass"),
    (
        "is_adult: wrong exception",
        'raise ValueError("age cannot be negative")',
        'raise TypeError("age cannot be negative")',
    ),
    ("is_adult: returns int", "return age >= 18", "return int(age >= 18)"),
    # celsius_to_fahrenheit
    ("c2f: 1 decimal", "round(celsius * 9 / 5 + 32, 2)", "round(celsius * 9 / 5 + 32, 1)"),
    ("c2f: no rounding", "round(celsius * 9 / 5 + 32, 2)", "celsius * 9 / 5 + 32"),
    ("c2f: +30", "round(celsius * 9 / 5 + 32, 2)", "round(celsius * 9 / 5 + 30, 2)"),
    ("c2f: 5/9", "round(celsius * 9 / 5 + 32, 2)", "round(celsius * 5 / 9 + 32, 2)"),
    ("c2f: floor div", "round(celsius * 9 / 5 + 32, 2)", "round(celsius * 9 // 5 + 32, 2)"),
    ("c2f: 3 decimals", "round(celsius * 9 / 5 + 32, 2)", "round(celsius * 9 / 5 + 32, 3)"),
    # count_vowels
    ("vowels: case sensitive", "for letter in text.lower()", "for letter in text"),
    ("vowels: missing u", 'if letter in "aeiou")', 'if letter in "aeio")'),
    ("vowels: missing a", 'if letter in "aeiou")', 'if letter in "eiou")'),
    ("vowels: includes y", 'if letter in "aeiou")', 'if letter in "aeiouy")'),
    ("vowels: counts consonants", 'if letter in "aeiou")', 'if letter not in "aeiou")'),
    ("vowels: no type check", 'raise TypeError("text must be a string")', "return 0"),
    (
        "vowels: wrong exception",
        'raise TypeError("text must be a string")',
        'raise ValueError("text must be a string")',
    ),
    # invert
    ("invert: identity", "return not flag", "return flag"),
    ("invert: always False", "return not flag", "return False"),
    ("invert: accepts ints", "if not isinstance(flag, bool):", "if not isinstance(flag, (bool, int)):"),
    ("invert: wrong message", 'raise TypeError("flag must be True or False")', 'raise TypeError("bad flag")'),
    # greet
    ("greet: no strip in check", 'if name is None or name.strip() == "":', 'if name is None or name == "":'),
    ("greet: no strip in result", 'return f"Hello, {name.strip()}!"', 'return f"Hello, {name}!"'),
    ("greet: missing !", 'return f"Hello, {name.strip()}!"', 'return f"Hello, {name.strip()}"'),
    ("greet: guest lower", 'return "Hello, Guest!"', 'return "Hello, guest!"'),
    ("greet: lstrip only", 'return f"Hello, {name.strip()}!"', 'return f"Hello, {name.lstrip()}!"'),
    ("greet: empty not guest", 'if name is None or name.strip() == "":', "if name is None:"),
    # find_max
    ("find_max: min", "return max(numbers)", "return min(numbers)"),
    ("find_max: first", "return max(numbers)", "return numbers[0]"),
    ("find_max: last", "return max(numbers)", "return numbers[-1]"),
    ("find_max: sorted", "return max(numbers)", "return sorted(numbers)[-2] if len(numbers) > 1 else numbers[0]"),
    (
        "find_max: empty -> None",
        'raise ValueError("list is empty")\n    return max(numbers)',
        "return None\n    return max(numbers)",
    ),
    ("find_max: drops last", "return max(numbers)", "return max(numbers[:-1] or numbers)"),
    # get_price
    ("get_price: returns item", "return prices[item]", "return item"),
    ("get_price: falsy is missing", "if item not in prices:", "if not prices.get(item):"),
    ("get_price: lower key", "if item not in prices:", "if item.lower() not in prices:"),
    ("get_price: wrong msg", 'raise KeyError(f"{item} not found")', "raise KeyError(item)"),
    ("get_price: wrong exc", 'raise KeyError(f"{item} not found")', 'raise ValueError(f"{item} not found")'),
    ("get_price: return None", 'raise KeyError(f"{item} not found")', "return None"),
    # swap
    ("swap: identity", "return (pair[1], pair[0])", "return (pair[0], pair[1])"),
    ("swap: list result", "return (pair[1], pair[0])", "return [pair[1], pair[0]]"),
    ("swap: len < 2", "if len(pair) != 2:", "if len(pair) < 2:"),
    ("swap: len > 2", "if len(pair) != 2:", "if len(pair) > 2:"),
    ("swap: duplicates second", "return (pair[1], pair[0])", "return (pair[1], pair[1])"),
    # common_items
    ("common: union", "return set_a & set_b", "return set_a | set_b"),
    ("common: difference", "return set_a & set_b", "return set_a - set_b"),
    ("common: symmetric diff", "return set_a & set_b", "return set_a ^ set_b"),
    ("common: list", "return set_a & set_b", "return sorted(set_a & set_b)"),
    ("common: mutates", "return set_a & set_b", "set_a &= set_b\n    return set_a"),
    ("common: lists accepted", "return set_a & set_b", "return set(set_a) & set(set_b)"),
    # is_leap_year
    ("leap: only %4", LEAP, "return year % 4 == 0"),
    ("leap: no 400 rule", LEAP, "return year % 4 == 0 and year % 100 != 0"),
    ("leap: and/or swapped", LEAP, "return (year % 4 == 0 or year % 100 != 0) and year % 400 == 0"),
    ("leap: < 1 -> < 0", "if year < 1:", "if year < 0:"),
    ("leap: <= 1", "if year < 1:", "if year <= 1:"),
    ("leap: wrong msg", 'raise ValueError("year must be 1 or more")', 'raise ValueError("bad year")'),
    # to_int
    ("to_int: bool allowed", 'raise TypeError("bool is not allowed")', "pass"),
    ("to_int: rounds", "return int(value)", "return round(float(value)) if not isinstance(value, str) else int(value)"),
    ("to_int: via float", "return int(value)", "return int(float(value))"),
    ("to_int: wrong exc", 'raise TypeError("bool is not allowed")', 'raise ValueError("bool is not allowed")'),
    # divide
    ("divide: floor", "return a / b", "return a // b"),
    ("divide: swapped", "return a / b", "return b / a"),
    ("divide: zero -> 0", 'raise ZeroDivisionError("cannot divide by zero")', "return 0"),
    ("divide: wrong msg", 'raise ZeroDivisionError("cannot divide by zero")', "raise ZeroDivisionError"),
    (
        "divide: wrong exc",
        'raise ZeroDivisionError("cannot divide by zero")',
        'raise ValueError("cannot divide by zero")',
    ),
    # power
    ("power: multiply", "return base ** exponent", "return base * exponent"),
    ("power: swapped", "return base ** exponent", "return exponent ** base"),
    ("power: math.pow", "return base ** exponent", "return math.pow(base, exponent)"),
    ("power: abs exponent", "return base ** exponent", "return base ** abs(exponent)"),
    ("power: abs base", "return base ** exponent", "return abs(base) ** exponent"),
    # square_root
    ("sqrt: <= 0", "if x < 0:", "if x <= 0:"),
    ("sqrt: abs", SQRT_MSG, "x = -x"),
    ("sqrt: x/2", "return math.sqrt(x)", "return x / 2"),
    ("sqrt: int result", "return math.sqrt(x)", "return math.isqrt(int(x)) if x == int(x) else math.sqrt(x)"),
    ("sqrt: wrong msg", SQRT_MSG, 'raise ValueError("negative")'),
    # factorial
    ("factorial: off by one", "math.prod(range(1, n + 1))", "math.prod(range(1, n))"),
    ("factorial: sum", "math.prod(range(1, n + 1))", "sum(range(1, n + 1))"),
    ("factorial: from 0", "math.prod(range(1, n + 1))", "math.prod(range(0, n + 1))"),
    ("factorial: 0 not allowed", "if n < 0:", "if n <= 0:"),
    ("factorial: neg -> 1", 'raise ValueError("factorial is not defined for negative numbers")', "return 1"),
    ("factorial: float result", "return math.prod(range(1, n + 1))", "return float(math.prod(range(1, n + 1)))"),
    # average
    ("average: floor div", "return sum(numbers) / len(numbers)", "return sum(numbers) // len(numbers)"),
    ("average: len-1", "return sum(numbers) / len(numbers)", "return sum(numbers) / max(len(numbers) - 1, 1)"),
    ("average: sum only", "return sum(numbers) / len(numbers)", "return sum(numbers)"),
    ("average: empty -> 0", 'raise ValueError("list is empty")\n    return sum', "return 0.0\n    return sum"),
    ("average: median", "return sum(numbers) / len(numbers)", "return float(sorted(numbers)[len(numbers) // 2])"),
]


def mutate(source, old, new):
    """Replace the first occurrence of `old` that is in code (not in a comment line)."""
    start = 0
    while True:
        idx = source.find(old, start)
        if idx == -1:
            return None
        line_start = source.rfind("\n", 0, idx) + 1
        if not source[line_start:idx].lstrip().startswith("#"):
            return source[:idx] + new + source[idx + len(old) :]
        start = idx + 1


def run_suite(workdir: pathlib.Path) -> int:
    cmd = [sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", "-o", "addopts=", "tests"]
    return subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, timeout=300).returncode


def make_workdir(base: pathlib.Path, name: str, source: str) -> pathlib.Path:
    work = base / name
    (work / "tests").mkdir(parents=True)
    shutil.copy(ROOT / "tests" / "test_target.py", work / "tests" / "test_target.py")
    shutil.copy(ROOT / "pytest.ini", work / "pytest.ini")
    (work / "target.py").write_text(source, encoding="utf-8")
    return work


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp)
        if run_suite(make_workdir(base, "baseline", SOURCE)) != 0:
            print("Baseline FAILED: tests must pass on the original target.py")
            return 1
        print("Baseline: all tests pass on the original target.py", flush=True)

        jobs, invalid = [], []
        for number, (name, old, new) in enumerate(MUTANTS):
            mutated = mutate(SOURCE, old, new)
            if mutated is None or mutated == SOURCE:
                invalid.append(name)
            else:
                jobs.append((name, make_workdir(base, f"m{number}", mutated)))

        with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() or 2) as pool:
            codes = list(pool.map(lambda job: run_suite(job[1]), jobs))

    survivors = []
    for (name, _), code in zip(jobs, codes, strict=True):
        killed = code != 0
        print(f"{'KILLED  ' if killed else 'SURVIVED'}  {name}")
        if not killed:
            survivors.append(name)
    print(
        f"\n{len(jobs)} mutants run, {len(jobs) - len(survivors)} killed, {len(survivors)} survived, {len(invalid)} invalid"
    )
    for name in invalid:
        print("  invalid (pattern not found):", name)
    return 1 if survivors or invalid else 0


if __name__ == "__main__":
    sys.exit(main())
