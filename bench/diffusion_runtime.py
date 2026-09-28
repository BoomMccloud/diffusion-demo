#!/usr/bin/env python3
"""Versioned resident worker and diffusion-only, matched-output benchmark.

Serve on loopback; run talks to the resident owner rather than competing for its
pipes. The native generation tuple and exact evaluator remain owned by the
existing benchmark module.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import shutil
import signal
import statistics
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
try:
    from . import dependency_density_bench as b
except ImportError:
    import dependency_density_bench as b


def atomic_json(path, value):
    path = Path(path)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, indent=2))
    temp.replace(path)


def mirror_file(path, mirror_dir):
    """Atomically copy a completed artifact to persistent storage."""
    if not mirror_dir:
        return
    source = Path(path)
    target = Path(mirror_dir) / source.name
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + ".tmp")
    shutil.copy2(source, temp)
    temp.replace(target)


def admit_case(remaining_seconds, case_seconds, reserve_seconds=5):
    return case_seconds > 0 and remaining_seconds >= case_seconds + reserve_seconds


def classify_result(case, raw, telemetry):
    final, thought = b.split_native_response(raw)
    if raw.startswith("<|channel>thought") and thought is None:
        thought, final = raw, ""
    score = b.evaluate_output(case, final)
    score.pop("parsed")
    events = telemetry.get("native_events", [])
    stops = [e for e in events if e.get("event") == "stop"]
    stop = stops[-1].get("reason") if stops else None
    error = telemetry.get("error")
    outcome = "correct" if score["valid"] else "incorrect" if score["canonical"] else "invalid_final"
    if len(stops) > 1:
        outcome = "ambiguous_native_stop"
    elif not stops:
        outcome = "missing_native_stop"
    elif not final.strip():
        outcome = "budget_exhausted" if stop == "block_budget" else "incomplete_reasoning"
    if stop == "cancelled":
        outcome = "cancelled"
    if error:
        kind = error.get("type") if isinstance(error, dict) else "RuntimeError"
        outcome = "timed_out" if kind == "TimeoutError" else "cancelled" if kind == "GenerationCancelled" else "native_crash" if telemetry.get("exit_code") is not None else "runtime_error"
    valid = score["valid"] and not error and len(stops) == 1 and stop in ("eog", "block_budget")
    return {**telemetry, **score, "valid": bool(valid), "outcome": outcome,
            "raw_output": raw, "final_output": final, "reasoning_content": thought,
            "native_stop_reason": stop, "native_stop_present": bool(stops), "error": error}


def summarize_run(rows, batch_seconds):
    valid = [r for r in rows if r["valid"]]
    count = len(valid)
    groups = {}
    for density in b.DEPENDENCY_DENSITIES:
        selected = [r for r in rows if r.get("density") == density]
        passed = [r for r in selected if r["valid"]]
        times = [r["wall_seconds"] for r in passed if r.get("wall_seconds") is not None]
        groups[density] = {"attempts": len(selected), "correct": len(passed),
                           "median_valid_seconds": statistics.median(times) if times else None}
    return {"attempts": len(rows), "correct": count, "success_rate": count / len(rows) if rows else None,
            "request_seconds_per_correct": sum(r.get("elapsed_seconds", 0) for r in rows) / count if count else None,
            "allocation_seconds_per_correct": batch_seconds / count if count else None,
            "batch_allocation_window_seconds": batch_seconds, "groups": groups}


def matched_cases(records=32, pairs=3, seed=20260910, final_channel_prompt=False):
    cases = []
    for index in range(pairs):
        base = b.make_case(256, "direct", index, base_seed=seed, item_count=records)
        values = base["expected"]["values"]
        for density in b.DEPENDENCY_DENSITIES:
            case = b.make_case(256, density, index, base_seed=seed, item_count=records)
            old = case["records"]
            encoded = [code[0] + str(int(values[j] != values[j-1]) if code[0] == "C" else int(values[j] == "B")) for j, code in enumerate(old)]
            case["prompt"] = case["prompt"].replace("Records:" + b.compact_json(old), "Records:" + b.compact_json(encoded))
            if final_channel_prompt:
                case["prompt"] = case["prompt"].replace("Do not include reasoning, Markdown, or additional keys.", "Use your reasoning channel as needed. In the final channel include only the required JSON, with no Markdown or additional keys.")
            case.update(records=encoded, expected=base["expected"], pair_id=index,
                        case_id=f"matched-{records}-{index}-{density}")
            assert b.solve_records(encoded) == case["expected"]
            case["case_hash"] = b.stable_hash({k: v for k, v in case.items() if k != "case_hash"})
            cases.append(case)
    return cases


class Worker:
    def __init__(self, session, output_dir):
        self.session = session
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.active = None
        self.thread = None
        self.results = {}
        self.specs = {}
        self.pending_cancel = threading.Event()
        for path in self.output_dir.glob("*.request.json"):
            request = json.loads(path.read_text())
            rid = request["request_id"]
            self.specs[rid] = b.stable_hash({"prompt": request["prompt"], "timeout_seconds": float(request.get("timeout_seconds", 120))})
            result = self.output_dir / (rid + ".result.json")
            if not result.exists():
                atomic_json(result, {"request_id": rid, "request_state": "failed",
                    "error": {"type": "WorkerInterrupted", "message": "Worker exited before persisting a terminal result; original request was not replayed"}})

    def status(self):
        with self.lock:
            alive = self.session.process is not None and self.session.process.poll() is None
            return {"protocol_version": 2 if self.session.native_protocol else None,
                    "active_request": self.active, "state": self.session.state if alive or self.session.state == "starting" else "unloaded",
                    "ready": self.active is None and self.session.ready, "loaded": alive,
                    "runner_pid": self.session.process.pid if alive else None,
                    "configuration": {"max_tokens": self.session.max_tokens, "context_size": self.session.context_size,
                                      "seed": self.session.seed, "native_protocol": self.session.native_protocol,
                                      "trace_mode": self.session.trace_mode, "runner_path": self.session.runner_path,
                                      "model_path": self.session.model_path,
                                      "prefill_chunk": int(os.environ.get("DIFFUSION_PREFILL_CHUNK", "2048")),
                                      "incremental_prefill": os.environ.get("DIFFUSION_INCREMENTAL_PREFILL", "1") != "0",
                                      "ubatch": self.session.ubatch_size,
                                      "repetition_policy": "off"}}

    def submit(self, request):
        rid, prompt = request.get("request_id"), request.get("prompt")
        timeout = float(request.get("timeout_seconds", 120))
        if not isinstance(rid, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", rid):
            raise ValueError("request_id must be 1-80 letters, digits, underscores or hyphens")
        limit = float(os.environ.get("DIFFUSION_MAX_TIMEOUT", "600"))  # long-budget experiments raise this
        if not isinstance(prompt, str) or not prompt.strip() or not 0 < timeout <= limit:
            raise ValueError(f"nonempty prompt and timeout in (0,{limit:g}] required")
        spec = b.stable_hash({"prompt": prompt, "timeout_seconds": timeout})
        with self.lock:
            if rid in self.specs:
                if self.specs[rid] != spec:
                    raise RuntimeError("request ID reused with different content")
                return self.result(rid)
            if self.active:
                raise RuntimeError("worker busy")
            self.specs[rid] = spec
            self.active = rid
            self.pending_cancel = threading.Event()
            self.results[rid] = {"request_id": rid, "request_state": "queued"}
            atomic_json(self.output_dir / (rid + ".request.json"), request)
            self.thread = threading.Thread(target=self._run, args=(rid, prompt, timeout, self.pending_cancel), daemon=True)
            self.thread.start()
            return dict(self.results[rid])

    def _run(self, rid, prompt, timeout, cancel_event):
        started = time.perf_counter()
        row = {"request_id": rid}
        try:
            self.session.timeout = timeout
            raw, wall, compute, canvas = self.session.generate(prompt, rid, cancel_event=cancel_event)
            row.update(self.session.last_result, raw_output=raw, wall_seconds=wall,
                       internal_compute_seconds=compute, canvas_work_tokens=canvas)
        except Exception as exc:
            row.update(self.session.last_result, error={"type": type(exc).__name__, "message": str(exc)},
                       raw_output=b.diffusion_response_text(self.session.last_transcript), wall_seconds=None)
        row["worker_elapsed_seconds"] = time.perf_counter() - started
        row["runtime_ready"] = self.session.ready
        with self.lock:
            atomic_json(self.output_dir / (rid + ".result.json"), row)
            self.results[rid] = row
            self.active = None

    def result(self, rid):
        if not isinstance(rid, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", rid):
            raise ValueError("invalid request ID")
        with self.lock:
            if rid not in self.results:
                path = self.output_dir / (rid + ".result.json")
                if path.exists():
                    return json.loads(path.read_text())
                raise KeyError(rid)
            return dict(self.results[rid])

    def cancel(self, rid):
        with self.lock:
            if rid != self.active:
                return {"request_id": rid, "cancel_requested": False}
            self.pending_cancel.set()
            self.session.cancel()
            return {"request_id": rid, "cancel_requested": True}

    def close(self):
        if self.active:
            self.cancel(self.active)
        if self.thread:
            self.thread.join(timeout=self.session.cancellation_grace + 5)
        self.session.close()


def serve(worker, port):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass
        def handle_request(self):
            code = 200
            try:
                if self.command == "GET" and self.path == "/status":
                    value = worker.status()
                elif self.command == "GET" and self.path.startswith("/result/"):
                    value = worker.result(self.path.split("/")[-1])
                elif self.command == "POST":
                    size = int(self.headers.get("Content-Length", 0))
                    if not 0 < size <= 1048576:
                        raise ValueError("invalid request size")
                    request = json.loads(self.rfile.read(size))
                    if self.path == "/generate":
                        value = worker.submit(request)
                    elif self.path == "/cancel":
                        value = worker.cancel(request["request_id"])
                    else:
                        raise KeyError(self.path)
                else:
                    raise KeyError(self.path)
            except KeyError as exc:
                code, value = 404, {"error": str(exc)}
            except (ValueError, TypeError) as exc:
                code, value = 400, {"error": str(exc)}
            except RuntimeError as exc:
                code, value = 409, {"error": str(exc)}
            body = json.dumps(value).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        do_GET = do_POST = handle_request
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    def interrupt(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupt)
    try:
        server.serve_forever()
    finally:
        worker.close()
        server.server_close()


def rpc(url, path, data=None):
    req = Request(url + path, data=json.dumps(data).encode() if data is not None else None,
                  headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=15) as response:
        return json.load(response)


def wait_result(url, rid, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        row = rpc(url, "/result/" + rid)
        if row.get("request_state") not in ("queued", "starting", "generating"):
            return row
        time.sleep(.2)
    rpc(url, "/cancel", {"request_id": rid})
    # Never leave an untracked request when the controller deadline expires.
    grace = time.monotonic() + 20
    while time.monotonic() < grace:
        row = rpc(url, "/result/" + rid)
        if row.get("request_state") not in ("queued", "starting", "generating"):
            return row
        time.sleep(.2)
    raise TimeoutError("worker did not acknowledge cancellation; inspect worker before reuse")


def run_cases(args):
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "registration.json").exists():
        raise ValueError("use a fresh output directory; prior attempts are immutable")
    cases = matched_cases(args.records, args.pairs, args.seed, args.final_channel_prompt)
    order = [(i, b.DEPENDENCY_DENSITIES[(j + i) % 3]) for i in range(args.pairs) for j in range(3)]
    state = rpc(args.url, "/status")
    config = state["configuration"]
    if not config["native_protocol"]:
        raise ValueError("benchmark requires native protocol v2")
    tokenizer = b.TokenizerService(args.tokenizer, config["model_path"])
    try:
        for case in cases:
            case["prompt_tokens"] = tokenizer.count_prompt(case["prompt"])
            case["expected_tokens"] = tokenizer.count(b.compact_json(case["expected"]))
            if case["prompt_tokens"] + config["max_tokens"] > config["context_size"]:
                raise ValueError("prompt plus full allowance exceeds configured context")
    finally:
        tokenizer.close()
    identities = {"runner": b.artifact_identity(config["runner_path"]), "model": b.artifact_identity(config["model_path"]),
                  "harness_sha256": b.artifact_identity(__file__)["sha256"], "hardware": b.hardware_identity()}
    registration = {"cases": cases, "order": order, "configuration": config, "identities": identities,
                    "timeout_seconds": args.timeout, "batch_seconds": args.batch_seconds,
                    "records": args.records, "pairs": args.pairs, "fixture_seed": args.seed,
                    "prompt_variant": "final-channel" if args.final_channel_prompt else "legacy"}
    atomic_json(output / "registration.json", registration)
    mirror_file(output / "registration.json", args.mirror_dir)
    started = time.monotonic()
    deadline = started + args.batch_seconds
    rows = []
    reason = "all_cases_completed"
    sampler = b.GPUMemorySampler()
    sampler.thread.start()
    try:
        if not admit_case(deadline-time.monotonic(), args.timeout):
            reason = "insufficient_warmup_budget"
            return rows
        warm_id = "warmup-" + uuid.uuid4().hex
        rpc(args.url, "/generate", {"request_id": warm_id, "prompt": 'Return exactly {"values":["A","B"]} and no other text.', "timeout_seconds": args.timeout})
        warm = wait_result(args.url, warm_id, args.timeout + 60)
        atomic_json(output / "warmup.json", warm)
        mirror_file(output / "warmup.json", args.mirror_dir)
        if warm.get("error"):
            raise RuntimeError("warmup failed; inspect retained worker result")
        for pair, density in order:
            if not admit_case(deadline-time.monotonic(), args.timeout):
                reason = "insufficient_full_case_budget"
                break
            case = next(c for c in cases if c["pair_id"] == pair and c["dependency_density"] == density)
            rid = "case-" + uuid.uuid4().hex
            measured = time.perf_counter()
            rpc(args.url, "/generate", {"request_id": rid, "prompt": case["prompt"], "timeout_seconds": args.timeout})
            result = wait_result(args.url, rid, args.timeout + 30)
            row = classify_result(case, result.get("raw_output", ""), result)
            row.update(case_id=case["case_id"], case_hash=case["case_hash"], density=density, pair_id=pair,
                       sampled_peak_device_memory_mib=sampler.peak_since(measured))
            rows.append(row)
            b.append_jsonl(output / "results.jsonl", row)
            atomic_json(output / (case["case_id"] + ".result.json"), row)
            atomic_json(output / "summary.json", {**summarize_run(rows, time.monotonic()-started), "stop_reason": "running"})
            for artifact in ("results.jsonl", case["case_id"] + ".result.json", "summary.json"):
                mirror_file(output / artifact, args.mirror_dir)
            print(json.dumps({k: row.get(k) for k in ("case_id", "valid", "outcome", "wall_seconds", "error")}), flush=True)
            if row.get("error") or not row["native_stop_present"]:
                reason = "runtime_gate_failed"
                break
    except Exception:
        reason = "controller_or_warmup_error"
        raise
    finally:
        sampler.close()
        atomic_json(output / "summary.json", {**summarize_run(rows, time.monotonic()-started), "stop_reason": reason})
        mirror_file(output / "summary.json", args.mirror_dir)
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    worker = sub.add_parser("serve")
    worker.add_argument("--runner", required=True)
    worker.add_argument("--model", required=True)
    worker.add_argument("--output-dir", required=True)
    worker.add_argument("--port", type=int, default=8765)
    worker.add_argument("--max-tokens", type=int, default=9216)
    worker.add_argument("--context", type=int, default=11264)
    worker.add_argument("--seed", type=int, default=20260909)
    worker.add_argument("--trace-mode", choices=("summary", "diagnostic"), default="summary")
    run = sub.add_parser("run")
    run.add_argument("--url", default="http://127.0.0.1:8765")
    run.add_argument("--output-dir", required=True)
    run.add_argument("--mirror-dir", help="persistent directory updated after every completed case")
    run.add_argument("--tokenizer", required=True)
    run.add_argument("--records", type=int, default=32)
    run.add_argument("--pairs", type=int, default=3)
    run.add_argument("--seed", type=int, default=20260910)
    run.add_argument("--timeout", type=float, default=120)
    run.add_argument("--batch-seconds", type=float, default=720)
    run.add_argument("--final-channel-prompt", action="store_true")
    args = p.parse_args()
    if args.command == "serve":
        session = b.DiffusionSession(args.runner, args.model, args.max_tokens, args.seed,
                  context_size=args.context, native_protocol=True,
                  trace_dir=Path(args.output_dir)/"native", trace_mode=args.trace_mode)
        serve(Worker(session, args.output_dir), args.port)
    else:
        if args.records < 1 or args.pairs < 1 or args.timeout <= 0:
            p.error("records, pairs and timeout must be positive")
        run_cases(args)


if __name__ == "__main__":
    main()
