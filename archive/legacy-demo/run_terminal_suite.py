#!/usr/bin/env python3
"""Run the complete Diffusion vs AR benchmark pipeline in terminal mode.

Usage (via Colab CLI):
    colab exec -f run_terminal_suite.py

Usage (interactive/local):
    python run_terminal_suite.py [--cases 5] [--attempts 3] [--skip-setup]
"""

import argparse
import os
import sys

# Determine repository root
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

# Platform detection
PLATFORM = os.environ.get("PLATFORM", "nvidia")


def run_cell_file(rel_path, env_globals):
    """Execute a cell file in the shared globals namespace."""
    abs_path = os.path.join(REPO_DIR, rel_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Cell file not found: {abs_path}")
    print(f"\n{'=' * 76}")
    print(f"▶ EXECUTING: {rel_path}")
    print(f"{'=' * 76}")
    with open(abs_path, "r", encoding="utf-8") as f:
        code = compile(f.read(), abs_path, "exec")
        exec(code, env_globals)


def main():
    parser = argparse.ArgumentParser(description="Run Diffusion vs AR Benchmark Suite")
    parser.add_argument(
        "--cases",
        type=int,
        default=int(os.environ.get("BENCHMARK_CASE_COUNT", 5)),
        help="Number of test cases to evaluate (default: 5)",
    )
    parser.add_argument(
        "--attempts",
        type=int,
        default=int(os.environ.get("BENCHMARK_ATTEMPTS", 3)),
        help="Number of attempts per test case (default: 3)",
    )
    parser.add_argument(
        "--skip-setup",
        action="store_true",
        help="Skip runner setup and model staging (Cells 2 & 3) if already warm",
    )
    args, _ = parser.parse_known_args()

    # Pass configuration into execution globals
    env = globals()
    env["BENCHMARK_CASE_COUNT"] = args.cases
    env["BENCHMARK_ATTEMPTS"] = args.attempts
    env["BENCHMARK_MODE"] = "terminal"

    # Define execution sequence
    pipeline = []
    if not args.skip_setup:
        pipeline.extend([
            f"cells/{PLATFORM}/cell_2_runner_setup.py",
            "cells/common/cell_3_model_setup.py",
        ])

    pipeline.extend([
        "cells/common/cell_4_schedule_puzzle.py",
        "cells/common/cell_4b_validation.py",
        f"cells/{PLATFORM}/cell_5_benchmark_engine.py",
        "cells/common/cell_6_ui_adapters.py",
        "cells/common/cell_7_terminal_runner.py",
    ])

    print(f"🚀 Starting Benchmark Pipeline ({len(pipeline)} steps)...")
    print(f"   Configuration: {args.cases} cases x {args.attempts} attempts")

    for rel_path in pipeline:
        run_cell_file(rel_path, env)

    print("\n✅ All benchmark steps completed successfully.")


if __name__ == "__main__":
    main()
