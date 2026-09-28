# --- CELL OPT: DIFFUSION OPTIMIZATION LAB ---
#
# Standalone profiling cell. Paste it anywhere after Cell 2/3 (or run it on a
# bare runtime that already has the runner and GGUF files staged).
#
# Pasting this cell only DEFINES things and prints a menu. Nothing expensive
# runs until you call one of the experiment functions in a later cell:
#
#     probe_storage_throughput()   # E1  why staging costs what it costs
#     profile_cold_start()         # E2  where the first 60s of a run goes
#     sweep_diffusion()            # E3  the parameter sweep (the main event)
#     sweep_token_budget()         # E4  -n sensitivity, AR vs diffusion
#     compare_cold_vs_warm()       # E5  the per-click cost of reloading
#     report()                     # roll everything up + recommendations
#
# Every experiment appends to LAB_RESULTS and writes a JSONL line to Drive, so
# you can stop and resume without losing measurements.

import contextlib
import gc
import json
import math
import os
import re
import selectors
import shlex
import subprocess
import threading
import time
from datetime import datetime, timezone

import numpy as np
import torch


# =========================================================
# 1. Configuration
# =========================================================

LAB = {
    # Paths. Reuse the notebook's globals when the earlier cells have run.
    "runner": globals().get("RUNNER_LOCAL_PATH", "/content/llama-diffusion-cli"),
    "diff_model": globals().get(
        "DIFF_MODEL_PATH",
        "/content/gguf_models/diffusiongemma-26B-A4B-it-Q4_K_M.gguf",
    ),
    "ar_model": globals().get(
        "AR_MODEL_PATH",
        "/content/gguf_models/gemma-4-26B-A4B-it-UD-Q4_K_M.gguf",
    ),
    "drive_root": globals().get(
        "DRIVE_ROOT", "/content/drive/MyDrive/diffusiongemma-demo"
    ),
    # Baseline == what the demo runs today. Every sweep is measured against it.
    "baseline_max_tokens": 2048,
    "baseline_eb_max_steps": 8,
    "baseline_block_length": None,   # None means "runner default"
    # Matches Cell 5's BENCHMARK_TEMPERATURE. 0.8 is high for structured
    # JSON; sweep_quality() tests whether that is causing the degeneration.
    "baseline_temperature": 0.8,
    # "on" mirrors Cell 5 (cell_5_benchmark_engine.py:315). "off" is the
    # correctness probe: it trades speed for an exact decode.
    "baseline_kv_cache": "on",
    "baseline_flash_attn": None,     # None means "do not pass the flag"
    "baseline_ubatch": None,
    # Sweep axes. Set an axis to [] to skip it.
    #
    # Values below are calibrated against observed runner telemetry:
    #   -n 2048 -> 8 blocks, canvas_length=256, 6.2 of 8 steps/block used.
    #
    # -n is a CEILING, not a multiplier: the runner stops early (4 of 8
    # blocks ran). It mainly sizes n_ctx, so only large cuts matter.
    "sweep_max_tokens": [2048, 1024],
    # The EB sampler already averages 6.2 steps/block, so 6 is nearly a
    # no-op. Only 4 and below actually bite.
    "sweep_eb_max_steps": [8, 4],
    # Canvas defaults to 256 and is where the in-step parallelism lives
    # (692 tok/s in-canvas vs 110 tok/s end to end). Smaller is likely
    # slower, so probe upward.
    "sweep_block_length": [256, 512],
    # Empty: this build reports "Flash Attention not supported, set to
    # disabled" for the diffusion path, so the flag is inert here.
    "sweep_flash_attn": [],
    # Runner already reports n_batch=n_ubatch=4096, well above the canvas.
    "sweep_ubatch": [],
    # Only meaningful when the model does not fully fit in VRAM. Keeping
    # attention on GPU and pushing only MoE experts to CPU usually beats
    # a blunt low -ngl. Populated automatically below when offload is partial.
    "sweep_n_cpu_moe": [],
    # Measurement hygiene.
    "repeats": 1,                    # raise to 3 once a config looks promising
    "timeout_seconds": 900,
    "gpu_sample_interval": 0.25,
    "workload_seed": 20260814,
    "verbose_child_logs": False,
    # "cnv"     — persistent conversation session, exactly what Cell 5 ships.
    #             The runner applies the GGUF's own chat template, so there
    #             is nothing to guess and lab numbers match demo numbers.
    # "oneshot" — one process per run with a hand-rolled template. Cleaner
    #             isolation, but a different runner code path, and hand
    #             templating reproduced neither the demo's behaviour nor
    #             valid output. Kept for comparison only.
    "mode": "cnv",
    # -cnv submits on newline, so Cell 5 flattens the prompt to one line
    # (cell_5_benchmark_engine.py:412). That destroys the structure of a
    # 3.7 KB prompt. "collapse" reproduces the demo; "multiline" preserves
    # newlines via --multiline-input where the runner supports it.
    "prompt_format": "collapse",
    # One-shot `-p` mode feeds raw completion text with NO chat template, so
    # an instruct model emits one block and stops. Wrap the prompt ourselves.
    # Verified against the GGUF's own tokenizer.chat_template via
    # inspect_model_template(). This checkpoint uses <|turn> / <turn|>
    # markers, NOT Gemma's <start_of_turn> / <end_of_turn>.
    #
    # Thinking is OPT-IN: the template only emits the <|think|> token inside
    # a system turn when enable_thinking is set. Emitting no system turn
    # means no reasoning channel, which is what we want for this benchmark.
    #
    # "diffusiongemma" | "gemma" | "none"
    "chat_template": "diffusiongemma",
    # Text appended after the model turn opens, to steer generation before
    # the first token. This model opens a "<|channel>thought" reasoning
    # trace and can spend the whole budget there; a prefill that names the
    # answer channel skips it. Discover the right value with
    # inspect_model_template(), then measure it with sweep_reasoning().
    "assistant_prefill": "",
}

LAB_RESULTS = []
LAB_STAGES = []

_RUN_STAMP = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
LAB_DIR = os.path.join(LAB["drive_root"], "optimization-lab", _RUN_STAMP)
try:
    os.makedirs(LAB_DIR, exist_ok=True)
    LAB_JSONL = os.path.join(LAB_DIR, "measurements.jsonl")
except OSError:
    # Drive not mounted. Fall back to local storage rather than failing.
    LAB_DIR = os.path.join("/content/optimization-lab", _RUN_STAMP)
    os.makedirs(LAB_DIR, exist_ok=True)
    LAB_JSONL = os.path.join(LAB_DIR, "measurements.jsonl")


def record(row):
    """Append one measurement to memory and to the durable log."""
    LAB_RESULTS.append(row)
    with open(LAB_JSONL, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, default=str) + "\n")
    return row


# =========================================================
# 2. Instrumentation
# =========================================================

ANSI = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def clean(text):
    return ANSI.sub("", text or "")


@contextlib.contextmanager
def stage(name):
    """Time a named setup step and keep it for the attribution report."""
    started = time.perf_counter()
    print(f"▶ {name}...")
    try:
        yield
    finally:
        elapsed = time.perf_counter() - started
        LAB_STAGES.append({"stage": name, "seconds": elapsed})
        print(f"✅ {name}: {elapsed:.2f}s")


