"""Audit stage: exports samples for a person to label, and scores the labels.

judge_audit.csv  50 judged records across cells. Fill `human_clean` with 1 or 0.
pair_audit.csv   40 clean record pairs from the same cell at cosine 0.95 to 0.98. Fill `same_case`
                 with 1 if a training set would count them as the same case, else 0.

`--score` prints judge agreement and the same-case share per similarity band. The README sets the
bars: judge agreement of at least 85%, and no more than a third of pairs at or above 0.97 labelled
as different cases.
"""
import csv, json, random

from . import metrics, tasks
from .generate import key

BANDS = [(0.95, 0.96), (0.96, 0.97), (0.97, 0.98)]


def export(cfg, run_dir, n_judge=50, n_pairs=40):
    rows = metrics.load(run_dir)
    rng = random.Random(0)
    judged = [r for r in rows if r["verdict"] and "error" not in r["verdict"]]
    rng.shuffle(judged)
    # Stratify: round-robin across cells so no single cell dominates.
    by_cell = {}
    for r in judged:
        by_cell.setdefault((r["task"], r["mode"], r["arm"], r["temp"]), []).append(r)
    pick = []
    while len(pick) < n_judge and any(by_cell.values()):
        for c in list(by_cell):
            if by_cell[c] and len(pick) < n_judge:
                pick.append(by_cell[c].pop())
    with (run_dir / "judge_audit.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["key", "request", "text", "judge_clean", "judge_note", "human_clean", "human_note"])
        for r in pick:
            w.writerow([json.dumps(key(r)), json.dumps(r["seed"], ensure_ascii=False) if r["seed"] else "open",
                        r["text"], int(r["clean"]), r["verdict"].get("note", ""), "", ""])

    pairs = {b: [] for b in BANDS}
    cells = {}
    for r in rows:
        if r["clean"]:
            cells.setdefault((r["task"], r["mode"], r["arm"], r["temp"], r["rep"]), []).append(r)
    for c, rs in cells.items():
        texts = [tasks.content(r["task"], r["text"], r["record"]) for r in rs]
        vecs = metrics.embed(texts, cfg.embed_model, run_dir / "embeddings.jsonl")
        sim = vecs @ vecs.T
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                for b in BANDS:
                    if b[0] <= sim[i, j] < b[1]:
                        pairs[b].append((float(sim[i, j]), rs[i], rs[j]))
    with (run_dir / "pair_audit.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["band", "cosine", "text_a", "text_b", "same_case"])
        per = n_pairs // len(BANDS) + 1
        for b, ps in pairs.items():
            for s, a, c in rng.sample(ps, min(per, len(ps))):
                w.writerow([f"{b[0]}-{b[1]}", f"{s:.3f}", a["text"], c["text"], ""])
    print(f"wrote {len(pick)} records to judge_audit.csv and pairs to pair_audit.csv in {run_dir}")


def score(run_dir):
    with (run_dir / "judge_audit.csv").open() as f:
        rows = [r for r in csv.DictReader(f) if r["human_clean"].strip() in ("0", "1")]
    if rows:
        agree = sum(r["human_clean"].strip() == r["judge_clean"] for r in rows) / len(rows)
        print(f"judge agreement: {agree:.0%} on {len(rows)} labelled records (bar: 85%)")
    with (run_dir / "pair_audit.csv").open() as f:
        prs = [r for r in csv.DictReader(f) if r["same_case"].strip() in ("0", "1")]
    for b in BANDS:
        g = [r for r in prs if r["band"] == f"{b[0]}-{b[1]}"]
        if g:
            same = sum(r["same_case"].strip() == "1" for r in g) / len(g)
            print(f"cosine {b[0]}-{b[1]}: {same:.0%} labelled same case ({len(g)} pairs)")
