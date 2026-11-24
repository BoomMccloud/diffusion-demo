"""Gap test: does a forward reference get harder as more text sits between it and its source?

python -m bench.taxloop.gap {generate,score,all} --run NAME [--probe]

One loop from the tax-form test. The answer starts with `taxable`, which must equal `line26`, and
`line26` is computed two lines later from wages and benefits. Between them the model writes a memo of
about G words (G = 0 means no memo). The served dLLM decodes 16-token blocks left to right, so its
bidirectional attention can only help while the source is in the same or a nearby block. If it does
help, the dLLM should beat Qwen at small G and the gap should close as G grows. Qwen can only compute
`taxable` in its head, so distance shouldn't matter to it. Order `backward` puts `taxable` last, as
a check that both models can do the arithmetic when it's written out. Every check is code.
"""
import argparse, asyncio, dataclasses, datetime, json, re, subprocess, time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from bench.synthdata import arms
from bench.tabdlm.longrange import bootstrap
from .run import RESULTS, case, parse, pct

GAPS = (0, 15, 60, 250, 1000)
ORDERS = ("forward", "backward")


@dataclass(frozen=True)
class Config:
    arms: tuple = ("dllm", "qwen")
    temp: float = 0.6
    n: int = 30
    gaps: tuple = GAPS
    orders: tuple = ORDERS
    max_tokens: int = 3000
    concurrency: int = 8


def truth(c):
    limit = pct(c["wages"], 40)
    excluded = min(c["dependent_care_benefits"], 5000, limit)
    line26 = c["dependent_care_benefits"] - excluded
    return {"wages": c["wages"], "benefits": c["dependent_care_benefits"], "taxable": line26,
            "limit": limit, "excluded": excluded, "line26": line26}


def keys(gap, order):
    calc = ["limit", "excluded", "line26"]
    memo = ["memo"] if gap else []
    if order == "forward":
        return ["wages", "benefits", "taxable"] + memo + calc
    return ["wages", "benefits"] + memo + calc + ["taxable"]


RULES = {
    "wages": "wages, from the facts",
    "benefits": "dependent care benefits, from the facts",
    "taxable": "taxable benefits: the same value as line26",
    "memo": "a plain-language note to the taxpayer of about {gap} words on keeping receipts and records for next year. Use no digits",
    "limit": "4% of wages, rounded down to a whole dollar",
    "excluded": "the smallest of benefits, 5000 and limit",
    "line26": "benefits minus excluded",
}

PROMPT = """You are filling in part of a tax form for a fictional test. The rules are invented for this test and are not real tax law. Follow them exactly.

Facts: wages {wages}, dependent care benefits {benefits}.

Fields:
{rules}

Answer with one flat JSON object. Use exactly these keys, in exactly this order:
{keys}

Write the keys in exactly the order listed. Do not move any key earlier or later, even when its value depends on keys listed after it. An answer with any key out of order is rejected.

{types} Output only the JSON object, with no other text."""


def prompt(c, gap, order):
    ks = keys(gap, order)
    return PROMPT.format(wages=c["wages"], benefits=c["dependent_care_benefits"], keys=", ".join(ks),
                         rules="\n".join(f"- {k}: {RULES[k].format(gap=gap)}" for k in ks),
                         types="memo is a string. Every other value is an integer." if gap else "Every value is an integer.")


# ---------- scoring

def _int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def score_request(row):
    """`linked`: taxable equals the model's own line26, with a reordered or unparsed answer failing.
    `correct`: taxable equals the true value. `calc`: limit, excluded and line26 all true."""
    t = truth(case(row["idx"]))
    o = row["obj"]
    if o is None:
        return {"parsed": False, "order_ok": False, "linked": False, "correct": False, "calc": False, "memo_words": None}
    memo = o.get("memo")
    return {"parsed": True, "order_ok": row["key_order"] == keys(row["gap"], row["order"]),
            "linked": row["key_order"] == keys(row["gap"], row["order"]) and _int(o.get("taxable"))
                      and o.get("taxable") == o.get("line26"),
            "correct": o.get("taxable") == t["taxable"] and _int(o.get("taxable")),
            "calc": all(o.get(k) == t[k] and _int(o.get(k)) for k in ("limit", "excluded", "line26")),
            "memo_words": len(memo.split()) if isinstance(memo, str) else None}


def key(r):
    return (r["gap"], r["order"], r["arm"], r["idx"])


# ---------- generate

