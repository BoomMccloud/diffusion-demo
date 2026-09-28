# --- OPTIONAL DIAGNOSTIC: DIFFUSIONGEMMA RUNNER PERFORMANCE ---

import csv
import json
import os
import re
import selectors
import shlex
import subprocess
import threading
import time

import torch


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

# Change this before running the cell to compare compute budgets:
# DIFF_DEBUG_STEPS = 8
# DIFF_DEBUG_STEPS = 16
# DIFF_DEBUG_STEPS = 48
PERF_DIFFUSION_STEPS = int(
    globals().get("DIFF_DEBUG_STEPS", 8)
)
if "BENCHMARK_SPEC" not in globals():
    raise RuntimeError("BENCHMARK_SPEC is missing. Run Cell 4 first.")

DEBUG_SPEC = BENCHMARK_SPEC
DEBUG_CASE_ID = globals().get(
    "DIFF_DEBUG_CASE_ID",
    DEBUG_SPEC["cases"][0]["case_id"],
)
if DEBUG_CASE_ID not in DEBUG_SPEC["case_by_id"]:
    raise ValueError(f"Unknown DIFF_DEBUG_CASE_ID: {DEBUG_CASE_ID}")
DEBUG_CASE = DEBUG_SPEC["case_by_id"][DEBUG_CASE_ID]
PROMPT = DEBUG_SPEC["build_prompt"](DEBUG_CASE)

PERF_MAX_TOKENS = int(
    globals().get(
        "DIFF_DEBUG_MAX_TOKENS",
        DEBUG_SPEC.get("default_output_tokens", 1024),
    )
)
PERF_TIMEOUT_SECONDS = int(
    globals().get("PERF_TIMEOUT_SECONDS", 20 * 60)
)
GPU_SAMPLE_INTERVAL_SECONDS = 0.5
GPU_PRINT_INTERVAL_SECONDS = 5

RUNNER_LOCAL_PATH = globals().get(
    "RUNNER_LOCAL_PATH",
    "/content/llama-diffusion-cli",
)
DIFF_MODEL_PATH = globals().get("DIFF_MODEL_PATH")
RUNNER_CACHE_KEY = globals().get("RUNNER_CACHE_KEY", "unknown")

if PERF_DIFFUSION_STEPS <= 0:
    raise ValueError("PERF_DIFFUSION_STEPS must be positive.")

if PERF_MAX_TOKENS <= 0:
    raise ValueError("PERF_MAX_TOKENS must be positive.")

if not isinstance(PROMPT, str) or not PROMPT.strip():
    raise RuntimeError("Cell 4 produced an empty diagnostic prompt.")

# This runner reads one line as one conversation turn. Collapse the multiline
# prompt so every constraint reaches the model in the first turn.
CLI_PROMPT = " ".join(PROMPT.split())

if not os.path.isfile(RUNNER_LOCAL_PATH):
    raise FileNotFoundError(
        f"Diffusion runner not found: {RUNNER_LOCAL_PATH}. Run Cell 2."
    )

if not DIFF_MODEL_PATH or not os.path.isfile(DIFF_MODEL_PATH):
    raise FileNotFoundError(
        "DiffusionGemma model is missing. Set "
        "MODELS_TO_STAGE = {'diffusion'}, then run Cell 3."
    )

if not torch.cuda.is_available():
    raise RuntimeError("A CUDA GPU runtime is required.")


# ---------------------------------------------------------
# Runtime and output paths
# ---------------------------------------------------------

gpu_name = torch.cuda.get_device_name(0)
gpu_properties = torch.cuda.get_device_properties(0)
gpu_vram_gib = gpu_properties.total_memory / 1024**3
gpu_architecture = (
    f"{gpu_properties.major}.{gpu_properties.minor}"
)

full_gpu_offload = gpu_vram_gib >= 32.0
diff_gpu_layers = 99 if full_gpu_offload else 16

DRIVE_ROOT = globals().get(
    "DRIVE_ROOT",
    "/content/drive/MyDrive/diffusiongemma-demo",
)
DEBUG_OUTPUT_DIR = os.path.join(DRIVE_ROOT, "performance-debug")
os.makedirs(DEBUG_OUTPUT_DIR, exist_ok=True)

