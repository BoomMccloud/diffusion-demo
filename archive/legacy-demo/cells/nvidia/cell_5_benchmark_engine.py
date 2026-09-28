# --- CELL 5: PUZZLE-AGNOSTIC WARM BENCHMARK ENGINE ---

import gc
import json
import os
import re
import selectors
import subprocess
import threading
import time
from datetime import datetime, timezone

import numpy as np
import torch
from llama_cpp import Llama


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

LOCAL_MODEL_DIR = globals().get(
    "LOCAL_MODEL_DIR",
    "/content/gguf_models" if os.path.isdir("/content") else "/tmp/gguf_models"
)
AR_MODEL_PATH = globals().get(
    "AR_MODEL_PATH",
    os.path.join(LOCAL_MODEL_DIR, "gemma-4-26B-A4B-it-UD-Q4_K_M.gguf"),
)
DIFF_MODEL_PATH = globals().get(
    "DIFF_MODEL_PATH",
    os.path.join(LOCAL_MODEL_DIR, "diffusiongemma-26B-A4B-it-Q4_K_M.gguf"),
)
RUNNER_LOCAL_PATH = globals().get(
    "RUNNER_LOCAL_PATH",
    "/content/llama-diffusion-cli" if os.path.isdir("/content") else "/tmp/llama-diffusion-cli"
)
RUNNER_CACHE_KEY = globals().get("RUNNER_CACHE_KEY", "unknown")

if "BENCHMARK_SPEC" not in globals():
    try:
        try:
            import cell_4_schedule_puzzle as _cell4
        except ImportError:
            from cells.common import cell_4_schedule_puzzle as _cell4
        BENCHMARK_SPEC = _cell4.BENCHMARK_SPEC
    except Exception:
        raise RuntimeError("BENCHMARK_SPEC is missing. Run Cell 4 before Cell 5.")

SPEC = BENCHMARK_SPEC
PUZZLE_CASES = SPEC["cases"]
PUZZLE_CASE_BY_ID = SPEC["case_by_id"]
BUILD_PROMPT = SPEC["build_prompt"]
PARSE_OUTPUT = SPEC["parse_output"]
EVALUATE_OUTPUT = SPEC["evaluate_output"]
RENDER_OUTPUT = SPEC["render"]
PUZZLE_NAME = SPEC["name"]
PUZZLE_SLUG = SPEC["slug"]

BENCHMARK_MAX_TOKENS = int(
    globals().get(
        "PUZZLE_OUTPUT_TOKENS",
        SPEC.get("default_output_tokens", 2048),
    )
)
DIFFUSION_MAX_STEPS = int(globals().get("DIFFUSION_BENCHMARK_STEPS", 48))
BENCHMARK_TEMPERATURE = float(globals().get("BENCHMARK_TEMPERATURE", 0.8))
# Measured cold-start is ~15s load plus ~10s generation, so 20 minutes only
# ever meant "a hung case stalls the demo for 20 minutes". 3 minutes is ~7x
# the observed worst case.
BENCHMARK_TIMEOUT_SECONDS = int(
    globals().get("BENCHMARK_TIMEOUT_SECONDS", 3 * 60)
)
BENCHMARK_BASE_SEED = int(globals().get("BENCHMARK_BASE_SEED", 20260814))
LIVE_DIFFUSION_LOGS = bool(globals().get("LIVE_DIFFUSION_LOGS", True))

DRIVE_ROOT = globals().get(
    "DRIVE_ROOT",
    "/content/drive/MyDrive/diffusiongemma-demo" if os.path.isdir("/content") else "/tmp/diffusiongemma-demo"
)
RESULTS_DIR = os.path.join(DRIVE_ROOT, "benchmark-results", PUZZLE_SLUG)
os.makedirs(RESULTS_DIR, exist_ok=True)

if BENCHMARK_MAX_TOKENS <= 0 or DIFFUSION_MAX_STEPS <= 0:
    raise ValueError("Token and diffusion-step limits must be positive.")
if not torch.cuda.is_available():
    raise RuntimeError("A CUDA GPU runtime is required.")

GPU_VRAM_GIB = torch.cuda.get_device_properties(0).total_memory / 1024**3
FULL_GPU_OFFLOAD = GPU_VRAM_GIB >= 32
AR_GPU_LAYERS = 99 if FULL_GPU_OFFLOAD else 20
DIFF_GPU_LAYERS = 99 if FULL_GPU_OFFLOAD else 16

