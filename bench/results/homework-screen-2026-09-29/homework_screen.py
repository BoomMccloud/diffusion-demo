#!/usr/bin/env python3
"""Homework-grading screen for the Nemotron runner.

Problems are GSM8K test questions (MIT license, openai/gsm8k). A weak model,
Llama 3.2 1B through OpenRouter, writes the student work, so the mistakes are
real ones. The grader gets a worksheet of problems, the answer key, and the
student's work, and must mark every question and total the score.

  students  write the student cases (run with nemotron_runner.py openrouter)
  build     turn student rows into worksheet cases for the grader
  score     score grader rows, print a per-arm summary, write scored.jsonl
"""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import random
import re
import statistics

SEED = 20260929
POOL = 300
SIZES = {10: 6, 25: 6, 50: 6}  # questions per worksheet: number of worksheets
MAX_NEW_TOKENS = 512

STUDENT_PROMPT = """Solve this math homework problem. Show your work in at most four short lines, then end with a line of the form "Answer: <number>".

{question}"""

GRADER_PROMPT = """You are grading a student's math homework. For each question you are given the problem, the answer key, and the student's work.

A question is CORRECT if the student's final answer equals the answer key. The final answer is the one the student marks as the answer, or, if none is marked, the last number the student writes. Ignore units, dollar signs, commas, and trailing zeros after a decimal point. Otherwise it is INCORRECT.

Write one line per question, in order, as Q<number>: CORRECT or Q<number>: INCORRECT. Then write a final line SCORE: <number correct>/<number of questions>. Write nothing else.

Example output for a three-question worksheet:
Q1: CORRECT
Q2: INCORRECT
Q3: CORRECT
SCORE: 2/3

{questions}"""


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def number(text):
    text = text.replace(",", "").replace("$", "").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(match.group()) if match else None


def cmd_students(args):
    import pyarrow.parquet as pq

    rows = pq.read_table(args.gsm8k).to_pylist()
    picked = random.Random(SEED).sample(range(len(rows)), POOL)
    with open(args.out, "w") as handle:
        for index in sorted(picked):
            row = rows[index]
            handle.write(json.dumps({
                "case_id": f"gsm8k-test-{index}", "prompt": STUDENT_PROMPT.format(question=row["question"]),
                "question": row["question"], "key": row["answer"].split("####")[-1].strip(), "max_new_tokens": 300,
            }) + "\n")


def cmd_build(args):
    students = {case["case_id"]: case for case in read_jsonl(args.student_cases)}
    pool = []
    for row in read_jsonl(args.student_rows):
        work = row["final_output"] or ""
        match = re.findall(r"(?:Answer:|answer is:?|\\boxed\{)\s*([^\n}]+)", work)
        numbers = re.findall(r"-?\d[\d,]*(?:\.\d+)?", work)
        given = number(match[-1]) if match else number(numbers[-1]) if numbers else None  # else the last number written
        if row["error"] or given is None:
            continue  # keep only work with a clear final answer, so the truth is unambiguous
        case = students[row["case_id"]]
        pool.append({"id": row["case_id"], "question": case["question"], "key": case["key"],
                     "work": row["final_output"].strip(), "correct": given == number(case["key"])})
    rng = random.Random(SEED)
    print(f"pool {len(pool)}, student correct {sum(p['correct'] for p in pool)}")
    with open(args.out, "w") as handle:
        for size, count in SIZES.items():
            for i in range(count):
                items = rng.sample(pool, size)
                blocks = [f"Q{n}. Problem: {item['question']}\nAnswer key: {item['key']}\nStudent work:\n{item['work']}"
                          for n, item in enumerate(items, 1)]
                handle.write(json.dumps({
                    "case_id": f"sheet{size}-{i}", "size": size,
                    "prompt": GRADER_PROMPT.format(questions="\n\n".join(blocks)),
                    "max_new_tokens": MAX_NEW_TOKENS,
                    "truth": [item["correct"] for item in items], "items": [item["id"] for item in items],
                }) + "\n")


def grade(truth, output):
    verdicts = {int(n): v == "CORRECT" for n, v in re.findall(r"Q(\d+)\s*:\s*(CORRECT|INCORRECT)", output)}
    right = sum(verdicts.get(n) == t for n, t in enumerate(truth, 1))
    score = re.search(r"SCORE:\s*(\d+)\s*/\s*(\d+)", output)
    score = (int(score.group(1)), int(score.group(2))) if score else None
    return {
        "items_right": right, "items_answered": sum(1 for n in range(1, len(truth) + 1) if n in verdicts),
        "extra_lines": sum(1 for n in verdicts if not 1 <= n <= len(truth)),
        "sheet_exact": right == len(truth) and len(verdicts) == len(truth),
        "score_line": score, "score_true": score == (sum(truth), len(truth)),
        "score_self_consistent": score is not None and score[0] == sum(verdicts.values()),
    }


def cmd_score(args):
    cases = {case["case_id"]: case for case in read_jsonl(args.cases)}
    by_arm = defaultdict(list)
    with open(args.scored, "w") as handle:
        for row in read_jsonl(args.rows):
            case = cases[row["case_id"]]
            result = grade(case["truth"], "" if row["error"] else row["final_output"])
            scored = {**{k: row[k] for k in ("arm", "case_id", "output_tokens", "nfe", "elapsed_seconds", "stop_reason", "final_output")},
                      "size": case["size"], **result}
            handle.write(json.dumps(scored) + "\n")
            by_arm[row["arm"]].append(scored)
    for arm, rows in by_arm.items():
        sizes = defaultdict(list)
        for row in rows:
            sizes[row["size"]].append(row)
        print(json.dumps({
            "arm": arm, "sheets": len(rows),
            "by_size": {size: {
                "items_right": f"{sum(r['items_right'] for r in v)}/{size * len(v)}",
                "sheets_exact": f"{sum(r['sheet_exact'] for r in v)}/{len(v)}",
                "score_true": f"{sum(r['score_true'] for r in v)}/{len(v)}",
                "median_s": round(statistics.median(r["elapsed_seconds"] for r in v), 2),
                "median_tokens": statistics.median(r["output_tokens"] for r in v),
            } for size, v in sorted(sizes.items())},
            "hit_cap": sum(r["stop_reason"] == "max_new_tokens" for r in rows),
        }))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("students")
    p.add_argument("--gsm8k", required=True, help="openai/gsm8k main test parquet")
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_students)
    p = sub.add_parser("build")
    p.add_argument("--student-cases", required=True)
    p.add_argument("--student-rows", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_build)
    p = sub.add_parser("score")
    p.add_argument("rows")
    p.add_argument("--cases", required=True)
    p.add_argument("--scored", required=True)
    p.set_defaults(func=cmd_score)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
