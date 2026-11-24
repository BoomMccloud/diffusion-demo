"""Distinctness of a synthetic dataset, per (model, temperature) cell.

Input is a list of items {cell, id, text, clean}. Each cell is compared at the same sample size N:
the metrics are averaged over `resamples` random subsets of N items, so a cell with more rows
doesn't look more diverse just because it is bigger. Cells with fewer than N items are skipped.

Metrics:
  distinct3        unique character 3-grams / total 3-grams across the subset (lexical variety)
  gzip_ratio       gzip size of the joined subset / sum of each item's gzip size; lower means the
                   items share more text
  mean_cos         mean pairwise cosine similarity of embeddings; lower is more spread out
  nn_cos           mean, over items, of the cosine to its nearest other item; high means near-copies
  near_dup         share of items whose nearest neighbour is above NEAR_DUP cosine
  vendi            Vendi score: the effective number of distinct items, out of N
"""
import gzip, hashlib, json, os, random, urllib.request
from pathlib import Path

import numpy as np

EMBED_MODEL = "gemini-embedding-001"
CACHE = Path(__file__).resolve().parent / "results/embeddings.jsonl"
NEAR_DUP = 0.95


def _load_cache():
    if not CACHE.exists():
        return {}
    return {r["sha"]: r["v"] for r in map(json.loads, open(CACHE))}


def embed(texts):
    """Returns unit-normalised embeddings, caching by text hash."""
    cache = _load_cache()
    sha = lambda t: hashlib.sha256(f"{EMBED_MODEL}\n{t}".encode()).hexdigest()
    missing = [t for t in dict.fromkeys(texts) if sha(t) not in cache]
    for i in range(0, len(missing), 50):
        batch = missing[i:i + 50]
        req = urllib.request.Request(
            "https://generativelanguage.googleapis.com/v1beta/openai/embeddings",
            json.dumps({"model": EMBED_MODEL, "input": batch}).encode(),
            {"Content-Type": "application/json", "Authorization": f"Bearer {os.environ['GEMINI_API_KEY']}"})
        data = json.load(urllib.request.urlopen(req, timeout=120))["data"]
        with CACHE.open("a") as f:
            for t, d in zip(batch, data):
                cache[sha(t)] = d["embedding"]
                f.write(json.dumps({"sha": sha(t), "v": d["embedding"]}) + "\n")
    m = np.array([cache[sha(t)] for t in texts], dtype=np.float64)
    return m / np.linalg.norm(m, axis=1, keepdims=True)


def vendi(sim):
    eig = np.linalg.eigvalsh(sim / len(sim))
    eig = eig[eig > 1e-12]
    return float(np.exp(-(eig * np.log(eig)).sum()))


def subset_metrics(texts, vecs):
    grams = [t[i:i + 3] for t in texts for i in range(len(t) - 2)]
    joined = gzip.compress("\n".join(texts).encode())
    separate = sum(len(gzip.compress(t.encode())) for t in texts)
    sim = vecs @ vecs.T
    off = sim[~np.eye(len(sim), dtype=bool)].reshape(len(sim), -1)
    nn = off.max(axis=1)
    return {"distinct3": len(set(grams)) / max(1, len(grams)), "gzip_ratio": len(joined) / separate,
            "mean_cos": float(off.mean()), "nn_cos": float(nn.mean()),
            "near_dup": float((nn > NEAR_DUP).mean()), "vendi": vendi(sim)}


def score(items, n, resamples=20, seed=0):
    """items: list of dicts with cell, text. Returns {cell: averaged metrics}."""
    by_cell = {}
    for it in items:
        by_cell.setdefault(it["cell"], []).append(it["text"])
    out = {}
    for cell, texts in sorted(by_cell.items()):
        if len(texts) < n:
            out[cell] = {"skipped": f"only {len(texts)} items"}
            continue
        vecs = embed(texts)
        rng = random.Random(seed)
        runs = []
        for _ in range(resamples):
            idx = rng.sample(range(len(texts)), n)
            runs.append(subset_metrics([texts[i] for i in idx], vecs[idx]))
        out[cell] = {k: round(float(np.mean([r[k] for r in runs])), 3) for k in runs[0]}
        out[cell]["items"] = len(texts)
    return out
