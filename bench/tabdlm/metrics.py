"""Score stage: per-cell rates, the no-model floors, metrics.json and summary.md.

Setting A yields divide by the records asked for (1 or 10 per request), so a failed request, a short
array or an invalid record counts against the model. A record is consistent when it passes the schema
and every check: the deterministic ProfileBio checks, or for Amazon the star-summary rule and all
four judge verdicts. It is new when it doesn't copy a few-shot example or repeat a key earlier in
its own batch.
"""
import json, statistics
from collections import Counter

from . import data, tasks
from .run import gen_key, last_rows


def _median(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 2) if xs else None


def _pct(a, b):
    return round(100 * a / b, 1) if b else None


def macro_f1(pairs, labels):
    f1s = []
    for c in labels:
        tp = sum(p == c and g == c for p, g in pairs)
        fp = sum(p == c and g != c for p, g in pairs)
        fn = sum(p != c and g == c for p, g in pairs)
        f1s.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return round(sum(f1s) / len(f1s), 3)


def gen_cell(ds, setting, rows, verdicts):
    per = tasks.N_RECORDS[setting]
    expected = per * len(rows)
    out = {"requests": len(rows), "records_asked": expected,
           "parse_ok": _pct(sum(r["records"] is not None for r in rows), len(rows)),
           "raw_json_ok": _pct(sum(r["raw_json_ok"] for r in rows), len(rows)),
           "truncated": sum(r.get("finish_reason") == "length" for r in rows),
           "errors": sum("error" in r for r in rows)}
    returned = schema_ok = consistent = new_consistent = copies = dups = 0
    fails, keys, ratings, words, claims, openings = Counter(), set(), Counter(), [], [], set()
    for r in rows:
        seen = set()
        for i, rec in enumerate((r["records"] or [])[:per]):
            returned += 1
            bad = tasks.amazon_schema(rec) if ds == "amazon" else tasks.bio_schema(rec)
            if bad:
                fails[f"schema:{bad}"] += 1
                continue
            schema_ok += 1
            if ds == "amazon":
                checks = tasks.amazon_checks(rec)
                v = verdicts.get(("gen",) + gen_key(r) + (i,), {})
                checks.update({k: v.get(k) is True for k in tasks.JUDGE_KEYS})
                checks["judged"] = bool(v) and "error" not in v
                key = tasks.amazon_key(rec)
                ratings[int(rec["rating"])] += 1
                words.append(len(rec["review_text"].split()))
                if isinstance(v.get("specific_claims"), int):
                    claims.append(v["specific_claims"])
            else:
                checks = tasks.bio_checks(rec)
                key = tasks.bio_key(rec)
                openings.add(tasks.bio_opening(rec))
                words.append(len(rec["biography"].split()))
            fails.update(k for k, ok in checks.items() if not ok)
            ok = all(checks.values())
            copy = tasks.copied(ds, rec)
            dup = key in seen
            seen.add(key)
            keys.add(key)
            copies += copy
            dups += dup
            consistent += ok
            new_consistent += ok and not copy and not dup
    out.update(records_returned=returned, schema_valid=schema_ok,
               consistent_yield=_pct(consistent, expected),
               new_consistent_yield=_pct(new_consistent, expected),
               consistent_given_schema=_pct(consistent, schema_ok),
               copies=copies, dups_in_batch=dups, distinct_keys=len(keys),
               failures=dict(fails.most_common()),
               median_words=_median(words),
               median_latency_s=_median([r["latency_s"] for r in rows]),
               median_completion_tokens=_median([r.get("completion_tokens") for r in rows]),
               median_tok_per_s=_median([r["completion_tokens"] / r["latency_s"] for r in rows
                                         if r.get("completion_tokens") and r["latency_s"]]))
    if ds == "amazon":
        out.update(rating_share=dict(sorted(ratings.items())), median_specific_claims=_median(claims))
    else:
        out["distinct_openings"] = len(openings)
    return out


def extract_cell(ds, rows):
    scores = [tasks.score_extract(ds, (r["records"] or [None])[0], r["gold"]) for r in rows]
    fields = list(scores[0]) if scores else []
    out = {"requests": len(rows), "parse_ok": _pct(sum(r["records"] is not None for r in rows), len(rows)),
           "fields": {k: _pct(sum(s[k] for s in scores), len(scores)) for k in fields},
           "median_latency_s": _median([r["latency_s"] for r in rows])}
    if ds == "amazon":
        pairs = [((r["records"] or [{}])[0].get("rating"), r["gold"]["rating"]) for r in rows]
        out["rating_macro_f1"] = macro_f1(pairs, [1, 2, 3, 4, 5])
    else:
        keep = [k for k in fields]
        out["all_fields"] = _pct(sum(all(s[k] for k in keep) for s in scores), len(scores))
    return out


