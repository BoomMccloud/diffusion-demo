"""Builds report/synth_data.json from results/synth.jsonl for the synthetic-data report page."""
import collections, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
rows = [json.loads(l) for l in open(HERE.parent / "results/synth.jsonl")]
norm = lambda x: re.sub(r"\s", "", x)
cells = []
groups = collections.defaultdict(list)
for r in rows:
    groups[(r["arm"], r["temp"])].append(r)
for (arm, temp), rs in sorted(groups.items()):
    valid = sorted((r for r in rs if r["valid"]), key=lambda r: r["t_done"])
    seen, curve = set(), [[0, 0]]
    for r in valid:
        dx = norm(r["record"]["diagnosis"])
        if dx not in seen:
            seen.add(dx)
            curve.append([r["t_done"], len(seen)])
    wall = max(r["t_done"] for r in rs)
    curve.append([wall, len(seen)])
    names = collections.Counter(r["record"]["name"] for r in valid)
    dxs = collections.Counter(norm(r["record"]["diagnosis"]) for r in valid)
    cells.append({
        "arm": arm, "temp": temp, "n": len(rs), "valid": len(valid),
        "distinct_dx": len(seen), "distinct_names": len(names), "wall_s": round(wall, 1),
        "reasons": collections.Counter(r["reason"] for r in rs if not r["valid"]),
        "curve": curve, "top_names": names.most_common(5), "top_dx": dxs.most_common(5),
    })
json.dump({"cells": cells}, open(HERE / "synth_data.json", "w"), ensure_ascii=False)
for c in cells:
    print(c["arm"], c["temp"], c["valid"], c["distinct_dx"], c["distinct_names"], c["wall_s"], c["top_names"][:2])

html = (HERE / "template.html").read_text().replace("__DATA__", json.dumps({"cells": cells}, ensure_ascii=False))
(HERE / "synth_report.html").write_text(html)
