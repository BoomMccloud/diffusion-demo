#!/usr/bin/env python3
"""Resident DiffusionGemma worker: one loaded native process behind a loopback API.

``serve`` owns the runner's pipes so a controller never competes for them.
``GET /status``, ``POST /generate``, ``POST /cancel`` and ``GET /result/<id>``
expose ownership and terminal state. ``rpc`` and ``wait_result`` are the client.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import shutil
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen
try:
    from . import gemma_runtimes as b
except ImportError:
    import gemma_runtimes as b


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
    args = p.parse_args()
    session = b.DiffusionSession(args.runner, args.model, args.max_tokens, args.seed,
              context_size=args.context, native_protocol=True,
              trace_dir=Path(args.output_dir)/"native", trace_mode=args.trace_mode)
    serve(Worker(session, args.output_dir), args.port)


if __name__ == "__main__":
    main()
