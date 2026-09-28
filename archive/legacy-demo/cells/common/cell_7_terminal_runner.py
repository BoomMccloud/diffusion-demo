# --- CELL 7: TERMINAL MULTI-RUN BENCHMARK HARNESS ---
#
# Terminal-based benchmark runner comparing Autoregressive (Gemma 4 AR)
# and Diffusion (DiffusionGemma) models across multiple cases and attempts.
#
# Designed for headless / CLI execution (e.g. via `colab exec`), eliminating
# the need for a web browser or Gradio UI.

import os
import sys
import time
import numpy as np

# ---------------------------------------------------------
# Formatting Utilities
# ---------------------------------------------------------
def _format_table(headers, rows, alignments=None):
    """Render an ASCII table with clean column padding and alignments.
    alignments: list of 'left' or 'right' per column.
    """
    if alignments is None:
        alignments = ["left"] + ["right"] * (len(headers) - 1)

    str_rows = [[str(cell) for cell in row] for row in rows]
    col_widths = [len(h) for h in headers]
    for row in str_rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    border_horiz = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

    def _render_row(vals):
        cols = []
        for i, val in enumerate(vals):
            align = alignments[i]
            w = col_widths[i]
            formatted = val.rjust(w) if align == "right" else val.ljust(w)
            cols.append(f" {formatted} ")
        return "|" + "|".join(cols) + "|"

    output_lines = [
        border_horiz,
        _render_row(headers),
        border_horiz,
    ]
    for row in str_rows:
        output_lines.append(_render_row(row))
    output_lines.append(border_horiz)

    return "\n".join(output_lines)


