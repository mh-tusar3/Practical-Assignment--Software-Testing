"""Tests for the Flask frontend (app.py)."""

import subprocess

import pytest

import app as webapp

SHA = "a" * 40


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GIT_SHA", SHA)
    webapp.app.config.update(TESTING=True)
    with webapp.app.test_client() as c:
        yield c


def run(client, name, *args):
    return client.post(f"/api/run/{name}", json={"args": list(args)})


# ---------------------------------------------------------------- pages / health


def test_health_returns_status_and_commit(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json() == {"status": "ok", "commit": SHA}


def test_index_lists_all_16_functions_and_shows_sha(client):
    res = client.get("/")
    html = res.get_data(as_text=True)
    assert res.status_code == 200
    for name in webapp.FUNCTIONS:
        assert f'data-name="{name}"' in html
    assert SHA in html


def test_functions_endpoint_matches_target_module(client):
    data = client.get("/api/functions").get_json()
    assert len(data) == 16
    for item in data:
        assert callable(getattr(webapp.target, item["name"]))
        assert all(len(example) == len(item["params"]) for example in item["examples"])


@pytest.mark.parametrize("env", ["GIT_SHA", "RENDER_GIT_COMMIT", "RAILWAY_GIT_COMMIT_SHA", "SOURCE_VERSION"])
def test_commit_sha_from_each_env_var(monkeypatch, env):
    for key in ("GIT_SHA", "RENDER_GIT_COMMIT", "RAILWAY_GIT_COMMIT_SHA", "SOURCE_VERSION"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv(env, "b" * 40)
    assert webapp.get_commit_sha() == "b" * 40


def test_commit_sha_falls_back_to_unknown(monkeypatch):
    for key in ("GIT_SHA", "RENDER_GIT_COMMIT", "RAILWAY_GIT_COMMIT_SHA", "SOURCE_VERSION"):
        monkeypatch.delenv(key, raising=False)

    def broken(*args, **kwargs):
        raise subprocess.CalledProcessError(128, "git")

    monkeypatch.setattr(webapp.subprocess, "run", broken)
    assert webapp.get_commit_sha() == "unknown"


# ---------------------------------------------------------------- results


@pytest.mark.parametrize(
    ("name", "args", "result", "result_type"),
    [
        ("is_adult", ["18"], "True", "bool"),
        ("celsius_to_fahrenheit", ["36.6"], "97.88", "float"),
        ("count_vowels", ["Hello World"], "3", "int"),
        ("invert", ["False"], "True", "bool"),
        ("greet", ["  Bob  "], "'Hello, Bob!'", "str"),
        ("greet", ["None"], "'Hello, Guest!'", "str"),
        ("greet", [""], "'Hello, Guest!'", "str"),
        ("find_max", ["[3, 9, 2]"], "9", "int"),
        ("get_price", ['{"apple": 1.5}', "apple"], "1.5", "float"),
        ("swap", ["(1, 2)"], "(2, 1)", "tuple"),
        ("common_items", ["{3, 1, 2}", "{2, 3, 4}"], "{2, 3}", "set"),
        ("common_items", ["{1}", "{2}"], "set()", "set"),
        ("is_leap_year", ["2000"], "True", "bool"),
        ("to_int", ['"42"'], "42", "int"),
        ("divide", ["10", "4"], "2.5", "float"),
        ("power", ["2", "10"], "1024", "int"),
        ("power", ["9", "1/2"], "3.0", "float"),
        ("square_root", ["16"], "4.0", "float"),
        ("factorial", ["5"], "120", "int"),
        ("average", ["[1, 2, 3, 4]"], "2.5", "float"),
    ],
)
def test_run_returns_result(client, name, args, result, result_type):
    res = run(client, name, *args)
    data = res.get_json()
    assert res.status_code == 200
    assert data["ok"] is True
    assert data["result"] == result
    assert data["result_type"] == result_type
    assert data["call"].startswith(f"{name}(")


@pytest.mark.parametrize(
    ("name", "args", "error_type", "error"),
    [
        ("is_adult", ["-1"], "ValueError", "age cannot be negative"),
        ("count_vowels", ["123"], "TypeError", "text must be a string"),
        ("invert", ["1"], "TypeError", "flag must be True or False"),
        ("find_max", ["[]"], "ValueError", "list is empty"),
        ("get_price", ['{"apple": 1}', "banana"], "KeyError", "banana not found"),
        ("swap", ["(1, 2, 3)"], "ValueError", "pair must have exactly 2 values"),
        ("is_leap_year", ["0"], "ValueError", "year must be 1 or more"),
        ("to_int", ["True"], "TypeError", "bool is not allowed"),
        ("divide", ["5", "0"], "ZeroDivisionError", "cannot divide by zero"),
        ("square_root", ["-4"], "ValueError", "cannot take the square root of a negative number"),
        ("factorial", ["-1"], "ValueError", "factorial is not defined for negative numbers"),
        ("average", ["[]"], "ValueError", "list is empty"),
    ],
)
def test_run_shows_function_error(client, name, args, error_type, error):
    res = run(client, name, *args)
    data = res.get_json()
    assert res.status_code == 200
    assert data == {"ok": False, "call": data["call"], "error_type": error_type, "error": error}


def test_plain_text_is_sent_as_string(client):
    data = run(client, "to_int", "abc").get_json()
    assert data["ok"] is False
    assert data["error_type"] == "ValueError"
    assert data["call"] == "to_int('abc')"


def test_large_set_with_mixed_types_still_displays(client):
    data = run(client, "common_items", '{1, "a"}', '{1, "a"}').get_json()
    assert data["ok"] is True
    assert data["result_type"] == "set"


def test_long_result_is_truncated(client):
    data = run(client, "factorial", "1000").get_json()
    assert data["ok"] is True
    assert len(data["result"]) < webapp.MAX_RESULT_CHARS + 50
    assert "characters" in data["result"]


# ---------------------------------------------------------------- bad requests


def test_unknown_function_is_404(client):
    res = run(client, "eval", "1")
    assert res.status_code == 404
    assert res.get_json()["ok"] is False


@pytest.mark.parametrize("body", [None, {"x": 1}, {"args": "1"}])
def test_bad_body_is_400(client, body):
    res = client.post("/api/run/is_adult", json=body)
    assert res.status_code == 400


def test_wrong_argument_count_is_400(client):
    res = run(client, "divide", "1")
    assert res.status_code == 400
    assert "2 argument" in res.get_json()["error"]


def test_non_string_argument_is_400(client):
    res = client.post("/api/run/is_adult", json={"args": [18]})
    assert res.status_code == 400


def test_too_long_input_is_400(client):
    res = run(client, "count_vowels", "a" * (webapp.MAX_INPUT_CHARS + 1))
    assert res.status_code == 400


@pytest.mark.parametrize(("name", "args"), [("factorial", ["100000"]), ("power", ["2", "100000"])])
def test_expensive_inputs_are_refused(client, name, args):
    res = run(client, name, *args)
    assert res.status_code == 400
    assert "frontend limit" in res.get_json()["error"]


def test_parser_never_executes_code():
    # Not a literal and not a fraction -> treated as plain text, never evaluated.
    assert webapp.parse_value("__import__('os').getcwd()") == "__import__('os').getcwd()"
    assert webapp.parse_value("1/0") == "1/0"
    assert webapp.parse_value("   ") == "   "
    assert webapp.parse_value("-8") == -8
    assert webapp.parse_value("-1/4") == -0.25
