"""Run the original task checks locally, redirecting only the gold-file path."""

import argparse
import json
import os
from pathlib import Path
import sys

import pytest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tests", type=Path, help="Original task tests directory")
    parser.add_argument("output", type=Path, help="Workbook to grade")
    args = parser.parse_args()
    tests = args.tests.resolve()
    os.environ["WB_BENCH_OUTPUT_PATH"] = str(args.output.resolve())
    os.environ["WB_BENCH_GOLD_PATH"] = str(tests / "gold/gold_answer.json")
    os.environ["WB_BENCH_FIXTURES_DIR"] = str(tests / "gold/fixtures")
    sys.path.insert(0, str(tests / "grading"))
    import eval_core

    def load_gold():
        with open(os.environ["WB_BENCH_GOLD_PATH"], encoding="utf8") as source:
            return json.load(source)

    eval_core.load_gold = load_gold
    return pytest.main([str(tests / "grading"), "-p", "no:cacheprovider", "-v", "--tb=short"])


if __name__ == "__main__":
    raise SystemExit(main())