# Auto-discover models in HuggingFace cache if path unset or invalid
def _find_cached_gguf(pattern_exclude=None, pattern_include=None):
    cache_dirs = [
        os.path.join(DRIVE_ROOT, "huggingface_cache"),
        LOCAL_MODEL_DIR,
        "/content",
    ]
    for cdir in cache_dirs:
        if not os.path.isdir(cdir):
            continue
        for root, _, files in os.walk(cdir):
            for f in files:
                if not f.endswith(".gguf"):
                    continue
                if pattern_include and pattern_include not in f:
                    continue
                if pattern_exclude and pattern_exclude in f:
                    continue
                full_path = os.path.join(root, f)
                if os.path.isfile(full_path) and os.path.getsize(full_path) > 1024**3:
                    return full_path
    return None

if not AR_MODEL_PATH or not os.path.isfile(AR_MODEL_PATH):
    discovered_ar = _find_cached_gguf(pattern_include="gemma-4-26B", pattern_exclude="diffusion")
    if discovered_ar:
        AR_MODEL_PATH = discovered_ar

if not DIFF_MODEL_PATH or not os.path.isfile(DIFF_MODEL_PATH):
    discovered_diff = _find_cached_gguf(pattern_include="diffusiongemma")
    if discovered_diff:
        DIFF_MODEL_PATH = discovered_diff

HAS_AR_MODEL = bool(AR_MODEL_PATH and os.path.isfile(AR_MODEL_PATH))

if not DIFF_MODEL_PATH or not os.path.isfile(DIFF_MODEL_PATH):
    raise FileNotFoundError(f"Diffusion model not found: {DIFF_MODEL_PATH}")
if not RUNNER_LOCAL_PATH or not os.path.isfile(RUNNER_LOCAL_PATH):
    raise FileNotFoundError(f"Diffusion runner not found: {RUNNER_LOCAL_PATH}")

required_spec_keys = {
    "name",
    "slug",
    "cases",
    "case_by_id",
    "build_prompt",
    "parse_output",
    "evaluate_output",
    "render",
    "case_label",
    "case_description",
}
missing_spec_keys = required_spec_keys - set(SPEC)
if missing_spec_keys:
    raise RuntimeError(
        "Cell 4 BENCHMARK_SPEC is incomplete. Missing: "
        f"{sorted(missing_spec_keys)}"
    )

os.chmod(RUNNER_LOCAL_PATH, 0o755)

# ---------------------------------------------------------
# Warm runtime configuration
# ---------------------------------------------------------

# Loading a model costs ~15s. Keeping runtimes resident turns that fixed
# cost into a one-time operation per session so retries and iterations run instantly (0.00s load).
# A single 26B A4B Q4 model requires ~15 GiB VRAM; both require ~30 GiB.
ACTIVE_MODEL_COUNT = (1 if HAS_AR_MODEL else 0) + 1
VRAM_NEEDED_GIB = 15.0 * ACTIVE_MODEL_COUNT
CAN_KEEP_WARM = GPU_VRAM_GIB >= VRAM_NEEDED_GIB or bool(globals().get("FORCE_WARM", False))
WARM_RUNTIMES = bool(
    globals().get("WARM_RUNTIMES", CAN_KEEP_WARM)
)

print(
    f"⚡ Warm Runtimes (GPU-Resident): {WARM_RUNTIMES} "
    f"({GPU_VRAM_GIB:.1f} GiB VRAM available, ~{VRAM_NEEDED_GIB:.1f} GiB needed for {ACTIVE_MODEL_COUNT} active model(s))"
)


