"""Generation stage: one row per request in generations.jsonl, written as each request finishes.

A job is (task, mode, arm, temp, replicate, idx). Jobs already in the file are skipped, so a run
resumes. Each model runs its own jobs at `concurrency`; the two models run at the same time.
"""
import asyncio, json, time

from . import arms, tasks


def jobs(cfg):
    out = []
    seeds = cfg.seed_dicts()
    for task in cfg.tasks:
        for mode in cfg.modes:
            for arm in cfg.arms:
                for temp in cfg.temps:
                    if cfg.skipped(task, mode, arm, temp):
                        continue
                    for rep in range(cfg.replicates):
                        if mode == "open":
                            out += [(task, mode, arm, temp, rep, i, None) for i in range(cfg.open_n)]
                        else:
                            out += [(task, mode, arm, temp, rep, si * cfg.seed_samples + k, seed)
                                    for si, seed in enumerate(seeds) for k in range(cfg.seed_samples)]
    return out


def key(row):
    return (row["task"], row["mode"], row["arm"], row["temp"], row["rep"], row["idx"])


def sampling_seed(task, mode, temp, rep, idx):
    """Distinct per request and replicate, identical across models."""
    return (1 if task == "narrative" else 2) * 10_000_000 + (1 if mode == "open" else 2) * 1_000_000 \
        + int(round(temp * 10)) * 100_000 + rep * 10_000 + idx


async def _one(client, cfg, job, t_cell):
    task, mode, arm, temp, rep, idx, seed = job
    a = arms.ARMS[arm]
    t0 = time.time()
    row = {"task": task, "mode": mode, "arm": arm, "model": a["model"], "temp": temp, "rep": rep,
           "idx": idx, "seed": seed, "t_start": round(t0 - t_cell, 3)}
    try:
        r = await client.chat.completions.create(
            model=a["model"], temperature=temp, max_tokens=cfg.tokens(task),
            seed=sampling_seed(task, mode, temp, rep, idx), extra_body=a["extra"],
            messages=[{"role": "user", "content": tasks.prompt(task, seed)}])
        raw = r.choices[0].message.content or ""
        row.update(raw=raw, finish_reason=r.choices[0].finish_reason,
                   prompt_tokens=r.usage.prompt_tokens if r.usage else None,
                   completion_tokens=r.usage.completion_tokens if r.usage else None,
                   provider=getattr(r, "provider", None) or (r.model_extra or {}).get("provider"),
                   served_model=r.model)
    except Exception as e:
        row.update(raw="", error=repr(e)[:300])
    t1 = time.time()
    row.update(latency_s=round(t1 - t0, 3), t_done=round(t1 - t_cell, 3))
    if "error" in row:
        text, record, reason, raw_ok = "", None, "error", False
    else:
        text, record, reason = tasks.check(task, seed, row["raw"])
        raw_ok = tasks.raw_format_ok(task, seed, row["raw"])
    row.update(text=text, record=record, format_ok=reason is None, reason=reason or "ok",
               raw_format_ok=raw_ok)
    return row


async def run(cfg, out_path):
    # A request that errored (rate limit, spend cap, timeout) is retried on the next run; metrics
    # read the last row per key, so the retry replaces the error.
    done = set()
    if out_path.exists():
        done = {key(r) for r in map(json.loads, open(out_path)) if "error" not in r}
    todo = [j for j in jobs(cfg) if j[:6] not in done]
    print(f"generate: {len(todo)} to run, {len(done)} already done", flush=True)
    by_arm = {}
    for j in todo:
        by_arm.setdefault(j[2], []).append(j)

    async def arm_run(arm, js):
        client = arms.client(arm)
        sem = asyncio.Semaphore(cfg.concurrency)
        # Cell clocks: t_done is measured from the start of each (task, mode, temp, rep) cell.
        cell_start = {}
        n = 0

        async def go(job):
            nonlocal n
            async with sem:
                c = job[:2] + job[3:5]
                cell_start.setdefault(c, time.time())
                row = await _one(client, cfg, job, cell_start[c])
            with out_path.open("a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
            if n % 100 == 0:
                print(f"  {arm}: {n}/{len(js)}", flush=True)

        # Run cell by cell so each cell's clock covers only its own requests.
        cells = {}
        for j in js:
            cells.setdefault(j[:2] + j[3:5], []).append(j)
        for c, cjs in cells.items():
            await asyncio.gather(*map(go, cjs))

    await asyncio.gather(*(arm_run(a, js) for a, js in by_arm.items()))
