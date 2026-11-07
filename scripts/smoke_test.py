"""Smoke-test the live site after a deploy (standard library only).

1. Poll  GET /health  until it reports the expected commit SHA (or time out).
2. Run three live requests:
     a) GET  /                       -> 200 and the page footer contains the SHA
     b) POST /api/run/divide [10, 4] -> ok, result 2.5
     c) POST /api/run/divide [5, 0]  -> ZeroDivisionError "cannot divide by zero"

Usage:
    python scripts/smoke_test.py --url https://your-app.onrender.com --sha <commit> [--timeout 900]
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def http(method, url, payload=None, timeout=30):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json", "Cache-Control": "no-cache"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status, res.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def wait_for_sha(base, sha, timeout, interval):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            status, body = http("GET", f"{base}/health")
            if status == 200:
                last = json.loads(body).get("commit")
                if last == sha:
                    print(f"[ok] /health reports {sha}")
                    return True
            print(f"[..] /health status={status} commit={last} (waiting for {sha[:7]})")
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            print(f"[..] /health not reachable yet: {exc}")
        time.sleep(interval)
    print(f"[FAIL] timed out after {timeout}s; live commit is still {last}")
    return False


def check(label, condition, detail):
    print(f"[{'ok' if condition else 'FAIL'}] {label}: {detail}")
    return condition


def run_checks(base, sha):
    results = []

    status, html = http("GET", f"{base}/")
    results.append(check("GET /", status == 200 and sha in html, f"status={status}, sha in page={sha in html}"))

    status, body = http("POST", f"{base}/api/run/divide", {"args": ["10", "4"]})
    data = json.loads(body) if status == 200 else {}
    results.append(check("divide(10, 4)", data.get("ok") is True and data.get("result") == "2.5", body.strip()))

    status, body = http("POST", f"{base}/api/run/divide", {"args": ["5", "0"]})
    data = json.loads(body) if status == 200 else {}
    results.append(
        check(
            "divide(5, 0)",
            data.get("error_type") == "ZeroDivisionError" and data.get("error") == "cannot divide by zero",
            body.strip(),
        )
    )
    return all(results)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", required=True, help="live base URL, e.g. https://app.onrender.com")
    parser.add_argument("--sha", required=True, help="commit SHA that must be live")
    parser.add_argument("--timeout", type=int, default=900, help="seconds to wait for the new SHA")
    parser.add_argument("--interval", type=int, default=15, help="seconds between /health polls")
    args = parser.parse_args(argv)
    base = args.url.rstrip("/")

    if not wait_for_sha(base, args.sha, args.timeout, args.interval):
        return 1
    if not run_checks(base, args.sha):
        return 1
    print("[ok] smoke test passed - change is live")
    return 0


if __name__ == "__main__":
    sys.exit(main())
