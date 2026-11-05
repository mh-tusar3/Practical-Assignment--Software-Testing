# Practical-Assignment--Software-Testing

[![CI](https://github.com/mh-tusar3/Practical-Assignment--Software-Testing/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/mh-tusar3/Practical-Assignment--Software-Testing/actions/workflows/ci.yml)

Functional tests, CI/CD and live deployment for `target.py` (16 functions: 11 data-type, 5 mathematics).

| | |
|---|---|
| **Live URL** | https://functional-testing-2608122.onrender.com |
| **Health** | https://functional-testing-2608122.onrender.com/health → `{"status": "ok", "commit": "<sha>"}` |
| **CI** | GitHub Actions: `test` (Python 3.10 / 3.11 / 3.12) → `deploy` → `smoke-test` |

> `target.py` is the instructor's file and is **not modified** (it is even excluded from `ruff format`).

---

## Project layout

```
target.py                    # given code (unchanged)
tests/test_target.py         # Part 1: functional tests for all 16 functions
tests/test_app.py            # tests for the web frontend
app.py                       # Part 4: Flask backend (/, /health, /api/functions, /api/run/<name>)
templates/index.html         # Part 4: frontend page
static/app.js, style.css     # Part 4: frontend behaviour and style
scripts/smoke_test.py        # Part 5: waits for the new SHA on the live site + 3 live checks
tools/mutation_check.py      # cross-validation: runs the tests against 89 faulty versions of target.py
.github/workflows/ci.yml     # Parts 3 + 5: test -> deploy -> smoke-test
render.yaml                  # Part 5: Render service (auto-deploy OFF)
requirements.in / .txt       # direct deps / fully pinned lock file (Python 3.10-3.12)
pyproject.toml, pytest.ini   # ruff, coverage and pytest settings
```

## Setup

```bash
git clone https://github.com/mh-tusar3/Practical-Assignment--Software-Testing.git
cd Practical-Assignment--Software-Testing
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Test command

```bash
pytest --cov=target --cov-branch --cov-report=term-missing --cov-fail-under=100
```

Expected: all tests pass and `target.py` shows **100 %** line and branch coverage
(59 statements, 26 branches, 0 missed).

Lint (same as CI):

```bash
ruff check .
ruff format --check .
```

Cross-validation – prove the tests catch faulty versions of `target.py`:

```bash
python tools/mutation_check.py      # every mutant must be KILLED
```

## Run the frontend locally

```bash
python app.py                       # http://127.0.0.1:5000
# or, like production:
gunicorn app:app --bind 127.0.0.1:5000
```

Each function has a card with input boxes, example buttons and a result panel that shows the call,
the result and its Python type, or the exception class and message. The footer shows the deployed
commit SHA read from `/health`.

Inputs are read as Python literals (`42`, `3.5`, `"text"`, `None`, `True`, `[1, 2]`, `(1, 2)`, `{1, 2}`,
`{"a": 1}`) or a fraction like `1/3`; anything else is sent as plain text. Inputs are parsed with
`ast.literal_eval` – nothing is ever passed to `eval`. To keep the public server responsive,
the frontend (not `target.py`) refuses `factorial(n)` with `n > 1000` and `power` with `|exponent| > 10000`.

## Test design (Part 1)

* Every function has tests for **valid inputs, boundary values, invalid values and wrong types**,
  all written with `@pytest.mark.parametrize`.
* Documented errors use `pytest.raises(<exact class>, match=r"^exact message$")`.
* Exact results are compared exactly (`==`, `is True`), and result types are asserted
  (`type(result) is float`, `is int`, `is tuple`, `is set` …). `pytest.approx` is used **only** for
  inexact float results such as `divide(1, 3)` or `average([0.1, 0.2])`.
* Boundaries tested include: age 17/18, year 0/1 and the 4/100/400 leap rules, 2-decimal rounding
  (`36.6 → 97.88`), empty vs. one-element lists, falsy dictionary values (`0`, `None`), `-0.0`
  divisor, `0! = 1`, truncation in `to_int(3.9) == 3`, and true vs. floor division (`-7 / 2 == -3.5`).
* No `skip`, `xfail` or hidden failures.

### Cross-validation with faulty versions

`tools/mutation_check.py` copies the tests to a temporary folder, runs them against the original
`target.py` (must pass) and then against 89 deliberately broken copies (e.g. `>=` changed to `>`,
`round(..., 1)`, a missing vowel, `max` → `min`, `&` → `|`, wrong leap-year rule, `/` → `//`,
`range(1, n)`, wrong exception class or message). **Every mutant is killed.**

## CI/CD pipeline (Parts 3 and 5)

```
push to main ──► test (3.10, 3.11, 3.12) ──all pass?──► deploy ──► smoke-test ──► change is live
                         │ lint (ruff)                   │ needs: test        │ waits for new SHA on /health
                         │ pytest, coverage = 100 %      │ main pushes only   │ GET /  (footer shows SHA)
                         │ upload coverage artifact      │ secret deploy hook │ divide(10, 4) = 2.5
                         └── any failure ──► pipeline stops, deploy skipped, live site unchanged
                                                                              divide(5, 0) → ZeroDivisionError
```

* `test` runs on **every push** and on **pull requests to `main`**, with pip caching, ruff lint, all tests and
  `--cov-fail-under=100`. Coverage (`coverage.xml`, `htmlcov/`, `junit.xml`) is uploaded as an artifact per
  Python version.
* `deploy` has `needs: test`, runs only for `push` to `main`, and calls the Render deploy hook stored in the
  GitHub secret `RENDER_DEPLOY_HOOK_URL`, pinned to the exact commit with `&ref=$GITHUB_SHA`.
* Render auto-deploy is **off** (`autoDeployTrigger: "off"`), so code that fails a test can never go live.
* `/health` returns the deployed commit (Render sets `RENDER_GIT_COMMIT`), and the page footer shows it.
* `smoke-test` polls `/health` until it reports the new SHA, then checks three live requests.

Required GitHub settings: secret `RENDER_DEPLOY_HOOK_URL`, repository variable `LIVE_URL`.

## Suspected bugs in `target.py`

These are reported, not fixed (the file must stay unchanged). Where the behaviour is reachable,
the tests pin the current behaviour so any change is noticed.

1. **`greet` – wrong exception for non-strings.** `greet(123)` raises `AttributeError: 'int' object has no
   attribute 'strip'` instead of a clear `TypeError`, unlike `count_vowels` and `invert`.
2. **`power` – complex result.** `power(-8, 1/3)` returns the complex number `(1.0000000000000002+1.7320508075688772j)`
   instead of `-2.0` or an error.
3. **`power(0, -1)`** raises Python's own `ZeroDivisionError: 0.0 cannot be raised to a negative power`, while
   `divide` uses the custom message `cannot divide by zero` – inconsistent.
4. **`bool` accepted as a number.** `is_adult(True)` → `False`, `is_leap_year(True)` → `False` (treated as year 1),
   `factorial(True)` → `1`, `celsius_to_fahrenheit(True)` → `33.8`, `divide(True, 2)` → `0.5`. Only `to_int` and
   `invert` check for `bool`.
5. **`is_adult` / `is_leap_year` accept floats.** `is_adult(17.99)` → `False`, `is_leap_year(2000.0)` → `True`;
   an age or a year should be an integer.
6. **No type checks in most functions.** Wrong types fail with Python's generic `TypeError` messages
   (e.g. `'<' not supported between instances of 'str' and 'int'`) instead of the clear messages
   used by `count_vowels`/`invert`.
7. **`to_int` truncates instead of rounding**, `to_int(3.9)` → `3`, and `to_int("3.5")` raises `ValueError`.
8. **`square_root(float("nan"))` returns `nan`** – NaN passes the `x < 0` check.
9. **`get_price` message** – `KeyError` wraps the message in quotes when printed (`"'banana not found'"`),
   which is how `KeyError.__str__` works.
10. **`count_vowels` ignores accented vowels** (`"Été"` → `0`) and `y`.
11. **`swap`, `find_max`, `average` accept any sequence** (e.g. `swap("ab")` → `('b', 'a')`) although the
    comments describe a tuple / list.
12. **`celsius_to_fahrenheit` returns `-0.0`** for values that round to zero from below (e.g. `-17.78`).

## Author

Md. Mokarrom Hosen – 2608122
