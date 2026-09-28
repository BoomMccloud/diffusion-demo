#!/usr/bin/env python3
"""POC A/B: run selected business fixtures through one resident worker and save one JSON per case.

The worker's DIFFUSION_INCREMENTAL_PREFILL setting decides the arm; this script only labels it.
Not a registered benchmark run: rows here must not be merged with business-screen evidence.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import business_benchmark as bench  # noqa: E402
import business_fixtures as fixtures  # noqa: E402
import diffusion_runtime as runtime  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", default="http://127.0.0.1:8765")
    p.add_argument("--arm", required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--timeout", type=float, default=600)
    p.add_argument("cases", nargs="+")
    args = p.parse_args()
    by_id = {f["case_id"]: f for f in fixtures.build_manifest()["fixtures"]}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    status = runtime.rpc(args.url, "/status")
    runtime.atomic_json(args.output_dir / f"{args.arm}-status.json", status)
    # Load the model outside the timed cases.
    warmup_id = f"ab-{args.arm}-warmup"
    runtime.rpc(args.url, "/generate", {"request_id": warmup_id, "timeout_seconds": args.timeout,
                                        "prompt": 'Return exactly {"values":["READY"]} and no other text.'})
    runtime.atomic_json(args.output_dir / f"{args.arm}-warmup.json",
                        runtime.wait_result(args.url, warmup_id, args.timeout + 60))
    for case_id in args.cases:
        target = args.output_dir / f"{args.arm}-{case_id}.json"
        if target.exists():
            continue
        fixture = by_id[case_id]
        rid = f"ab-{args.arm}-{case_id}"
        started = time.perf_counter()
        runtime.rpc(args.url, "/generate", {"request_id": rid, "prompt": fixture["prompt"],
                                            "timeout_seconds": args.timeout})
        result = runtime.wait_result(args.url, rid, args.timeout + 60)
        wall = time.perf_counter() - started
        raw = result.get("raw_output", "")
        final = raw.split("<channel|>", 1)[1] if "<channel|>" in raw else ""
        try:
            score = fixtures.evaluate_answer(fixture, bench.parse_canonical_answer(final.strip()))
        except Exception as error:  # an unparseable answer is an observation, not a failure
            score = {"valid": False, "error": repr(error)}
        events = result.get("native_events") or result.get("events") or []
        prefill = sum(e.get("duration_seconds", 0) for e in events if e.get("event") == "prefill_end")
        denoise = sum(e.get("duration_seconds", 0) for e in events if e.get("event") == "denoise_end")
        stops = [e.get("reason") for e in events if e.get("event") == "stop"]
        row = {"arm": args.arm, "case_id": case_id, "client_wall_seconds": wall, "prefill_seconds": prefill,
               "denoise_seconds": denoise, "blocks": sum(e.get("event") == "block_start" for e in events),
               "reused_tokens": [e.get("reused_tokens") for e in events if e.get("event") == "prefill_start"],
               "native_stop": stops[-1] if stops else None, "valid": bool(score.get("valid")), "score": score,
               "result": result}
        runtime.atomic_json(target, row)
        print(json.dumps({k: row[k] for k in ("arm", "case_id", "client_wall_seconds", "prefill_seconds",
                                               "denoise_seconds", "blocks", "native_stop", "valid")}), flush=True)


if __name__ == "__main__":
    main()