class GpuSampler:
    """Background nvidia-smi poller. Cheap enough to leave on during runs."""

    QUERY = (
        "utilization.gpu,utilization.memory,memory.used,power.draw,"
        "temperature.gpu,clocks.sm"
    )

    def __init__(self, interval=None):
        self.interval = interval or LAB["gpu_sample_interval"]
        self.samples = []
        self._stop = threading.Event()
        self._thread = None
        self._t0 = None

    def _poll(self):
        while not self._stop.is_set():
            try:
                completed = subprocess.run(
                    [
                        "nvidia-smi",
                        f"--query-gpu={self.QUERY}",
                        "--format=csv,noheader,nounits",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                parts = [
                    value.strip()
                    for value in completed.stdout.strip().split(",")
                ]
                if len(parts) == 6:
                    self.samples.append(
                        {
                            "t": time.perf_counter() - self._t0,
                            "gpu_util": float(parts[0]),
                            "mem_util": float(parts[1]),
                            "mem_used_mib": float(parts[2]),
                            "power_w": float(parts[3]),
                            "temp_c": float(parts[4]),
                            "sm_mhz": float(parts[5]),
                        }
                    )
            except (subprocess.SubprocessError, ValueError, OSError):
                pass
            self._stop.wait(self.interval)

    def __enter__(self):
        self._t0 = time.perf_counter()
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def summary(self, since=None):
        """Aggregate samples, optionally only those after `since` seconds."""
        rows = [
            sample
            for sample in self.samples
            if since is None or sample["t"] >= since
        ]
        if not rows:
            return {}
        return {
            "gpu_util_mean": float(np.mean([r["gpu_util"] for r in rows])),
            "gpu_util_p95": float(np.percentile([r["gpu_util"] for r in rows], 95)),
            "mem_peak_mib": float(max(r["mem_used_mib"] for r in rows)),
            "power_mean_w": float(np.mean([r["power_w"] for r in rows])),
            "sm_clock_mean_mhz": float(np.mean([r["sm_mhz"] for r in rows])),
            "samples": len(rows),
        }


# llama.cpp emits its own perf block at exit. Parse whatever is present rather
# than assuming a fixed format, so a runner upgrade degrades to "unknown".
PERF_PATTERNS = {
    "load_ms": r"load time\s*=\s*([0-9.]+)\s*ms",
    "prompt_eval_ms": r"prompt eval time\s*=\s*([0-9.]+)\s*ms",
    "prompt_tokens": r"prompt eval time.*?/\s*([0-9]+)\s*tokens",
    "eval_ms": r"(?<!prompt )eval time\s*=\s*([0-9.]+)\s*ms",
    "eval_runs": r"(?<!prompt )eval time.*?/\s*([0-9]+)\s*runs",
    "total_ms": r"total time\s*=\s*([0-9.]+)\s*ms",
    "sample_ms": r"sampling time\s*=\s*([0-9.]+)\s*ms",
}


# This runner emits far better telemetry than llama.cpp's standard perf block.
# Prefer it: these are the runner's own counts, not our inference from them.
#
#   diffusion: -n 2048 -> 8 blocks, n_ubatch=4096 ... (canvas_length=256)
#   throughput: 110.7 tok/s (1024 tok in 9250.13ms),
#               in-step parallel 692 tok/s (256-tok canvas x 6.2 steps/block)
RUNNER_PATTERNS = {
    "blocks_allocated": r"-n\s+[0-9]+\s*->\s*([0-9]+)\s*blocks",
    "canvas_length": r"canvas_length\s*=\s*([0-9]+)",
    "n_ctx": r"n_ctx\s*=\s*([0-9]+)",
    "n_batch": r"\bn_batch\s*=\s*([0-9]+)",
    "n_ubatch": r"n_ubatch\s*=\s*([0-9]+)",
    "throughput_tok_s": r"throughput:\s*([0-9.]+)\s*tok/s",
    "generated_tokens": r"throughput:.*?\(\s*([0-9]+)\s*tok in",
    "generate_ms": r"throughput:.*?tok in\s*([0-9.]+)\s*ms",
    "parallel_tok_s": r"in-step parallel\s*([0-9.]+)\s*tok/s",
    "avg_steps_per_block": r"canvas\s*x\s*([0-9.]+)\s*steps/block",
    "eb_max_steps_actual": r"diffusion_eb:\s*max_steps\s*=\s*([0-9]+)",
    "total_steps_param": r"diffusion_params:\s*steps\s*=\s*([0-9]+)",
    "entropy_bound": r"entropy_bound\s*=\s*([0-9.]+)",
    "confidence": r"confidence\s*=\s*([0-9.]+)",
}


def parse_perf(text):
    """Pull the runner's self-reported telemetry out of a captured log.

    Falls back to llama.cpp's standard perf block when present, but this
    runner does not emit one, so RUNNER_PATTERNS carries the real numbers.
    """
    found = {}
    for key, pattern in PERF_PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            found[key] = float(match.group(1))

    for key, pattern in RUNNER_PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            found[key] = float(match.group(1))

    # Count blocks by counting "step 0/N" restarts. The runner prints no
    # per-block summary line, so this is the only reliable block counter.
    steps = re.findall(r"diffusion step:\s*([0-9]+)\s*/\s*([0-9]+)", text)
    if steps:
        found["diffusion_steps_seen"] = len(steps)
        found["diffusion_steps_per_block"] = int(steps[-1][1])
        found["diffusion_blocks_seen"] = sum(
            1 for index, _ in steps if index == "0"
        )

    # Capability claims from --help can be overridden at runtime. Record it.
    found["flash_attn_disabled_at_runtime"] = bool(
        re.search(r"Flash Attention not supported", text, re.IGNORECASE)
    )
    return found


# =========================================================
# 3. Environment and runner capabilities
# =========================================================

if not torch.cuda.is_available():
    raise RuntimeError("A CUDA GPU runtime is required for this lab.")

GPU_PROPS = torch.cuda.get_device_properties(0)
GPU_NAME = torch.cuda.get_device_name(0)
GPU_VRAM_GIB = GPU_PROPS.total_memory / 1024**3
FULL_OFFLOAD = GPU_VRAM_GIB >= 32.0
DIFF_NGL = 99 if FULL_OFFLOAD else 16
AR_NGL = 99 if FULL_OFFLOAD else 20

for label, path in (
    ("Diffusion runner", LAB["runner"]),
    ("Diffusion model", LAB["diff_model"]),
):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"{label} not found: {path}")

AR_AVAILABLE = os.path.isfile(LAB["ar_model"])
os.chmod(LAB["runner"], 0o755)

if not FULL_OFFLOAD and not LAB["sweep_n_cpu_moe"]:
    # Partial offload is the regime where this knob decides everything.
    # Sweep it with -ngl 99 so only expert tensors land on the CPU.
    LAB["sweep_n_cpu_moe"] = [8, 16, 24]

_help = subprocess.run(
    [LAB["runner"], "--help"], capture_output=True, text=True, timeout=60
)
RUNNER_HELP = (_help.stdout or "") + "\n" + (_help.stderr or "")


def supports(flag):
    """True when the compiled runner advertises a flag."""
    return bool(
        re.search(rf"(?:^|\s){re.escape(flag)}(?:[\s,=]|$)", RUNNER_HELP)
    )


CAPS = {
    "block_length": supports("--diffusion-block-length"),
    "eb_max_steps": supports("--diffusion-eb-max-steps"),
    "steps": supports("--diffusion-steps"),
    "algorithm": supports("--diffusion-algorithm"),
    "kv_cache": supports("--diffusion-kv-cache"),
    "flash_attn": supports("-fa") or supports("--flash-attn"),
    "n_cpu_moe": supports("--n-cpu-moe") or supports("-ncmoe"),
    "override_tensor": supports("-ot") or supports("--override-tensor"),
    "ubatch": supports("-ub") or supports("--ubatch-size"),
    "temperature": supports("--temp") or supports("--temperature"),
    "reasoning_budget": supports("--reasoning-budget"),
    "single_prompt": supports("-p") or supports("--prompt"),
    # Lets -cnv accept newlines: lines ending in a backslash continue.
    # Without it, the prompt must be flattened to one line.
    "multiline_input": supports("--multiline-input") or supports("-mli"),
}

# Newer llama.cpp takes `-fa on|off|auto`; older builds treat it as a bare
# boolean flag. Passing a value to the boolean form breaks argument parsing,
# so detect which form this build uses.
FLASH_ATTN_TAKES_VALUE = bool(
    re.search(
        r"(?:-fa|--flash-attn)[^\n]*\[?\s*(?:on\|off|\{on)",
        RUNNER_HELP,
        re.IGNORECASE,
    )
)


# =========================================================
# 4. Workload
# =========================================================
# Self-contained so the lab runs without Cell 4. When Cell 4 HAS run, its real
# prompt and scorer are used instead, so lab numbers match demo numbers.

def _synthetic_case(seed):
    import random

    rng = random.Random(seed)
    slot_minutes = 30
    slot_count = 32
    places = ["home", "office", "gym", "market", "clinic", "cafe"]
    starts = [
        f"{8 + (index * slot_minutes) // 60:02d}:"
        f"{(index * slot_minutes) % 60:02d}"
        for index in range(slot_count)
    ]

    schedule = [
        {"start": starts[index], "activity": "Free", "location": "home"}
        for index in range(slot_count)
    ]
    for _ in range(5):
        start = rng.randrange(0, slot_count - 4)
        length = rng.randrange(1, 4)
        place = rng.choice(places)
        for index in range(start, min(start + length, slot_count)):
            schedule[index] = {
                "start": starts[index],
                "activity": rng.choice(["Meeting", "Class", "Call", "Lunch"]),
                "location": place,
            }

    travel = [
        {"from": a, "to": b, "minutes": rng.choice([10, 15, 20, 30])}
        for a in places
        for b in places
        if a != b
    ]
    return {"schedule": schedule, "travel": travel, "slot_count": slot_count}


def _synthetic_prompt(case):
    return f"""
Add one errand to an existing daily schedule.

Rules:
1. Preserve every non-Free slot exactly.
2. Keep all {case['slot_count']} slots in their original order.
3. Add the errand to contiguous Free slots.
4. Leave enough Free slots before and after it for the supplied travel time.

Errand:
{json.dumps({"activity": "Pick up prescription", "location": "clinic",
             "duration_minutes": 60, "opens": "09:00", "closes": "17:00"},
            separators=(",", ":"))}

Travel times:
{json.dumps(case['travel'], separators=(",", ":"))}

Existing schedule:
{json.dumps(case['schedule'], separators=(",", ":"))}

Return exactly one JSON object in this form:
{{"schedule":[{{"start":"08:00","activity":"...","location":"..."}},...]}}

Return the complete {case['slot_count']}-slot schedule. Return only JSON, with
no Markdown, analysis, explanation, or additional keys.
""".strip()


def _synthetic_score(case, text):
    """Cheap validity check so speed gains that destroy quality are visible."""
    cleaned = (text or "").replace("```json", "").replace("```", "")
    decoder = json.JSONDecoder()
    for position, character in enumerate(cleaned):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(cleaned[position:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and isinstance(value.get("schedule"), list):
            slots = value["schedule"]
            return {
                "parsed": True,
                "slot_count": len(slots),
                "valid": len(slots) == case["slot_count"],
            }
    return {"parsed": False, "slot_count": 0, "valid": False}


# Cell 4 defines BENCHMARK_SPEC, including its own "cases" list. Do NOT gate
# on PUZZLE_CASES: that name is created by Cell 5, so requiring it made the
# lab fall back to the synthetic workload whenever Cell 5 had not run.
_spec = globals().get("BENCHMARK_SPEC")
if _spec and _spec.get("cases"):
    WORKLOAD_SOURCE = f"Cell 4 BENCHMARK_SPEC ({_spec['name']})"
    WORKLOAD_CASE = _spec["cases"][0]
    PROMPT = _spec["build_prompt"](WORKLOAD_CASE)

    def score_output(text):
        evaluation = _spec["evaluate_output"](
            WORKLOAD_CASE, _spec["parse_output"](text)
        )
        return {
            "parsed": text is not None,
            "valid": bool(evaluation["valid"]),
            "status": str(evaluation["status"]),
        }
else:
    WORKLOAD_SOURCE = "built-in synthetic case"
    WORKLOAD_CASE = _synthetic_case(LAB["workload_seed"])
    PROMPT = _synthetic_prompt(WORKLOAD_CASE)

    def score_output(text):
        return _synthetic_score(WORKLOAD_CASE, text)


def apply_chat_template(prompt):
    """Wrap a bare prompt in the model's turn markers.

    Required for one-shot `-p` runs: that path does no templating, and an
    instruct model handed raw text will not follow the instruction. The `-cnv`
    path templates internally, so it passes the prompt through unchanged.
    """
    style = LAB["chat_template"]
    prefill = LAB["assistant_prefill"]
    if style == "none":
        return prompt + prefill
    if style == "diffusiongemma":
        # No system turn is emitted on purpose: that is where the template
        # would place <|think|>, and omitting it disables the reasoning
        # channel that was consuming the entire token budget.
        return (
            "<|turn>user\n"
            f"{prompt}<turn|>\n"
            f"<|turn>model\n{prefill}"
        )
    if style == "gemma":
        # Wrong for this checkpoint. Kept only as a comparison baseline:
        # it drives the model out of distribution and into <|channel>thought.
        return (
            "<start_of_turn>user\n"
            f"{prompt}<end_of_turn>\n"
            f"<start_of_turn>model\n{prefill}"
        )
    raise ValueError(f"Unknown chat_template: {style!r}")


def inspect_model_template(model_path=None):
    """Read the GGUF's chat template and channel-ish special tokens.

    Uses the gguf format reader rather than llama-cpp-python: this model is
    an experimental architecture that only the custom-built runner can load,
    but GGUF metadata is architecture-agnostic and parses regardless. Memory
    maps the file, so it costs no VRAM and about a second.
    """
    import sys

    try:
        from gguf import GGUFReader
    except ImportError:
        print("Installing the gguf metadata reader...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "gguf"],
            check=True,
        )
        from gguf import GGUFReader

    path = model_path or LAB["diff_model"]
    print(f"Reading metadata from {os.path.basename(path)}...")
    reader = GGUFReader(path)

    from gguf import GGUFValueType

    def field_is_stringy(field):
        """True only for STRING or ARRAY-of-STRING fields.

        Without this check a numeric field's raw bytes decode into garbage
        text instead of falling through to the numeric branch.
        """
        types = list(getattr(field, "types", []) or [])
        return bool(types) and types[-1] == GGUFValueType.STRING

    def field_to_strings(field):
        """Decode a GGUF string or string-array field."""
        if not field_is_stringy(field):
            return []
        values = []
        for index in field.data:
            try:
                values.append(
                    bytes(field.parts[index]).decode("utf-8", errors="replace")
                )
            except (IndexError, TypeError, ValueError):
                continue
        return values

    template = None
    template_field = reader.fields.get("tokenizer.chat_template")
    if template_field is not None:
        strings = field_to_strings(template_field)
        template = strings[0] if strings else None

    print("\n── chat template ──")
    print(template or "(none stored in the GGUF)")

    print("\n── channel / thinking tokens ──")
    hits = []
    tokens_field = reader.fields.get("tokenizer.ggml.tokens")
    if tokens_field is not None:
        markers = (
            "channel", "think", "thought", "analysis",
            "final", "reason", "answer",
        )
        for token_id, piece in enumerate(field_to_strings(tokens_field)):
            lowered = piece.lower()
            if any(marker in lowered for marker in markers):
                hits.append((token_id, piece))
    for token_id, piece in hits[:80]:
        print(f"  {token_id:>7}  {piece!r}")
    if not hits:
        print("  (none found — the markers may be plain text, not tokens)")
    print(f"\n{len(hits)} candidate tokens found.")

    # Anything else that hints at how the model separates reasoning.
    print("\n── other relevant metadata ──")
    for name, field in reader.fields.items():
        if any(
            key in name.lower()
            for key in ("eot", "eog", "eos", "template", "prefix", "suffix")
        ):
            strings = field_to_strings(field)
            if strings:
                preview = strings[0][:120]
            else:
                # Numeric field: show the scalar rather than a raw array.
                try:
                    preview = field.parts[field.data[0]].tolist()
                    if isinstance(preview, list) and len(preview) == 1:
                        preview = preview[0]
                except (IndexError, AttributeError, TypeError):
                    preview = "(unreadable)"
            print(f"  {name}: {preview}")

    return {"template": template, "tokens": hits}


PROMPT_BYTES = len(PROMPT.encode("utf-8"))
PROMPT_TOKENS_EST = PROMPT_BYTES // 4


# =========================================================
# 5. Diffusion profiler
# =========================================================

def build_diffusion_command(
    max_tokens=None,
    eb_max_steps=None,
    block_length=None,
    flash_attn=None,
    ubatch=None,
    n_cpu_moe=None,
    ngl=None,
    temperature=None,
    kv_cache=None,
    interactive=False,
):
    """Assemble a runner command, silently dropping unsupported flags."""
    command = [
        LAB["runner"],
        "-m",
        LAB["diff_model"],
        "-ngl",
        str(DIFF_NGL if ngl is None else ngl),
        "-n",
        str(max_tokens if max_tokens is not None else LAB["baseline_max_tokens"]),
    ]
    # Was hardcoded "on", so every run in the investigation carried it and it
    # was never a variable. KV caching across denoising steps is an
    # approximation: values are reused while positions are still being
    # rewritten, which is a candidate cause of the progressive mid-generation
    # collapse seen on this workload.
    effective_kv = (
        kv_cache if kv_cache is not None else LAB["baseline_kv_cache"]
    )
    if CAPS["kv_cache"] and effective_kv is not None:
        command += ["--diffusion-kv-cache", effective_kv]

    steps = (
        eb_max_steps
        if eb_max_steps is not None
        else LAB["baseline_eb_max_steps"]
    )
    if CAPS["eb_max_steps"] and steps is not None:
        command += ["--diffusion-eb-max-steps", str(steps)]

    if block_length is not None and CAPS["block_length"]:
        command += ["--diffusion-block-length", str(block_length)]
    if flash_attn is not None and CAPS["flash_attn"]:
        command += ["-fa", str(flash_attn)] if FLASH_ATTN_TAKES_VALUE else ["-fa"]
    if ubatch is not None and CAPS["ubatch"]:
        command += ["-ub", str(ubatch)]
    if n_cpu_moe is not None and CAPS["n_cpu_moe"]:
        command += ["--n-cpu-moe", str(n_cpu_moe)]
    # Cell 5 passes --temp 0.8. The lab was silently using the runner
    # default, so lab and demo were not measuring the same configuration.
    effective_temp = (
        temperature if temperature is not None else LAB["baseline_temperature"]
    )
    if effective_temp is not None and CAPS["temperature"]:
        command += ["--temp", str(effective_temp)]
    if CAPS["reasoning_budget"]:
        command += ["--reasoning-budget", "0"]

    if interactive:
        # -cnv applies the chat template itself; pass the prompt bare on stdin.
        command += ["-cnv"]
        if LAB["prompt_format"] == "multiline" and CAPS["multiline_input"]:
            command += ["--multiline-input"]
    elif CAPS["single_prompt"]:
        command += ["-p", apply_chat_template(PROMPT), "-no-cnv"]
    else:
        command += ["-cnv"]
    return command


class LabDiffusionSession:
    """Persistent -cnv runner session, mirroring Cell 5's DiffusionSession.

    The runner applies the GGUF chat template itself in this mode, so the
    prompt is sent raw. Keeping the process alive across turns is also what
    makes the warm-vs-cold measurement possible.
    """

    def __init__(self, **overrides):
        self.overrides = overrides
        self.process = None
        self.selector = None
        self.startup_seconds = 0.0
        self.turn_count = 0
        self.startup_output = ""
        self.command = build_diffusion_command(interactive=True, **overrides)

    def start(self):
        if self.process is not None:
            return self.startup_seconds
        started = time.perf_counter()
        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ, "stdout")
        self.selector.register(self.process.stderr, selectors.EVENT_READ, "stderr")
        # Keep the startup banner: the geometry line ("-n 2048 -> 8 blocks,
        # canvas_length=256") and the flash-attention warning are printed
        # once at load and would otherwise be lost before the first turn.
        out, err, _ = self._read_until_prompt(require_generation=False)
        self.startup_output = out + "\n" + err
        self.startup_seconds = time.perf_counter() - started
        return self.startup_seconds

    def _read_until_prompt(self, require_generation):
        started = time.perf_counter()
        stdout_chunks, stderr_chunks = [], []
        recent = ""
        saw_generation = False
        while True:
            if time.perf_counter() - started > LAB["timeout_seconds"]:
                raise TimeoutError("diffusion turn timed out")
            if self.process.poll() is not None:
                tail = clean(b"".join(stderr_chunks).decode("utf-8", "replace"))
                raise RuntimeError(
                    f"runner exited with {self.process.returncode}: {tail[-1500:]}"
                )
            for key, _ in self.selector.select(timeout=1.0):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    continue
                if key.data == "stdout":
                    stdout_chunks.append(chunk)
                    recent = (recent + chunk.decode("utf-8", "replace"))[-8192:]
                else:
                    stderr_chunks.append(chunk)
                    if b"diffusion step:" in chunk:
                        saw_generation = True
                if LAB["verbose_child_logs"]:
                    print(chunk.decode("utf-8", "replace"), end="", flush=True)
            at_prompt = bool(re.search(r"(?:^|\n)>\s*$", clean(recent)))
            if at_prompt and (saw_generation or not require_generation):
                break
        return (
            clean(b"".join(stdout_chunks).decode("utf-8", "replace")),
            clean(b"".join(stderr_chunks).decode("utf-8", "replace")),
            time.perf_counter() - started,
        )

    def _write(self, text):
        self.process.stdin.write((text + "\n").encode("utf-8"))
        self.process.stdin.flush()

    def clear(self):
        self._write("/clear")
        self._read_until_prompt(require_generation=False)

    def generate(self, prompt):
        self.start()
        if self.turn_count:
            self.clear()
        if LAB["prompt_format"] == "multiline" and CAPS["multiline_input"]:
            # With --multiline-input a trailing backslash continues the line,
            # so the prompt's structure survives.
            lines = prompt.split("\n")
            self._write("\\\n".join(lines))
        else:
            # Newlines submit in -cnv, so the prompt must be a single line.
            self._write(" ".join(prompt.split()))
        stdout, stderr, elapsed = self._read_until_prompt(require_generation=True)
        self.turn_count += 1
        return stdout, stderr, elapsed

    def close(self):
        if self.selector is not None:
            self.selector.close()
            self.selector = None
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)
        self.process = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.close()


def _finish_row(label, overrides, stdout, stderr, wall, marks, sampler,
                load_s, prefill_s, generate_s, timing_source, command,
                timed_out=False, return_code=0):
    """Shared row construction for both runner modes."""
    perf = parse_perf(stdout + "\n" + stderr)
    max_tokens = overrides.get("max_tokens") or LAB["baseline_max_tokens"]
    block_length = overrides.get("block_length") or LAB["baseline_block_length"]
    steps = overrides.get("eb_max_steps") or LAB["baseline_eb_max_steps"]
    blocks = perf.get("diffusion_blocks_seen") or (
        math.ceil(max_tokens / block_length) if block_length else None
    )
    observed_steps = perf.get("diffusion_steps_per_block") or steps

    row = {
        "experiment": "diffusion",
        "label": label,
        "model": "DiffusionGemma",
        "mode": LAB["mode"],
        "timed_out": timed_out,
        "return_code": return_code,
        "max_tokens": max_tokens,
        "eb_max_steps": steps,
        # Temperature was previously applied but never recorded, so a results
        # row could not be traced back to the configuration that produced it.
        "temperature": (
            overrides["temperature"] if overrides.get("temperature") is not None
            else LAB["baseline_temperature"]
        ),
        "block_length": block_length,
        "flash_attn": overrides.get("flash_attn"),
        "ubatch": overrides.get("ubatch"),
        "n_cpu_moe": overrides.get("n_cpu_moe"),
        "kv_cache": overrides.get("kv_cache") or LAB["baseline_kv_cache"],
        "ngl": overrides.get("ngl", DIFF_NGL),
        "wall_seconds": wall,
        "load_seconds": load_s,
        "prefill_seconds": prefill_s,
        "generate_seconds": generate_s,
        "timing_source": timing_source,
        "chat_template": LAB["chat_template"],
        "spawn_to_first_log": marks.get("first_stderr"),
        "spawn_to_first_diffusion_step": marks.get("first_diffusion_step"),
        "spawn_to_first_output_char": marks.get("first_generated_char"),
        "prompt_tokens": perf.get("prompt_tokens"),
        "output_tokens": perf.get("eval_runs") or perf.get("generated_tokens"),
        "blocks_allocated": perf.get("blocks_allocated"),
        "canvas_length": perf.get("canvas_length"),
        "n_ctx": perf.get("n_ctx"),
        "throughput_tok_s": perf.get("throughput_tok_s"),
        "parallel_tok_s": perf.get("parallel_tok_s"),
        "avg_steps_per_block": perf.get("avg_steps_per_block"),
        "flash_attn_disabled_at_runtime": perf.get(
            "flash_attn_disabled_at_runtime"
        ),
        "blocks_reported": blocks,
        "steps_per_block": observed_steps,
        "diffusion_steps_seen": perf.get("diffusion_steps_seen"),
        "forward_passes": (
            perf.get("diffusion_steps_seen")
            or ((blocks * observed_steps) if (blocks and observed_steps) else None)
        ),
        "gpu": sampler.summary(since=marks.get("first_diffusion_step")),
        "command": command,
    }
    row.update(score_output(stdout))

    generated = stdout
    for marker in ("<start_of_turn>model", "<end_of_turn>", "<|turn>model"):
        if marker in generated:
            generated = generated.split(marker)[-1]
    row["output_head"] = generated.strip()[:1200]
    row["output_tail"] = generated.strip()[-600:]
    row["thought_channel"] = "<|channel>thought" in stdout
    row["seconds_per_forward"] = (
        generate_s / row["forward_passes"] if row["forward_passes"] else None
    )
    row["tokens_per_second"] = (
        row["output_tokens"] / generate_s
        if row["output_tokens"] and generate_s
        else None
    )

    log_path = os.path.join(LAB_DIR, f"{label}.log")
    with open(log_path, "w", encoding="utf-8") as handle:
        handle.write(command + "\n\n=== STDOUT ===\n" + stdout)
        handle.write("\n\n=== STDERR ===\n" + stderr)
    row["log_path"] = log_path
    return record(row)


def _run_diffusion_cnv(label="baseline", **overrides):
    """One turn in a fresh -cnv session, with startup timed separately."""
    marks = {}
    with GpuSampler() as sampler:
        started = time.perf_counter()
        session = LabDiffusionSession(**overrides)
        try:
            startup = session.start()
            marks["first_diffusion_step"] = startup
            stdout, stderr, turn_seconds = session.generate(PROMPT)
            marks["first_generated_char"] = startup
            # Load-time geometry lives in the startup banner, generation
            # telemetry in the turn. Both are needed for a complete row.
            stderr = session.startup_output + "\n" + stderr
        finally:
            session.close()
        wall = time.perf_counter() - started

    perf = parse_perf(stdout + "\n" + stderr)
    generate_s = (
        perf["generate_ms"] / 1000 if perf.get("generate_ms") else turn_seconds
    )
    return _finish_row(
        label, overrides, stdout, stderr, wall, marks, sampler,
        load_s=startup,
        prefill_s=max(0.0, turn_seconds - generate_s),
        generate_s=generate_s,
        timing_source=(
            "runner-throughput" if perf.get("generate_ms") else "timeline"
        ),
        command=" ".join(shlex.quote(part) for part in session.command),
    )


def run_diffusion_once(label="baseline", **overrides):
    """Dispatch to the configured runner mode."""
    if LAB["mode"] == "cnv":
        return _run_diffusion_cnv(label, **overrides)
    return _run_diffusion_oneshot(label, **overrides)


def _run_diffusion_oneshot(label="baseline", **overrides):
    """One cold process with a hand-rolled template. Comparison only."""
    command = build_diffusion_command(**overrides)
    stdout_chunks, stderr_chunks = [], []
    marks = {}

    started = time.perf_counter()
    with GpuSampler() as sampler:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )

        interactive = "-cnv" in command
        if interactive:
            # Interactive mode needs the prompt fed on stdin.
            threading.Timer(
                0.0,
                lambda: _feed_prompt(process),
            ).start()

        def drain(pipe, sink, key):
            for chunk in iter(lambda: pipe.read(4096), b""):
                now = time.perf_counter() - started
                text = chunk.decode("utf-8", errors="replace")
                sink.append(text)
                marks.setdefault(f"first_{key}", now)
                if "diffusion step:" in text:
                    marks.setdefault("first_diffusion_step", now)
                if key == "stdout" and text.strip():
                    marks.setdefault("first_generated_char", now)
                marks[f"last_{key}"] = now
                if LAB["verbose_child_logs"]:
                    print(text, end="", flush=True)

        threads = [
            threading.Thread(
                target=drain, args=(process.stdout, stdout_chunks, "stdout")
            ),
            threading.Thread(
                target=drain, args=(process.stderr, stderr_chunks, "stderr")
            ),
        ]
        for thread in threads:
            thread.start()

        timed_out = False
        try:
            process.wait(timeout=LAB["timeout_seconds"])
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            process.wait(timeout=30)
        for thread in threads:
            thread.join(timeout=10)

        wall = time.perf_counter() - started

    stdout = clean("".join(stdout_chunks))
    stderr = clean("".join(stderr_chunks))
    perf = parse_perf(stdout + "\n" + stderr)

    # This runner emits per-block "total time: Xms" but not llama.cpp's
    # llama_perf_context_print block, so the self-reported fields are usually
    # absent. Fall back to the observed process timeline, and say which
    # source was used so the numbers are never silently ambiguous.
    timing_source = "runner"
    load_s = perf.get("load_ms", 0.0) / 1000
    prefill_s = perf.get("prompt_eval_ms", 0.0) / 1000
    generate_s = perf.get("eval_ms", 0.0) / 1000

    first_step = marks.get("first_diffusion_step")
    if not generate_s and perf.get("generate_ms"):
        # The runner's own throughput line is the most accurate source.
        timing_source = "runner-throughput"
        generate_s = perf["generate_ms"] / 1000
    if not generate_s:
        timing_source = "timeline"
        generate_s = max(0.0, wall - (first_step or 0.0))
    if not load_s and first_step:
        # Everything before the first diffusion step is load + prefill. We
        # cannot split them without runner support, so attribute jointly.
        load_s = first_step
        prefill_s = 0.0

    max_tokens = overrides.get("max_tokens") or LAB["baseline_max_tokens"]
    block_length = overrides.get("block_length") or LAB["baseline_block_length"]
    steps = overrides.get("eb_max_steps") or LAB["baseline_eb_max_steps"]
    # Prefer what the runner actually reported over what we asked for.
    blocks = perf.get("diffusion_blocks_seen") or (
        math.ceil(max_tokens / block_length) if block_length else None
    )
    observed_steps = perf.get("diffusion_steps_per_block") or steps

    row = {
        "experiment": "diffusion",
        "label": label,
        "model": "DiffusionGemma",
        "timed_out": timed_out,
        "return_code": process.returncode,
        # Knobs under test.
        "max_tokens": max_tokens,
        "eb_max_steps": steps,
        "temperature": (
            overrides["temperature"] if overrides.get("temperature") is not None
            else LAB["baseline_temperature"]
        ),
        "block_length": block_length,
        "flash_attn": overrides.get("flash_attn"),
        "ubatch": overrides.get("ubatch"),
        "n_cpu_moe": overrides.get("n_cpu_moe"),
        "kv_cache": overrides.get("kv_cache") or LAB["baseline_kv_cache"],
        "ngl": overrides.get("ngl", DIFF_NGL),
        # The breakdown. This is the point of the whole cell.
        "wall_seconds": wall,
        "load_seconds": load_s,
        "prefill_seconds": prefill_s,
        "generate_seconds": generate_s,
        "timing_source": timing_source,
        "chat_template": LAB["chat_template"],
        "spawn_to_first_log": marks.get("first_stderr"),
        "spawn_to_first_diffusion_step": marks.get("first_diffusion_step"),
        "spawn_to_first_output_char": marks.get("first_generated_char"),
        # Work actually performed.
        "prompt_tokens": perf.get("prompt_tokens"),
        "output_tokens": perf.get("eval_runs") or perf.get("generated_tokens"),
        # Runner-reported geometry. blocks_allocated is what -n bought;
        # blocks_reported is what actually ran. A gap means early stopping.
        "blocks_allocated": perf.get("blocks_allocated"),
        "canvas_length": perf.get("canvas_length"),
        "n_ctx": perf.get("n_ctx"),
        "throughput_tok_s": perf.get("throughput_tok_s"),
        "parallel_tok_s": perf.get("parallel_tok_s"),
        "avg_steps_per_block": perf.get("avg_steps_per_block"),
        "flash_attn_disabled_at_runtime": perf.get(
            "flash_attn_disabled_at_runtime"
        ),
        "blocks_reported": blocks,
        "steps_per_block": observed_steps,
        "diffusion_steps_seen": perf.get("diffusion_steps_seen"),
        "forward_passes": (
            perf.get("diffusion_steps_seen")
            or ((blocks * observed_steps) if (blocks and observed_steps) else None)
        ),
        "gpu": sampler.summary(since=marks.get("first_diffusion_step")),
        "command": " ".join(shlex.quote(part) for part in command),
    }
    row.update(score_output(stdout))
    # Keep a trimmed copy of the generated text on the row itself. Debugging
    # an invalid result should never require a second trip to the log file.
    generated = stdout
    # Must match _finish_row's marker list: this path templates with
    # <|turn>model, and omitting it left the model's echoed prompt in the
    # captured output.
    for marker in ("<start_of_turn>model", "<end_of_turn>", "<|turn>model"):
        if marker in generated:
            generated = generated.split(marker)[-1]
    row["output_head"] = generated.strip()[:1200]
    row["output_tail"] = generated.strip()[-600:]
    # This builder had drifted from _finish_row and never set these, so any
    # caller that compared cnv and oneshot rows side by side hit a KeyError.
    row["mode"] = LAB["mode"]
    row["thought_channel"] = "<|channel>thought" in stdout
    row["seconds_per_forward"] = (
        generate_s / row["forward_passes"] if row["forward_passes"] else None
    )
    row["tokens_per_second"] = (
        row["output_tokens"] / generate_s
        if row["output_tokens"] and generate_s
        else None
    )

    log_path = os.path.join(LAB_DIR, f"{label}.log")
    with open(log_path, "w", encoding="utf-8") as handle:
        handle.write(row["command"] + "\n\n=== STDOUT ===\n" + stdout)
        handle.write("\n\n=== STDERR ===\n" + stderr)
    row["log_path"] = log_path

    return record(row)