def floors(cfg, verdicts):
    out = {}
    if "amazon" in cfg.datasets:
        for name, recs in (("fewshot", data.amazon_fewshot()), ("real", data.amazon_real(20)),
                           ("bland", tasks.BLAND_AMAZON)):
            vs = [verdicts.get(("floor", name, i), {}) for i in range(len(recs))]
            ok = [tasks.judge_ok(v) and all(tasks.amazon_checks(r).values()) for v, r in zip(vs, recs)]
            out[f"amazon_{name}"] = {"n": len(recs), "consistent": _pct(sum(ok), len(recs)),
                                     "judged": sum(bool(v) and "error" not in v for v in vs),
                                     "median_specific_claims": _median([v.get("specific_claims") for v in vs])}
        gold = [tasks.amazon_label(r) for r in data.amazon_heldout(cfg.n)]
        top = data.amazon_categories()[0]
        majority = [tasks.score_extract("amazon", {"rating": 5, "category": top}, g) for g in gold]
        out["amazon_extract_majority"] = {k: _pct(sum(s[k] for s in majority), len(gold)) for k in majority[0]}
        out["amazon_extract_majority"]["rating_macro_f1"] = macro_f1([(5, g["rating"]) for g in gold], [1, 2, 3, 4, 5])
    if "bio" in cfg.datasets:
        held = data.bio_heldout(cfg.n)
        code = [all(tasks.bio_checks(tasks.bio_code_record(r)).values()) for r in held]
        out["bio_code_template"] = {"n": len(held), "consistent": _pct(sum(code), len(held))}
        rx = [tasks.score_extract("bio", tasks.bio_regex_extract(r["biography"]), r) for r in held]
        out["bio_extract_regex"] = {"all_fields": _pct(sum(all(s.values()) for s in rx), len(held))}
    return out


def score(cfg, run_dir):
    rows = list(last_rows(run_dir / "generations.jsonl", gen_key).values())
    verdicts = {tuple(j["key"]): j["verdict"] for j in last_rows(run_dir / "judgments.jsonl", lambda j: tuple(j["key"])).values()}
    m = {"cells": {}, "floors": floors(cfg, verdicts)}
    for ds in cfg.datasets:
        for s in cfg.settings:
            for arm in cfg.arms:
                cell = [r for r in rows if (r["dataset"], r["setting"], r["arm"]) == (ds, s, arm)]
                if cell:
                    m["cells"][f"{ds}/{s}/{arm}"] = (extract_cell(ds, cell) if s == "extract"
                                                     else gen_cell(ds, s, cell, verdicts))
    (run_dir / "metrics.json").write_text(json.dumps(m, ensure_ascii=False, indent=1))
    (run_dir / "summary.md").write_text(summary(cfg, m))
    print((run_dir / "summary.md").read_text())


def summary(cfg, m):
    temps = ", ".join(f"{a} at {t}" for a, t in cfg.temps)
    lines = [f"# TabDLM consistency smoke", "", f"{cfg.n} requests per cell and arm; {temps}; thinking off.", "",
             "## Setting A: generation", "",
             "| cell | arm | parse ok | bare JSON | records | schema ok | consistent yield | new consistent yield | consistent given schema | copies | batch dups | distinct keys | median words | median latency s | trunc |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, c in m["cells"].items():
        if "/extract/" in k:
            continue
        ds, s, arm = k.split("/")
        lines.append(f"| {ds} {s} | {arm} | {c['parse_ok']} | {c['raw_json_ok']} | {c['records_returned']}/{c['records_asked']} "
                     f"| {c['schema_valid']} | {c['consistent_yield']} | {c['new_consistent_yield']} | {c['consistent_given_schema']} "
                     f"| {c['copies']} | {c['dups_in_batch']} | {c['distinct_keys']} | {c['median_words']} | {c['median_latency_s']} | {c['truncated']} |")
    lines += ["", "Yields are % of records asked for. Failures among schema-valid records:", ""]
    for k, c in m["cells"].items():
        if "/extract/" not in k:
            extra = (f"; ratings {c['rating_share']}; median specific claims {c['median_specific_claims']}"
                     if "rating_share" in c else f"; distinct 5-word openings {c.get('distinct_openings')}")
            lines.append(f"- `{k}`: {c['failures'] or 'none'}{extra}")
    lines += ["", "## Setting B: extraction", "", "| cell | arm | parse ok | field accuracy | extra |", "|---|---|---|---|---|"]
    for k, c in m["cells"].items():
        if "/extract/" in k:
            ds, s, arm = k.split("/")
            extra = f"rating macro-F1 {c['rating_macro_f1']}" if "rating_macro_f1" in c else f"all fields {c['all_fields']}"
            lines.append(f"| {ds} | {arm} | {c['parse_ok']} | {c['fields']} | {extra} |")
    lines += ["", "## Floors (no model)", ""] + [f"- `{k}`: {v}" for k, v in m["floors"].items()]
    return "\n".join(lines) + "\n"
