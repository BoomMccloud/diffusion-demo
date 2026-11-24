"""Batch-wide constraints: can a model satisfy rules that no single record shows?

python -m bench.tabdlm.constraints {generate,score,all} --run NAME [--probe]

Each request asks for 30 person records as one JSON array, under one constraint or all five:
- quota: each of the 10 occupations exactly 3 times
- sorted: salary never decreases down the list
- sum: the ages sum to exactly 1200 (mean 40)
- balance: exactly 15 male and 15 female
- forward: the first record's salary equals the sum of the last three records' ages

An AR model has to plan these one token at a time. A diffusion model can in principle revise
earlier records. Every check is code. The hypotheses are in README.md, fixed before the run.
"""
import argparse, asyncio, dataclasses, datetime, json, subprocess, time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from bench.synthdata import arms
from . import data, tasks
from .longrange import bootstrap

RESULTS = Path(__file__).resolve().parents[1] / "results"
N = 30
TYPES = ("quota", "sorted", "sum", "balance", "forward")
CONDITIONS = TYPES + ("all",)

RULES = {
    "quota": "Each of the 10 occupations appears exactly 3 times.",
    "sorted": "The records are sorted by salary from lowest to highest. Equal salaries are allowed.",
    "sum": f"The ages of all {N} records sum to exactly 1200, so the mean age is exactly 40.",
    "balance": f"Exactly {N // 2} records are male and exactly {N // 2} are female.",
    "forward": "The salary of the first record equals the sum of the ages of the last three records.",
}


@dataclass(frozen=True)
class Config:
    arms: tuple = ("dllm", "qwen")
    # One matched temperature: this is a precision task, and the dLLM degrades above 0.8.
    temp: float = 0.6
    n: int = 30
    max_tokens: int = 3000
    concurrency: int = 8


PROMPT = f"""You generate synthetic person records for a dataset.

Fields:
- age: integer, 21 to 70
- salary: integer, annual salary in thousands of USD (75 means $75,000), 40 to 250
- sex: "male" or "female"
- birth_state: lowercase US state
- occupation: one of {", ".join(data.bio_values("occupation"))}

Example records, to show the format only:
{{examples}}

Generate exactly {N} new records as one JSON array. The whole list must satisfy {{these}}:
{{rules}}

Check the whole list against {{these_short}} before you answer. Output only the JSON array of {N} objects, with no other text."""

EXAMPLES = [{"age": 37, "salary": 116, "sex": "female", "birth_state": "georgia", "occupation": "creative content professional"},
            {"age": 28, "salary": 122, "sex": "male", "birth_state": "california", "occupation": "software developer"},
            {"age": 52, "salary": 88, "sex": "male", "birth_state": "ohio", "occupation": "education professional"}]


def prompt(cond):
    types = TYPES if cond == "all" else (cond,)
    rules = "\n".join(f"{i + 1}. {RULES[t]}" for i, t in enumerate(types))
    many = len(types) > 1
    return PROMPT.format(examples="\n".join(json.dumps(e) for e in EXAMPLES),
                         these="all of these rules" if many else "this rule", rules=rules,
                         these_short="every rule" if many else "the rule")


# ---------- scoring

def valid(r):
    return (tasks._is_int(r.get("age")) and tasks._is_int(r.get("salary")) and r.get("sex") in ("male", "female")
            and isinstance(r.get("birth_state"), str) and r.get("occupation") in data.bio_values("occupation"))


