"""Flask frontend for target.py.

Routes
  GET  /                   HTML page that lets you run every target.py function
  GET  /health             {"status": "ok", "commit": "<deployed git SHA>"}
  GET  /api/functions      metadata for the 16 functions (used by the page)
  POST /api/run/<name>     {"args": ["...", ...]} -> result or error
"""

import ast
import os
import subprocess

from flask import Flask, jsonify, render_template, request

import target

app = Flask(__name__)

MAX_INPUT_CHARS = 1000  # per argument
MAX_RESULT_CHARS = 2000  # long results (e.g. huge ints) are truncated for display
MAX_FACTORIAL_N = 1000  # protect the public server from very slow requests
MAX_POWER_EXPONENT = 10_000

# name -> (group, parameter names, short description, example inputs)
FUNCTIONS = {
    "is_adult": (
        "Integer",
        ["age"],
        "True if age is 18 or more. Negative age raises ValueError.",
        [["18"], ["17"], ["-1"], ['"18"']],
    ),
    "celsius_to_fahrenheit": (
        "Float",
        ["celsius"],
        "Convert Celsius to Fahrenheit, rounded to 2 decimals.",
        [["36.6"], ["-40"], ["100"], ["None"]],
    ),
    "count_vowels": (
        "String",
        ["text"],
        "Count a, e, i, o, u ignoring case. Non-string raises TypeError.",
        [["Hello World"], ["AEIOU"], [""], ["123"]],
    ),
    "invert": (
        "Boolean",
        ["flag"],
        "Return the opposite of flag. Non-bool raises TypeError.",
        [["True"], ["False"], ["1"]],
    ),
    "greet": (
        "None",
        ["name"],
        'Greet by name, or "Guest" if name is None, empty or only spaces.',
        [["Alice"], ["  Bob  "], ["None"], ['"   "'], ["123"]],
    ),
    "find_max": (
        "List",
        ["numbers"],
        "Return the largest number. Empty list raises ValueError.",
        [["[3, 9, 2]"], ["[-5, -2]"], ["[]"]],
    ),
    "get_price": (
        "Dictionary",
        ["prices", "item"],
        "Return the price of item. Missing item raises KeyError.",
        [['{"apple": 1.5, "bread": 2}', "apple"], ['{"apple": 1.5}', "banana"]],
    ),
    "swap": (
        "Tuple",
        ["pair"],
        "Return the two values swapped. Not exactly 2 values raises ValueError.",
        [["(1, 2)"], ['("a", "b")'], ["(1, 2, 3)"]],
    ),
    "common_items": (
        "Set",
        ["set_a", "set_b"],
        "Return the items found in both sets.",
        [["{1, 2, 3}", "{2, 3, 4}"], ["{1, 2}", "{3}"], ["[1, 2]", "{1}"]],
    ),
    "is_leap_year": (
        "Date",
        ["year"],
        "True if year is a leap year. Year below 1 raises ValueError.",
        [["2024"], ["1900"], ["2000"], ["0"]],
    ),
    "to_int": (
        "Type conversion",
        ["value"],
        "Convert value to int. A bool raises TypeError.",
        [['"42"'], ["3.9"], ["True"], ["abc"]],
    ),
    "divide": (
        "Math",
        ["a", "b"],
        "Return a / b. Dividing by zero raises ZeroDivisionError.",
        [["10", "4"], ["1", "3"], ["5", "0"]],
    ),
    "power": (
        "Math",
        ["base", "exponent"],
        "Return base raised to exponent.",
        [["2", "10"], ["2", "-1"], ["0", "-1"], ["-8", "1/3"]],
    ),
    "square_root": (
        "Math",
        ["x"],
        "Return the square root of x. Negative x raises ValueError.",
        [["16"], ["2"], ["-4"]],
    ),
    "factorial": ("Math", ["n"], "Return n factorial. Negative n raises ValueError.", [["5"], ["0"], ["-1"], ["3.5"]]),
    "average": (
        "Math",
        ["numbers"],
        "Return the average of a list. Empty list raises ValueError.",
        [["[1, 2, 3, 4]"], ["[0.1, 0.2]"], ["[]"]],
    ),
}


class InputError(Exception):
    """Bad request from the browser (not an error raised by target.py)."""


