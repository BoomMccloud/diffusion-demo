"""Score stage: per-cell clean and distinct yields, the pre-registered comparison, and summary.md.

A cell is (task, mode, arm, temp, rep). Yields divide by the number of requests in the cell, so a
failed or unformatted request counts against the model.

Distinct: walk the cell's clean records in a random order and keep one when its embedding cosine to
every kept record is below tau and its case key is new. The count is averaged over `orderings` random
orders, so it doesn't depend on which request finished first.
"""
import hashlib, json, os, random, statistics, time, urllib.error, urllib.request

import numpy as np

from . import tasks
from .generate import key

# ---------- embeddings (cached in the run directory by text hash)


def embed(texts, model, cache_path):
    cache = {}
    if cache_path.exists():
        cache = {r["sha"]: r["v"] for r in map(json.loads, open(cache_path))}
    sha = lambda t: hashlib.sha256(f"{model}\n{t}".encode()).hexdigest()
    missing = [t for t in dict.fromkeys(texts) if sha(t) not in cache]
    for i in range(0, len(missing), 50):
        batch = missing[i:i + 50]
        req = urllib.request.Request(
            "https://generativelanguage.googleapis.com/v1beta/openai/embeddings",
            json.dumps({"model": model, "input": batch}).encode(),
            {"Content-Type": "application/json", "Authorization": f"Bearer {os.environ['GEMINI_API_KEY']}"})
        # Rate limits (429) and server errors are retried with backoff, up to about 5 minutes.
        for attempt in range(8):
            try:
                data = json.load(urllib.request.urlopen(req, timeout=120))["data"]
                break
            except urllib.error.HTTPError as e:
                if e.code != 429 and e.code < 500 or attempt == 7:
                    raise
                time.sleep(min(60, 5 * 2 ** attempt))
        with cache_path.open("a") as f:
            for t, d in zip(batch, data):
                cache[sha(t)] = d["embedding"]
                f.write(json.dumps({"sha": sha(t), "v": d["embedding"]}) + "\n")
    if not texts:
        return np.zeros((0, 1))
    m = np.array([cache[sha(t)] for t in texts], dtype=np.float64)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


# ---------- distinctness


def greedy_distinct(sim, keys, order, tau):
    kept, seen = [], set()
    for i in order:
        if keys[i] in seen or (kept and sim[i, kept].max() >= tau):
            continue
        kept.append(i)
        seen.add(keys[i])
    return len(kept)


def expected_distinct(sim, keys, tau, orderings, rng, subset=None):
    idx = list(range(len(keys))) if subset is None else list(subset)
    if not idx:
        return 0.0
    total = 0
    for _ in range(orderings):
        rng.shuffle(idx)
        total += greedy_distinct(sim, keys, idx, tau)
    return total / orderings


def vendi(vecs):
    sim = vecs @ vecs.T
    eig = np.linalg.eigvalsh(sim / len(sim))
    eig = eig[eig > 1e-12]
    return float(np.exp(-(eig * np.log(eig)).sum()))


# ---------- loading


def load(run_dir):
    gens = {}
    for r in map(json.loads, open(run_dir / "generations.jsonl")):
        gens[key(r)] = r
    verdicts = {}
    jp = run_dir / "judgments.jsonl"
    if jp.exists():
        for j in map(json.loads, open(jp)):
            verdicts[tuple(j["key"])] = j
    for k, r in gens.items():
        j = verdicts.get(k)
        r["clean"] = bool(r["format_ok"] and j and j["clean"])
        r["verdict"] = j["verdict"] if j else None
    return list(gens.values())


# ---------- scoring


