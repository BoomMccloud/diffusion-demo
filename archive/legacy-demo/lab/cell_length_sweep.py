# --- LAB: OUTPUT-LENGTH CROSSOVER SWEEP (TASK-005) ---
#
# Question: is there an output length at which DiffusionGemma overtakes the AR
# model on wall time, and what happens to validity across that range?
#
# Method: scale the schedule *horizon* rather than inventing a new puzzle. The
# model must emit every slot, so horizon sets output length while the task
# itself stays confined to one active day. Extra days are transcription load.
#
# This file has two halves:
#   1. measure_corpus()  - runs anywhere, no GPU. Measures the actual prompt and
#                          output sizes each horizon produces.
#   2. predict_crossover() - applies the cost model from
#                          docs/diffusion_optimization_findings.md to those
#                          sizes. Predictions ONLY; replace the constants with
#                          measured values once the sweep runs on Colab.

import importlib.util
import json
import os
import sys
import time

HORIZONS = (1, 2, 3, 5, 8, 10)

# Rough JSON tokenization ratio. Good enough to rank horizons; replace with a
# real tokenizer count when running on Colab where one is available.
CHARS_PER_TOKEN = 3.6

# ---------------------------------------------------------
# Cost model constants, from docs/diffusion_optimization_findings.md
# ---------------------------------------------------------
# Diffusion: cost is quantized to the canvas. 9235ms over 4 blocks (section 2),
# plus ~1.2s prefill (section 1). A block costs the same whether it holds 10
# useful tokens or 256.
DIFFUSION_CANVAS_TOKENS = 256
DIFFUSION_SECONDS_PER_BLOCK = 9.235 / 4
DIFFUSION_PREFILL_SECONDS = 1.2

# AR: cost is proportional to tokens emitted.
#
# WARNING - THIS IS A PLACEHOLDER, NOT A MEASUREMENT.
# The findings doc contains NO AR throughput figure. 110 tok/s is *diffusion's*
# own telemetry (findings line 50), reused here only so the model has a number.
# Because diffusion amortizes to ~9.0 ms/token, setting AR to the same rate
# makes the two curves parallel BY CONSTRUCTION. Do not read the head-to-head
# table as evidence; read the sensitivity table, which is valid for any rate.
# Replace this with a measured value before quoting any crossover.
AR_TOKENS_PER_SECOND = 110.0
AR_PREFILL_SECONDS = 0.6


def load_puzzle(horizon_days):
    """Import cell 4 fresh at a given horizon."""
    os.environ["SCHEDULE_HORIZON_DAYS"] = str(horizon_days)
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "cells", "common", "cell_4_schedule_puzzle.py",
    )
    name = f"_puzzle_h{horizon_days}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def measure_corpus(horizon_days):
    started = time.time()
    module = load_puzzle(horizon_days)
    build_seconds = time.time() - started

    spec = module.BENCHMARK_SPEC
    prompt_chars = []
    output_chars = []
    for case in spec["cases"]:
        prompt_chars.append(len(spec["build_prompt"](case)))
        solution = module.reference_solution(case)
        output_chars.append(
            len(json.dumps({"schedule": solution}, separators=(",", ":")))
        )

    mean = lambda values: sum(values) / len(values)
    return {
        "horizon_days": horizon_days,
        "slots": module.SLOT_COUNT,
        "prompt_tokens": mean(prompt_chars) / CHARS_PER_TOKEN,
        "output_tokens": mean(output_chars) / CHARS_PER_TOKEN,
        "token_budget": spec["default_output_tokens"],
        "build_seconds": build_seconds,
        "solution_count": mean(
            [case["solution_count"] for case in spec["cases"]]
        ),
    }