def _feed_prompt(process):
    """Interactive fallback: send the prompt, then close stdin so the runner
    exits after generating instead of waiting forever at its prompt."""
    try:
        process.stdin.write((" ".join(PROMPT.split()) + "\n").encode("utf-8"))
        process.stdin.flush()
        process.stdin.close()
    except (BrokenPipeError, ValueError, OSError):
        pass


# =========================================================
# 6. AR profiler
# =========================================================

def run_ar_once(label="ar-baseline", max_tokens=None):
    """AR baseline. Prefill is isolated with a separate 1-token call."""
    from llama_cpp import Llama

    max_tokens = max_tokens or LAB["baseline_max_tokens"]
    messages = [
        {
            "role": "system",
            "content": (
                "Return only the requested JSON. Do not output analysis, "
                "reasoning, Markdown, or explanations."
            ),
        },
        {"role": "user", "content": PROMPT},
    ]

    load_start = time.perf_counter()
    model = Llama(
        model_path=LAB["ar_model"],
        n_ctx=8192,
        n_batch=1024,
        n_gpu_layers=AR_NGL,
        seed=LAB["workload_seed"],
        verbose=False,
    )
    load_s = time.perf_counter() - load_start

    try:
        # A cold-cache 1-token call isolates prefill. The full call that
        # follows reuses that cached prefix, so its wall time is essentially
        # pure decode — do NOT subtract prefill from it a second time.
        prefill_start = time.perf_counter()
        model.create_chat_completion(messages=messages, max_tokens=1)
        prefill_s = time.perf_counter() - prefill_start

        with GpuSampler() as sampler:
            gen_start = time.perf_counter()
            response = model.create_chat_completion(
                messages=messages, max_tokens=max_tokens, temperature=0.8
            )
            generate_s = time.perf_counter() - gen_start

        output = response["choices"][0]["message"]["content"] or ""
        usage = response.get("usage", {})
        total_s = prefill_s + generate_s

        row = {
            "experiment": "ar",
            "label": label,
            "model": "Gemma 4 AR",
            "max_tokens": max_tokens,
            "wall_seconds": total_s,
            "load_seconds": load_s,
            "prefill_seconds": prefill_s,
            "generate_seconds": generate_s,
            "prompt_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
            "gpu": sampler.summary(),
            "tokens_per_second": (
                usage.get("completion_tokens", 0) / generate_s
                if generate_s
                else None
            ),
        }
        row.update(score_output(output))
        return record(row)
    finally:
        model.close()
        gc.collect()
        torch.cuda.empty_cache()


