# --- BENCH: MINIMAL AR vs DIFFUSION COST CONSTANTS (TASK-005) ---
#
# Purpose: measure the two constants every extrapolation in this repo needs,
# for each model:
#
#     generation_seconds  ~=  fixed_overhead  +  ms_per_token * tokens_emitted
#
# `docs/diffusion_optimization_findings.md` §8 currently has NO measured AR
# throughput, so its crossover analysis plugs in diffusion's own 110 tok/s as a
# placeholder. That one missing number decides the whole AR-vs-diffusion latency
# question. This file exists to replace it with a measurement.
#
# Deliberately standalone: no BENCHMARK_SPEC, no puzzle, no Cells 4-7. The
# prompt is a trivial fixed-length filler task so that output length is the only
# thing varying and prompt cost falls out of the slope.
#
# ---------------------------------------------------------------------------
# RUNNING THIS ON COLAB
#
# Requires Cells 2 and 3 to have run in the SAME runtime (runner built, GGUFs
# present). It does NOT need Cells 4-7.
#
# Preferred - in a notebook cell, no subprocess, reuses a loaded AR model:
#
#     bench = load_micro_bench()          # see load_micro_bench() at the bottom
#     bench.AR_MODEL_PATH = AR_MODEL_PATH
#     bench.DIFF_MODEL_PATH = DIFF_MODEL_PATH
#     bench.RUNNER_PATH = RUNNER_LOCAL_PATH
#     rows, load = bench.bench_ar(model=globals().get("_AR_RUNTIME"))
#     rows += bench.bench_diffusion()
#     bench.report(rows, load)
#
# Or as a subprocess, exporting Cell 3's paths first so the defaults below are
# not used:
#
#     import os
#     os.environ["AR_MODEL_PATH"] = AR_MODEL_PATH
#     os.environ["DIFF_MODEL_PATH"] = DIFF_MODEL_PATH
#     os.environ["RUNNER_LOCAL_PATH"] = RUNNER_LOCAL_PATH
#     !python bench/micro_bench.py
#
# WARNING about the subprocess form: it loads its own copy of the AR model. If
# Cell 5's warm runtime is already holding both models in VRAM, that is a second
# ~15 GiB resident. Either run it in a fresh runtime with only Cells 2 and 3, or
# use the in-notebook form above and pass the model you already have.
#
# Model loading is excluded from the fit on both sides: the AR model is loaded
# once and reused, and diffusion is timed by the runner's own `total time:`
# telemetry rather than process wall clock. Process wall time is reported too,
# so the load asymmetry stays visible.

import json
import os
import re
import subprocess
import sys
import time

LOCAL_MODEL_DIR = os.environ.get("LOCAL_MODEL_DIR", "/content/gguf_models")
AR_MODEL_PATH = os.environ.get(
    "AR_MODEL_PATH",
    os.path.join(LOCAL_MODEL_DIR, "gemma-4-26B-A4B-it-UD-Q4_K_M.gguf"),
)
DIFF_MODEL_PATH = os.environ.get(
    "DIFF_MODEL_PATH",
    os.path.join(LOCAL_MODEL_DIR, "diffusiongemma-26B-A4B-it-Q4_K_M.gguf"),
)
RUNNER_PATH = os.environ.get(
    "RUNNER_LOCAL_PATH",
    "/content/llama-diffusion-cli" if os.path.isdir("/content")
    else "/tmp/llama-diffusion-cli",
)

# Requested output lengths. Kept small and few - the point is a slope, not
# coverage. Diffusion quantizes to a 256-token canvas, so these straddle 1, 2
# and 4 blocks, which is where its step function shows up.
LENGTHS = [int(v) for v in os.environ.get("BENCH_LENGTHS", "64,128,256,512,1024").split(",")]
REPEATS = int(os.environ.get("BENCH_REPEATS", "2"))
SEED = 20260814
TEMPERATURE = 0.0
GPU_LAYERS = 99
OUT_PATH = os.environ.get("BENCH_OUT", "bench/micro_bench_results.json")


