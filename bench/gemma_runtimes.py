#!/usr/bin/env python3
"""How the two pinned Gemma 4 26B A4B runtimes are driven.

- AR: ``gemma-4-26B-A4B-it`` GGUF through ``llama-cpp-python`` chat completion.
- Diffusion: ``diffusiongemma-26B-A4B-it`` GGUF through the instrumented
  protocol-v2 ``llama-diffusion-cli`` (built by ``bench/native``), owned by one
  ``DiffusionSession`` per resident process.

Neither side contains a workload. Callers supply prompts and score outputs.
"""

from __future__ import annotations

import codecs
import hashlib
import json
import os
import re
import selectors
import signal
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path


ANSI_PATTERN = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
TELEMETRY_TOTAL_RE = re.compile(r"total time:\s*([0-9.]+)ms", re.IGNORECASE)
TELEMETRY_TOKEN_RE = re.compile(r"\(([0-9]+) tok in", re.IGNORECASE)


def compact_json(value):
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def stable_hash(value):
    if not isinstance(value, str):
        value = compact_json(value)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class TokenizerService:
    """Persistent pinned-runtime tokenizer: UTF-8 hex lines in, counts out."""

    def __init__(self, command, model_path, timeout=180):
        self.timeout = timeout
        self.stderr = tempfile.TemporaryFile()
        self.selector = selectors.DefaultSelector()
        self.process = None
        self.pending = b""
        try:
            self.process = subprocess.Popen(
                [command, model_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=self.stderr, bufsize=0)
            self.selector.register(self.process.stdout, selectors.EVENT_READ)
        except Exception:
            self.close()
            raise

    def count(self, text):
        return self._request(text, b"")

    def count_prompt(self, text):
        return self._request(text, b"p:")

    def _request(self, text, prefix):
        self.process.stdin.write(prefix + text.encode("utf-8").hex().encode("ascii") + b"\n")
        self.process.stdin.flush()
        deadline = time.monotonic() + self.timeout
        while b"\n" not in self.pending:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("tokenizer helper response timed out")
            if not self.selector.select(timeout=min(remaining, 1.0)):
                continue
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk:
                self.stderr.seek(0)
                diagnostic = self.stderr.read().decode("utf-8", errors="replace")[-4000:]
                raise RuntimeError(f"tokenizer helper closed stdout: {diagnostic}")
            self.pending += chunk
        line, self.pending = self.pending.split(b"\n", 1)
        if not line.strip().isdigit():
            raise ValueError(f"invalid tokenizer count: {line!r}")
        return int(line)

    def close(self):
        if self.process is not None:
            if self.process.stdin:
                self.process.stdin.close()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)
            if self.process.stdout:
                self.process.stdout.close()
        self.selector.close()
        self.stderr.close()


def artifact_identity(path):
    candidate = Path(path)
    if not candidate.is_file():
        return str(path)
    digest = hashlib.sha256()
    with candidate.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return {"path": str(candidate), "size_bytes": candidate.stat().st_size, "sha256": digest.hexdigest()}


def hardware_identity():
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return completed.stdout.strip()
    except Exception as error:
        return f"unavailable:{type(error).__name__}"


def split_native_response(text):
    """Decode only one well-formed native thought/final channel boundary."""
    prefix = "<|channel>thought\n"
    if (text.startswith(prefix) and text.count("<|channel>") == 1
            and text.count("<channel|>") == 1):
        reasoning, final = text[len(prefix):].split("<channel|>", 1)
        return final, reasoning
    return text, None


def diffusion_response_text(transcript):
    """Remove only observed runner transport around the complete model reply."""
    text = ANSI_PATTERN.sub("", transcript)
    text = re.sub(r"\n> $", "", text)
    text = re.sub(
        r"\ntotal time: [0-9.]+ms, time per step: [^\n]*\n"
        r"(?:throughput: [0-9.]+ tok/s [^\n]*\n)?\n*$", "", text)
    timestamp = r"(?:\d+\.\d+\.\d+\.\d+ [IW] )?"
    prefix = re.compile(
        r"\A\n*" + timestamp + r"(?:"
        r"\rdiffusion step: \d+/\d+ \[[^\]\n]*\] \d+%"
        r"|init: embeddings required but some input tokens were not marked as outputs -> overriding\n)")
    while True:
        matched = prefix.match(text)
        if matched is None:
            break
        text = text[matched.end():]
    return text.strip()


class GenerationCancelled(RuntimeError):
    """A request was cancelled; cleanup has acknowledged idle or process exit."""