def get_commit_sha():
    """Deployed commit SHA: env var set by the host, else local git, else 'unknown'."""
    for key in ("GIT_SHA", "RENDER_GIT_COMMIT", "RAILWAY_GIT_COMMIT_SHA", "SOURCE_VERSION"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _eval_fraction(node):
    """Allow simple a/b in numeric inputs (e.g. 1/3) without using eval()."""
    if (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Div)
        and all(isinstance(side, (ast.Constant, ast.UnaryOp)) for side in (node.left, node.right))
    ):
        left = ast.literal_eval(node.left)
        right = ast.literal_eval(node.right)
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (left, right)) and right != 0:
            return left / right
    raise ValueError("not a fraction")


def parse_value(raw):
    """Turn one text box into a Python value.

    The text is read as a Python literal (42, 3.5, "text", None, True, [..], (..), {..}).
    A simple fraction such as 1/3 is also accepted. Anything else is used as a plain string,
    so typing Alice is the same as typing "Alice".
    """
    if not isinstance(raw, str):
        raise InputError("each argument must be sent as text")
    if len(raw) > MAX_INPUT_CHARS:
        raise InputError(f"input longer than {MAX_INPUT_CHARS} characters")
    text = raw.strip()
    if text == "":
        return raw  # keep "", "   " etc. exactly as typed
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        pass
    try:
        return _eval_fraction(ast.parse(text, mode="eval").body)
    except (ValueError, SyntaxError, TypeError, ZeroDivisionError, RecursionError):
        return raw


def guard(name, args):
    """Refuse inputs that would only make the public server slow."""
    if name == "factorial" and isinstance(args[0], int) and args[0] > MAX_FACTORIAL_N:
        raise InputError(f"frontend limit: n must be at most {MAX_FACTORIAL_N}")
    if name == "power" and isinstance(args[1], (int, float)) and abs(args[1]) > MAX_POWER_EXPONENT:
        raise InputError(f"frontend limit: |exponent| must be at most {MAX_POWER_EXPONENT}")


def describe(value):
    """Readable representation, with sets shown in a stable order."""
    if isinstance(value, (set, frozenset)) and value:
        try:
            text = "{" + ", ".join(repr(v) for v in sorted(value)) + "}"
        except TypeError:
            text = repr(value)
    else:
        try:
            text = repr(value)
        except ValueError:  # int too large to convert to str
            text = f"<{type(value).__name__} with more than 4300 digits>"
    if len(text) > MAX_RESULT_CHARS:
        text = text[:MAX_RESULT_CHARS] + f"... ({len(text)} characters)"
    return text


@app.get("/")
def index():
    return render_template("index.html", functions=FUNCTIONS, commit=get_commit_sha())


@app.get("/health")
def health():
    return jsonify(status="ok", commit=get_commit_sha())


@app.get("/api/functions")
def list_functions():
    return jsonify(
        [{"name": n, "group": g, "params": p, "description": d, "examples": e} for n, (g, p, d, e) in FUNCTIONS.items()]
    )


@app.post("/api/run/<name>")
def run(name):
    if name not in FUNCTIONS:
        return jsonify(ok=False, error_type="NotFound", error=f"unknown function: {name}"), 404
    params = FUNCTIONS[name][1]
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not isinstance(body.get("args"), list):
        return jsonify(ok=False, error_type="BadRequest", error='body must be JSON: {"args": [...]}'), 400
    raw_args = body["args"]
    if len(raw_args) != len(params):
        return jsonify(
            ok=False, error_type="BadRequest", error=f"{name} needs {len(params)} argument(s): {', '.join(params)}"
        ), 400
    try:
        args = [parse_value(raw) for raw in raw_args]
        guard(name, args)
    except InputError as exc:
        return jsonify(ok=False, error_type="BadRequest", error=str(exc)), 400

    call = f"{name}({', '.join(describe(a) for a in args)})"
    try:
        result = getattr(target, name)(*args)
    except Exception as exc:  # noqa: BLE001 - showing the function's own error is the point
        message = exc.args[0] if isinstance(exc, KeyError) and exc.args else str(exc)
        return jsonify(ok=False, call=call, error_type=type(exc).__name__, error=str(message))
    return jsonify(ok=True, call=call, result=describe(result), result_type=type(result).__name__)


if __name__ == "__main__":  # pragma: no cover
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