def runner_help_text():
    try:
        completed = subprocess.run(
            [RUNNER_LOCAL_PATH, "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return (completed.stdout or "") + "\n" + (completed.stderr or "")
    except Exception:
        return ""


RUNNER_HELP = runner_help_text()
RUNNER_SUPPORTS_REASONING_BUDGET = "--reasoning-budget" in RUNNER_HELP
RUNNER_SUPPORTS_TEMPERATURE = bool(
    re.search(r"(?:^|\s)--temp(?:erature)?(?:\s|,|$)", RUNNER_HELP)
)


# ---------------------------------------------------------
# Shared result helpers
# ---------------------------------------------------------

ANSI_PATTERN = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def clean_text(text):
    return ANSI_PATTERN.sub("", text or "").strip()


def utc_timestamp():
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def make_result(
    model_name,
    case,
    attempt,
    output_text,
    load_seconds,
    response_seconds,
    compute_seconds,
    output_tokens=None,
    error=None,
):
    parsed = PARSE_OUTPUT(output_text)

    if error is None:
        evaluation = EVALUATE_OUTPUT(case, parsed)
    else:
        evaluation = {
            "valid": False,
            "status": f"ERROR: {type(error).__name__}: {error}",
            "metrics": {},
            "display_value": None,
        }

    valid = bool(evaluation["valid"])
    status = str(evaluation["status"])
    metrics = dict(evaluation.get("metrics", {}))
    image = RENDER_OUTPUT(
        case,
        evaluation,
        f"{model_name}: {status}",
    )
    quality_key = SPEC.get("primary_quality_metric")
    optimal_key = SPEC.get("optimal_quality_metric")
    return {
        "case_id": case["case_id"],
        "difficulty": case["difficulty"],
        "model": model_name,
        "attempt": attempt,
        "valid": valid,
        "status": status,
        "load_seconds": load_seconds,
        "response_seconds": response_seconds,
        "compute_seconds": compute_seconds,
        "output_tokens": output_tokens,
        "metrics": metrics,
        "quality_value": metrics.get(quality_key) if quality_key else None,
        "optimal_quality_value": (
            metrics.get(optimal_key) if optimal_key else None
        ),
        "raw_output": output_text,
        "parsed_output": parsed,
        "display_value": evaluation.get("display_value"),
        "image": image,
    }


def serializable_result(result):
    return {
        key: value
        for key, value in result.items()
        if key != "image" and not isinstance(value, np.ndarray)
    }


# ---------------------------------------------------------
# Warm Gemma 4 AR runtime
# ---------------------------------------------------------

def load_ar_runtime():
    print(f"⏳ Loading Gemma 4 AR model into GPU VRAM: {AR_MODEL_PATH} ...")
    started = time.perf_counter()
    model = Llama(
        model_path=AR_MODEL_PATH,
        n_ctx=8192,
        n_batch=1024,
        n_gpu_layers=AR_GPU_LAYERS,
        seed=BENCHMARK_BASE_SEED,
        verbose=False,
    )
    elapsed = time.perf_counter() - started
    print(f"✅ Gemma 4 AR model loaded into GPU in {elapsed:.2f}s")
    return model, elapsed


def run_ar_case(model, case, attempt, load_seconds=0.0, max_tokens=None):
    seed = BENCHMARK_BASE_SEED + attempt
    if hasattr(model, "set_seed"):
        model.set_seed(seed)

    prompt = BUILD_PROMPT(case)
    started = time.perf_counter()
    effective_max_tokens = int(max_tokens or BENCHMARK_MAX_TOKENS)
    try:
        response = model.create_chat_completion(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return only the requested JSON. Do not output analysis, "
                        "reasoning, Markdown, or explanations."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=effective_max_tokens,
            temperature=BENCHMARK_TEMPERATURE,
        )
        elapsed = time.perf_counter() - started
        output = response["choices"][0]["message"]["content"] or ""
        usage = response.get("usage", {})
        return make_result(
            "Gemma 4 AR",
            case,
            attempt,
            output,
            load_seconds,
            elapsed,
            elapsed,
            usage.get("completion_tokens"),
        )
    except Exception as error:
        elapsed = time.perf_counter() - started
        return make_result(
            "Gemma 4 AR",
            case,
            attempt,
            "",
            load_seconds,
            elapsed,
            0.0,
            error=error,
        )


# ---------------------------------------------------------
# Persistent DiffusionGemma conversation process
# ---------------------------------------------------------

class DiffusionSession:
    def __init__(self, seed=BENCHMARK_BASE_SEED, live_logs=False):
        self.seed = seed
        self.live_logs = live_logs
        self.process = None
        self.selector = None
        self.startup_seconds = 0.0
        self.turn_count = 0

    def _command(self):
        command = [
            RUNNER_LOCAL_PATH,
            "-m",
            DIFF_MODEL_PATH,
            "-ngl",
            str(DIFF_GPU_LAYERS),
            "-cnv",
            "-n",
            str(BENCHMARK_MAX_TOKENS),
            "--seed",
            str(self.seed),
            "--diffusion-kv-cache",
            "on",
            "--diffusion-eb-max-steps",
            str(DIFFUSION_MAX_STEPS),
        ]
        if RUNNER_SUPPORTS_REASONING_BUDGET:
            command.extend(["--reasoning-budget", "0"])
        if RUNNER_SUPPORTS_TEMPERATURE:
            command.extend(["--temp", str(BENCHMARK_TEMPERATURE)])
        return command

    def start(self):
        if self.process is not None:
            return self.startup_seconds

        print(f"⏳ Launching DiffusionGemma runner process: {DIFF_MODEL_PATH} ...")
        started = time.perf_counter()
        self.process = subprocess.Popen(
            self._command(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        if (
            self.process.stdin is None
            or self.process.stdout is None
            or self.process.stderr is None
        ):
            self.close()
            raise RuntimeError("Could not open DiffusionGemma runner pipes.")

        self.selector = selectors.DefaultSelector()
        self.selector.register(
            self.process.stdout, selectors.EVENT_READ, data="stdout"
        )
        self.selector.register(
            self.process.stderr, selectors.EVENT_READ, data="stderr"
        )
        self._read_until_prompt(require_generation=False)
        self.startup_seconds = time.perf_counter() - started
        print(f"✅ DiffusionGemma runner initialized in {self.startup_seconds:.2f}s")
        return self.startup_seconds

    def _write_line(self, text):
        if self.process is None or self.process.stdin is None:
            raise RuntimeError("DiffusionGemma session is not running.")
        self.process.stdin.write((text + "\n").encode("utf-8"))
        self.process.stdin.flush()

    def _read_until_prompt(self, require_generation):
        if self.process is None or self.selector is None:
            raise RuntimeError("DiffusionGemma session is not running.")

        started = time.perf_counter()
        stdout_chunks = []
        stderr_chunks = []
        recent_stdout = ""
        recent_stderr = ""
        saw_diffusion = False

        while True:
            elapsed = time.perf_counter() - started
            if elapsed > BENCHMARK_TIMEOUT_SECONDS:
                raise TimeoutError("DiffusionGemma response timed out.")
            if self.process.poll() is not None:
                stderr = b"".join(stderr_chunks).decode(
                    "utf-8", errors="replace"
                )
                raise RuntimeError(
                    f"DiffusionGemma exited with {self.process.returncode}: "
                    f"{clean_text(stderr)[-2000:]}"
                )

            events = self.selector.select(timeout=0.5)
            for key, _ in events:
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    continue
                stream = key.data
                decoded = chunk.decode("utf-8", errors="replace")
                if stream == "stdout":
                    stdout_chunks.append(chunk)
                    recent_stdout = (recent_stdout + decoded)[-8192:]
                else:
                    stderr_chunks.append(chunk)
                    recent_stderr = (recent_stderr + decoded)[-8192:]
                    if "diffusion step:" in decoded:
                        saw_diffusion = True

                if self.live_logs:
                    print(decoded, end="", flush=True)

            clean_stdout = clean_text(recent_stdout)
            clean_stderr = clean_text(recent_stderr)
            clean_combined = clean_text(recent_stdout + "\n" + recent_stderr)
            
            has_telemetry = bool(
                re.search(r"total time:\s*[0-9.]+ms", clean_combined)
                or re.search(r"throughput:\s*[0-9.]+\s*tok/s", clean_combined)
            )
            at_prompt = (
                bool(re.search(r"(?:^|\n)>\s*$", clean_combined))
                or clean_combined.rstrip().endswith(">")
                or "conversation mode:" in clean_stderr
            )

            if not require_generation:
                if at_prompt or "conversation mode:" in clean_stderr:
                    break
            else:
                if has_telemetry or (at_prompt and (saw_diffusion or has_telemetry)):
                    break

        stdout = clean_text(
            b"".join(stdout_chunks).decode("utf-8", errors="replace")
        )
        stderr = clean_text(
            b"".join(stderr_chunks).decode("utf-8", errors="replace")
        )
        return stdout, stderr, time.perf_counter() - started

    def clear(self):
        self._write_line("/clear")
        self._read_until_prompt(require_generation=False)

    def generate(self, prompt):
        self.start()
        if self.turn_count:
            self.clear()
        one_line_prompt = " ".join(prompt.split())
        self._write_line(one_line_prompt)
        stdout, stderr, elapsed = self._read_until_prompt(
            require_generation=True
        )
        self.turn_count += 1

        combined = stdout + "\n" + stderr
        compute_ms = [
            float(value)
            for value in re.findall(
                r"total time:\s*([0-9.]+)ms", combined, re.IGNORECASE
            )
        ]
        token_matches = re.findall(r"\(([0-9]+) tok in", combined)
        return {
            "output": stdout or stderr,
            "response_seconds": elapsed,
            "compute_seconds": sum(compute_ms) / 1000,
            "output_tokens": int(token_matches[-1]) if token_matches else None,
        }

    def close(self):
        process = self.process
        if self.selector is not None:
            self.selector.close()
            self.selector = None
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        self.process = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def run_diffusion_case(session, case, attempt):
    try:
        generated = session.generate(BUILD_PROMPT(case))
        return make_result(
            "DiffusionGemma",
            case,
            attempt,
            generated["output"],
            session.startup_seconds if session.turn_count == 1 else 0.0,
            generated["response_seconds"],
            generated["compute_seconds"],
            generated["output_tokens"],
        )
    except Exception as error:
        session.close()
        return make_result(
            "DiffusionGemma",
            case,
            attempt,
            "",
            session.startup_seconds if session.turn_count == 0 else 0.0,
            0.0,
            0.0,
            error=error,
        )


def run_diffusion_file_proc(case, attempt, run_dir, max_tokens=BENCHMARK_MAX_TOKENS, temperature=BENCHMARK_TEMPERATURE):
    """Robust, procedural file-logged diffusion runner.
    
    Feeds prompt on stdin, closes stdin to signal EOF, streams all output in real time
    to disk logs, and waits for OS process exit (zero stdin deadlocks / regex prompt bugs).
    """
    prompt_text = BUILD_PROMPT(case)
    one_line_prompt = " ".join(prompt_text.split())
    
    stdout_file = os.path.join(run_dir, "diffusion_stdout.log")
    stderr_file = os.path.join(run_dir, "diffusion_stderr.log")
    combined_file = os.path.join(run_dir, "diffusiongemma_raw.txt")
    
    cmd = [
        RUNNER_LOCAL_PATH,
        "-m", DIFF_MODEL_PATH,
        "-ngl", str(DIFF_GPU_LAYERS),
        "-cnv",
        "-n", str(max_tokens),
        "--seed", str(BENCHMARK_BASE_SEED + attempt),
        "--diffusion-kv-cache", "on",
        "--diffusion-eb-max-steps", str(DIFFUSION_MAX_STEPS),
    ]
    if RUNNER_SUPPORTS_REASONING_BUDGET:
        cmd.extend(["--reasoning-budget", "0"])
    if RUNNER_SUPPORTS_TEMPERATURE:
        cmd.extend(["--temp", str(temperature)])

    started = time.perf_counter()
    stdout_chunks, stderr_chunks = [], []
    
    with open(stdout_file, "w", encoding="utf-8") as out_f, open(stderr_file, "w", encoding="utf-8") as err_f:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        
        # Send prompt and close stdin to signal single-turn execution
        if process.stdin is not None:
            process.stdin.write((one_line_prompt + "\n").encode("utf-8"))
            process.stdin.flush()
            process.stdin.close()

        def drain(stream, sink, log_file):
            for chunk in iter(lambda: stream.read(4096), b""):
                text = chunk.decode("utf-8", errors="replace")
                sink.append(text)
                log_file.write(text)
                log_file.flush()
                if LIVE_DIFFUSION_LOGS:
                    print(text, end="", flush=True)

        t_out = threading.Thread(target=drain, args=(process.stdout, stdout_chunks, out_f))
        t_err = threading.Thread(target=drain, args=(process.stderr, stderr_chunks, err_f))
        t_out.start()
        t_err.start()
        
        effective_timeout = max(
            BENCHMARK_TIMEOUT_SECONDS,
            int(max_tokens * 0.06 + 60)
        )
        try:
            process.wait(timeout=effective_timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
            raise TimeoutError(f"Diffusion runner process timed out after {effective_timeout}s.")
        finally:
            t_out.join(timeout=5)
            t_err.join(timeout=5)

    elapsed = time.perf_counter() - started
    stdout_raw = "".join(stdout_chunks)
    stderr_raw = "".join(stderr_chunks)
    combined_raw = stdout_raw + "\n" + stderr_raw
    
    with open(combined_file, "w", encoding="utf-8") as f:
        f.write(combined_raw)
        
    compute_ms = [
        float(value)
        for value in re.findall(
            r"total time:\s*([0-9.]+)ms", combined_raw, re.IGNORECASE
        )
    ]
    token_matches = re.findall(r"\(([0-9]+) tok in", combined_raw)
    output_tokens = int(token_matches[-1]) if token_matches else None
    compute_seconds = sum(compute_ms) / 1000 if compute_ms else elapsed
    
    return make_result(
        "DiffusionGemma",
        case,
        attempt,
        clean_text(stdout_raw or stderr_raw),
        0.0,
        elapsed,
        compute_seconds,
        output_tokens,
    )


# ---------------------------------------------------------
# Warm runtime cache
# ---------------------------------------------------------
# Held for the life of the notebook session. Call release_runtimes() to free
# the GPU, for example before loading a different model in another cell.

_WARM_AR_MODEL = None
_WARM_DIFFUSION_SESSION = None


def acquire_ar_runtime():
    """Return (model, load_seconds). Zero load_seconds means it was warm."""
    global _WARM_AR_MODEL

    if not WARM_RUNTIMES:
        return load_ar_runtime()

    if _WARM_AR_MODEL is None:
        _WARM_AR_MODEL, load_seconds = load_ar_runtime()
        return _WARM_AR_MODEL, load_seconds

    return _WARM_AR_MODEL, 0.0


def acquire_diffusion_session():
    """Return (session, caller_must_close).

    A warm session keeps the seed fixed at startup, so repeated attempts vary
    through the advancing sampler state rather than a per-attempt seed. Set
    WARM_RUNTIMES = False before running this cell to restore per-attempt
    seeding at the cost of a process restart each time.
    """
    global _WARM_DIFFUSION_SESSION

    if not WARM_RUNTIMES:
        return (
            DiffusionSession(
                seed=BENCHMARK_BASE_SEED,
                live_logs=LIVE_DIFFUSION_LOGS,
            ),
            True,
        )

    if _WARM_DIFFUSION_SESSION is None:
        _WARM_DIFFUSION_SESSION = DiffusionSession(
            seed=BENCHMARK_BASE_SEED,
            live_logs=LIVE_DIFFUSION_LOGS,
        )
        _WARM_DIFFUSION_SESSION.start()

    return _WARM_DIFFUSION_SESSION, False


def release_runtimes():
    """Unload both models and free GPU memory."""
    global _WARM_AR_MODEL, _WARM_DIFFUSION_SESSION

    if _WARM_AR_MODEL is not None:
        _WARM_AR_MODEL.close()
        _WARM_AR_MODEL = None
    if _WARM_DIFFUSION_SESSION is not None:
        _WARM_DIFFUSION_SESSION.close()
        _WARM_DIFFUSION_SESSION = None

    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    print("Runtimes released.")


# ---------------------------------------------------------
# Single case and repeated suite entry points
# ---------------------------------------------------------

def run_single_demo(case_id=None, attempt=1, verbose=True, max_tokens=None):
    if case_id is None:
        case_id = PUZZLE_CASES[0]["case_id"]
    case = PUZZLE_CASE_BY_ID[case_id]
    prompt_text = BUILD_PROMPT(case)
    run_time_str = utc_timestamp()
    run_dir = os.path.join(RESULTS_DIR, "runs", f"{case_id}_{run_time_str}")
    os.makedirs(run_dir, exist_ok=True)

    effective_max_tokens = int(
        max_tokens
        if max_tokens is not None
        else globals().get("PUZZLE_OUTPUT_TOKENS", BENCHMARK_MAX_TOKENS)
    )

    # Save prompt to file
    prompt_file = os.path.join(run_dir, "prompt.txt")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write(prompt_text)

    print(f"\n{'=' * 70}")
    print(f"▶ RUNNING BENCHMARK DEMO: {case_id} ({case.get('difficulty', 'medium')}) [Max Tokens: {effective_max_tokens}]")
    print(f"📁 Run Artifacts Directory: {run_dir}")
    print(f"{'=' * 70}")

    if verbose:
        print(f"\n--- [PROMPT PREVIEW] ---")
        prompt_lines = prompt_text.strip().split("\n")
        print("\n".join(prompt_lines[:8]))
        print("... [schedule canvas omitted] ...")
        print("\n".join(prompt_lines[-6:]))

    # 1. Gemma 4 AR
    if HAS_AR_MODEL:
        print(f"\n[1/2] ⏳ Executing Gemma 4 AR...")
        ar_model, ar_load = acquire_ar_runtime()
        try:
            ar_result = run_ar_case(ar_model, case, attempt, ar_load, max_tokens=effective_max_tokens)
            print(f"      ✓ Gemma 4 AR completed in {ar_result['response_seconds']:.2f}s | Valid: {ar_result['valid']} ({ar_result['status']})")
        finally:
            if not WARM_RUNTIMES:
                ar_model.close()
                gc.collect()
                torch.cuda.empty_cache()
    else:
        print(f"\n[1/2] ℹ️  Gemma 4 AR skipped (not staged)")
        ar_result = make_result(
            "Gemma 4 AR",
            case,
            attempt,
            "(AR model was not staged in Cell 3)",
            0.0,
            0.0,
            0.0,
            error=RuntimeError("AR model not staged"),
        )

    # Save AR raw output to file
    ar_file = os.path.join(run_dir, "gemma_4_ar_raw.txt")
    with open(ar_file, "w", encoding="utf-8") as f:
        f.write(ar_result.get("raw_output", ""))

    # 2. DiffusionGemma (Hot-loaded resident session)
    print(f"\n[2/2] ⏳ Executing DiffusionGemma (Hot-loaded resident session)...")
    diff_file = os.path.join(run_dir, "diffusiongemma_raw.txt")
    diff_session, caller_must_close = acquire_diffusion_session()
    try:
        diff_result = run_diffusion_case(diff_session, case, attempt)
        print(f"\n      ✓ DiffusionGemma completed in {diff_result['response_seconds']:.2f}s | Valid: {diff_result['valid']} ({diff_result['status']})")
    except Exception as error:
        diff_result = make_result(
            "DiffusionGemma",
            case,
            attempt,
            "",
            0.0,
            0.0,
            0.0,
            error=error,
        )
        print(f"\n      ❌ DiffusionGemma error: {error}")
    finally:
        if caller_must_close:
            diff_session.close()

    # Save Diffusion raw output to file
    with open(diff_file, "w", encoding="utf-8") as f:
        f.write(diff_result.get("raw_output", ""))

    # Verbose stdout output
    if verbose:
        print(f"\n{'=' * 70}")
        print("📄 RAW OUTPUTS:")
        print(f"{'=' * 70}")
        if HAS_AR_MODEL:
            print(f"\n--- [Gemma 4 AR Raw Output] ---")
            print(ar_result.get("raw_output", "(empty)").strip())
        print(f"\n--- [DiffusionGemma Raw Output] ---")
        print(diff_result.get("raw_output", "(empty)").strip())

    ar_res, diff_res, summary = _summarize_single(case_id, ar_result, diff_result)

    # Save summary and JSON evaluation to file
    summary_file = os.path.join(run_dir, "summary.md")
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary)

    json_eval_file = os.path.join(run_dir, "evaluation.json")
    with open(json_eval_file, "w", encoding="utf-8") as f:
        json.dump({
            "case_id": case_id,
            "timestamp": run_time_str,
            "ar": serializable_result(ar_result),
            "diffusion": serializable_result(diff_result),
        }, f, indent=2)

    # Also append to master benchmark results log
    master_log_path = os.path.join(RESULTS_DIR, "all_runs.jsonl")
    append_result(master_log_path, ar_result)
    append_result(master_log_path, diff_result)

    print(f"\n{'=' * 70}")
    print(f"📊 SUMMARY REPORT:")
    print(f"{'=' * 70}")
    print(summary)
    print(f"\n📁 Saved Artifacts:")
    print(f"   • Prompt:        {prompt_file}")
    if HAS_AR_MODEL:
        print(f"   • AR Output:     {ar_file}")
    print(f"   • Diff Output:   {diff_file}")
    print(f"   • Evaluation:    {json_eval_file}")
    print(f"   • Master Log:    {master_log_path}")

    return ar_res, diff_res, summary


def _summarize_single(case_id, ar_result, diff_result):
    startup_note = (
        "Both runtimes stay loaded between runs, so startup is 0.00s after "
        "the first click."
        if WARM_RUNTIMES
        else "Runtimes are reloaded on every run, so startup is paid each time."
    )
    summary = f"""
### {PUZZLE_NAME}: {case_id}

| Model | Startup | Warm response | Core compute | Result |
|---|---:|---:|---:|---|
| Gemma 4 AR | {ar_result['load_seconds']:.2f}s | {ar_result['response_seconds']:.2f}s | {ar_result['compute_seconds']:.2f}s | {ar_result['status']} |
| DiffusionGemma | {diff_result['load_seconds']:.2f}s | {diff_result['response_seconds']:.2f}s | {diff_result['compute_seconds']:.2f}s | {diff_result['status']} |

Both models used a {BENCHMARK_MAX_TOKENS}-token maximum output and temperature
{BENCHMARK_TEMPERATURE}. Startup is shown separately from response latency.
{startup_note}
"""
    return ar_result, diff_result, summary


def append_result(path, result):
    with open(path, "a", encoding="utf-8") as file:
        file.write(json.dumps(serializable_result(result)) + "\n")


def summarize_suite(results):
    rows = []
    models_to_report = (
        ("Gemma 4 AR", "DiffusionGemma")
        if HAS_AR_MODEL
        else ("DiffusionGemma",)
    )
    for model_name in models_to_report:
        model_results = [item for item in results if item["model"] == model_name]
        valid_results = [item for item in model_results if item["valid"]]
        response_times = [item["response_seconds"] for item in model_results]
        optimal_count = sum(
            item["valid"]
            and item["quality_value"] is not None
            and item["quality_value"] == item["optimal_quality_value"]
            for item in model_results
        )
        rows.append(
            {
                "model": model_name,
                "attempts": len(model_results),
                "success_rate": (
                    len(valid_results) / len(model_results)
                    if model_results else 0.0
                ),
                "optimal_rate": (
                    optimal_count / len(model_results)
                    if model_results else 0.0
                ),
                "median_response_seconds": (
                    float(np.median(response_times)) if response_times else 0.0
                ),
            }
        )

    markdown = """
### Repeated benchmark results

| Model | Attempts | Success rate | Optimal rate | Median warm response |
|---|---:|---:|---:|---:|
"""
    for row in rows:
        markdown += (
            f"| {row['model']} | {row['attempts']} | "
            f"{row['success_rate']:.1%} | {row['optimal_rate']:.1%} | "
            f"{row['median_response_seconds']:.2f}s |\n"
        )
    return markdown, rows


def run_benchmark_suite(case_count=10, attempts=1):
    case_count = max(1, min(int(case_count), len(PUZZLE_CASES)))
    attempts = max(1, int(attempts))
    selected_cases = PUZZLE_CASES[:case_count]
    result_path = os.path.join(
        RESULTS_DIR,
        f"{PUZZLE_SLUG}-{utc_timestamp()}-{case_count}x{attempts}.jsonl",
    )
    results = []

    if HAS_AR_MODEL:
        # Reuse whatever run_single_demo already warmed rather than reloading.
        ar_model, ar_load = acquire_ar_runtime()
        try:
            if ar_load:
                print("Loading Gemma 4 AR once for the complete suite...")
            else:
                print("Reusing the already-loaded Gemma 4 AR runtime.")
            for case in selected_cases:
                for attempt in range(1, attempts + 1):
                    result = run_ar_case(
                        ar_model,
                        case,
                        attempt,
                        ar_load if not results else 0.0,
                    )
                    results.append(result)
                    append_result(result_path, result)
                    print(case["case_id"], "AR", attempt, result["status"])
        finally:
            if not WARM_RUNTIMES:
                ar_model.close()
                gc.collect()
                torch.cuda.empty_cache()

    suite_run_dir = os.path.join(RESULTS_DIR, "runs", f"suite_{utc_timestamp()}")
    os.makedirs(suite_run_dir, exist_ok=True)
    diff_session, caller_must_close = acquire_diffusion_session()
    try:
        for case in selected_cases:
            for attempt in range(1, attempts + 1):
                result = run_diffusion_case(diff_session, case, attempt)
                results.append(result)
                append_result(result_path, result)
                print(case["case_id"], "Diffusion", attempt, result["status"])
    finally:
        if caller_must_close:
            diff_session.close()

    markdown, rows = summarize_suite(results)
    markdown += f"\nResults saved incrementally to `{result_path}`."
    return results, markdown, rows, result_path



print(f"✅ Cell 5: Warm benchmark engine ready for {PUZZLE_NAME}")
print(f"GPU VRAM: {GPU_VRAM_GIB:.1f} GiB")
print(f"Output maximum: {BENCHMARK_MAX_TOKENS} tokens")
print(f"Diffusion steps: {DIFFUSION_MAX_STEPS}")
print(f"Temperature: {BENCHMARK_TEMPERATURE}")
print(f"Runner cache key: {RUNNER_CACHE_KEY}")
print(f"Runner supports reasoning budget: {RUNNER_SUPPORTS_REASONING_BUDGET}")
print(f"Response timeout: {BENCHMARK_TIMEOUT_SECONDS}s")
if WARM_RUNTIMES:
    print(
        "Warm runtimes: ON. Both models stay resident after the first run, "
        "saving roughly 30s per click. Call release_runtimes() to free VRAM."
    )
else:
    print(
        f"Warm runtimes: OFF ({GPU_VRAM_GIB:.0f} GiB VRAM is below the 48 GiB "
        "needed to hold both models). Each run reloads its model."
    )
