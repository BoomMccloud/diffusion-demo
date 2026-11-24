"""Generate and judge stages. Both append one JSON line per finished request and resume on rerun.

A job is (dataset, setting, arm, idx). Request idx gets the same sampling seed and, for `extract`,
the same held-out row in both arms.
"""
import asyncio, json, os, time

from openai import AsyncOpenAI

from bench.synthdata import arms
from . import data, tasks


def items(cfg, ds):
    return data.amazon_heldout(cfg.n) if ds == "amazon" else data.bio_heldout(cfg.n)


def jobs(cfg):
    return [(ds, s, arm, i) for ds in cfg.datasets for s in cfg.settings for arm in cfg.arms for i in range(cfg.n)]


def gen_key(r):
    return (r["dataset"], r["setting"], r["arm"], r["idx"])


def sampling_seed(ds, setting, idx):
    return (1 + tasks.DATASETS.index(ds)) * 100_000 + (1 + tasks.SETTINGS.index(setting)) * 10_000 + idx


async def _one(client, cfg, job, heldout):
    ds, setting, arm, idx = job
    a = arms.ARMS[arm]
    item = heldout[ds][idx] if setting == "extract" else None
    temp = dict(cfg.temps)[arm]
    row = {"dataset": ds, "setting": setting, "arm": arm, "model": a["model"], "temp": temp, "idx": idx,
           "gold": (tasks.amazon_label(item) if ds == "amazon" else tasks.bio_label(item)) if item else None}
    t0 = time.time()
    try:
        r = await client.chat.completions.create(
            model=a["model"], temperature=temp, max_tokens=dict(cfg.max_tokens)[(ds, setting)],
            seed=sampling_seed(ds, setting, idx), extra_body=a["extra"],
            messages=[{"role": "user", "content": tasks.prompt(ds, setting, item)}])
        row.update(raw=r.choices[0].message.content or "", finish_reason=r.choices[0].finish_reason,
                   prompt_tokens=r.usage.prompt_tokens if r.usage else None,
                   completion_tokens=r.usage.completion_tokens if r.usage else None,
                   served_model=r.model)
    except Exception as e:
        row.update(raw="", error=repr(e)[:300])
    row["latency_s"] = round(time.time() - t0, 3)
    records, raw_ok, reason = tasks.parse(setting, row["raw"]) if "error" not in row else (None, False, "error")
    row.update(records=records, raw_json_ok=raw_ok, parse_reason=reason or "ok")
    return row


async def generate(cfg, out):
    done = {gen_key(r) for r in map(json.loads, open(out)) if "error" not in r} if out.exists() else set()
    todo = [j for j in jobs(cfg) if j not in done]
    print(f"generate: {len(todo)} to run, {len(done)} already done", flush=True)
    heldout = {ds: items(cfg, ds) for ds in cfg.datasets}

    async def arm_run(arm, js):
        client = arms.client(arm)
        sem = asyncio.Semaphore(cfg.concurrency)
        n = 0

        async def go(job):
            nonlocal n
            async with sem:
                row = await _one(client, cfg, job, heldout)
            with out.open("a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
            if n % 20 == 0:
                print(f"  {arm}: {n}/{len(js)}", flush=True)

        # Cell by cell, so one cell's latencies aren't shaped by another's queue.
        for c in dict.fromkeys(j[:2] for j in js):
            await asyncio.gather(*(go(j) for j in js if j[:2] == c))

    by_arm = {}
    for j in todo:
        by_arm.setdefault(j[2], []).append(j)
    await asyncio.gather(*(arm_run(a, js) for a, js in by_arm.items()))


def last_rows(path, key):
    out = {}
    if path.exists():
        for r in map(json.loads, open(path)):
            out[key(r)] = r
    return out


def judge_targets(gen_path):
    """Every schema-valid Amazon record from Setting A, plus the real and bland floor records."""
    out = []
    for r in last_rows(gen_path, gen_key).values():
        if r["dataset"] != "amazon" or r["setting"] == "extract" or not r.get("records"):
            continue
        for i, rec in enumerate(r["records"]):
            if tasks.amazon_schema(rec) is None:
                out.append((("gen",) + gen_key(r) + (i,), rec))
    for name, recs in (("fewshot", data.amazon_fewshot()), ("real", data.amazon_real(20)),
                       ("bland", tasks.BLAND_AMAZON)):
        out += [(("floor", name, i), rec) for i, rec in enumerate(recs)]
    return out


async def judge(cfg, gen_path, out):
    done = {tuple(j["key"]) for j in map(json.loads, open(out)) if "error" not in j["verdict"]} \
        if out.exists() else set()
    todo = [(k, rec) for k, rec in judge_targets(gen_path) if k not in done]
    print(f"judge: {len(todo)} to run, {len(done)} already done", flush=True)
    client = AsyncOpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                         api_key=os.environ["GEMINI_API_KEY"], timeout=120, max_retries=3)
    sem = asyncio.Semaphore(cfg.judge_concurrency)

    async def one(k, rec):
        async with sem:
            try:
                resp = await client.chat.completions.create(
                    model=cfg.judge_model, temperature=0, response_format={"type": "json_object"},
                    messages=[{"role": "user", "content": tasks.judge_prompt(rec)}])
                v = json.loads(resp.choices[0].message.content)
            except Exception as e:
                v = {"error": repr(e)[:200]}
        with out.open("a") as f:
            f.write(json.dumps({"key": list(k), "judge": cfg.judge_model, "verdict": v}, ensure_ascii=False) + "\n")

    await asyncio.gather(*(one(k, rec) for k, rec in todo))