def score(cfg, run_dir, tag=""):
    """Scores the cells in cfg's grid. `tag` names the output files, e.g. metrics_early.json."""
    rows = [r for r in load(run_dir) if r["task"] in cfg.tasks and r["mode"] in cfg.modes
            and r["arm"] in cfg.arms and r["temp"] in cfg.temps
            and not cfg.skipped(r["task"], r["mode"], r["arm"], r["temp"])]
    cache = run_dir / "embeddings.jsonl"
    rng = random.Random(0)
    cells = {}
    for r in rows:
        cells.setdefault((r["task"], r["mode"], r["arm"], r["temp"], r["rep"]), []).append(r)

    # Per cell: clean records with their similarity matrix, kept for the comparison below.
    prepared, out = {}, []
    for c, rs in sorted(cells.items()):
        task, mode, arm, temp, rep = c
        clean = sorted((r for r in rs if r["clean"]), key=lambda r: r["idx"])
        texts = [tasks.content(task, r["text"], r["record"]) for r in clean]
        keys = [tasks.case_key(task, r["text"], r["record"]) for r in clean]
        vecs = embed(texts, cfg.embed_model, cache)
        sim = vecs @ vecs.T if len(clean) else np.zeros((0, 0))
        prepared[c] = (clean, keys, sim)
        n = len(rs)
        m = {"task": task, "mode": mode, "arm": arm, "temp": temp, "rep": rep, "requests": n,
             "raw_format": sum(r["raw_format_ok"] for r in rs) / n,
             "format": sum(r["format_ok"] for r in rs) / n,
             "clean": len(clean) / n,
             "errors": sum("error" in r for r in rs)}
        for tau in cfg.taus:
            m[f"distinct@{tau}"] = expected_distinct(sim, keys, tau, cfg.orderings, rng) / n
        if mode == "seeded":
            by_seed = {}
            for i, r in enumerate(clean):
                by_seed.setdefault(r["idx"] // cfg.seed_samples, []).append(i)
            pairs = [g for g in by_seed.values() if len(g) >= 2]
            tau = cfg.taus[0]
            m["within_seed_distinct"] = (sum(all(sim[a, b] < tau and keys[a] != keys[b]
                                                 for x, a in enumerate(g) for b in g[x + 1:]) for g in pairs)
                                         / len(pairs)) if pairs else None
        if len(clean) >= cfg.vendi_n:
            m["vendi"] = statistics.mean(vendi(vecs[rng.sample(range(len(clean)), cfg.vendi_n)]) for _ in range(20))
        wall = max(r["t_done"] for r in rs) / 60
        m["distinct_per_min"] = m[f"distinct@{cfg.taus[0]}"] * n / wall if wall else None
        m["latency_p50"] = statistics.median(r["latency_s"] for r in rs)
        toks = [r["completion_tokens"] for r in rs if r.get("completion_tokens")]
        m["tokens_mean"] = statistics.mean(toks) if toks else None
        out.append(m)

    decision = compare(cfg, cells, prepared, out)
    metrics = {"cells": out, "decision": decision}
    sfx = f"_{tag}" if tag else ""
    (run_dir / f"metrics{sfx}.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=1))
    (run_dir / f"summary{sfx}.md").write_text(summary(cfg, out, decision))
    print((run_dir / f"summary{sfx}.md").read_text())


def compare(cfg, cells, prepared, out):
    """Pick each model's best temperature on replicate 0, compare on the other replicates.

    The interval subsamples 80% of request slots (open) or seeds (seeded) without replacement, the
    same slots for both models, 200 times, and takes the 2.5th and 97.5th percentiles of the gap.
    """
    tau = cfg.taus[0]
    res = []
    for task in cfg.tasks:
        for mode in cfg.modes:
            if len(cfg.arms) < 2:
                continue
            best = {}
            for arm in cfg.arms:
                cand = [m for m in out if (m["task"], m["mode"], m["arm"], m["rep"]) == (task, mode, arm, 0)]
                if cand:
                    best[arm] = max(cand, key=lambda m: m[f"distinct@{tau}"])["temp"]
            held = range(1, cfg.replicates) if cfg.replicates > 1 else range(0, 1)
            for rep in held:
                a, b = cfg.arms[0], cfg.arms[1]
                ca, cb = (task, mode, a, best.get(a), rep), (task, mode, b, best.get(b), rep)
                if ca not in prepared or cb not in prepared:
                    continue
                ma = next(m for m in out if (m["task"], m["mode"], m["arm"], m["temp"], m["rep"]) == ca)
                mb = next(m for m in out if (m["task"], m["mode"], m["arm"], m["temp"], m["rep"]) == cb)
                slot = (lambda r: r["idx"]) if mode == "open" else (lambda r: r["idx"] // cfg.seed_samples)
                slots = sorted({slot(r) for r in cells[ca]})
                rng = random.Random(rep)
                gaps = []
                for _ in range(200):
                    keep = set(rng.sample(slots, int(0.8 * len(slots))))
                    vals = []
                    for c in (ca, cb):
                        clean, keys, sim = prepared[c]
                        sub = [i for i, r in enumerate(clean) if slot(r) in keep]
                        nreq = sum(slot(r) in keep for r in cells[c])
                        vals.append(expected_distinct(sim, keys, tau, 5, rng, sub) / nreq)
                    gaps.append(vals[0] - vals[1])
                gaps.sort()
                res.append({"task": task, "mode": mode, "rep": rep, "temps": best,
                            f"{a}_distinct": ma[f"distinct@{tau}"], f"{b}_distinct": mb[f"distinct@{tau}"],
                            f"{a}_clean": ma["clean"], f"{b}_clean": mb["clean"],
                            "gap": ma[f"distinct@{tau}"] - mb[f"distinct@{tau}"],
                            "interval": [gaps[int(0.025 * len(gaps))], gaps[int(0.975 * len(gaps)) - 1]]})
    return res


def _fmt(vals, pct=True):
    vals = [v for v in vals if v is not None]
    if not vals:
        return "–"
    f = (lambda v: f"{100 * v:.0f}") if pct else (lambda v: f"{v:.1f}")
    mean = statistics.mean(vals)
    return f(mean) if len(vals) == 1 else f"{f(mean)} ({f(min(vals))}–{f(max(vals))})"


def summary(cfg, out, decision):
    t0, t1 = cfg.taus[0], cfg.taus[1]
    lines = ["# Synthetic data benchmark", "",
             f"Yields are per 100 requests; ranges are across {cfg.replicates} replicate(s). "
             f"Distinct counts clean records whose cosine to every kept record is below the threshold "
             f"and whose case key is new.", ""]
    if cfg.skip:
        lines += ["Deviation from the plan: these cells were not run or not scored: "
                  + "; ".join(f"{t} {m} {a} {tp}" for t, m, a, tp in cfg.skip) + ".", ""]
    for task in cfg.tasks:
        for mode in cfg.modes:
            ms = [m for m in out if m["task"] == task and m["mode"] == mode]
            if not ms:
                continue
            lines += [f"## {task}, {mode}", "",
                      f"| model | temp | raw format | format | clean | distinct <{t0} | distinct <{t1} |"
                      + (" within-seed distinct |" if mode == "seeded" else "") + " Vendi | distinct/min |",
                      "|---|---|---|---|---|---|---|" + ("---|" if mode == "seeded" else "") + "---|---|"]
            for arm in cfg.arms:
                for temp in cfg.temps:
                    g = [m for m in ms if m["arm"] == arm and m["temp"] == temp]
                    if not g:
                        continue
                    col = lambda k, pct=True: _fmt([m.get(k) for m in g], pct)
                    lines.append(f"| {arm} | {temp} | {col('raw_format')} | {col('format')} | {col('clean')} | "
                                 f"{col(f'distinct@{t0}')} | {col(f'distinct@{t1}')} |"
                                 + (f" {col('within_seed_distinct')} |" if mode == "seeded" else "")
                                 + f" {col('vendi', False)} | {col('distinct_per_min', False)} |")
            lines.append("")
    lines += ["## Pre-registered comparison", "",
              "Each model at its best temperature by distinct yield on replicate 0, compared on held-out "
              "replicates. Interval: 80% subsamples of request slots or seeds, same slots for both models.", ""]
    if cfg.replicates == 1:
        lines += ["With one replicate, the temperature is chosen and compared on the same data, so this "
                  "table only checks the pipeline.", ""]
    if decision:
        a, b = cfg.arms[0], cfg.arms[1]
        lines += [f"| format | prompting | rep | temps | {a} distinct | {b} distinct | gap | 95% interval | "
                  f"{a} clean | {b} clean |", "|---|---|---|---|---|---|---|---|---|---|"]
        for d in decision:
            lines.append(f"| {d['task']} | {d['mode']} | {d['rep']} | "
                         f"{', '.join(f'{k} {v}' for k, v in d['temps'].items())} | "
                         f"{100 * d[f'{a}_distinct']:.0f} | {100 * d[f'{b}_distinct']:.0f} | "
                         f"{100 * d['gap']:+.0f} | {100 * d['interval'][0]:+.0f} to {100 * d['interval'][1]:+.0f} | "
                         f"{100 * d[f'{a}_clean']:.0f} | {100 * d[f'{b}_clean']:.0f} |")
    return "\n".join(lines) + "\n"