def run_terminal_benchmark(case_count=None, attempts=None):
    """Execute the benchmark across multiple test cases and repeated attempts,
    outputting live metrics directly to the terminal.
    """
    # Auto-load puzzle spec if not already in globals
    if "BENCHMARK_SPEC" not in globals():
        try:
            try:
                import cell_4_schedule_puzzle as _cell4
            except ImportError:
                from cells.common import cell_4_schedule_puzzle as _cell4
            globals()["BENCHMARK_SPEC"] = _cell4.BENCHMARK_SPEC
            globals()["PUZZLE_CASES"] = _cell4.BENCHMARK_SPEC["cases"]
            globals()["PUZZLE_CASE_BY_ID"] = _cell4.BENCHMARK_SPEC["case_by_id"]
        except Exception as _load_err:
            raise RuntimeError(
                f"BENCHMARK_SPEC is missing and could not be loaded: {_load_err}. "
                "Ensure Cell 4 has executed before Cell 7."
            )

    spec = globals()["BENCHMARK_SPEC"]
    globals().setdefault("PUZZLE_CASES", spec["cases"])
    globals().setdefault("PUZZLE_CASE_BY_ID", spec["case_by_id"])

    # Verify prerequisites in execution environment
    for required_name in (
        "BENCHMARK_SPEC",
        "PUZZLE_CASES",
        "PUZZLE_CASE_BY_ID",
        "run_benchmark_suite",
    ):
        if required_name not in globals():
            raise RuntimeError(
                f"'{required_name}' is missing from globals. "
                "Ensure Cells 4 and 5 have executed before running Cell 7."
            )

    spec = globals()["BENCHMARK_SPEC"]
    puzzle_cases = globals()["PUZZLE_CASES"]
    puzzle_name = spec.get("name", "Schedule Puzzle")
    results_dir = globals().get("RESULTS_DIR", "/tmp/benchmark-results")

    max_cases = len(puzzle_cases)
    if case_count is None:
        case_count = int(globals().get("BENCHMARK_CASE_COUNT", os.environ.get("BENCHMARK_CASE_COUNT", 5)))
    if attempts is None:
        attempts = int(globals().get("BENCHMARK_ATTEMPTS", os.environ.get("BENCHMARK_ATTEMPTS", 3)))

    case_count = max(1, min(case_count, max_cases))
    attempts = max(1, attempts)
    total_runs_per_model = case_count * attempts
    print("\n" + "=" * 76)
    print(f"🚀 BENCHMARK SUITE: {puzzle_name}")
    print("=" * 76)
    print(f"  Cases to Evaluate: {case_count} (out of {max_cases} available)")
    print(f"  Attempts per Case: {attempts}")
    print(f"  Total Trials/Model: {total_runs_per_model}")
    if "GPU_VRAM_GIB" in globals():
        print(f"  Hardware:          CUDA GPU ({globals()['GPU_VRAM_GIB']:.1f} GiB VRAM)")
    print("=" * 76 + "\n")

    start_wall_time = time.time()

    # Execute the suite (saves incrementally to JSONL)
    results, markdown_summary, rows, result_path = run_benchmark_suite(
        case_count=case_count,
        attempts=attempts,
    )

    elapsed_wall_time = time.time() - start_wall_time

    # ---------------------------------------------------------
    # Render Terminal Comparison Summary
    # ---------------------------------------------------------
    table_headers = [
        "Model",
        "Attempts",
        "Success Rate",
        "Optimal Rate",
        "Median Latency",
        "Min",
        "Max",
    ]
    table_rows = []

    models_present = sorted(list({r["model"] for r in results}))
    latencies_by_model = {}

    for model_name in models_present:
        model_results = [r for r in results if r["model"] == model_name]
        valid_results = [r for r in model_results if r.get("valid", False)]
        times = [r["response_seconds"] for r in model_results if "response_seconds" in r]
        latencies_by_model[model_name] = float(np.median(times)) if times else 0.0

        optimal_count = sum(
            1
            for r in model_results
            if r.get("valid")
            and r.get("quality_value") is not None
            and r.get("quality_value") == r.get("optimal_quality_value")
        )

        n_trials = len(model_results)
        succ_pct = f"{(len(valid_results) / n_trials):.1%}" if n_trials else "0.0%"
        opt_pct = f"{(optimal_count / n_trials):.1%}" if n_trials else "0.0%"
        med_s = f"{np.median(times):.2f}s" if times else "N/A"
        min_s = f"{np.min(times):.2f}s" if times else "N/A"
        max_s = f"{np.max(times):.2f}s" if times else "N/A"

        table_rows.append([
            model_name,
            n_trials,
            succ_pct,
            opt_pct,
            med_s,
            min_s,
            max_s,
        ])

    print("\n" + "=" * 76)
    print("📊 BENCHMARK RESULTS SUMMARY")
    print("=" * 76)
    print(_format_table(table_headers, table_rows))

    # Speedup calculation
    if "Gemma 4 AR" in latencies_by_model and "DiffusionGemma" in latencies_by_model:
        ar_lat = latencies_by_model["Gemma 4 AR"]
        diff_lat = latencies_by_model["DiffusionGemma"]
        if ar_lat > 0 and diff_lat > 0:
            speedup = ar_lat / diff_lat
            faster_model = "DiffusionGemma" if speedup >= 1.0 else "Gemma 4 AR"
            ratio = speedup if speedup >= 1.0 else (1.0 / speedup)
            print(f"\n⚡ Latency Comparison: {faster_model} is {ratio:.2f}x faster in median response.")

    print(f"\n⏱️  Total Wall-Clock Time: {elapsed_wall_time:.1f}s")
    print(f"📁 Detailed Logs Saved:  {result_path}")
    print("=" * 76 + "\n")

    # Save formatted markdown summary alongside raw results
    md_summary_path = result_path.replace(".jsonl", "_summary.md")
    try:
        with open(md_summary_path, "w", encoding="utf-8") as f:
            f.write(f"# {puzzle_name} Benchmark Summary\n\n")
            f.write(f"- Cases Evaluated: {case_count}\n")
            f.write(f"- Attempts per Case: {attempts}\n")
            f.write(f"- Wall-clock Time: {elapsed_wall_time:.1f}s\n\n")
            f.write(markdown_summary)
        print(f"📄 Markdown Summary Saved: {md_summary_path}\n")
    except Exception as e:
        print(f"Note: could not save markdown summary: {e}")

    return results, table_rows, result_path


# Automatically execute benchmark when cell is run in notebook/interactive mode
if __name__ == "__main__" or ("__file__" not in globals() and globals().get("AUTO_RUN_TERMINAL_BENCHMARK", True)):
    terminal_results, summary_table, summary_file = run_terminal_benchmark()
