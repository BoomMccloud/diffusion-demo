#!/usr/bin/env python3
"""BFCL live function-calling screen for the Nemotron runner.

Needs ``pip install bfcl-eval==2026.3.23`` (Apache 2.0). Prompts and scoring come
from BFCL's own prompting-mode system prompt, decoder, and AST checker.

  build   write cases.jsonl for bench/nemotron_runner.py
  score   score runner rows, print a per-arm summary, write scored.jsonl
"""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import random
import statistics

from bfcl_eval.constants.enums import Language
from bfcl_eval.eval_checker.ast_eval.ast_checker import ast_checker
from bfcl_eval.model_handler.utils import default_decode_ast_prompting, system_prompt_pre_processing_chat_model
import bfcl_eval

DATA = Path(bfcl_eval.__file__).parent / "data"
# Real user-contributed queries. live_multiple is sampled to keep the run short.
CATEGORIES = {"live_simple": None, "live_multiple": 100, "live_parallel": None, "live_parallel_multiple": None}
SEED = 20260928
MAX_NEW_TOKENS = 512
FORMAT_LINE = "You SHOULD NOT include any other text in the response."
# Optional worked example. BFCL's prompt only gives a placeholder template, and the
# function list is JSON, so small models tend to answer in JSON.
EXAMPLE = (
    'For example, given functions get_weather(city, unit) and get_time(city), the request '
    '"What is the weather in Paris in celsius, and the time in Tokyo?" is answered exactly as:\n'
    '[get_weather(city="Paris", unit="celsius"), get_time(city="Tokyo")]'
)
# The checker only uses the name to decide dot-to-underscore renaming; this entry disables it.
CHECKER_MODEL = "mistralai_Ministral-8B-Instruct-2410"


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def entries():
    for category, sample in CATEGORIES.items():
        rows = read_jsonl(DATA / f"BFCL_v4_{category}.json")
        answers = {row["id"]: row["ground_truth"] for row in read_jsonl(DATA / "possible_answer" / f"BFCL_v4_{category}.json")}
        if sample:
            rows = sorted(random.Random(SEED).sample(rows, sample), key=lambda row: rows.index(row))
        for row in rows:
            yield category, row, answers[row["id"]]


def cmd_build(args):
    with open(args.out, "w") as handle:
        for category, row, _ in entries():
            messages = system_prompt_pre_processing_chat_model(row["question"][0], row["function"], row["id"])
            assert [m["role"] for m in messages] == ["system", "user"], row["id"]
            if args.example:
                assert FORMAT_LINE in messages[0]["content"], row["id"]
                messages[0]["content"] = messages[0]["content"].replace(FORMAT_LINE, FORMAT_LINE + "\n\n" + EXAMPLE, 1)
            handle.write(json.dumps({
                "case_id": row["id"], "category": category,
                "system": messages[0]["content"], "prompt": messages[1]["content"],
                "max_new_tokens": MAX_NEW_TOKENS,
            }) + "\n")


def decode_json_calls(output):
    """Lenient decoder: the 3B model often writes JSON objects instead of Python calls."""
    text = output.strip().strip("`").removeprefix("json").strip()
    calls = json.loads(text)
    calls = calls if isinstance(calls, list) else [calls]
    decoded = []
    for call in calls:
        call = dict(call)
        name = call.pop("name", None) or call.pop("function", None)
        args = call.pop("arguments", None) or call.pop("parameters", None) or call
        if isinstance(args, str):
            args = json.loads(args)
        decoded.append({name: args})
    return decoded


def check(category, functions, answer, output, lenient=False):
    try:
        decoded = default_decode_ast_prompting(output)
    except Exception as exc:
        if not lenient:
            return False, "decode", str(exc)[:200]
        try:
            decoded = decode_json_calls(output)
        except Exception:
            return False, "decode", str(exc)[:200]
    if not decoded or not all(isinstance(call, dict) for call in decoded):
        return False, "decode", "not a list of calls"
    result = ast_checker(functions, decoded, answer, Language.PYTHON, category, CHECKER_MODEL)
    return result["valid"], result.get("error_type"), None if result["valid"] else str(result.get("error"))[:300]


def cmd_score(args):
    lookup = {row["id"]: (category, row["function"], answer) for category, row, answer in entries()}
    by_arm = defaultdict(list)
    with open(args.scored, "w") as handle:
        for row in read_jsonl(args.rows):
            category, functions, answer = lookup[row["case_id"]]
            valid, error_type, detail = (False, "runner_error", None) if row["error"] else check(category, functions, answer, row["final_output"])
            lenient = False if row["error"] else check(category, functions, answer, row["final_output"], lenient=True)[0]
            scored = {**{k: row[k] for k in ("arm", "case_id", "output_tokens", "nfe", "elapsed_seconds", "stop_reason", "final_output")},
                      "category": category, "valid": valid, "valid_lenient": lenient, "error_type": error_type, "detail": detail}
            handle.write(json.dumps(scored) + "\n")
            by_arm[row["arm"]].append(scored)
    for arm, rows in by_arm.items():
        cats = defaultdict(list)
        for row in rows:
            cats[row["category"]].append(row["valid"])
        summary = {
            "arm": arm, "n": len(rows), "valid": sum(r["valid"] for r in rows),
            "valid_lenient": sum(r["valid_lenient"] for r in rows),
            "by_category": {c: f"{sum(v)}/{len(v)}" for c, v in cats.items()},
            "median_s": round(statistics.median(r["elapsed_seconds"] for r in rows), 3),
            "total_s": round(sum(r["elapsed_seconds"] for r in rows), 1),
            "median_output_tokens": statistics.median(r["output_tokens"] for r in rows),
            "median_nfe": statistics.median(r["nfe"] for r in rows if r["nfe"] is not None),
            "decode_failures": sum(r["error_type"] == "decode" for r in rows),
            "hit_cap": sum(r["stop_reason"] == "max_new_tokens" for r in rows),
        }
        print(json.dumps(summary))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("build")
    p.add_argument("--out", required=True)
    p.add_argument("--example", action="store_true", help="add one worked Python-syntax example to the system prompt")
    p.set_defaults(func=cmd_build)
    p = sub.add_parser("score")
    p.add_argument("rows")
    p.add_argument("--scored", required=True)
    p.set_defaults(func=cmd_score)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