def filler_prompt(target_tokens):
    """A task with a controllable, near-deterministic output length and no
    reasoning. Roughly 4 tokens per emitted item."""
    count = max(4, target_tokens // 4)
    return (
        f"Output a JSON array of the integers from 1 to {count}, in order, "
        "with no other text. Example format: [1,2,3]"
    )


# ---------------------------------------------------------
# AR side
# ---------------------------------------------------------

def bench_ar(model=None):
    """Measure the AR cost curve.

    Pass `model` to reuse a Llama instance the notebook already holds, which
    avoids a second multi-GiB copy in VRAM. Load time is excluded from the fit
    either way.
    """
    if model is not None:
        load_seconds = 0.0
        print("Reusing the AR model already loaded in this process")
    else:
        from llama_cpp import Llama

        print(f"Loading AR model: {AR_MODEL_PATH}")
        started = time.perf_counter()
        model = Llama(
            model_path=AR_MODEL_PATH,
            n_ctx=8192,
            n_batch=1024,
            n_gpu_layers=GPU_LAYERS,
            seed=SEED,
            verbose=False,
        )
        load_seconds = time.perf_counter() - started
        print(f"  loaded in {load_seconds:.2f}s")

    rows = []
    for length in LENGTHS:
        for repeat in range(REPEATS):
            started = time.perf_counter()
            response = model.create_chat_completion(
                messages=[
                    {"role": "system", "content": "Return only the requested JSON."},
                    {"role": "user", "content": filler_prompt(length)},
                ],
                max_tokens=length,
                temperature=TEMPERATURE,
            )
            elapsed = time.perf_counter() - started
            emitted = response.get("usage", {}).get("completion_tokens")
            if not emitted:
                text = response["choices"][0]["message"]["content"] or ""
                emitted = max(1, len(text) // 4)
            rows.append(
                {
                    "model": "ar",
                    "requested": length,
                    "repeat": repeat,
                    "tokens": int(emitted),
                    "generation_seconds": elapsed,
                    "wall_seconds": elapsed,
                }
            )
            print(
                f"  AR  n={length:<5} rep={repeat}  "
                f"{emitted:>5} tok in {elapsed:>6.2f}s  "
                f"({emitted / elapsed:>6.1f} tok/s)"
            )
    return rows, load_seconds


# ---------------------------------------------------------
# Diffusion side
# ---------------------------------------------------------

THROUGHPUT_RE = re.compile(r"throughput:\s*([\d.]+)\s*tok/s\s*\((\d+)\s*tok in\s*([\d.]+)\s*ms\)")
TOTAL_RE = re.compile(r"total time:\s*([\d.]+)\s*ms.*?\((\d+)\s*steps over\s*(\d+)\s*blocks")


def bench_diffusion():
    rows = []
    for length in LENGTHS:
        for repeat in range(REPEATS):
            cmd = [
                RUNNER_PATH,
                "-m", DIFF_MODEL_PATH,
                "-ngl", str(GPU_LAYERS),
                "-cnv",
                "-n", str(length),
                "--seed", str(SEED + repeat),
                "--diffusion-kv-cache", "on",
            ]
            prompt = " ".join(filler_prompt(length).split())
            started = time.perf_counter()
            done = subprocess.run(
                cmd,
                input=(prompt + "\n").encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=600,
            )
            wall = time.perf_counter() - started
            text = done.stdout.decode("utf-8", errors="replace")

            throughput = THROUGHPUT_RE.search(text)
            total = TOTAL_RE.search(text)
            if not throughput:
                print(f"  DIFF n={length:<5} rep={repeat}  NO TELEMETRY (rc={done.returncode})")
                continue
            tokens = int(throughput.group(2))
            generation = float(throughput.group(3)) / 1000.0
            rows.append(
                {
                    "model": "diffusion",
                    "requested": length,
                    "repeat": repeat,
                    "tokens": tokens,
                    "generation_seconds": generation,
                    "wall_seconds": wall,
                    "steps": int(total.group(2)) if total else None,
                    "blocks": int(total.group(3)) if total else None,
                }
            )
            print(
                f"  DIFF n={length:<5} rep={repeat}  "
                f"{tokens:>5} tok in {generation:>6.2f}s  "
                f"({tokens / generation:>6.1f} tok/s)  "
                f"blocks={total.group(3) if total else '?'}  "
                f"wall={wall:.1f}s"
            )
    return rows


# ---------------------------------------------------------
# Fit and report
# ---------------------------------------------------------

def least_squares(points):
    """Ordinary least squares on (tokens, seconds). Returns intercept, slope."""
    n = len(points)
    if n < 2:
        return None, None
    mean_x = sum(x for x, _ in points) / n
    mean_y = sum(y for _, y in points) / n
    denominator = sum((x - mean_x) ** 2 for x, _ in points)
    if denominator == 0:
        return None, None
    slope = sum((x - mean_x) * (y - mean_y) for x, y in points) / denominator
    return mean_y - slope * mean_x, slope


def report(rows, ar_load):
    print()
    print("=" * 72)
    print("FITTED COST CONSTANTS   generation_s = overhead + ms_per_token * tokens")
    print("=" * 72)
    fits = {}
    for model in ("ar", "diffusion"):
        points = [
            (row["tokens"], row["generation_seconds"])
            for row in rows if row["model"] == model
        ]
        intercept, slope = least_squares(points)
        if slope is None:
            print(f"{model:>10}: insufficient data")
            continue
        fits[model] = {
            "overhead_seconds": intercept,
            "ms_per_token": slope * 1000.0,
            "tokens_per_second": (1.0 / slope) if slope > 0 else None,
            "samples": len(points),
        }
        print(
            f"{model:>10}: overhead {intercept:>6.2f}s   "
            f"{slope * 1000.0:>6.2f} ms/tok   "
            f"{(1.0 / slope) if slope > 0 else float('nan'):>7.1f} tok/s   "
            f"(n={len(points)})"
        )

    if "ar" in fits and "diffusion" in fits:
        ar_ms = fits["ar"]["ms_per_token"]
        diff_ms = fits["diffusion"]["ms_per_token"]
        print()
        print(f"AR marginal cost is {diff_ms / ar_ms:.2f}x diffusion's per token.")
        if ar_ms < diff_ms:
            print(
                "=> AR is cheaper per token. Longer outputs will NOT produce a "
                "diffusion win; the curves diverge in AR's favour."
            )
        else:
            crossover = (
                (fits["ar"]["overhead_seconds"] - fits["diffusion"]["overhead_seconds"])
                / ((ar_ms - diff_ms) / 1000.0)
            )
            print(
                f"=> Diffusion is cheaper per token. Predicted crossover at "
                f"~{crossover:.0f} emitted tokens."
            )
        print()
        print("Replace AR_TOKENS_PER_SECOND in lab/cell_length_sweep.py with "
              f"{fits['ar']['tokens_per_second']:.1f} and re-run it.")

    payload = {
        "ar_load_seconds": ar_load,
        "lengths": LENGTHS,
        "repeats": REPEATS,
        "fits": fits,
        "rows": rows,
    }
    os.makedirs(os.path.dirname(OUT_PATH) or ".", exist_ok=True)
    with open(OUT_PATH, "w") as handle:
        json.dump(payload, handle, indent=2)
    print(f"\nRaw measurements written to {OUT_PATH}")


def selftest():
    """Offline check of the parsing and fitting, using the real telemetry lines
    quoted in docs/diffusion_optimization_findings.md section 2. Needs no GPU
    and no models - run this before spending Colab time."""
    sample = (
        "total time: 9235.59ms, time per step: 369.42ms "
        "(25 steps over 4 blocks, entropy-bound)\n"
        "throughput: 110.9 tok/s (1024 tok in 9235.59ms), in-step parallel "
        "693 tok/s (256-tok canvas x 6.2 steps/block)"
    )
    throughput = THROUGHPUT_RE.search(sample)
    total = TOTAL_RE.search(sample)
    assert throughput, "throughput telemetry regex does not match the runner"
    assert total, "total-time telemetry regex does not match the runner"
    assert (throughput.group(2), throughput.group(3)) == ("1024", "9235.59")
    assert (total.group(2), total.group(3)) == ("25", "4")

    intercept, slope = least_squares(
        [(n, 2.0 + 0.009 * n) for n in (64, 128, 256, 512, 1024)]
    )
    assert abs(intercept - 2.0) < 1e-6, intercept
    assert abs(slope - 0.009) < 1e-9, slope

    assert least_squares([]) == (None, None)
    assert least_squares([(5, 1.0)]) == (None, None)
    assert least_squares([(5, 1.0), (5, 2.0)]) == (None, None)

    for length in LENGTHS:
        assert "JSON array" in filler_prompt(length)

    print("selftest OK - telemetry parsers and fit verified against real log lines")
    print(f"  a 9.0 ms/token slope reads back as {1 / slope:.1f} tok/s")


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which == "selftest":
        selftest()
        return
    rows, ar_load = [], None
    if which in ("both", "ar"):
        ar_rows, ar_load = bench_ar()
        rows.extend(ar_rows)
    if which in ("both", "diffusion"):
        rows.extend(bench_diffusion())
    report(rows, ar_load)


def load_micro_bench(path=None):
    """Import this file as a module from a Colab cell.

    Returns the module so its constants can be overridden before running:
        bench = load_micro_bench()
        bench.AR_MODEL_PATH = AR_MODEL_PATH
    """
    import importlib.util

    path = path or os.path.abspath(__file__)
    spec = importlib.util.spec_from_file_location("micro_bench", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["micro_bench"] = module
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    main()
