#!/usr/bin/env python3
"""
Smoke test for the MLflow local stack.

Requires no extra dependencies — uses only the Python standard library
and the MLflow REST API + RustFS health endpoint.

Usage:
    python3 test_stack.py
"""

import json
import sys
import urllib.request
import urllib.error

MLFLOW_URL = "http://localhost:5000"
RUSTFS_URL = "http://localhost:9090"

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"

results = []


def check(label: str, ok: bool, detail: str = "") -> bool:
    status = PASS if ok else FAIL
    line = f"  [{status}] {label}"
    if detail:
        line += f"  ({detail})"
    print(line)
    results.append(ok)
    return ok


def http(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    url = f"{MLFLOW_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read()
            try:
                body = json.loads(raw) if raw.strip() else {}
            except json.JSONDecodeError:
                body = {}
            return r.status, body
    except urllib.error.HTTPError as e:
        return e.code, {}


# ── 1. Health checks ─────────────────────────────────────────────────────────
print("\n1. Health checks")

status, _ = http("GET", "/health")
check("MLflow /health → 200", status == 200, f"got {status}")

try:
    with urllib.request.urlopen(f"{RUSTFS_URL}/health", timeout=10) as r:
        rustfs_ok = r.status == 200
    check("RustFS /health → 200", rustfs_ok)
except Exception as e:
    check("RustFS /health → 200", False, str(e))

# ── 2. Create experiment ──────────────────────────────────────────────────────
print("\n2. Experiment")

status, body = http("POST", "/api/2.0/mlflow/experiments/create",
                    {"name": "smoke-test"})
if status == 200:
    experiment_id = body["experiment_id"]
    check("Create experiment", True, f"id={experiment_id}")
else:
    # May already exist from a previous run
    status2, body2 = http("GET", "/api/2.0/mlflow/experiments/get-by-name"
                                  "?experiment_name=smoke-test")
    experiment_id = body2.get("experiment", {}).get("experiment_id")
    check("Create experiment (already exists)", status2 == 200,
          f"id={experiment_id}")

# ── 3. Create run ─────────────────────────────────────────────────────────────
print("\n3. Run lifecycle")

status, body = http("POST", "/api/2.0/mlflow/runs/create",
                    {"experiment_id": experiment_id})
check("Create run", status == 200, f"status={status}")
run_id = body.get("run", {}).get("info", {}).get("run_id", "")

# ── 4. Log params & metrics ───────────────────────────────────────────────────
status, _ = http("POST", "/api/2.0/mlflow/runs/log-parameter",
                 {"run_id": run_id, "key": "lr", "value": "0.01"})
check("Log param  lr=0.01", status == 200)

status, _ = http("POST", "/api/2.0/mlflow/runs/log-metric",
                 {"run_id": run_id, "key": "accuracy", "value": 0.95,
                  "timestamp": 0, "step": 1})
check("Log metric accuracy=0.95", status == 200)

# ── 5. Finish run ─────────────────────────────────────────────────────────────
status, _ = http("POST", "/api/2.0/mlflow/runs/update",
                 {"run_id": run_id, "status": "FINISHED"})
check("Finish run", status == 200)

# ── 6. Read back and verify ───────────────────────────────────────────────────
print("\n4. Verify stored data")

status, body = http("GET", f"/api/2.0/mlflow/runs/get?run_id={run_id}")
if check("Fetch run", status == 200):
    run = body.get("run", {})
    stored_status = run.get("info", {}).get("status")
    check("Run status is FINISHED", stored_status == "FINISHED",
          f"got {stored_status}")

    params = {p["key"]: p["value"]
              for p in run.get("data", {}).get("params", [])}
    check("Param lr=0.01 persisted", params.get("lr") == "0.01",
          f"params={params}")

    metrics = {m["key"]: m["value"]
               for m in run.get("data", {}).get("metrics", [])}
    check("Metric accuracy=0.95 persisted",
          abs(metrics.get("accuracy", 0) - 0.95) < 1e-9,
          f"metrics={metrics}")

# ── Summary ───────────────────────────────────────────────────────────────────
passed = sum(results)
total = len(results)
print(f"\n{'─' * 40}")
print(f"  {passed}/{total} checks passed")
if passed == total:
    print("  \033[32mAll good — stack is healthy.\033[0m\n")
    sys.exit(0)
else:
    print("  \033[31mSome checks failed.\033[0m\n")
    sys.exit(1)