# =========================================================
# 7. Experiments
# =========================================================

def probe_storage_throughput(sample_mib=512):
    """E1: measure Drive vs local read speed without recopying 30 GB.

    Justifies (or kills) the 'download straight to local disk' change by
    extrapolating a measured sample to the real model size.
    """
    print("=== E1: storage throughput ===")
    rows = []
    targets = {"local": LAB["diff_model"]}
    drive_candidate = os.path.join(LAB["drive_root"], "huggingface_cache")
    if os.path.isdir(drive_candidate):
        for root, _, files in os.walk(drive_candidate):
            for name in files:
                if name.endswith(".gguf"):
                    targets["drive"] = os.path.join(root, name)
                    break
            if "drive" in targets:
                break

    chunk = 16 * 1024**2
    limit = sample_mib * 1024**2
    for tier, path in targets.items():
        if not os.path.isfile(path):
            continue
        read = 0
        started = time.perf_counter()
        with open(path, "rb") as handle:
            while read < limit:
                block = handle.read(chunk)
                if not block:
                    break
                read += len(block)
        elapsed = time.perf_counter() - started
        mibps = (read / 1024**2) / elapsed if elapsed else 0.0
        size_gib = os.path.getsize(path) / 1024**3
        rows.append(
            record(
                {
                    "experiment": "storage",
                    "label": f"read-{tier}",
                    "tier": tier,
                    "path": path,
                    "mib_per_second": mibps,
                    "file_gib": size_gib,
                    "projected_full_copy_seconds": (
                        (size_gib * 1024) / mibps if mibps else None
                    ),
                }
            )
        )
        if mibps:
            minutes = (size_gib * 1024) / mibps / 60
            print(
                f"  {tier:<6} {mibps:7.1f} MiB/s  → a {size_gib:.1f} GiB "
                f"copy at this rate takes {minutes:.1f} min"
            )
        else:
            print(f"  {tier:<6} unmeasurable")

    if "drive" not in targets:
        print("  (no Drive-cached GGUF found; skipping the Drive tier)")
    return rows


