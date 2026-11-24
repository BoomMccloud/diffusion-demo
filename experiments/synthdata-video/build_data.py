"""Builds data.json and replay.html from the 2026-10-20 synthdata run.
Run from the repo root: PYTHONPATH=. python experiments/synthdata-video/build_data.py

Cell: seeded narratives, replicate 1 (held out), each model at its best temperature
(dLLM 0.6, Qwen 1.0). Every request becomes one event at its real completion time:
  failed  not clean (format, judge, or request): ticks the rejected counter
  new     clean and distinct from everything that model had kept so far
  dup     clean but a near-copy (cosine >= 0.97 or same case key) of an earlier kept record
Clean records from both models share one t-SNE projection of their embeddings, so positions
are comparable across the two maps.
"""
import hashlib, json
from pathlib import Path

import numpy as np
from sklearn.manifold import TSNE

from bench.synthdata import metrics, tasks

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "bench/results/synthdata-2026-10-20"
CELLS = {"dllm": 0.6, "qwen": 1.0}
REP, TAU, EMBED = 1, 0.97, "gemini-embedding-001"


def load_vectors(texts):
    sha = lambda t: hashlib.sha256(f"{EMBED}\n{t}".encode()).hexdigest()
    want = {sha(t) for t in texts}
    found = {}
    with open(RUN / "embeddings.jsonl") as f:
        for line in f:
            if line[9:73] in want:  # '{"sha": "' prefix is 9 characters
                r = json.loads(line)
                found[r["sha"]] = r["v"]
    m = np.array([found[sha(t)] for t in texts])
    return m / np.linalg.norm(m, axis=1, keepdims=True)


def main():
    rows = [r for r in metrics.load(RUN) if r["task"] == "narrative" and r["mode"] == "seeded"
            and r["rep"] == REP and CELLS.get(r["arm"]) == r["temp"]]
    clean = [r for r in rows if r["clean"]]
    vecs = load_vectors([r["text"] for r in clean])
    xy = TSNE(n_components=2, metric="cosine", init="pca", perplexity=25, random_state=0).fit_transform(vecs)
    xy = (xy - xy.min(0)) / (xy.max(0) - xy.min(0))
    pos = {id(r): (i, xy[i]) for i, r in enumerate(clean)}

    out = {"cells": {}, "departments": {}}
    for arm in CELLS:
        rs = sorted((r for r in rows if r["arm"] == arm), key=lambda r: r["t_done"])
        kept, keys, events = [], set(), []
        for r in rs:
            e = {"t": round(r["t_done"], 2), "dept": r["seed"]["department"]}
            if not r["clean"]:
                e["kind"] = "failed"
            else:
                i, (x, y) = pos[id(r)]
                k = tasks.case_key("narrative", r["text"], None)
                sims = [float(vecs[i] @ vecs[j]) for j in kept]
                twin = int(np.argmax(sims)) if sims else None
                if k in keys or (sims and max(sims) >= TAU):
                    e.update(kind="dup", x=round(float(x), 4), y=round(float(y), 4),
                             twin=twin if (sims and max(sims) >= TAU) else None)
                else:
                    e.update(kind="new", x=round(float(x), 4), y=round(float(y), 4), id=len(kept))
                    kept.append(i)
                    keys.add(k)
                e["cc"] = tasks.section(r["text"], "主诉")[:40]
                e["dx"] = tasks.section(r["text"], "诊断")[:40]
            events.append(e)
        out["cells"][arm] = {"temp": CELLS[arm], "requests": len(rs), "events": events,
                             "end": max(e["t"] for e in events)}
        print(arm, {k: sum(e["kind"] == k for e in events) for k in ("new", "dup", "failed")},
              "end", out["cells"][arm]["end"])

    # Department label positions: centroid of each department's clean points across both models.
    for d in sorted({r["seed"]["department"] for r in clean}):
        pts = np.array([pos[id(r)][1] for r in clean if r["seed"]["department"] == d])
        out["departments"][d] = [round(float(v), 4) for v in pts.mean(0)]
    (Path(__file__).parent / "data.json").write_text(json.dumps(out, ensure_ascii=False))
    render()


def render():
    """Inlines data.json into template.html as replay.html, so it opens from disk."""
    here = Path(__file__).parent
    html = (here / "template.html").read_text().replace("__DATA__", (here / "data.json").read_text())
    (here / "replay.html").write_text(html)


if __name__ == "__main__":
    main()
