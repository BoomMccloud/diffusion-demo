"""Summarize a finished WebArena study: overall and per-site success, step use,
judge-graded tasks, and model-call latency and tokens.

Run inside the agent container: python analyze_webarena.py /results/<study dir>
"""

import glob
import json
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

study = Path(sys.argv[1])
results = pd.read_csv(sorted(study.glob("result_df_trial_*.csv"))[-1])
cfg = {c["task_id"]: c for c in json.load(open(
    glob.glob("/opt/venv/lib/python3.*/site-packages/webarena/test.raw.json")[0]))}

results["task_id"] = results["env.task_name"].str.split(".").str[1].astype(int)
results["sites"] = results.task_id.map(lambda i: " ".join(sorted(cfg[i]["sites"])))
results["eval"] = results.task_id.map(lambda i: " ".join(cfg[i]["eval"]["eval_types"]))
results["judged"] = results.task_id.map(
    lambda i: "fuzzy_match" in (cfg[i]["eval"].get("reference_answers") or {}))
results["unachievable"] = results.task_id.map(
    lambda i: (cfg[i]["eval"].get("reference_answers") or {}).get("fuzzy_match") == "N/A")
results["ok"] = results.cum_reward.fillna(0) > 0
results["capped"] = results.n_steps >= results["env.max_steps"]


def line(name, df):
    n, k = len(df), int(df.ok.sum())
    se = math.sqrt(k / n * (1 - k / n) / n) if n else 0
    return f"| {name} | {n} | {k} | {100 * k / n:.1f}% | {100 * se:.1f} | {df.n_steps.mean():.1f} | {100 * df.capped.mean():.0f}% |"


print("| Group | Tasks | Passed | Success | SE (pts) | Mean steps | Hit 30-step cap |")
print("|---|---|---|---|---|---|---|")
print(line("All", results))
for site, df in sorted(results.groupby("sites"), key=lambda x: -len(x[1])):
    print(line(site, df))
print(line("Judge-graded (fuzzy_match)", results[results.judged]))
print(line("  of which unachievable (N/A)", results[results.unachievable]))
print(line("Not judge-graded", results[~results.judged]))
print("errors:", int(results.err_msg.notna().sum()))

# Model calls across every pass of the study.
rows = []
for f in glob.glob(str(study / "**" / "*.jsonl"), recursive=True) + glob.glob(
        str(study.parent / "llm_calls" / "*.jsonl")):
    rows += [json.loads(l) for l in open(f)]
lat = [r["latency_s"] for r in rows]
comp = [r["usage"]["completion_tokens"] for r in rows]
prompt = [r["usage"]["prompt_tokens"] for r in rows]
reason = [r["usage"].get("reasoning_tokens") or 0 for r in rows]
q = lambda xs, p: sorted(xs)[int(p * (len(xs) - 1))]
print(f"\nmodel calls in logs: {len(rows)}")
print(f"latency s: median {st.median(lat):.2f}, p90 {q(lat, .9):.2f}, max {max(lat):.1f}")
print(f"prompt tokens: median {st.median(prompt):.0f}, p90 {q(prompt, .9)}")
print(f"completion tokens: median {st.median(comp):.0f}, p90 {q(comp, .9)}, of which reasoning median {st.median(reason):.0f}")
print(f"tool-call replies: {sum(bool(r.get('tool_calls')) for r in rows) / len(rows):.1%}")