def profile_cold_start():
    """E2: where the seconds go before the first generated character."""
    print("=== E2: cold start breakdown ===")
    row = run_diffusion_once(label="cold-start")
    print(f"  process spawn → first log      {row['spawn_to_first_log']}")
    print(f"  spawn → first diffusion step   {row['spawn_to_first_diffusion_step']}")
    print(f"  spawn → first output char      {row['spawn_to_first_output_char']}")
    print(f"  load + prefill                 {row['load_seconds']:.2f}s")
    print(f"  generation                     {row['generate_seconds']:.2f}s")
    print(f"  wall                           {row['wall_seconds']:.2f}s")
    print(f"  timing source                  {row['timing_source']}")
    print(f"  blocks allocated / run         "
          f"{row['blocks_allocated']} / {row['blocks_reported']}")
    print(f"  canvas length                  {row['canvas_length']}")
    print(f"  output tokens                  {row['output_tokens']}")
    print(f"  throughput                     {row['throughput_tok_s']} tok/s "
          f"({row['parallel_tok_s']} tok/s in-canvas)")
    print(f"  avg steps/block                {row['avg_steps_per_block']}")
    print(f"  output valid                   {row['valid']}")
    if row["flash_attn_disabled_at_runtime"]:
        print("  ℹ Flash attention disabled by the runner — that axis is inert.")
    if (
        row["blocks_allocated"]
        and row["blocks_reported"]
        and row["blocks_reported"] < row["blocks_allocated"]
    ):
        print(f"  ℹ Stopped after {row['blocks_reported']:.0f} of "
              f"{row['blocks_allocated']:.0f} blocks — -n is a ceiling here,")
        print("    so cutting it saves little beyond a smaller n_ctx.")
    if not row["valid"]:
        print("\n  ⚠ INVALID OUTPUT — do not sweep against this.")
        print(f"    Full log: {row['log_path']}")
        print("\n  ── generated text, first 1200 chars ──")
        print(row["output_head"] or "(nothing on stdout)")
        print("\n  ── generated text, last 600 chars ──")
        print(row["output_tail"] or "(nothing on stdout)")
        print("  ──────────────────────────────────────")
    return row