run_timestamp = time.strftime("%Y%m%d-%H%M%S")
run_prefix = os.path.join(
    DEBUG_OUTPUT_DIR,
    f"{run_timestamp}-steps-{PERF_DIFFUSION_STEPS}",
)

COMBINED_OUTPUT_PATH = run_prefix + "-combined.txt"
STDOUT_OUTPUT_PATH = run_prefix + "-stdout.txt"
STDERR_OUTPUT_PATH = run_prefix + "-stderr.txt"
GPU_METRICS_PATH = run_prefix + "-gpu.csv"
SUMMARY_OUTPUT_PATH = run_prefix + "-summary.json"

command = [
    RUNNER_LOCAL_PATH,
    "-m",
    DIFF_MODEL_PATH,
    "-ngl",
    str(diff_gpu_layers),
    "-cnv",
    "-n",
    str(PERF_MAX_TOKENS),
    "--diffusion-kv-cache",
    "on",
    "--diffusion-eb-max-steps",
    str(PERF_DIFFUSION_STEPS),
]


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

ANSI_ESCAPE_PATTERN = re.compile(
    r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])"
)


def clean_text(text):
    return ANSI_ESCAPE_PATTERN.sub("", text).strip()


def stop_process(process):
    """Stop the CLI and ensure it releases GPU memory."""
    if process.poll() is not None:
        return

    process.terminate()

    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def run_text_command(command_parts):
    result = subprocess.run(
        command_parts,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return clean_text(result.stdout or result.stderr)


def query_gpu_metrics():
    query = (
        "timestamp,name,utilization.gpu,utilization.memory,"
        "memory.used,memory.total,power.draw,temperature.gpu"
    )
    result = subprocess.run(
        [
            "nvidia-smi",
            f"--query-gpu={query}",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        return None

    values = [value.strip() for value in result.stdout.strip().split(",")]

    if len(values) != 8:
        return None

    try:
        return {
            "timestamp": values[0],
            "gpu_name": values[1],
            "gpu_util_percent": float(values[2]),
            "memory_util_percent": float(values[3]),
            "memory_used_mib": float(values[4]),
            "memory_total_mib": float(values[5]),
            "power_watts": float(values[6]),
            "temperature_c": float(values[7]),
        }
    except ValueError:
        return None


# ---------------------------------------------------------
# Environment report
# ---------------------------------------------------------

runner_version = run_text_command([RUNNER_LOCAL_PATH, "--version"])
nvcc_version = run_text_command(["nvcc", "--version"])
model_size_gib = os.path.getsize(DIFF_MODEL_PATH) / 1024**3
prompt_bytes = len(CLI_PROMPT.encode("utf-8"))

print(f"DiffusionGemma performance diagnostic: {DEBUG_SPEC['name']}")
print(f"Case: {DEBUG_CASE_ID}")
print(f"GPU: {gpu_name}")
print(f"GPU compute capability: {gpu_architecture}")
print(f"GPU VRAM: {gpu_vram_gib:.1f} GiB")
print(f"PyTorch CUDA: {torch.version.cuda}")
print(f"Full GPU offload: {full_gpu_offload}")
print(f"GPU layers requested: {diff_gpu_layers}")
print(f"Model size: {model_size_gib:.2f} GiB")
print(f"Prompt size: {prompt_bytes:,} bytes")
print(f"Prompt preview: {CLI_PROMPT[:300]}")
print(f"Maximum output tokens: {PERF_MAX_TOKENS}")
print(f"Maximum diffusion steps: {PERF_DIFFUSION_STEPS}")
print(f"Runner cache key: {RUNNER_CACHE_KEY}")
print(f"Runner version: {runner_version[:500]}")
print(f"nvcc: {nvcc_version.splitlines()[-1] if nvcc_version else 'unknown'}")
print("Command:", " ".join(shlex.quote(part) for part in command))
print(f"Combined log: {COMBINED_OUTPUT_PATH}")
print(f"GPU metrics: {GPU_METRICS_PATH}")

baseline_metrics = query_gpu_metrics()
if baseline_metrics:
    print(
        "GPU before launch: "
        f"{baseline_metrics['gpu_util_percent']:.0f}% utilization, "
        f"{baseline_metrics['memory_used_mib']:.0f} MiB used"
    )


# ---------------------------------------------------------
# GPU monitoring thread
# ---------------------------------------------------------

gpu_samples = []
monitor_stop_event = threading.Event()
run_start = time.perf_counter()


def monitor_gpu():
    last_print_elapsed = -GPU_PRINT_INTERVAL_SECONDS

    with open(GPU_METRICS_PATH, "w", newline="") as metrics_file:
        writer = csv.DictWriter(
            metrics_file,
            fieldnames=[
                "elapsed_seconds",
                "timestamp",
                "gpu_name",
                "gpu_util_percent",
                "memory_util_percent",
                "memory_used_mib",
                "memory_total_mib",
                "power_watts",
                "temperature_c",
            ],
        )
        writer.writeheader()

        while not monitor_stop_event.is_set():
            sample = query_gpu_metrics()

            if sample is not None:
                sample["elapsed_seconds"] = round(
                    time.perf_counter() - run_start,
                    2,
                )
                gpu_samples.append(sample)
                writer.writerow(sample)
                metrics_file.flush()

                if (
                    sample["elapsed_seconds"] - last_print_elapsed
                    >= GPU_PRINT_INTERVAL_SECONDS
                ):
                    print(
                        f"[+{sample['elapsed_seconds']:7.1f}s GPU] "
                        f"util={sample['gpu_util_percent']:5.1f}%  "
                        f"VRAM={sample['memory_used_mib']:8.0f}/"
                        f"{sample['memory_total_mib']:.0f} MiB  "
                        f"power={sample['power_watts']:5.0f} W",
                        flush=True,
                    )
                    last_print_elapsed = sample["elapsed_seconds"]

            monitor_stop_event.wait(GPU_SAMPLE_INTERVAL_SECONDS)


monitor_thread = threading.Thread(target=monitor_gpu, daemon=True)


# ---------------------------------------------------------
# Run one puzzle prompt and stream CLI output
# ---------------------------------------------------------

print("\n--- LIVE CLI OUTPUT ---\n", flush=True)

process = subprocess.Popen(
    command,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    bufsize=0,
)

if process.stdin is None or process.stdout is None or process.stderr is None:
    stop_process(process)
    raise RuntimeError("Failed to open llama-diffusion-cli pipes.")

monitor_thread.start()

selector = selectors.DefaultSelector()
selector.register(process.stdout, selectors.EVENT_READ, data="stdout")
selector.register(process.stderr, selectors.EVENT_READ, data="stderr")

stdout_chunks = []
stderr_chunks = []
timed_out = False
first_diffusion_seconds = None
first_stdout_seconds = None
first_generated_stdout_seconds = None
first_turn_completed = False
recent_output = ""

try:
    try:
        process.stdin.write((CLI_PROMPT + "\n").encode("utf-8"))
        process.stdin.flush()
    except BrokenPipeError as error:
        raise RuntimeError("Runner exited before accepting the prompt.") from error

    with (
        open(COMBINED_OUTPUT_PATH, "wb") as combined_file,
        open(STDOUT_OUTPUT_PATH, "wb") as stdout_file,
        open(STDERR_OUTPUT_PATH, "wb") as stderr_file,
    ):
        while selector.get_map():
            elapsed = time.perf_counter() - run_start

            if elapsed > PERF_TIMEOUT_SECONDS and not timed_out:
                timed_out = True
                print("Performance diagnostic timed out. Stopping CLI.")
                stop_process(process)

            events = selector.select(timeout=1.0)

            for key, _ in events:
                chunk = os.read(key.fileobj.fileno(), 65536)
                stream_name = key.data
                elapsed = time.perf_counter() - run_start

                if not chunk:
                    selector.unregister(key.fileobj)
                    continue

                if stream_name == "stdout":
                    stdout_chunks.append(chunk)
                    stdout_file.write(chunk)

                    if first_stdout_seconds is None and chunk.strip():
                        first_stdout_seconds = elapsed

                    if (
                        first_generated_stdout_seconds is None
                        and first_diffusion_seconds is not None
                        and chunk.strip() not in (b">", b"> ")
                    ):
                        first_generated_stdout_seconds = elapsed
                else:
                    stderr_chunks.append(chunk)
                    stderr_file.write(chunk)

                    if (
                        first_diffusion_seconds is None
                        and b"diffusion step:" in b"".join(stderr_chunks)
                    ):
                        first_diffusion_seconds = elapsed

                decoded_chunk = chunk.decode("utf-8", errors="replace")
                recent_output = (recent_output + decoded_chunk)[-8192:]

                prefix = f"[+{elapsed:8.2f}s {stream_name}] "
                combined_file.write(prefix.encode("utf-8") + chunk)

                combined_file.flush()
                stdout_file.flush()
                stderr_file.flush()

                print(
                    prefix + decoded_chunk,
                    end="",
                    flush=True,
                )

                # This experimental runner has no --single-turn option. Keep
                # stdin open during generation, then stop when the next user
                # prompt appears. Closing stdin earlier makes it generate the
                # same request repeatedly.
                if (
                    not first_turn_completed
                    and first_diffusion_seconds is not None
                    and first_stdout_seconds is not None
                    and re.search(r"(?:^|\n)>\s*$", recent_output)
                ):
                    first_turn_completed = True
                    print(
                        "\nDetected the end of the first response. "
                        "Stopping the interactive runner.",
                        flush=True,
                    )
                    stop_process(process)

except BaseException:
    stop_process(process)
    raise
finally:
    selector.close()
    if process.stdin is not None and not process.stdin.closed:
        process.stdin.close()
    if process.poll() is None:
        stop_process(process)
    monitor_stop_event.set()
    monitor_thread.join(timeout=15)

return_code = process.wait()
total_elapsed = time.perf_counter() - run_start
stdout_text = b"".join(stdout_chunks).decode("utf-8", errors="replace")
stderr_text = b"".join(stderr_chunks).decode("utf-8", errors="replace")
all_output_text = stdout_text + "\n" + stderr_text


# ---------------------------------------------------------
# Performance and correctness summary
# ---------------------------------------------------------

parsed_output = DEBUG_SPEC["parse_output"](stdout_text)
if parsed_output is None:
    parsed_output = DEBUG_SPEC["parse_output"](stderr_text)
evaluation = DEBUG_SPEC["evaluate_output"](DEBUG_CASE, parsed_output)
output_valid = bool(evaluation["valid"])
output_status = str(evaluation["status"])

peak_gpu_util = max(
    (sample["gpu_util_percent"] for sample in gpu_samples),
    default=0.0,
)
average_gpu_util = (
    sum(sample["gpu_util_percent"] for sample in gpu_samples)
    / len(gpu_samples)
    if gpu_samples
    else 0.0
)
peak_vram_mib = max(
    (sample["memory_used_mib"] for sample in gpu_samples),
    default=0.0,
)
average_power_watts = (
    sum(sample["power_watts"] for sample in gpu_samples)
    / len(gpu_samples)
    if gpu_samples
    else 0.0
)

active_gpu_samples = [
    sample
    for sample in gpu_samples
    if (
        first_diffusion_seconds is not None
        and sample["elapsed_seconds"] >= first_diffusion_seconds
    )
]
active_average_gpu_util = (
    sum(sample["gpu_util_percent"] for sample in active_gpu_samples)
    / len(active_gpu_samples)
    if active_gpu_samples
    else 0.0
)

block_times_ms = [
    float(value)
    for value in re.findall(
        r"total time:\s*([0-9.]+)ms",
        all_output_text,
        flags=re.IGNORECASE,
    )
]
diffusion_compute_seconds = sum(block_times_ms) / 1000
interactive_turns = len(
    re.findall(r"(?:^|\n)>\s*", all_output_text)
)

interesting_log_lines = []
for line in clean_text(stderr_text).splitlines():
    lowered = line.lower()
    if any(
        marker in lowered
        for marker in (
            "offload",
            "cuda",
            "load time",
            "prompt eval",
            "eval time",
            "diffusion",
            "sampling",
        )
    ):
        interesting_log_lines.append(line)

summary = {
    "timestamp": run_timestamp,
    "return_code": return_code,
    "timed_out": timed_out,
    "total_elapsed_seconds": round(total_elapsed, 2),
    "time_to_first_diffusion_seconds": (
        round(first_diffusion_seconds, 2)
        if first_diffusion_seconds is not None
        else None
    ),
    "time_to_first_stdout_seconds": (
        round(first_stdout_seconds, 2)
        if first_stdout_seconds is not None
        else None
    ),
    "time_to_first_generated_stdout_seconds": (
        round(first_generated_stdout_seconds, 2)
        if first_generated_stdout_seconds is not None
        else None
    ),
    "diffusion_blocks_reported": len(block_times_ms),
    "diffusion_compute_seconds": round(diffusion_compute_seconds, 2),
    "interactive_turn_markers": interactive_turns,
    "first_turn_completed": first_turn_completed,
    "gpu_name": gpu_name,
    "gpu_vram_gib": round(gpu_vram_gib, 2),
    "gpu_layers": diff_gpu_layers,
    "model_size_gib": round(model_size_gib, 2),
    "max_output_tokens": PERF_MAX_TOKENS,
    "max_diffusion_steps": PERF_DIFFUSION_STEPS,
    "gpu_samples": len(gpu_samples),
    "average_gpu_util_percent": round(average_gpu_util, 2),
    "active_average_gpu_util_percent": round(
        active_average_gpu_util,
        2,
    ),
    "peak_gpu_util_percent": round(peak_gpu_util, 2),
    "peak_vram_mib": round(peak_vram_mib, 2),
    "average_power_watts": round(average_power_watts, 2),
    "puzzle_name": DEBUG_SPEC["name"],
    "case_id": DEBUG_CASE_ID,
    "output_parsed": parsed_output is not None,
    "output_valid": output_valid,
    "output_status": output_status,
    "stdout_bytes": len(stdout_text.encode("utf-8")),
    "stderr_bytes": len(stderr_text.encode("utf-8")),
    "interesting_log_lines": interesting_log_lines[-100:],
}

with open(SUMMARY_OUTPUT_PATH, "w") as summary_file:
    json.dump(summary, summary_file, indent=2)

print("\n\n--- PERFORMANCE SUMMARY ---")
print(f"Exit code: {return_code}")
print(f"Total wall time: {total_elapsed:.2f} seconds")
print(
    "Time to first diffusion step: "
    + (
        f"{first_diffusion_seconds:.2f} seconds"
        if first_diffusion_seconds is not None
        else "not detected"
    )
)
print(
    "Time to first stdout: "
    + (
        f"{first_stdout_seconds:.2f} seconds"
        if first_stdout_seconds is not None
        else "not detected"
    )
)
print(
    "Time to first generated stdout: "
    + (
        f"{first_generated_stdout_seconds:.2f} seconds"
        if first_generated_stdout_seconds is not None
        else "not detected"
    )
)
print(f"Diffusion step limit: {PERF_DIFFUSION_STEPS}")
print(f"Diffusion blocks reported: {len(block_times_ms)}")
print(f"Reported diffusion compute: {diffusion_compute_seconds:.2f} seconds")
print(f"Interactive turn markers: {interactive_turns}")
print(f"First response boundary detected: {first_turn_completed}")
print(f"GPU samples: {len(gpu_samples)}")
print(f"Average GPU utilization: {average_gpu_util:.1f}%")
print(
    f"Generation-phase GPU utilization: "
    f"{active_average_gpu_util:.1f}%"
)
print(f"Peak GPU utilization: {peak_gpu_util:.1f}%")
print(f"Peak VRAM usage: {peak_vram_mib / 1024:.2f} GiB")
print(f"Average GPU power: {average_power_watts:.1f} W")
print(f"Puzzle result: {output_status}")
print(f"Summary JSON: {SUMMARY_OUTPUT_PATH}")

if interesting_log_lines:
    print("\nRelevant runner log lines:")
    for line in interesting_log_lines[-30:]:
        print(line)

if interactive_turns > 2:
    print(
        "⚠️ More interactive prompt markers than expected were detected. "
        "Inspect the combined transcript for a repeated request."
    )

if timed_out:
    raise TimeoutError(
        f"Run exceeded {PERF_TIMEOUT_SECONDS} seconds. "
        f"Inspect {SUMMARY_OUTPUT_PATH}."
    )

if return_code != 0 and not first_turn_completed:
    raise RuntimeError(
        "llama-diffusion-cli exited unsuccessfully. "
        f"Inspect {STDERR_OUTPUT_PATH}."
    )

if first_turn_completed and return_code != 0:
    print(
        "Runner termination after the first response was intentional; "
        f"exit code {return_code} is accepted."
    )

print("\n✅ Performance diagnostic completed")