async def generate(cfg, out):
    done = {key(r) for r in map(json.loads, open(out)) if "error" not in r} if out.exists() else set()
    todo = [(g, o, a, i) for g in cfg.gaps for o in cfg.orders for a in cfg.arms for i in range(cfg.n)
            if (g, o, a, i) not in done]
    print(f"generate: {len(todo)} to run, {len(done)} already done", flush=True)

    async def one(client, job):
        gap, order, arm, idx = job
        a = arms.ARMS[arm]
        row = {"gap": gap, "order": order, "arm": arm, "model": a["model"], "temp": cfg.temp, "idx": idx}
        t0 = time.time()
        try:
            r = await client.chat.completions.create(
                model=a["model"], temperature=cfg.temp, max_tokens=cfg.max_tokens,
                seed=GAPS.index(gap) * 10_000 + ORDERS.index(order) * 1_000 + idx, extra_body=a["extra"],
                messages=[{"role": "user", "content": prompt(case(idx), gap, order)}])
            row.update(raw=r.choices[0].message.content or "", finish_reason=r.choices[0].finish_reason,
                       prompt_tokens=r.usage.prompt_tokens if r.usage else None,
                       completion_tokens=r.usage.completion_tokens if r.usage else None, served_model=r.model)
        except Exception as e:
            row.update(raw="", error=repr(e)[:300])
        row["latency_s"] = round(time.time() - t0, 3)
        obj, order_keys, reason = parse(row["raw"])
        row.update(obj=obj, key_order=order_keys, parse_reason=reason or "ok")
        return row

    async def arm_run(arm, js):
        client = arms.client(arm)
        sem = asyncio.Semaphore(cfg.concurrency)

        async def go(job):
            async with sem:
                row = await one(client, job)
            with out.open("a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        await asyncio.gather(*(go(j) for j in js))

    by_arm = defaultdict(list)
    for j in todo:
        by_arm[j[2]].append(j)
    await asyncio.gather(*(arm_run(a, js) for a, js in by_arm.items()))


# ---------- score

def _median(xs):
    xs = sorted(x for x in xs if x is not None)
    return xs[len(xs) // 2] if xs else None


def _pct(ss, f):
    return round(100 * sum(s[f] for s in ss) / len(ss), 1) if ss else None


def score(cfg, run_dir):
    rows = {key(r): r for r in map(json.loads, open(run_dir / "generations.jsonl"))}
    cells = defaultdict(list)
    for r in rows.values():
        cells[(r["gap"], r["order"], r["arm"])].append((r, score_request(r)))
    m = {"cells": {}, "tests": {}}
    for (gap, order, arm), items in sorted(cells.items(), key=lambda kv: (kv[0][1], kv[0][0], kv[0][2])):
        ss = [s for _, s in items]
        m["cells"][f"{order}/{gap}/{arm}"] = {
            "requests": len(ss), "order_ok_pct": _pct(ss, "order_ok"), "linked_pct": _pct(ss, "linked"),
            "taxable_correct_pct": _pct(ss, "correct"), "calc_correct_pct": _pct(ss, "calc"),
            "median_memo_words": _median([s["memo_words"] for s in ss]),
            "median_completion_tokens": _median([r.get("completion_tokens") for r, _ in items]),
            "median_latency_s": _median([r["latency_s"] for r, _ in items])}
    # The test: dLLM minus Qwen on linked % at each gap, forward order.
    for gap in cfg.gaps:
        g = {arm: [s for _, s in cells.get((gap, "forward", arm), [])] for arm in cfg.arms}
        if all(g.values()):
            f = lambda s: 100 * (sum(x["linked"] for x in s["dllm"]) / len(s["dllm"])
                                 - sum(x["linked"] for x in s["qwen"]) / len(s["qwen"]))
            m["tests"][gap] = {"dllm_minus_qwen_linked": round(f(g), 1), "ci": bootstrap(g, f)}
    (run_dir / "metrics.json").write_text(json.dumps(m, indent=1))
    lines = ["# Gap test", "", f"Temperature {cfg.temp} for both arms; thinking off. Linked % needs the "
             "requested key order and taxable equal to the model's own line26.", "",
             "| order | memo words asked | arm | requests | key order ok % | linked % | taxable correct % "
             "| limit, excluded, line26 correct % | median memo words | median tokens | median latency s |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, c in m["cells"].items():
        lines.append(f"| {' | '.join(k.split('/'))} | {c['requests']} | {c['order_ok_pct']} | {c['linked_pct']} | "
                     f"{c['taxable_correct_pct']} | {c['calc_correct_pct']} | {c['median_memo_words']} | "
                     f"{c['median_completion_tokens']} | {c['median_latency_s']} |")
    lines += ["", "## dLLM minus Qwen, forward linked % (95% bootstrap interval)", ""]
    lines += [f"- gap {g}: {v['dllm_minus_qwen_linked']:+.1f} ({v['ci'][0]:+.1f} to {v['ci'][1]:+.1f})"
              for g, v in m["tests"].items()]
    (run_dir / "summary.md").write_text("\n".join(lines) + "\n")
    print((run_dir / "summary.md").read_text())


def main():
    p = argparse.ArgumentParser(prog="python -m bench.taxloop.gap")
    p.add_argument("stage", choices=["generate", "score", "all"])
    p.add_argument("--run", required=True, help="output goes to bench/results/taxloop-gap-<run>/")
    p.add_argument("--probe", action="store_true", help="two requests per cell, to check the pipeline")
    a = p.parse_args()
    cfg = dataclasses.replace(Config(), n=2) if a.probe else Config()
    run_dir = RESULTS / f"taxloop-gap-{a.run}"
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = run_dir / "manifest.json"
    if a.stage != "score" and not manifest.exists():
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        manifest.write_text(json.dumps({
            "started": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "git_commit": commit,
            "config": dataclasses.asdict(cfg), "arms": arms.fingerprint()}, indent=1, default=list))
    if a.stage in ("generate", "all"):
        asyncio.run(generate(cfg, run_dir / "generations.jsonl"))
    if a.stage in ("score", "all"):
        score(cfg, run_dir)


if __name__ == "__main__":
    main()