def _baseline_is_sane():
    """Refuse to burn 40 minutes measuring a workload that does not work."""
    row = run_diffusion_once(label="preflight")
    if row["valid"]:
        print(f"  preflight OK: {row['wall_seconds']:.1f}s, "
              f"{row['forward_passes']} forward passes, valid output")
        return True
    print("\n⛔ Preflight failed: the baseline config produced invalid output.")
    print(f"   Inspect {row['log_path']}, fix LAB['chat_template'] or the")
    print("   workload, then rerun. Sweeping now would rank broken configs.")
    return False


def sweep_reasoning(candidates=None):
    """E6: find a prefill that skips the reasoning channel.

    This model opens a "<|channel>thought" trace and can burn the entire
    token budget there without ever emitting the answer. That shows up as
    invalid output AND as inflated latency, so it must be fixed before any
    speed comparison against the AR model means anything.

    Run inspect_model_template() first to get the real channel names, then
    pass them here. Reports validity and tokens for each candidate.
    """
    print("=== E6: reasoning suppression ===")
    if LAB["mode"] == "cnv":
        print("Mode is 'cnv': the runner applies the GGUF template itself, so")
        print("chat_template and assistant_prefill have no effect. This run")
        print("simply measures whether the shipped path reasons at all.")
        row = run_diffusion_once(label="cnv-baseline")
        print(f"\n  thought channel opened: {row['thought_channel']}")
        print(f"  valid={row['valid']}  tokens={row['output_tokens']}  "
              f"generate={row['generate_seconds']:.1f}s  "
              f"blocks={row['blocks_reported']}")
        print(f"\n  ── generated text, first 800 chars ──\n{row['output_head'][:800]}")
        if row["thought_channel"]:
            print("\n  ⚠ The shipped -cnv path DOES reason. That cost is real")
            print("    and is present in your demo today.")
        elif row["valid"]:
            print("\n  ✅ Shipped path is clean: no reasoning, valid output.")
            print("     The thought channel was an artifact of -p templating.")
        return [row]

    # (chat_template, assistant_prefill) pairs. The template is the variable
    # that actually matters: the GGUF uses <|turn> markers and only emits a
    # thinking channel when a system turn carries <|think|>.
    if candidates is None:
        candidates = [
            ("diffusiongemma", ""),
            ("diffusiongemma", '{"schedule":['),
            # Closing an empty thought, in case one opens anyway.
            ("diffusiongemma", "<|channel>thought\n<channel|>\n"),
            # The wrong template, kept as the control that reproduces the bug.
            ("gemma", ""),
        ]
    candidates = [
        item if isinstance(item, tuple) else (LAB["chat_template"], item)
        for item in candidates
    ]

    original_prefill = LAB["assistant_prefill"]
    original_template = LAB["chat_template"]
    rows = []
    try:
        for index, (template, candidate) in enumerate(candidates):
            LAB["chat_template"] = template
            LAB["assistant_prefill"] = candidate
            label = f"tmpl-{template}-prefill-{index}"
            print(f"\n  {label}: template={template!r} prefill={candidate!r}")
            row = run_diffusion_once(label=label)
            row["prefill"] = candidate
            rows.append(row)
            print(f"    valid={row['valid']}  "
                  f"tokens={row['output_tokens']}  "
                  f"generate={row['generate_seconds']:.1f}s  "
                  f"blocks={row['blocks_reported']}")
            if not row["valid"]:
                print(f"    head: {(row['output_head'] or '')[:160]!r}")
    finally:
        LAB["assistant_prefill"] = original_prefill
        LAB["chat_template"] = original_template

    thinking = [
        row for row in rows
        if "<|channel>thought" in (row.get("output_head") or "")
    ]
    print(f"\n{len(thinking)} of {len(rows)} runs opened a thought channel.")

    valid_rows = [row for row in rows if row["valid"]]
    if valid_rows:
        best = min(valid_rows, key=lambda item: item["generate_seconds"])
        print(f"\n✅ Best valid config: template={best['chat_template']!r} "
              f"prefill={best['prefill']!r} "
              f"({best['generate_seconds']:.1f}s, "
              f"{best['output_tokens']} tokens)")
        print("   Set LAB['chat_template'] / LAB['assistant_prefill'] to it.")
    else:
        print("\n⛔ No candidate produced valid output.")
        print("   Check whether the runner already applies the GGUF template "
              "to -p input; if so, double-templating is the problem and "
              "chat_template should be 'none'.")
    return rows


