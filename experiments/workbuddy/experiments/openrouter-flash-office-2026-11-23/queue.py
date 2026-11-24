"""Run the two ticket smokes, then the matched WorkBuddy Office batches."""
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

import yaml

CODE = Path("/run/workbuddy-code")
ROUTES = ("deepseek-flash-office", "glm-flash-office")
ROOT = Path("results/openrouter-flash-office-20261123")
LEDGER = ROOT / "queue.jsonl"
TICKET = "ticket-weekly-L3-010"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

FORBIDDEN_DIAGNOSTIC = '''
            if route.slug in {"deepseek-flash-office", "glm-flash-office"} and e.status == 403:
                try:
                    details = json.loads(e.body or "{}")
                    message = str(details.get("error", {}).get("message", "")).lower()
                    metadata = details.get("openrouter_metadata") or {}
                    blocked = any(
                        stage.get("type") == "guardrail"
                        and (stage.get("data") or {}).get("action") in {"block", "blocked"}
                        for stage in metadata.get("pipeline", [])
                    )
                    if blocked or any(term in message for term in (
                        "content policy", "content filter", "moderation", "prompt injection",
                        "sensitive information", "sensitive info",
                    )):
                        category = "content_restriction"
                    elif any(term in message for term in (
                        "budget", "limit exceeded", "credit", "spend",
                    )):
                        category = "account_budget"
                    elif any(term in message for term in (
                        "region", "allowlist", "not allowed", "blocked for", "permission",
                    )):
                        category = "access_restriction"
                    else:
                        category = "unclassified_json"
                except (ValueError, TypeError, AttributeError):
                    category = "non_json_or_malformed_error"
                log.warning("OPENROUTER_FORBIDDEN category=%s", category)
'''


def register_routes():
    for route in ROUTES:
        shutil.copyfile(CODE / f"{route}.yaml", Path("configs/models") / f"{route}.yaml")

    pipeline = Path("src/workbuddy_bench/proxy/pipeline.py")
    original = pipeline.read_text()
    source = original
    baseline = '"clover-spark-uncapped", "clover-spark-serial", "qwen36-flash-serial"'
    extended = ", ".join([baseline, *(json.dumps(route) for route in ROUTES)])
    if extended not in source:
        expected = "route.slug in {" + baseline + "}"
        if source.count(expected) != 1:
            raise RuntimeError("The baseline completion-cap hook has changed")
        source = source.replace(expected, "route.slug in {" + extended + "}")
    if "OPENROUTER_FORBIDDEN category=" not in source:
        anchor = "            # The error event goes to the *client*, so its wire format must follow"
        if source.count(anchor) != 1:
            raise RuntimeError("The streaming error hook has changed")
        source = source.replace(anchor, FORBIDDEN_DIAGNOSTIC.lstrip("\n") + anchor)
    if source != original:
        compile(source, str(pipeline), "exec")
        pipeline.write_text(source)

    preflight = Path("scripts/workbuddy-task-proxy-preflight.sh")
    source = preflight.read_text()
    marker = 'if [[ -n "${WORKBUDDY_OPENROUTER_ROUTE:-}" ]]; then'
    if marker not in source:
        hook = marker + """
  docker compose -p workbuddy-preflight -f .workspace/preflight-json-screener-summary-L4-004.yaml run --rm --no-deps --entrypoint python3 main -c '
import json, sys
from urllib.request import urlopen
with urlopen(f"http://{sys.argv[1]}:{sys.argv[2]}/health", timeout=8) as response:
    assert response.status == 200 and sys.argv[3] in json.load(response)["routes"]
    print(f"Office task container reached {sys.argv[3]} (HTTP 200)")
' "$1" "$2" "$WORKBUDDY_OPENROUTER_ROUTE"
  exit 0
fi
"""
        anchor = "set -euo pipefail\n"
        if not source.startswith(anchor):
            raise RuntimeError("The baseline task-proxy preflight has changed")
        preflight.write_text(anchor + hook + source[len(anchor):])


def append(row):
    with LEDGER.open("a") as file:
        file.write(json.dumps(row) + "\n")
        file.flush()
        os.fsync(file.fileno())


def clean_proxy(job):
    configs = {
        str(path.resolve()).encode()
        for path in Path("scripts/logs/instances").glob(f"{job}-*/proxy.yaml")
    }
    for process in Path("/proc").glob("[0-9]*"):
        try:
            args = (process / "cmdline").read_bytes().split(b"\x00")
            if b"workbuddy_bench.proxy" in args and configs.intersection(args):
                os.kill(int(process.name), signal.SIGTERM)
        except (ProcessLookupError, FileNotFoundError, PermissionError):
            continue


def next_attempt(prefix):
    attempts = [
        int(path.name.removeprefix(prefix))
        for path in Path("results").glob(f"{prefix}*")
        if path.name.removeprefix(prefix).isdigit()
    ]
    return max(attempts, default=0) + 1