class DiffusionSession:
    """One owner for a native process, pipe draining, and acknowledged recovery."""

    def __init__(self, runner_path, model_path, max_tokens, seed, gpu_layers=99,
                 timeout=300, context_size=8192, *, native_protocol=False,
                 trace_dir=None, trace_mode="summary", cancellation_grace=10):
        self.runner_path, self.model_path = runner_path, model_path
        self.max_tokens, self.seed = int(max_tokens), int(seed)
        self.gpu_layers, self.timeout = int(gpu_layers), float(timeout)
        self.context_size = int(context_size)
        self.native_protocol, self.trace_mode = native_protocol, trace_mode
        self.trace_dir = Path(trace_dir or tempfile.mkdtemp(prefix="diffusion-events-"))
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.cancellation_grace = float(cancellation_grace)
        self.last_transcript, self.last_result = "", {}
        self.process = self.selector = None
        self.load_seconds, self.turn_count = 0.0, 0
        self.state = "closed"
        self.cancel_event = threading.Event()
        self._request_lock = threading.Lock()
        self.event_path = None
        self._event_offset = 0
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")

    @property
    def ready(self):
        return self.state == "ready" and self.process is not None and self.process.poll() is None

    @property
    def ubatch_size(self):
        # DIFFUSION_UBATCH decouples the batch from the context; only safe with the incremental-prefill runner.
        return int(os.environ.get("DIFFUSION_UBATCH", self.context_size))

    def command(self):
        return [self.runner_path, "-m", self.model_path, "-ngl", str(self.gpu_layers),
                "-cnv", "-c", str(self.context_size), "-b", str(self.ubatch_size),
                "-ub", str(self.ubatch_size), "-n", str(self.max_tokens),
                "--seed", str(self.seed), "--diffusion-kv-cache", "on",
                "--diffusion-eb-max-steps", "48"]

    def events(self):
        if not self.event_path or not self.event_path.exists():
            return []
        rows = []
        with self.event_path.open() as f:
            f.seek(self._event_offset)
            for line in f:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    # A concurrent writer may not have completed the last line.
                    break
        return rows

    def start(self, *, preserve_cancel=False):
        if self.ready:
            return
        if self.state in ("generating", "cancelling"):
            raise RuntimeError("native process is not idle")
        self.close()
        if not preserve_cancel:
            self.cancel_event.clear()
        self.state = "starting"
        self.turn_count = 0
        self.process_generation = uuid.uuid4().hex
        self.event_path = self.trace_dir / (self.process_generation + ".jsonl")
        self._event_offset = 0
        env = os.environ.copy()
        if self.native_protocol:
            env.update(DIFFUSION_EVENT_PATH=str(self.event_path),
                       DIFFUSION_TRACE_MODE=self.trace_mode,
                       DIFFUSION_REPETITION_POLICY="off")
        started = time.perf_counter()
        try:
            self.process = subprocess.Popen(self.command(), stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0, env=env)
            os.set_blocking(self.process.stdout.fileno(), False)
            self.selector = selectors.DefaultSelector()
            self.selector.register(self.process.stdout, selectors.EVENT_READ)
            self._read_until_prompt(False)
            if self.native_protocol and not any(e.get("event") == "ready" and e.get("version") == 2 for e in self.events()):
                raise RuntimeError("runner does not acknowledge native protocol v2")
            self.load_seconds = time.perf_counter() - started
            self.state = "ready"
        except BaseException:
            self._terminate()
            self.state = "failed"
            raise

    def _write(self, text):
        self.process.stdin.write((text + "\n").encode("utf-8"))
        self.process.stdin.flush()

    def _pump(self, wait=0.05):
        chunks = []
        if self.selector is None:
            return
        for key, _ in self.selector.select(wait):
            while True:
                try:
                    chunk = os.read(key.fileobj.fileno(), 65536)
                except BlockingIOError:
                    break
                if not chunk:
                    self.selector.unregister(key.fileobj)
                    break
                chunks.append(chunk)
        if chunks:
            self.last_transcript += self._decoder.decode(b"".join(chunks), final=False)

    def _read_until_prompt(self, require_generation, *, append=False, limit=None, interruptible=True):
        if not append:
            self.last_transcript = ""
            self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        deadline = time.monotonic() + (self.timeout if limit is None else limit)
        while True:
            self._pump()
            # Drain first, including when the child exited before we resumed.
            code = self.process.poll()
            if code is not None:
                self._pump(0)
                raise RuntimeError(f"diffusion runner exited with {code}")
            clean = ANSI_PATTERN.sub("", self.last_transcript)
            if clean.endswith("\n> "):
                self.last_transcript = clean
                return clean, ""
            if interruptible and self.cancel_event.is_set():
                raise GenerationCancelled("diffusion request cancelled")
            if time.monotonic() >= deadline:
                raise TimeoutError("diffusion response timed out")

    def _terminate(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=3)
            self._pump(0)

    def cancel(self):
        if self.state not in ("generating", "starting", "cancelling"):
            return False
        self.cancel_event.set()
        if self.state == "generating":
            self.state = "cancelling"
        return True

    def _acknowledge_interruption(self):
        if self.native_protocol and self.process is not None and self.process.poll() is None:
            try:
                self.state = "cancelling"
                self.process.send_signal(signal.SIGUSR1)
                self._read_until_prompt(True, append=True, limit=self.cancellation_grace, interruptible=False)
                if any(e.get("event") == "stop" and e.get("reason") == "cancelled" for e in self.events()):
                    self.state = "ready"
                    return "native_cancelled"
            except (RuntimeError, TimeoutError, OSError):
                pass
        self._terminate()
        self.state = "failed"
        return "process_exited"

    def generate(self, prompt, request_id=None, *, cancel_event=None):
        if not self._request_lock.acquire(blocking=False):
            raise RuntimeError("a diffusion request is already active")
        request_id = request_id or uuid.uuid4().hex
        started = time.perf_counter()
        self.last_result = {"request_id": request_id, "request_state": "starting"}
        self.last_transcript = ""
        self._event_offset = self.event_path.stat().st_size if self.event_path and self.event_path.exists() else 0
        try:
            self.cancel_event = cancel_event if cancel_event is not None else threading.Event()
            if self.cancel_event.is_set():
                raise GenerationCancelled("diffusion request cancelled before start")
            self.start(preserve_cancel=True)
            if self.turn_count:
                self._write("/clear")
                self._read_until_prompt(False)
            self._event_offset = self.event_path.stat().st_size if self.event_path.exists() else 0
            self.state = "generating"
            self.last_result.update(request_state="generating", process_generation=self.process_generation,
                                    native_turn=self.turn_count + 1, trace_path=str(self.event_path))
            started = time.perf_counter()
            self._write(" ".join(prompt.split()))
            stdout, stderr = self._read_until_prompt(True)
            wall = time.perf_counter() - started
            self.turn_count += 1
            events = self.events()
            stops = [e for e in events if e.get("event") == "stop"]
            if self.native_protocol and len(stops) != 1:
                raise RuntimeError("missing or ambiguous native stop event")
            self.state = "ready"
            self.last_result.update(request_state="completed", elapsed_seconds=wall,
                                    native_events=events, native_stop_reason=stops[0]["reason"] if stops else None,
                                    exit_code=None, error=None, trace_mode=self.trace_mode)
            combined = stdout + "\n" + stderr
            compute = sum(float(x) for x in TELEMETRY_TOTAL_RE.findall(combined)) / 1000
            tokens = TELEMETRY_TOKEN_RE.findall(combined)
            return diffusion_response_text(stdout), wall, compute or None, int(tokens[-1]) if tokens else None
        except BaseException as exc:
            interrupted = isinstance(exc, (TimeoutError, GenerationCancelled))
            ack = self._acknowledge_interruption() if interrupted else None
            if not interrupted:
                self._terminate()
                self.state = "failed"
            self.last_result.update(request_state="cancelled" if isinstance(exc, GenerationCancelled) else "timed_out" if isinstance(exc, TimeoutError) else "failed",
                elapsed_seconds=time.perf_counter() - started, error={"type": type(exc).__name__, "message": str(exc)},
                exit_code=self.process.poll() if self.process else None, native_events=self.events(),
                cancellation_ack=ack, runtime_ready=self.ready)
            if ack == "native_cancelled":
                self.turn_count += 1
            raise
        finally:
            self.last_result["runner_transcript"] = self.last_transcript
            self._request_lock.release()

    def close(self):
        self._terminate()
        if self.selector is not None:
            self.selector.close()
            self.selector = None
        if self.process is not None:
            for stream in (self.process.stdin, self.process.stdout):
                if stream:
                    stream.close()
        self.process = None
        self.state = "closed"