def sweep_quality(temperatures=(0.8, 0.3, 0.0), step_budgets=(8, 16, 32)):
    """E7: find a configuration that produces VALID output.

    The shipped config degenerates: it hits the eb-max-steps ceiling (8.0 of
    8, versus 6.2 elsewhere) and emits malformed text. Two suspects:

      * temperature 0.8, inherited from Cell 5, is high for structured JSON
      * 8 steps/block is too FEW for the sampler to converge on this content

    Both push against speed, so this measures the correctness frontier
    first. Optimizing a config that cannot produce a valid schedule is
    meaningless, so this must land before sweep_diffusion().
    """
    print("=== E7: quality frontier (temperature x step budget) ===")

    # A whole earlier round of correctness work was invalidated by silently
    # scoring the synthetic prompt with the synthetic scorer. Never again:
    # this experiment is about the demo's real task, so refuse to guess.
    if not WORKLOAD_SOURCE.startswith("Cell 4"):
        print(f"⛔ Workload is {WORKLOAD_SOURCE!r}, not Cell 4.")
        print("   Run Cell 4 first, then re-paste this cell. Results scored")
        print("   against the synthetic case say nothing about the demo.")
        return []

    print(f"Workload:  {WORKLOAD_SOURCE}")
    print("Sweeping steps UPWARD: the sampler is hitting its ceiling.")

    # Prompt shape is a correctness variable too: -cnv flattens the prompt
    # unless the runner supports --multiline-input.
    formats = ["collapse"]
    if CAPS["multiline_input"]:
        formats.append("multiline")
        print("Runner supports --multiline-input, so prompt shape is swept "
              "as well (the flattened prompt is what Cell 5 ships).")
    else:
        print("Runner has no --multiline-input: the prompt must stay "
              "flattened, so prompt shape cannot be tested here.")

    # Each config needs its own process: temperature and eb-max-steps are CLI
    # flags, so a warm session cannot be reused across the grid. ~15s load plus
    # ~10s generation each, and the high-step configs run longer than that.
    run_count = len(formats) * len(temperatures) * len(step_budgets)
    print(f"\n{run_count} configurations, each a fresh process "
          f"(~25s+). Estimated {run_count * 30 // 60}–"
          f"{run_count * 45 // 60} minutes.")

    original_format = LAB["prompt_format"]
    rows = []
    try:
        for prompt_format in formats:
            LAB["prompt_format"] = prompt_format
            for temperature in temperatures:
                for steps in step_budgets:
                    label = f"{prompt_format}-temp{temperature}-steps{steps}"
                    print(f"\n  {label}")
                    row = run_diffusion_once(
                        label=label,
                        temperature=temperature,
                        eb_max_steps=steps,
                    )
                    row["prompt_format"] = prompt_format
                    rows.append(row)
                    print(f"    valid={row['valid']}  "
                          f"thought={row['thought_channel']}  "
                          f"tokens={row['output_tokens']}  "
                          f"blocks={row['blocks_reported']}  "
                          f"steps/block={row['avg_steps_per_block']}  "
                          f"generate={row['generate_seconds']:.1f}s")
                    if not row["valid"]:
                        # Cell 4's evaluator explains WHY, which is far more
                        # useful than another 120 characters of broken JSON.
                        if row.get("status"):
                            print(f"    why:  {row['status']}")
                        print(f"    head: {(row['output_head'] or '')[:120]!r}")
    finally:
        LAB["prompt_format"] = original_format

    # The grid is the deliverable: it shows whether failure tracks temperature,
    # step budget, both, or neither. Nine scattered log lines do not.
    for prompt_format in formats:
        group = [r for r in rows if r.get("prompt_format") == prompt_format]
        if not group:
            continue
        print(f"\n  {prompt_format} — ✅ valid / 💭 thought trace / ❌ invalid")
        print("  temp \\ steps   " + "   ".join(
            f"{steps:>13}" for steps in step_budgets))
        for temperature in temperatures:
            cells = []
            for steps in step_budgets:
                match = next(
                    (r for r in group
                     if r["eb_max_steps"] == steps
                     and abs(r["temperature"] - temperature) < 1e-9),
                    None,
                )
                if match is None:
                    cells.append(f"{'—':>13}")
                    continue
                mark = "✅" if match["valid"] else (
                    "💭" if match["thought_channel"] else "❌")
                cells.append(
                    f"{mark} {match['generate_seconds']:>5.1f}s "
                    f"{match['output_tokens'] or 0:>4}t")
            print(f"  {temperature:<14} " + "   ".join(cells))
        print("                  (generation time, generated tokens)")

    valid_rows = [row for row in rows if row["valid"]]
    print(f"\n{len(valid_rows)} of {len(rows)} configurations produced valid "
          "output.")
    if valid_rows:
        best = min(valid_rows, key=lambda item: item["generate_seconds"])
        print(f"✅ Fastest valid: {best['label']} "
              f"({best['generate_seconds']:.1f}s, "
              f"{best['output_tokens']} tokens)")
        print("   Apply this temperature and step budget to Cell 5, then "
              "run sweep_diffusion() for the remaining speed work.")
    else:
        print("⛔ Nothing valid at any temperature or step budget.")
        # Measured, not guessed: -n 1024 vs 2048 produced byte-identical
        # output, and so did temp 0.8 / 0.3 / 0.0. A deterministic failure
        # at a fixed token position is not a sampling problem, so no runner
        # knob will fix it. Do not send anyone back to -n.
        print("   Runner knobs are exhausted: -n, --temp, eb-max-steps, -fa,")
        print("   -ub and --n-cpu-moe are all measured inert or irrelevant.")
        print("   The failure is deterministic, so the remaining levers are")
        print("   the prompt and the reasoning trace: try sweep_reasoning()")
        print("   to suppress the thought channel and answer directly.")

    by_format = {}
    for row in rows:
        key = row.get("prompt_format", "collapse")
        by_format.setdefault(key, []).append(row)
    if len(by_format) > 1:
        print("\nValid outputs by prompt shape:")
        for key, group in by_format.items():
            good = sum(1 for item in group if item["valid"])
            print(f"  {key:<10} {good}/{len(group)}")

    ceiling_bound = [
        row for row in rows
        if row.get("avg_steps_per_block")
        and row.get("eb_max_steps")
        and row["avg_steps_per_block"] >= row["eb_max_steps"] - 0.1
    ]
    if ceiling_bound:
        print(f"\nℹ {len(ceiling_bound)} runs hit the step ceiling — those "
              "were step-starved, not converged.")
    return rows


def sweep_diffusion():
    """E3: the main sweep. One axis at a time, against a fixed baseline."""
    print("=== E3: diffusion parameter sweep ===")
    print(f"Baseline: -n {LAB['baseline_max_tokens']} "
          f"--diffusion-eb-max-steps {LAB['baseline_eb_max_steps']}")

    print("Preflight...")
    if not _baseline_is_sane():
        return []

    rows = []
    for repeat in range(LAB["repeats"]):
        rows.append(
            run_diffusion_once(label=f"baseline-r{repeat}")
        )

    axes = [
        ("max_tokens", LAB["sweep_max_tokens"], True),
        ("eb_max_steps", LAB["sweep_eb_max_steps"], CAPS["eb_max_steps"]),
        ("block_length", LAB["sweep_block_length"], CAPS["block_length"]),
        ("flash_attn", LAB["sweep_flash_attn"], CAPS["flash_attn"]),
        ("ubatch", LAB["sweep_ubatch"], CAPS["ubatch"]),
        ("n_cpu_moe", LAB["sweep_n_cpu_moe"], CAPS["n_cpu_moe"]),
    ]

    for axis, values, available in axes:
        if not values:
            print(f"  · {axis}: skipped (empty sweep list)")
            continue
        if not available:
            print(f"  · {axis}: SKIPPED — runner does not advertise the flag")
            continue
        for value in values:
            baseline_value = LAB.get(f"baseline_{axis}")
            if value == baseline_value:
                continue
            kwargs = {axis: value}
            if axis == "n_cpu_moe":
                # Pointless unless every layer is nominally on the GPU and
                # only the expert tensors are pushed back to the CPU.
                kwargs["ngl"] = 99
            for repeat in range(LAB["repeats"]):
                label = f"{axis}={value}-r{repeat}"
                print(f"  running {label}")
                rows.append(run_diffusion_once(label=label, **kwargs))

    print(f"Sweep complete: {len(rows)} runs. Call report() to summarize.")
    return rows


def sweep_token_budget():
    """E4: -n sensitivity for BOTH models.

    This is the fairness measurement: diffusion pays for the whole budget,
    AR stops at EOS. Run it before quoting any speed ratio.
    """
    print("=== E4: token budget sensitivity ===")
    rows = []
    for budget in LAB["sweep_max_tokens"]:
        rows.append(
            run_diffusion_once(label=f"budget-diff-{budget}", max_tokens=budget)
        )
    if AR_AVAILABLE:
        for budget in LAB["sweep_max_tokens"]:
            rows.append(run_ar_once(label=f"budget-ar-{budget}", max_tokens=budget))
    else:
        print("  AR model not staged; skipping the AR half of this experiment.")
    return rows


