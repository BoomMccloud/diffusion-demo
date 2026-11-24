"""Long-range consistency: does a model keep records consistent as a batch grows?

python -m bench.tabdlm.longrange {generate,score,all} --run NAME [--scale F]

Each request asks for B person records (B = 10, 30 or 50) as one JSON array. Each record has
attributes and a biography that must state them, and two year fields that must agree with age
by arithmetic. Order is `fields` (biography last in each object) or `text` (biography first, so
the attributes must repeat facts written earlier). Across the batch, no two records may share a
(college, occupation) pair, so a late record must not repeat an early one.

Every check is code. There is no judge. Hypotheses are fixed in README.md before the run.
"""
import argparse, asyncio, dataclasses, datetime, json, random, re, subprocess, time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from bench.synthdata import arms
from . import data, tasks

RESULTS = Path(__file__).resolve().parents[1] / "results"
YEAR = 2026
BATCHES = (10, 30, 50)
ORDERS = ("fields", "text")
ATTRS = ("age", "birth_year", "salary", "sex", "birth_state", "college", "degree", "graduation_year", "occupation")
TEXT_CHECKS = ("age", "birth_year", "salary", "pronoun", "birth_state", "college", "degree",
               "graduation_year", "occupation")
FIELD_CHECKS = ("birth_year_math", "graduation_math")
CHECKS = TEXT_CHECKS + FIELD_CHECKS + ("unique_pair",)


@dataclass(frozen=True)
class Config:
    arms: tuple = ("dllm", "qwen")
    temps: tuple = (("dllm", 0.6), ("qwen", 1.0))
    # About 550 to 600 records per arm per cell.
    requests: tuple = ((10, 55), (30, 20), (50, 12))
    orders: tuple = ORDERS
    concurrency: int = 8

    def n(self, batch):
        return dict(self.requests)[batch]

    def max_tokens(self, batch):
        return 300 * batch + 500


# ---------- prompt

SCHEMA = f"""Fields:
- biography: 3 to 6 sentences of natural prose. It must state the exact age, the birth year, the exact salary in dollars, the birth state, the college, the degree, the graduation year and the occupation, using the exact field values for state, college, degree and occupation. Refer to the person with pronouns that match the sex. Write each biography in your own words, not from a template.
- age: integer, 21 to 70
- birth_year: integer, {YEAR} minus age (one less is fine if the birthday hasn't come yet)
- salary: integer, annual salary in thousands of USD (75 means $75,000)
- sex: "male" or "female"
- birth_state: lowercase US state
- college: lowercase college name
- degree: one of {", ".join(data.bio_values("degree"))}
- graduation_year: integer, at least birth_year + 18 and no later than {YEAR}
- occupation: one of {", ".join(data.bio_values("occupation"))}"""

PROMPT = """You generate synthetic person records for a dataset. Each record is a set of attributes and a biography that describes them.

{schema}

Every field must agree with the biography and with the other fields. Within one answer, no two records may have the same college and occupation pair. Make the records new and realistic. Do not copy the examples.

Put the fields of each object in this order: {order}.

Examples:
{examples}

Generate {batch} new records. Output only a JSON array of {batch} objects, with no other text."""

FEWSHOT = [
    ({"age": 37, "birth_year": 1989, "salary": 116, "sex": "female", "birth_state": "georgia",
      "college": "houston community college", "degree": "bachelor", "graduation_year": 2011,
      "occupation": "creative content professional"},
     "At 37, she has spent most of her working life as a creative content professional, writing campaigns "
     "for regional brands. Born in georgia in 1989, she earned a bachelor degree at houston community college "
     "in 2011. Her work now pays $116,000 a year."),
    ({"age": 28, "birth_year": 1998, "salary": 122, "sex": "male", "birth_state": "california",
      "college": "arizona state university", "degree": "bachelor", "graduation_year": 2020,
      "occupation": "software developer"},
     "He is a 28-year-old software developer who builds payment services for a retailer. Born in california "
     "in 1998, he finished a bachelor degree at arizona state university in 2020. He earns $122,000 a year "
     "and still codes side projects on weekends."),
    ({"age": 31, "birth_year": 1995, "salary": 125, "sex": "male", "birth_state": "washington",
      "college": "ohio state university", "degree": "bachelor", "graduation_year": 2017,
      "occupation": "creative content professional"},
     "Originally from washington, where he was born in 1995, he moved east and took a bachelor degree at "
     "ohio state university in 2017. He is 31 now and works as a creative content professional, "
     "producing video for nonprofits. His salary is $125,000."),
]


def example(attrs, bio, order):
    return {"biography": bio, **attrs} if order == "text" else {**attrs, "biography": bio}


def prompt(batch, order):
    keys = ("biography",) + ATTRS if order == "text" else ATTRS + ("biography",)
    ex = json.dumps([example(a, b, order) for a, b in FEWSHOT], ensure_ascii=False, indent=1)
    return PROMPT.format(schema=SCHEMA, order=", ".join(keys), examples=ex, batch=batch)