def distances(recs):
    """How far a list is from each rule, 0 meaning satisfied. Needs a list of valid records."""
    occ = Counter(r["occupation"] for r in recs)
    ages = [int(r["age"]) for r in recs]
    sal = [int(r["salary"]) for r in recs]
    males = sum(r["sex"] == "male" for r in recs)
    return {"quota": sum(abs(occ.get(o, 0) - 3) for o in data.bio_values("occupation")),
            "sorted": sum(a > b for a, b in zip(sal, sal[1:])),
            "sum": abs(sum(ages) - 1200),
            "balance": abs(males - N // 2),
            "forward": abs(sal[0] - sum(ages[-3:])) if len(recs) >= 4 else 999}


def score_request(row):
    """Pass needs exactly N valid records and every rule of the condition at distance 0."""
    recs = row["records"] or []
    out = {"returned": len(recs), "all_valid": bool(recs) and all(map(valid, recs))}
    out["shape_ok"] = out["all_valid"] and len(recs) == N
    out["dist"] = distances(recs) if out["all_valid"] and len(recs) >= 4 else None
    types = TYPES if row["condition"] == "all" else (row["condition"],)
    out["pass_by_type"] = {t: out["shape_ok"] and out["dist"][t] == 0 for t in types}
    out["pass"] = all(out["pass_by_type"].values())
    return out


# ---------- generate

def key(r):
    return (r["condition"], r["arm"], r["idx"])


async def generate(cfg, out):
    done = {key(r) for r in map(json.loads, open(out)) if "error" not in r and r.get("finish_reason") != "error"} \
        if out.exists() else set()
    todo = [(c, a, i) for c in CONDITIONS for a in cfg.arms for i in range(cfg.n) if (c, a, i) not in done]
    print(f"generate: {len(todo)} to run, {len(done)} already done", flush=True)

    async def one(client, job):
        cond, arm, idx = job
        a = arms.ARMS[arm]
        row = {"condition": cond, "arm": arm, "model": a["model"], "temp": cfg.temp, "idx": idx}
        t0 = time.time()
        try:
            r = await client.chat.completions.create(
                model=a["model"], temperature=cfg.temp, max_tokens=cfg.max_tokens,
                seed=CONDITIONS.index(cond) * 1_000 + idx, extra_body=a["extra"],
                messages=[{"role": "user", "content": prompt(cond)}])
            row.update(raw=r.choices[0].message.content or "", finish_reason=r.choices[0].finish_reason,
                       prompt_tokens=r.usage.prompt_tokens if r.usage else None,
                       completion_tokens=r.usage.completion_tokens if r.usage else None, served_model=r.model)
        except Exception as e:
            row.update(raw="", error=repr(e)[:300])
        row["latency_s"] = round(time.time() - t0, 3)
        recs, raw_ok, reason = tasks.parse("gen10", row["raw"]) if "error" not in row else (None, False, "error")
        row.update(records=recs, raw_json_ok=raw_ok, parse_reason=reason or "ok")
        return row

    async def arm_run(arm, js):
        client = arms.client(arm)
        sem = asyncio.Semaphore(cfg.concurrency)
        n = 0

        async def go(job):
            nonlocal n
            async with sem:
                row = await one(client, job)
            with out.open("a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
            if n % 30 == 0:
                print(f"  {arm}: {n}/{len(js)}", flush=True)

        for c in dict.fromkeys(j[0] for j in js):
            await asyncio.gather(*(go(j) for j in js if j[0] == c))

    by_arm = defaultdict(list)
    for j in todo:
        by_arm[j[1]].append(j)
    await asyncio.gather(*(arm_run(a, js) for a, js in by_arm.items()))


def _median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else None


def score(cfg, run_dir):
    rows = {}
    for r in map(json.loads, open(run_dir / "generations.jsonl")):
        rows[key(r)] = r
    cells = defaultdict(list)
    for r in rows.values():
        cells[(r["condition"], r["arm"])].append((r, score_request(r)))
    m = {"cells": {}, "tests": {}}
    for (cond, arm), items in sorted(cells.items(), key=lambda kv: (CONDITIONS.index(kv[0][0]), kv[0][1])):
        ss = [s for _, s in items]
        types = TYPES if cond == "all" else (cond,)
        m["cells"][f"{cond}/{arm}"] = {
            "requests": len(ss), "pass_pct": round(100 * sum(s["pass"] for s in ss) / len(ss), 1),
            "shape_ok_pct": round(100 * sum(s["shape_ok"] for s in ss) / len(ss), 1),
            "type_pass_pct": {t: round(100 * sum(s["pass_by_type"][t] for s in ss) / len(ss), 1) for t in types},
            "median_distance": {t: _median([s["dist"][t] for s in ss if s["dist"]]) for t in types},
            "median_returned": _median([s["returned"] for s in ss]),
            # Shortcuts like all ages 40 or ages 21 to 50 in order pass `sum` but aren't realistic data.
            "median_distinct_ages": _median([len({x.get("age") for x in r["records"]}) for r, _ in items if r["records"]]),
            "median_latency_s": _median([r["latency_s"] for r, _ in items]),
            "median_completion_tokens": _median([r.get("completion_tokens") or 0 for r, _ in items])}
    # Pass-rate gap per condition, dLLM minus Qwen, bootstrap over requests.
    for cond in CONDITIONS:
        g = {arm: [s["pass"] for _, s in cells.get((cond, arm), [])] for arm in cfg.arms}
        if all(g.values()):
            gap = lambda s: sum(s["dllm"]) / len(s["dllm"]) - sum(s["qwen"]) / len(s["qwen"])
            m["tests"][cond] = {"dllm_minus_qwen_pass": round(gap(g), 3), "ci": bootstrap(g, gap)}
    (run_dir / "metrics.json").write_text(json.dumps(m, indent=1))
    lines = ["# Batch-wide constraints", "", f"{N} records per request; temperature {cfg.temp} for both arms; thinking off.", "",
             "| condition | arm | requests | pass % | exactly 30 valid % | pass % by rule | median distance by rule | distinct ages | median latency s | median tokens |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for k, c in m["cells"].items():
        cond, arm = k.split("/")
        lines.append(f"| {cond} | {arm} | {c['requests']} | {c['pass_pct']} | {c['shape_ok_pct']} | {c['type_pass_pct']} | "
                     f"{c['median_distance']} | {c['median_distinct_ages']} | {c['median_latency_s']} | {c['median_completion_tokens']} |")
    lines += ["", "## dLLM minus Qwen pass rate (95% bootstrap interval)", ""]
    lines += [f"- `{k}`: {v['dllm_minus_qwen_pass']:+.3f} ({v['ci'][0]:+.3f} to {v['ci'][1]:+.3f})" for k, v in m["tests"].items()]
    (run_dir / "summary.md").write_text("\n".join(lines) + "\n")
    print((run_dir / "summary.md").read_text())


def main():
    p = argparse.ArgumentParser(prog="python -m bench.tabdlm.constraints")
    p.add_argument("stage", choices=["generate", "score", "all"])
    p.add_argument("--run", required=True, help="output goes to bench/results/tabdlm-constraints-<run>/")
    p.add_argument("--probe", action="store_true", help="two requests per cell, to check the pipeline")
    a = p.parse_args()
    cfg = dataclasses.replace(Config(), n=2) if a.probe else Config()
    run_dir = RESULTS / f"tabdlm-constraints-{a.run}"
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = run_dir / "manifest.json"
    if a.stage != "score" and not manifest.exists():
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        manifest.write_text(json.dumps({
            "started": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "git_commit": commit,
            "config": dataclasses.asdict(cfg), "arms": arms.fingerprint(), "data": data.sources()}, indent=1, default=list))
    if a.stage in ("generate", "all"):
        asyncio.run(generate(cfg, run_dir / "generations.jsonl"))
    if a.stage in ("score", "all"):
        score(cfg, run_dir)


if __name__ == "__main__":
    main()
