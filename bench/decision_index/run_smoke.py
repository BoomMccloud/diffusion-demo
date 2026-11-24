"""Send smoke rows to a /v1/systemone endpoint and score them.

    python3 bench/decision_index/run_smoke.py --out bench/decision_index/runs/<name> [--concurrency 1] [--limit N]

Resumes from an existing results.jsonl; rows with status "error" are retried.
"""

import argparse
import json
import math
import statistics
import time
import urllib.error
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Same request options as the endpoint's reference curl example.
EXTRA = {"output_template": "lines", "prompt_layout": "user_questions", "temperature": 2, "samples": 1, "steps": 1, "think": 0}


def validate(row, response):
    """Apply the kit's rules: every option gets a finite probability, nothing extra."""
    answers = response.get("answers") or {}
    for key, q in row["questions"].items():
        a = answers.get(key)
        if not a or a.get("type") != q["type"]:
            return f"missing or mistyped answer for {key}"
        probs = a.get("probabilities") or {}
        if set(probs) != set(q["criteria"]):
            return f"probability keys differ from criteria for {key}"
        if not all(isinstance(p, (int, float)) and math.isfinite(p) and 0 <= p <= 1 for p in probs.values()):
            return f"invalid probability for {key}"
        if abs(sum(probs.values()) - 1) > 1e-3:
            return f"probabilities for {key} sum to {sum(probs.values()):.4f}"
        if a.get("choice") not in q["criteria"]:
            return f"choice for {key} is not an option"
    return None


def call(url, row, timeout):
    body = json.dumps({"state": row["state"], "questions": row["questions"], **EXTRA}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    out = {"id": row["id"], "benchmark": row["benchmark"], "expected": row["expected"], "started_utc": started}
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = json.loads(r.read())
        out["http_wall_ms"] = (time.perf_counter() - t0) * 1000
        problem = validate(row, raw)
        out.update(status="invalid" if problem else "ok", response=raw)
        if problem:
            out["error"] = problem
    except urllib.error.HTTPError as e:
        out.update(status="error", http_wall_ms=(time.perf_counter() - t0) * 1000, error=f"HTTP {e.code}: {e.read()[:500].decode(errors='replace')}")
    except Exception as e:
        out.update(status="error", http_wall_ms=(time.perf_counter() - t0) * 1000, error=f"{type(e).__name__}: {e}")
    return out


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, math.ceil(len(xs) * p) - 1)] if xs else None


def score(results, rows_by_id):
    by = defaultdict(list)
    for r in results:
        by[r["benchmark"]].append(r)
    report = {}
    for bench, rs in by.items():
        n = len(rs)
        ok = [r for r in rs if r["status"] == "ok"]
        correct, chance, label_mass, off_label = 0, 0.0, [], 0
        for r in rs:
            row = rows_by_id[r["id"]]
            chance += statistics.mean(1 / len(q["criteria"]) for q in row["questions"].values())
            if r["status"] != "ok":
                continue
            for key, gold in r["expected"].items():
                a = r["response"]["answers"][key]
                correct += a["choice"] == gold
                if "label_mass" in a:
                    label_mass.append(a["label_mass"])
                    off_label += a.get("raw_argmax_is_label") is False
        acc, ch = correct / n, chance / n
        lat = [r["http_wall_ms"] for r in ok]
        report[bench] = {
            "requests": n, "ok": len(ok),
            "invalid": sum(r["status"] == "invalid" for r in rs), "errors": sum(r["status"] == "error" for r in rs),
            "accuracy": round(acc, 4), "chance": round(ch, 4), "skill": round(min(1, max(0, (acc - ch) / (1 - ch))), 4),
            "median_label_mass": round(statistics.median(label_mass), 4) if label_mass else None,
            "raw_argmax_off_label": off_label,
            "median_ms": round(statistics.median(lat), 1) if lat else None, "p95_ms": round(pct(lat, 0.95), 1) if lat else None,
        }
    lat = [r["http_wall_ms"] for r in results if r["status"] == "ok"]
    overall = {"requests": len(results), "ok": len(lat), "median_ms": round(statistics.median(lat), 1) if lat else None,
               "mean_ms": round(statistics.mean(lat), 1) if lat else None, "p80_ms": round(pct(lat, 0.8), 1) if lat else None,
               "p95_ms": round(pct(lat, 0.95), 1) if lat else None}
    return {"overall": overall, "benchmarks": report}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://43.107.54.53:31001/v1/systemone")
    ap.add_argument("--rows", default=str(HERE / "smoke-rows.jsonl"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--timeout", type=float, default=120)
    a = ap.parse_args()

    rows = [json.loads(x) for x in Path(a.rows).read_text(encoding="utf-8").splitlines()]
    if a.limit:
        # Round-robin across benchmarks so a small limit still covers each one.
        groups = defaultdict(list)
        for r in rows:
            groups[r["benchmark"]].append(r)
        rows = [g[i] for i in range(max(map(len, groups.values()))) for g in groups.values() if i < len(g)][: a.limit]
    rows_by_id = {r["id"]: r for r in rows}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    res_path = out / "results.jsonl"
    done = {}
    if res_path.exists():
        for line in res_path.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r["status"] != "error":
                done[r["id"]] = r
    todo = [r for r in rows if r["id"] not in done]
    print(f"{len(rows)} rows, {len(done)} done, {len(todo)} to run at concurrency {a.concurrency}", flush=True)

    t0 = time.perf_counter()
    with res_path.open("a", encoding="utf-8") as f, ThreadPoolExecutor(a.concurrency) as pool:
        for i, r in enumerate(pool.map(lambda row: call(a.url, row, a.timeout), todo), 1):
            done[r["id"]] = r
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            if r["status"] != "ok":
                print(f"  {r['id']}: {r['status']}: {r.get('error')}", flush=True)
            if i % 20 == 0:
                print(f"  {i}/{len(todo)}", flush=True)
    wall = time.perf_counter() - t0

    summary = score([done[r["id"]] for r in rows if r["id"] in done], rows_by_id)
    summary["run"] = {"url": a.url, "concurrency": a.concurrency, "request_options": EXTRA, "wall_s_this_pass": round(wall, 1),
                      "throughput_rps_this_pass": round(len(todo) / wall, 2) if todo and wall else None}
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