class GPUMemorySampler:
    """Sample device-wide used memory; this is not a process allocation peak."""

    def __init__(self):
        self.stop_event = threading.Event()
        self.samples = []
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self.stop_event.is_set():
            try:
                measured = subprocess.run(
                    ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5, check=True)
                self.samples.append((time.perf_counter(), max(float(value) for value in measured.stdout.splitlines())))
            except Exception:
                pass
            self.stop_event.wait(0.5)

    def peak_since(self, started):
        values = [value for timestamp, value in self.samples if timestamp >= started]
        return max(values) if values else None

    def close(self):
        self.stop_event.set()
        self.thread.join(timeout=6)


def append_jsonl(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(compact_json(row) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def load_ar(model_path, context_size, seed, gpu_layers=99):
    """Load the AR GGUF fully on GPU; n_batch 512 matches every recorded AR run."""
    from llama_cpp import Llama

    return Llama(model_path=model_path, n_ctx=int(context_size), n_batch=512,
                 n_gpu_layers=gpu_layers, seed=int(seed), verbose=False)


def ar_generate(model, prompt, max_tokens, seed):
    """One greedy AR chat turn from a clean state: (content, reasoning, wall, usage)."""
    model.reset()
    model.set_seed(int(seed))
    started = time.perf_counter()
    response = model.create_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=int(max_tokens), temperature=0.0)
    wall = time.perf_counter() - started
    message = response["choices"][0]["message"]
    return message["content"] or "", message.get("reasoning_content"), wall, response.get("usage", {})


def ar_token_counter(model_path):
    """Count tokens with the AR model's own vocabulary, without BOS or special parsing."""
    from llama_cpp import Llama

    vocab = Llama(model_path=model_path, vocab_only=True, verbose=False)
    return lambda text: len(vocab.tokenize(text.encode(), add_bos=False, special=False))