def check_key_budget(key):
    request = Request(
        f"{OPENROUTER_BASE_URL}/key",
        headers={"Authorization": f"Bearer {key}"},
    )
    with urlopen(request, timeout=20) as response:
        remaining = json.load(response)["data"]["limit_remaining"]
    if remaining is not None and remaining <= 0:
        raise SystemExit("OpenRouter key limit reached; restore its budget before resuming")


def run_task(base, route, task, phase, index):
    prefix = f"{route}-20261123-{phase}-{index:03d}-a"
    first = next_attempt(prefix)
    for attempt in range(first, first + 3):
        job = f"{prefix}{attempt:03d}"
        config = dict(base, model=route, task_selection={"mode": "name", "names": [task]})
        Path(f"configs/jobs/{job}.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
        row = dict(route=route, phase=phase, task=task, job=job)
        print(f"Starting {phase} {index:02d} {route} {task} attempt {attempt}", flush=True)
        try:
            code = subprocess.call(
                ["bash", "scripts/run.sh", "--job", job],
                env={**os.environ, "WORKBUDDY_OPENROUTER_ROUTE": route},
            )
        finally:
            clean_proxy(job)
        logs = [
            path.read_text(errors="replace")
            for path in Path("scripts/logs/proxy").glob(f"proxy-{job}-*.log")
        ]
        statuses = re.findall(r"HTTP/1\.1 (\d{3})", "\n".join(logs))
        paths = list(Path("results", job).glob("*/*/result.json"))
        trial = json.loads(paths[0].read_text()) if len(paths) == 1 else {}
        tokens = (trial.get("agent_result") or {}).get("n_output_tokens") or 0
        row.update(output_tokens=tokens, http_200=statuses.count("200"),
                   http_429=statuses.count("429"), launcher_exit=code)
        if "429" in statuses and (not tokens or statuses[-1] == "429"):
            append(dict(row, status="retry_429"))
            time.sleep(10)
            continue
        if code or not trial or not tokens or "200" not in statuses:
            diagnostics = re.findall(r"OPENROUTER_FORBIDDEN category=(\w+)", "\n".join(logs))
            append(dict(row, status="infrastructure_error", http=statuses[-8:], diagnostic=diagnostics))
            raise RuntimeError(f"Rollout infrastructure failure: {job}")
        row["result"] = str(paths[0])
        score_path = paths[0].parent / "verifier/score.json"
        score = json.loads(score_path.read_text()) if score_path.is_file() else {}
        if (score.get("test_status") in (None, "judge_error", "build_error")
                or not score.get("tests_total") or score.get("reward") is None):
            append(dict(row, status="verifier_error"))
            raise RuntimeError(f"Verifier failure: {job}")
        if phase == "smoke" and (
            not any("UNCAPPED_WIRE" in log for log in logs)
            or not score.get("tests_passed")
        ):
            append(dict(row, status="smoke_failed", tests_passed=score.get("tests_passed")))
            raise RuntimeError(f"Smoke did not verify a workbook or uncapped route: {job}")
        append(dict(row, status="completed", score=score["reward"],
                    tests_passed=score["tests_passed"], tests_total=score["tests_total"]))
        print(f"Scored {job}: {score['tests_passed']}/{score['tests_total']}", flush=True)
        return
    raise RuntimeError(f"Attempt limit reached for {route} {task}")


def main():
    secret = Path("/run/workbuddy-secret/credentials")
    if secret.is_file():
        try:
            key = secret.read_text().strip()
        finally:
            secret.unlink()
        if not key:
            raise RuntimeError("Missing OpenRouter credential")
        os.environ["OPENROUTER_API_KEY"] = key
        del key
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise RuntimeError("Missing OpenRouter credential")
    check_key_budget(os.environ["OPENROUTER_API_KEY"])
    os.environ.update(
        OPENROUTER_BASE_URL=OPENROUTER_BASE_URL,
        PATH=f"{Path.cwd()}/.venv/bin:{os.environ['PATH']}",
        PYTHONPATH=str(Path.cwd() / "src"),
        PROXY_HOST="workbuddy-openrouter-office-proxy",
        PROXY_PORT="3489",
        SHARD_CONCURRENCY="1",
    )
    ROOT.mkdir(parents=True, exist_ok=True)
    register_routes()
    base = yaml.safe_load(Path("configs/jobs/clover-office-full-uncapped.yaml").read_text())
    names = base["task_selection"]["names"]
    if len(names) != 50 or len(set(names)) != 50 or TICKET not in names:
        raise RuntimeError("The saved 50-task baseline has changed")
    rows = [json.loads(line) for line in LEDGER.read_text().splitlines()] if LEDGER.exists() else []
    completed = {(r["phase"], r["route"], r["task"]) for r in rows if r["status"] == "completed"}
    for route in ROUTES:
        if ("smoke", route, TICKET) not in completed:
            run_task(base, route, TICKET, "smoke", 1)
    print("Both weekly ticket smokes passed", flush=True)
    if "--smoke-only" in sys.argv:
        return
    for route in ROUTES:
        for index, task in enumerate(names, 1):
            if ("batch", route, task) not in completed:
                run_task(base, route, task, "batch", index)
    print("All 100 Office trials scored", flush=True)


if __name__ == "__main__":
    main()
