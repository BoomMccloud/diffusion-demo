"""Compare complete OpenRouter Office batches to the matched saved baselines."""
import argparse
import csv
import json
import math
from pathlib import Path
from statistics import mean

ROUTES = ("deepseek-flash-office", "glm-flash-office")
BASELINE = (Path(__file__).resolve().parent.parent
            / "qwen36-flash-office-2026-11-19/rerun/comparison/comparison.csv")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    args = parser.parse_args()
    with BASELINE.open(newline="") as file:
        baseline = list(csv.DictReader(file))
    names = {row["task"] for row in baseline}
    if len(baseline) != 50 or len(names) != 50:
        parser.error("expected 50 distinct baseline tasks")
    scores = {route: {} for route in ROUTES}
    for line in args.ledger.read_text().splitlines():
        row = json.loads(line)
        if row["phase"] != "batch" or row["status"] != "completed":
            continue
        model_scores = scores[row["route"]]
        task, score = row["task"], float(row["score"])
        if task not in names or task in model_scores or not (math.isfinite(score) and 0 <= score <= 1):
            parser.error(f"invalid or duplicate scored task: {row['route']} {task}")
        model_scores[task] = score
    if any(set(model_scores) != names for model_scores in scores.values()):
        parser.error("batch score counts: " + ", ".join(f"{route} {len(scores[route])}/50"
                                                        for route in ROUTES))
    rows = [
        dict(row, **{route: scores[route][row["task"]] for route in ROUTES})
        for row in baseline
    ]
    columns = ("clover_rule_score", "qwen_rule_score", *ROUTES)
    print(json.dumps({
        "task_count": len(rows),
        "deterministic_means": {column: mean(float(row[column]) for row in rows) for column in columns},
        "tasks": rows,
    }, indent=2))


if __name__ == "__main__":
    main()
