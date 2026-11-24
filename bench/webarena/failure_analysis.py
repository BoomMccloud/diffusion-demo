"""Classify WebArena failures by how each failed episode ended.

Run inside the agent container:
    python failure_analysis.py /results/<study dir> [out.jsonl]

Writes one JSON row per task (all 812) and prints category counts.
"""

import glob
import gzip
import json
import pickle
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

study = Path(sys.argv[1])
out_path = sys.argv[2] if len(sys.argv) > 2 else None
results = pd.read_csv(sorted(study.glob("result_df_trial_*.csv"))[-1])
cfg = {c["task_id"]: c for c in json.load(open(
    glob.glob("/opt/venv/lib/python3.*/site-packages/webarena/test.raw.json")[0]))}
SITE_PORTS = ("localhost:", "127.0.0.1")


def clean(s):
    return re.sub(r"\s+", " ", str(s).strip().lower().strip("\"'. "))


def load_steps(exp_dir):
    steps = []
    for f in sorted(Path(exp_dir).glob("step_*.pkl.gz"), key=lambda p: int(p.stem.split("_")[1].split(".")[0])):
        try:
            with gzip.open(f) as fh:
                steps.append(pickle.load(fh))
        except Exception:
            pass
    return steps


def call_name(action):
    m = re.match(r"\s*(\w+)\(", action or "")
    return m.group(1) if m else None


def call_text(action):
    m = re.search(r"\((?:text|reason)?=?\s*(['\"])(.*)\1\s*\)\s*$", action or "", re.S)
    return m.group(2) if m else ""


rows = []
for _, r in results.iterrows():
    tid = int(r["env.task_name"].split(".")[1])
    c = cfg[tid]
    ev = c["eval"]
    ref = ev.get("reference_answers") or {}
    steps = load_steps(r.exp_dir)
    actions = [s.action for s in steps if getattr(s, "action", None)]
    errors = [s.obs.get("last_action_error") for s in steps if getattr(s, "obs", None)]
    urls = [s.obs.get("url", "") for s in steps if getattr(s, "obs", None)]
    last = actions[-1] if actions else None
    name = call_name(last)
    answer = call_text(last) if name in ("send_msg_to_user", "report_infeasible") else ""
    longest_repeat = run = 1
    for a, b in zip(actions, actions[1:]):
        run = run + 1 if a == b else 1
        longest_repeat = max(longest_repeat, run)
    row = {
        "task": tid,
        "sites": " ".join(sorted(c["sites"])),
        "eval": " ".join(ev["eval_types"]),
        "intent": c["intent"],
        "ok": bool((r.cum_reward or 0) > 0),
        "n_steps": int(r.n_steps),
        "capped": int(r.n_steps) >= int(r["env.max_steps"]),
        "last_action": name,
        "answer": answer[:500],
        "reference": ref,
        "unachievable": ref.get("fuzzy_match") == "N/A",
        "action_errors": sum(bool(e) for e in errors),
        "longest_repeat": longest_repeat,
        "left_sites": any(u and not any(p in u for p in SITE_PORTS) and not u.startswith("about:") for u in urls),
    }
    # Why a wrong answer was wrong, for answer-graded tasks.
    if not row["ok"] and name == "send_msg_to_user" and ref:
        a = clean(answer)
        if "exact_match" in ref:
            row["answer_check"] = "format" if clean(ref["exact_match"]) in a else "wrong"
        elif "must_include" in ref:
            hits = sum(clean(x) in a for x in ref["must_include"])
            row["answer_check"] = "partial" if 0 < hits < len(ref["must_include"]) else ("all_present" if hits else "wrong")
        elif "fuzzy_match" in ref:
            row["answer_check"] = "judged_wrong"
    rows.append(row)

df = pd.DataFrame(rows)
if out_path:
    df.to_json(out_path, orient="records", lines=True)


def category(x):
    if x.ok:
        return "passed"
    if x.left_sites:
        return "left the WebArena sites"
    if x.capped:
        return "hit 30-step cap"
    if x.last_action == "report_infeasible":
        return "gave up (said infeasible)" if not x.unachievable else "infeasible, reason judged wrong"
    if x.last_action == "send_msg_to_user":
        if "string_match" not in x.eval:
            return "answered, but required page state or URL not reached"
        return {
            "format": "answer right, wording failed exact match",
            "partial": "answer incomplete (some required items missing)",
            "all_present": "answer had all items, still failed",
            "judged_wrong": "free-text answer judged wrong",
        }.get(x.get("answer_check"), "wrong answer")
    return "ended early, no answer (parse or action failure)"


df["category"] = df.apply(category, axis=1)
fail = df[~df.ok]
print(f"failed: {len(fail)} of {len(df)}\n")
print(fail.category.value_counts().to_string())
print("\nby site (failure category share):")
print(pd.crosstab(fail.sites, fail.category).to_string())
print("\ncapped tasks: median action errors", fail[fail.capped].action_errors.median(),
      "| share with a 3+ repeated action run", round((fail[fail.capped].longest_repeat >= 3).mean(), 2))
print("non-capped failures: median steps", fail[~fail.capped].n_steps.median())
print("passed: median steps", df[df.ok].n_steps.median())