def compare_cold_vs_warm(turns=3):
    """E5: the cost your UI pays by reloading models on every click."""
    print("=== E5: cold vs warm ===")
    cold_total = 0.0
    for index in range(turns):
        row = run_diffusion_once(label=f"cold-turn-{index}")
        cold_total += row["wall_seconds"]

    command = build_diffusion_command(interactive=True)
    started = time.perf_counter()
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )
    warm_turns = []
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    try:
        buffer = ""

        def read_to_prompt(require_generation):
            """Non-blocking drain until the runner shows its `>` prompt."""
            nonlocal buffer
            saw_generation = False
            deadline = time.perf_counter() + LAB["timeout_seconds"]
            while time.perf_counter() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("runner exited during warm test")
                for key, _ in selector.select(timeout=1.0):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        continue
                    if key.data == "stdout":
                        buffer = (
                            buffer + chunk.decode("utf-8", "replace")
                        )[-8192:]
                    elif b"diffusion step:" in chunk:
                        saw_generation = True
                if re.search(r"(?:^|\n)>\s*$", clean(buffer)) and (
                    saw_generation or not require_generation
                ):
                    return
            raise TimeoutError("warm turn timed out")

        read_to_prompt(require_generation=False)
        startup_s = time.perf_counter() - started

        for index in range(turns):
            turn_start = time.perf_counter()
            process.stdin.write(
                (" ".join(PROMPT.split()) + "\n").encode("utf-8")
            )
            process.stdin.flush()
            read_to_prompt(require_generation=True)
            warm_turns.append(time.perf_counter() - turn_start)
            process.stdin.write(b"/clear\n")
            process.stdin.flush()
            read_to_prompt(require_generation=False)
    finally:
        selector.close()
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)

    warm_total = startup_s + sum(warm_turns)
    row = record(
        {
            "experiment": "cold_vs_warm",
            "label": f"{turns}-turns",
            "turns": turns,
            "cold_total_seconds": cold_total,
            "warm_total_seconds": warm_total,
            "warm_startup_seconds": startup_s,
            "warm_turn_seconds": warm_turns,
            "seconds_saved": cold_total - warm_total,
            "reload_overhead_per_turn": (cold_total - warm_total) / max(turns, 1),
        }
    )
    print(f"  cold ({turns} processes): {cold_total:.1f}s")
    print(f"  warm (1 process):         {warm_total:.1f}s "
          f"[{startup_s:.1f}s startup + {len(warm_turns)} turns]")
    print(f"  → reload overhead: {row['reload_overhead_per_turn']:.1f}s per turn")
    return row


# =========================================================
# 8. Reporting
# =========================================================

def _table(rows, columns, title):
    print(f"\n{title}")
    widths = [max(len(str(c)), 12) for c in columns]
    header = "  ".join(str(c).ljust(w) for c, w in zip(columns, widths))
    print(header)
    print("-" * len(header))
    for row in rows:
        cells = []
        for column, width in zip(columns, widths):
            value = row.get(column)
            if isinstance(value, float):
                value = f"{value:.2f}"
            cells.append(str(value if value is not None else "—").ljust(width))
        print("  ".join(cells))


def report(show_charts=True):
    """Roll up every measurement taken so far and rank the levers."""
    diffusion = [
        r for r in LAB_RESULTS
        if r["experiment"] == "diffusion" and not r.get("timed_out")
    ]
    if not diffusion:
        print("No diffusion runs recorded yet. Run sweep_diffusion() first.")
        return

    _table(
        sorted(diffusion, key=lambda r: r["wall_seconds"]),
        [
            "label", "wall_seconds", "load_seconds", "prefill_seconds",
            "generate_seconds", "output_tokens", "forward_passes",
            "seconds_per_forward", "valid",
        ],
        "Diffusion runs, fastest first",
    )

    # Cost model: generation time should be linear in forward passes.
    points = [
        (r["forward_passes"], r["generate_seconds"])
        for r in diffusion
        if r.get("forward_passes") and r.get("generate_seconds")
    ]
    if len(points) >= 3:
        xs = np.array([p[0] for p in points], dtype=float)
        ys = np.array([p[1] for p in points], dtype=float)
        slope, intercept = np.polyfit(xs, ys, 1)
        predicted = slope * xs + intercept
        variance = float(np.sum((ys - ys.mean()) ** 2))
        residual = (
            float(1 - np.sum((ys - predicted) ** 2) / variance)
            if variance > 0
            else float("nan")
        )
        print(
            f"\nCost model: generate_seconds ≈ {slope * 1000:.1f}ms × "
            f"forward_passes + {intercept:.1f}s   (R² = {residual:.3f})"
        )
        print(
            "  A high R² means forward-pass count IS the cost — so the knobs "
            "that reduce it (-n, block length, steps) are the real levers."
        )

    baselines = [r for r in diffusion if r["label"].startswith("baseline")]
    if baselines:
        base = float(np.median([r["wall_seconds"] for r in baselines]))
        print(f"\nBaseline wall time: {base:.1f}s")
        gains = []
        for row in diffusion:
            if row["label"].startswith("baseline") or not row.get("valid"):
                continue
            gains.append(
                {
                    "config": row["label"],
                    "wall_seconds": row["wall_seconds"],
                    "saved_seconds": base - row["wall_seconds"],
                    "speedup": base / row["wall_seconds"]
                    if row["wall_seconds"]
                    else None,
                }
            )
        gains.sort(key=lambda item: item["saved_seconds"], reverse=True)
        _table(
            gains[:15],
            ["config", "wall_seconds", "saved_seconds", "speedup"],
            "Ranked levers (valid outputs only)",
        )
        invalid = [r["label"] for r in diffusion if not r.get("valid")]
        if invalid:
            print(f"\n⚠ Excluded {len(invalid)} runs with invalid output: "
                  f"{', '.join(invalid[:8])}")
            print("  Speed that breaks correctness is not a speedup.")

    ar_rows = [r for r in LAB_RESULTS if r["experiment"] == "ar"]
    if ar_rows:
        _table(
            ar_rows,
            ["label", "max_tokens", "wall_seconds", "load_seconds",
             "prefill_seconds", "generate_seconds", "output_tokens"],
            "AR baseline",
        )
        print(
            "\nCompare output_tokens across AR rows: if it barely moves while "
            "max_tokens quadruples, AR is EOS-bound and the shared -n knob is "
            "charging diffusion for headroom AR never uses."
        )

    warm = [r for r in LAB_RESULTS if r["experiment"] == "cold_vs_warm"]
    for row in warm:
        print(
            f"\nSession reuse saves {row['reload_overhead_per_turn']:.1f}s per "
            f"generation ({row['seconds_saved']:.0f}s over {row['turns']} turns)."
        )

    if LAB_STAGES:
        _table(LAB_STAGES, ["stage", "seconds"], "Setup stage attribution")

    print(f"\nAll measurements: {LAB_JSONL}")

    if show_charts:
        _charts(diffusion)


def _charts(diffusion):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return

    ordered = sorted(diffusion, key=lambda r: r["wall_seconds"])
    labels = [r["label"] for r in ordered]
    load = [r["load_seconds"] for r in ordered]
    prefill = [r["prefill_seconds"] for r in ordered]
    generate = [r["generate_seconds"] for r in ordered]

    fig, axes = plt.subplots(1, 2, figsize=(16, max(4, len(labels) * 0.35)))
    positions = range(len(labels))
    axes[0].barh(positions, load, label="load")
    axes[0].barh(positions, prefill, left=load, label="prefill")
    axes[0].barh(
        positions,
        generate,
        left=[a + b for a, b in zip(load, prefill)],
        label="generate",
    )
    axes[0].set_yticks(list(positions), labels, fontsize=8)
    axes[0].set_xlabel("Seconds")
    axes[0].set_title("Where each run spends its time")
    axes[0].legend()

    points = [
        (r["forward_passes"], r["generate_seconds"])
        for r in diffusion
        if r.get("forward_passes") and r.get("generate_seconds")
    ]
    if points:
        axes[1].scatter([p[0] for p in points], [p[1] for p in points])
        axes[1].set_xlabel("Forward passes (blocks × steps)")
        axes[1].set_ylabel("Generate seconds")
        axes[1].set_title("Is forward-pass count the whole story?")
    plt.tight_layout()
    plt.show()


# =========================================================
# 9. Menu
# =========================================================

print("=" * 62)
print("DIFFUSION OPTIMIZATION LAB")
print("=" * 62)
print(f"GPU:              {GPU_NAME} ({GPU_VRAM_GIB:.1f} GiB)")
print(f"Full offload:     {FULL_OFFLOAD}  (diffusion -ngl {DIFF_NGL})")
if not FULL_OFFLOAD:
    print("  ⚠ Partial offload. Diffusion does ~8x more forward passes than")
    print("    AR, so CPU-resident layers hurt it ~8x more. Try n_cpu_moe.")
print(f"Runner:           {LAB['runner']}")
print(f"Diffusion model:  {os.path.basename(LAB['diff_model'])}")
print(f"AR model:         "
      f"{os.path.basename(LAB['ar_model']) if AR_AVAILABLE else 'NOT STAGED'}")
print(f"Workload:         {WORKLOAD_SOURCE}")
print(f"Prompt:           {PROMPT_BYTES:,} bytes (~{PROMPT_TOKENS_EST:,} tokens)")
print(f"Results:          {LAB_JSONL}")
print("\nRunner capabilities detected from --help:")
for name, available in sorted(CAPS.items()):
    print(f"  {'✅' if available else '❌'} {name}")
missing = [name for name, available in CAPS.items() if not available]
if missing:
    print(f"\n  Sweep axes for missing flags will be SKIPPED, not silently")
    print(f"  substituted: {', '.join(missing)}")
print("\nExperiments (nothing has run yet):")
print("  inspect_model_template()     read chat template + channel tokens")
print("  sweep_reasoning()            E6  does the shipped path reason?")
print("  sweep_quality()              E7  temperature x steps -> VALID output")
print("  probe_storage_throughput()   E1  Drive vs local read speed")
print("  profile_cold_start()         E2  pre-first-token breakdown")
print("  sweep_diffusion()            E3  parameter sweep")
print("  sweep_token_budget()         E4  -n sensitivity, AR vs diffusion")
print("  compare_cold_vs_warm()       E5  per-click reload cost")
print("  report()                     roll-up + ranked levers")
print("=" * 62)