# ---------- checks

def schema(r):
    bad = tasks.bio_schema(r)
    if bad:
        return bad
    for k in ("birth_year", "graduation_year"):
        if not tasks._is_int(r.get(k)) or not 1900 <= r[k] <= YEAR:
            return k
    return None


def _year_in(text, y):
    return bool(re.search(rf"\b{int(y)}\b", text))


def checks(r):
    base = tasks.bio_checks(r)
    bio = r["biography"]
    base["occupation"] = tasks._norm(r["occupation"]) in tasks._norm(bio)  # exact name, as the prompt asks
    base.update(birth_year=_year_in(bio, r["birth_year"]), graduation_year=_year_in(bio, r["graduation_year"]),
                birth_year_math=YEAR - r["age"] - 1 <= r["birth_year"] <= YEAR - r["age"],
                graduation_math=r["birth_year"] + 18 <= r["graduation_year"] <= YEAR)
    return base


def pair(r):
    return (tasks._norm(r["college"]), tasks._norm(r["occupation"]))


def score_request(row):
    """One entry per position asked for. Missing and schema-invalid records fail every check."""
    recs = row["records"] or []
    seen, out = set(), []
    for i in range(row["batch"]):
        rec = recs[i] if i < len(recs) else None
        if rec is None:
            out.append({"pos": i, "status": "missing"})
            continue
        bad = schema(rec)
        if bad:
            out.append({"pos": i, "status": f"schema:{bad}"})
            continue
        c = checks(rec)
        c["unique_pair"] = pair(rec) not in seen
        seen.add(pair(rec))
        out.append({"pos": i, "status": "ok" if all(c.values()) else "inconsistent", "checks": c})
    return out


# ---------- generate

def jobs(cfg):
    return [(b, o, arm, i) for b, _ in cfg.requests for o in cfg.orders for arm in cfg.arms for i in range(cfg.n(b))]


def key(r):
    return (r["batch"], r["order"], r["arm"], r["idx"])


async def generate(cfg, out):
    # A request that raised, or that the provider ended with finish_reason "error", is retried. The
    # score stage reads the last row per key, so the retry replaces it.
    done = {key(r) for r in map(json.loads, open(out)) if "error" not in r and r.get("finish_reason") != "error"} \
        if out.exists() else set()
    todo = [j for j in jobs(cfg) if j not in done]
    print(f"generate: {len(todo)} to run, {len(done)} already done", flush=True)

    async def one(client, job):
        batch, order, arm, idx = job
        a = arms.ARMS[arm]
        row = {"batch": batch, "order": order, "arm": arm, "model": a["model"], "temp": dict(cfg.temps)[arm], "idx": idx}
        t0 = time.time()
        try:
            r = await client.chat.completions.create(
                model=a["model"], temperature=row["temp"], max_tokens=cfg.max_tokens(batch),
                seed=batch * 10_000 + ORDERS.index(order) * 1_000 + idx, extra_body=a["extra"],
                messages=[{"role": "user", "content": prompt(batch, order)}])
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
            if n % 10 == 0:
                print(f"  {arm}: {n}/{len(js)}", flush=True)

        for c in dict.fromkeys(j[:2] for j in js):
            await asyncio.gather(*(go(j) for j in js if j[:2] == c))

    by_arm = defaultdict(list)
    for j in todo:
        by_arm[j[2]].append(j)
    await asyncio.gather(*(arm_run(a, js) for a, js in by_arm.items()))


# ---------- score

def _rate(entries):
    return sum(e["status"] != "ok" for e in entries) / len(entries) if entries else float("nan")


def bootstrap(groups, stat, reps=2000, seed=0):
    """95% interval of stat over request-level resamples. groups maps a name to its list of requests."""
    rng = random.Random(seed)
    vals = []
    for _ in range(reps):
        vals.append(stat({k: [rng.choice(v) for _ in v] for k, v in groups.items()}))
    vals.sort()
    return round(vals[int(0.025 * reps)], 3), round(vals[int(0.975 * reps)], 3)


def late_minus_early(reqs, batch, returned_only=False):
    """Failure rate in the last 10 positions minus the first 10. With returned_only, records the model
    didn't return are left out, so the drift is in consistency alone, not in stopping short."""
    keep = lambda e: not (returned_only and e["status"] == "missing")
    early = [e for r in reqs for e in r if e["pos"] < 10 and keep(e)]
    late = [e for r in reqs for e in r if e["pos"] >= batch - 10 and keep(e)]
    return _rate(late) - _rate(early)