def diffusion_seconds(output_tokens):
    blocks = max(1, -(-int(output_tokens) // DIFFUSION_CANVAS_TOKENS))
    return DIFFUSION_PREFILL_SECONDS + blocks * DIFFUSION_SECONDS_PER_BLOCK


def ar_seconds(output_tokens):
    return AR_PREFILL_SECONDS + output_tokens / AR_TOKENS_PER_SECOND


def predict_crossover():
    """Smallest output length at which the diffusion model is predicted to win."""
    for tokens in range(16, 40001, 16):
        if diffusion_seconds(tokens) < ar_seconds(tokens):
            return tokens
    return None


def main():
    rows = [measure_corpus(days) for days in HORIZONS]

    print()
    print("=" * 88)
    print("MEASURED: corpus size by horizon  (50 cases each, task fixed to one active day)")
    print("=" * 88)
    header = (
        f"{'days':>5} {'slots':>6} {'prompt tok':>11} {'output tok':>11} "
        f"{'budget':>7} {'layouts':>8} {'build s':>8}"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{row['horizon_days']:>5} {row['slots']:>6} "
            f"{row['prompt_tokens']:>11.0f} {row['output_tokens']:>11.0f} "
            f"{row['token_budget']:>7} {row['solution_count']:>8.1f} "
            f"{row['build_seconds']:>8.1f}"
        )

    print()
    print("=" * 88)
    print("ILLUSTRATIVE ONLY: AR rate is a PLACEHOLDER (= diffusion's own 110 tok/s).")
    print("These columns are parallel by construction. Use the sensitivity table below.")
    print("=" * 88)
    header = (
        f"{'days':>5} {'output tok':>11} {'blocks':>7} {'AR s':>8} "
        f"{'diff s':>8} {'winner':>9} {'margin':>9}"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        tokens = row["output_tokens"]
        ar = ar_seconds(tokens)
        diff = diffusion_seconds(tokens)
        blocks = max(1, -(-int(tokens) // DIFFUSION_CANVAS_TOKENS))
        winner = "AR" if ar < diff else "diffusion"
        print(
            f"{row['horizon_days']:>5} {tokens:>11.0f} {blocks:>7} "
            f"{ar:>8.1f} {diff:>8.1f} {winner:>9} "
            f"{abs(ar - diff) / min(ar, diff):>8.1f}x"
        )

    # Context budget. The runner derives n_ctx from -n plus the canvas
    # (findings section 2: -n 1024 -> n_ctx 3072, -n 2048 -> n_ctx 4096), so a
    # long horizon needs -n raised or the case will not fit at all.
    print()
    print("=" * 88)
    print("CONTEXT BUDGET: what the diffusion runner must be launched with")
    print("=" * 88)
    header = (
        f"{'days':>5} {'prompt':>8} {'output':>8} {'total':>8} "
        f"{'needs n_ctx':>12} {'fits -n 2048?':>14}"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        total = row["prompt_tokens"] + row["output_tokens"]
        fits = "yes" if total <= 4096 else "NO - raise -n"
        print(
            f"{row['horizon_days']:>5} {row['prompt_tokens']:>8.0f} "
            f"{row['output_tokens']:>8.0f} {total:>8.0f} "
            f"{total:>12.0f} {fits:>14}"
        )

    # Sensitivity. AR throughput is the one unmeasured constant, and it decides
    # the whole question, so report the answer as a function of it.
    print()
    print("=" * 88)
    print("SENSITIVITY: crossover vs AR throughput (the one number worth measuring)")
    print("=" * 88)
    tokens_per_day = rows[0]["output_tokens"] / rows[0]["horizon_days"]
    global AR_TOKENS_PER_SECOND
    baseline = AR_TOKENS_PER_SECOND
    header = f"{'AR tok/s':>9} {'AR ms/tok':>10} {'crossover tok':>14} {'horizon days':>13}"
    print(header)
    print("-" * len(header))
    for rate in (50, 70, 90, 110, 150, 200, 300):
        AR_TOKENS_PER_SECOND = float(rate)
        point = predict_crossover()
        if point is None:
            print(
                f"{rate:>9} {1000 / rate:>10.1f} {'never':>14} {'-':>13}"
            )
        else:
            print(
                f"{rate:>9} {1000 / rate:>10.1f} {point:>14} "
                f"{point / tokens_per_day:>13.1f}"
            )
    AR_TOKENS_PER_SECOND = baseline
    print(
        f"\nDiffusion's amortized rate is "
        f"{DIFFUSION_SECONDS_PER_BLOCK / DIFFUSION_CANVAS_TOKENS * 1000:.1f} ms/token. "
        "AR beats it at any rate above that, at every length."
    )

    crossover = predict_crossover()
    print()
    if crossover is None:
        print(
            "Predicted crossover: NONE below 40k tokens at "
            f"AR={AR_TOKENS_PER_SECOND:.0f} tok/s."
        )
    else:
        days = crossover / (rows[0]["output_tokens"] / rows[0]["horizon_days"])
        print(
            f"Predicted crossover: ~{crossover} output tokens "
            f"(~{days:.1f} day horizon) at AR={AR_TOKENS_PER_SECOND:.0f} tok/s."
        )
    print(
        "Sensitivity: the crossover is set entirely by AR tok/s vs diffusion's "
        f"{DIFFUSION_SECONDS_PER_BLOCK / DIFFUSION_CANVAS_TOKENS * 1000:.1f} ms/token "
        "amortized over a full canvas."
    )
    print()
    print("Next: run this on Colab with both runtimes to replace the predicted")
    print("half with measured wall times and validity rates (TASK-005).")


if __name__ == "__main__":
    main()
