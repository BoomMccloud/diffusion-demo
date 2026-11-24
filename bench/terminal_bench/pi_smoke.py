"""Exercise Pi's normal and compaction calls through the Clover relay."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid

from pi_relay import BASE_URL, MODEL, SETTINGS


def wait_for_event(process, predicate):
    for line in process.stdout:
        record = json.loads(line)
        if predicate(record):
            return record
    raise RuntimeError("Pi RPC exited before the expected event")


def send(process, **record):
    process.stdin.write(json.dumps(record) + "\n")
    process.stdin.flush()


def prompt(process, text):
    send(process, type="prompt", message=text)
    finished = wait_for_event(process, lambda event: event.get("type") == "agent_end")
    assistant = [m for m in finished.get("messages", []) if m.get("role") == "assistant"]
    if not assistant or assistant[-1].get("stopReason") in {"error", "aborted"}:
        raise RuntimeError("Pi did not finish the normal model turn")
    return finished.get("messages", [])


def main(model_id="Clover-35B-A3B-Preview", *endpoint):
    with tempfile.TemporaryDirectory() as tmp:
        config = Path(tmp)
        session = "clover-pi-smoke-" + str(uuid.uuid4())
        (config / "models.json").write_text(json.dumps({"providers": {"clover": {
            "baseUrl": BASE_URL,
            "api": "openai-completions",
            "apiKey": "$OPENAI_API_KEY",
            "models": [{"id": model_id, **MODEL}],
        }}}))
        (config / "settings.json").write_text(json.dumps({
            **SETTINGS, "compaction": {**SETTINGS["compaction"], "keepRecentTokens": 128},
        }))
        audit = config / "requests.jsonl"
        with audit.open("w") as log:
            relay = subprocess.Popen(
                [sys.executable, str(Path(__file__).with_name("pi_relay.py")), session, *endpoint],
                stdout=log,
            )
            try:
                for _ in range(30):
                    try:
                        with urllib.request.urlopen(BASE_URL.removesuffix("/v1") + "/health", timeout=1):
                            break
                    except urllib.error.URLError:
                        time.sleep(0.2)
                else:
                    raise RuntimeError("Clover relay failed to start")
                with subprocess.Popen(
                    ["pi", "--mode", "rpc", "--provider", "clover", "--model", model_id],
                    cwd=config, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                    env={**os.environ, "PI_CODING_AGENT_DIR": tmp},
                ) as pi:
                    try:
                        first = prompt(pi, "Use the bash tool once to print APRICOT, then reply with one short sentence. "
                                       + "These are filler words for the compaction check. " * 48)
                        if not any(m.get("role") == "toolResult" and not m.get("isError") for m in first):
                            raise RuntimeError("Pi did not execute a successful shell tool call")
                        prompt(pi, "What was the sample marker? Reply briefly. "
                               + "This second message is long enough to retain independently. " * 24)
                        before = len(audit.read_text().splitlines())
                        send(pi, type="compact", id="summary")
                        summary = wait_for_event(
                            pi, lambda e: e.get("type") == "response" and e.get("id") == "summary"
                        )
                        if not summary.get("success") or not summary.get("data", {}).get("summary"):
                            raise RuntimeError("Pi did not return a compaction summary: " + str(summary.get("error")))
                    finally:
                        pi.terminate()
            finally:
                relay.terminate()
                relay.wait(timeout=10)
        requests = [json.loads(line) for line in audit.read_text().splitlines()]
        if before < 2 or len(requests) <= before:
            raise RuntimeError("Expected successful normal and compaction API calls")
        for number, request in enumerate(requests):
            thinking = len(endpoint) != 1 or number < before
            if number < before and request["max_tokens"] != MODEL["maxTokens"]:
                raise RuntimeError("Pi normal request did not use the configured output budget")
            if not (
                request["status"] == 200 and request["authorized"]
                and request["user_id"] == "user-1" and request["session_id"] == session
                and request["thinking"] == {"enable_thinking": thinking, "preserve_thinking": thinking}
            ):
                raise RuntimeError("Clover request audit did not match expected configuration")
            print(json.dumps({"phase": "normal" if number < before else "compaction", **request}))


if __name__ == "__main__":
    main(*sys.argv[1:])