def score(cfg, run_dir):
    rows = {}
    for r in map(json.loads, open(run_dir / "generations.jsonl")):
        rows[key(r)] = r
    by_cell = defaultdict(list)
    meta = defaultdict(list)
    for r in rows.values():
        by_cell[(r["batch"], r["order"], r["arm"])].append(score_request(r))
        meta[(r["batch"], r["order"], r["arm"])].append(r)
    m = {"cells": {}, "tests": {}}
    for (b, o, arm), reqs in sorted(by_cell.items()):
        flat = [e for r in reqs for e in r]
        fails = Counter()
        for e in flat:
            if e["status"] == "ok":
                continue
            if e["status"] == "inconsistent":
                fails.update(k for k, v in e["checks"].items() if not v)
            else:
                fails[e["status"]] += 1
        buckets = {f"{lo + 1}-{lo + 10}": round(100 * _rate([e for e in flat if lo <= e["pos"] < lo + 10]), 1)
                   for lo in range(0, b, 10)}
        rs = meta[(b, o, arm)]
        m["cells"][f"{b}/{o}/{arm}"] = {
            "requests": len(reqs), "records_asked": len(flat),
            "parse_ok": sum(r["records"] is not None for r in rs), "truncated": sum(r.get("finish_reason") == "length" for r in rs),
            "errors": sum("error" in r for r in rs),
            "fail_pct": round(100 * _rate(flat), 1), "fail_by_position": buckets,
            "failures": dict(fails.most_common()),
            "median_latency_s": round(sorted(r["latency_s"] for r in rs)[len(rs) // 2], 2),
            "median_completion_tokens": sorted(r.get("completion_tokens") or 0 for r in rs)[len(rs) // 2]}
    # H1 and H2 (README): late-minus-early drift at 50, and the dLLM minus Qwen gap in that drift.
    for o in cfg.orders:
        g = {arm: by_cell.get((50, o, arm), []) for arm in cfg.arms}
        if not all(g.values()):
            continue
        drift = {arm: late_minus_early(g[arm], 50) for arm in cfg.arms}
        m["tests"][f"drift50/{o}"] = {
            **{arm: {"value": round(drift[arm], 3), "ci": bootstrap({arm: g[arm]}, lambda s, a=arm: late_minus_early(s[a], 50))}
               for arm in cfg.arms},
            "dllm_minus_qwen": {"value": round(drift["dllm"] - drift["qwen"], 3),
                                "ci": bootstrap(g, lambda s: late_minus_early(s["dllm"], 50) - late_minus_early(s["qwen"], 50))},
            "returned_only_dllm_minus_qwen": {
                "value": round(late_minus_early(g["dllm"], 50, True) - late_minus_early(g["qwen"], 50, True), 3),
                "ci": bootstrap(g, lambda s: late_minus_early(s["dllm"], 50, True) - late_minus_early(s["qwen"], 50, True))}}
    for b, _ in cfg.requests:
        for o in cfg.orders:
            g = {arm: by_cell.get((b, o, arm), []) for arm in cfg.arms}
            if all(g.values()):
                rate = lambda s: _rate([e for r in s["dllm"] for e in r]) - _rate([e for r in s["qwen"] for e in r])
                m["tests"][f"gap/{b}/{o}"] = {"dllm_minus_qwen_fail": round(rate(g), 3), "ci": bootstrap(g, rate)}
    (run_dir / "metrics.json").write_text(json.dumps(m, indent=1))
    lines = ["# Long-range consistency", "", f"Temperatures {dict(cfg.temps)}; thinking off; {cfg.concurrency} concurrent per arm.", "",
             "| batch | order | arm | requests | parse ok | trunc | fail % | fail % by position | median latency s | median tokens |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for k, c in m["cells"].items():
        b, o, arm = k.split("/")
        lines.append(f"| {b} | {o} | {arm} | {c['requests']} | {c['parse_ok']} | {c['truncated']} | {c['fail_pct']} | "
                     f"{' / '.join(map(str, c['fail_by_position'].values()))} | {c['median_latency_s']} | {c['median_completion_tokens']} |")
    lines += ["", "Failures by check (a record can fail several):", ""]
    lines += [f"- `{k}`: {c['failures']}" for k, c in m["cells"].items()]
    lines += ["", "## Tests (95% intervals, bootstrap over requests)", ""]
    lines += [f"- `{k}`: {json.dumps(v)}" for k, v in m["tests"].items()]
    (run_dir / "summary.md").write_text("\n".join(lines) + "\n")
    print((run_dir / "summary.md").read_text())


def main():
    p = argparse.ArgumentParser(prog="python -m bench.tabdlm.longrange")
    p.add_argument("stage", choices=["generate", "score", "all"])
    p.add_argument("--run", required=True, help="output goes to bench/results/tabdlm-longrange-<run>/")
    p.add_argument("--probe", action="store_true", help="one request per cell, to check limits before a run")
    a = p.parse_args()
    cfg = Config()
    if a.probe:
        cfg = dataclasses.replace(cfg, requests=tuple((b, 1) for b, _ in cfg.requests))
    run_dir = RESULTS / f"tabdlm-longrange-{a.run}"
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
