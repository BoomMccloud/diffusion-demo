#!/usr/bin/env python3
"""Sudoku race: the hosted dLLM against Qwen3.6 AR on the same puzzles.

Both arms stream, so every chunk is timestamped for a side-by-side replay.
Standard library only. Load .env.local first.

    python3 experiments/sudoku/sudoku.py puzzles
    python3 experiments/sudoku/sudoku.py run --run smoke --limit 2 --thinking off
    python3 experiments/sudoku/sudoku.py summarize --run smoke
"""

from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
import threading
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
PUZZLES = HERE / "puzzles.json"

ARMS = {
    "dllm": {
        # The latest checkpoint is served on port 31004 of the DIFFUSION_BASE_URL host
        # (31005 serves the same weights with radix cache on). Override with DLLM_PORT.
        # Its model id is read from /v1/models at startup.
        "model": None,
        "url": lambda: dllm_url(),
        "key": lambda: "none",
        # The server defaults to presence 0.9 and repetition 1.05. --penalties neutral turns them off,
        # but on 2026-10-21 that let the model loop until the token cap.
        "extra": lambda thinking: {"chat_template_kwargs": {"enable_thinking": thinking},
                                   **NEUTRAL_PENALTIES},
    },
    "qwen": {
        "model": "qwen/qwen3.6-35b-a3b",
        "url": lambda: "https://openrouter.ai/api/v1/chat/completions",
        "key": lambda: os.environ["OPENROUTER_API_KEY"],
        "extra": lambda thinking: {"reasoning": {"enabled": thinking}},
    },
}

NEUTRAL_PENALTIES = {}


def dllm_url():
    if os.environ.get("DLLM_URL"):
        return os.environ["DLLM_URL"]
    u = urllib.parse.urlsplit(os.environ["DIFFUSION_BASE_URL"])
    return f"{u.scheme}://{u.hostname}:{os.environ.get('DLLM_PORT', '31004')}/v1/chat/completions"


def resolve_dllm_model():
    url = dllm_url().removesuffix("/chat/completions") + "/models"
    ARMS["dllm"]["model"] = json.load(urllib.request.urlopen(url, timeout=30))["data"][0]["id"]
    print(f"dllm: {ARMS['dllm']['model']} at {dllm_url()}")


# Clue counts: easy, medium, hard. Every puzzle has exactly one solution.
LEVELS = {"easy": 40, "medium": 32, "hard": 26}
PER_LEVEL = 4

PROMPT = """Solve this sudoku. Empty cells are shown as dots.

{grid}

Reply with only the solved grid: 9 lines of 9 digits, no spaces, no other text."""


# Puzzles --------------------------------------------------------------------


def candidates(g, i):
    r, c = divmod(i, 9)
    used = set(g[r * 9:r * 9 + 9]) | set(g[c::9])
    br, bc = r // 3 * 3, c // 3 * 3
    used |= {g[(br + y) * 9 + bc + x] for y in range(3) for x in range(3)}
    return [d for d in range(1, 10) if d not in used]


def count_solutions(g, limit=2):
    try:
        i = g.index(0)
    except ValueError:
        return 1
    n = 0
    for d in candidates(g, i):
        g[i] = d
        n += count_solutions(g, limit - n)
        g[i] = 0
        if n >= limit:
            break
    return n


def full_grid(rng):
    g = [0] * 81

    def fill(i=0):
        if i == 81:
            return True
        ds = candidates(g, i)
        rng.shuffle(ds)
        for d in ds:
            g[i] = d
            if fill(i + 1):
                return True
        g[i] = 0
        return False

    fill()
    return g


def make_puzzle(rng, clues):
    while True:
        sol = full_grid(rng)
        g = sol[:]
        for i in rng.sample(range(81), 81):
            keep = g[i]
            g[i] = 0
            if count_solutions(g[:]) != 1:
                g[i] = keep
            if sum(1 for v in g if v) == clues:
                return g, sol


def show(g):
    return "\n".join("".join(str(v) if v else "." for v in g[r * 9:r * 9 + 9]) for r in range(9))


def cmd_puzzles(_):
    rng = random.Random(20261020)
    out = []
    for level, clues in LEVELS.items():
        for k in range(PER_LEVEL):
            g, sol = make_puzzle(rng, clues)
            out.append({"id": f"{level}-{k + 1}", "level": level, "clues": clues,
                        "puzzle": show(g), "solution": show(sol)})
    PUZZLES.write_text(json.dumps(out, indent=1))
    print(f"wrote {len(out)} puzzles to {PUZZLES}")


# Scoring --------------------------------------------------------------------


def parse_grid(text):
    rows = [ln.strip().replace(" ", "").replace("|", "") for ln in text.strip().splitlines()]
    rows = [r for r in rows if r and all(ch.isdigit() for ch in r)]
    if len(rows) != 9 or any(len(r) != 9 for r in rows):
        return None
    return "\n".join(rows)


def score(case, text):
    grid = parse_grid(text)
    if grid is None:
        return {"parsed": False, "solved": False, "givens_kept": False, "cells_correct": 0}
    flat, sol, puz = grid.replace("\n", ""), case["solution"].replace("\n", ""), case["puzzle"].replace("\n", "")
    blanks = [i for i, ch in enumerate(puz) if ch == "."]
    return {
        "parsed": True,
        "solved": flat == sol,
        "givens_kept": all(flat[i] == ch for i, ch in enumerate(puz) if ch != "."),
        "cells_correct": sum(flat[i] == sol[i] for i in blanks),
    }


# Requests -------------------------------------------------------------------


def stream(arm, prompt, thinking, max_tokens):
    a = ARMS[arm]
    body = {"model": a["model"], "messages": [{"role": "user", "content": prompt}],
            "temperature": 0, "max_tokens": max_tokens, "stream": True,
            "stream_options": {"include_usage": True}, **a["extra"](thinking)}
    req = urllib.request.Request(a["url"](), data=json.dumps(body).encode(), headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {a['key']()}"})
    t0 = time.monotonic()
    chunks, content, reasoning, usage, finish = [], "", "", None, None
    with urllib.request.urlopen(req, timeout=1800) as resp:
        for raw in resp:
            line = raw.decode().strip()
            if not line.startswith("data:") or line == "data: [DONE]":
                continue
            ev = json.loads(line[5:])
            usage = ev.get("usage") or usage
            for ch in ev.get("choices", []):
                d = ch.get("delta", {})
                c, r = d.get("content") or "", d.get("reasoning_content") or d.get("reasoning") or ""
                if c or r:
                    chunks.append([round(time.monotonic() - t0, 4), c, r])
                content += c
                reasoning += r
                finish = ch.get("finish_reason") or finish
    return {"content": content, "reasoning": reasoning, "chunks": chunks, "usage": usage,
            "finish_reason": finish, "elapsed": round(time.monotonic() - t0, 3)}


def cmd_run(args):
    cases = json.loads(PUZZLES.read_text())
    cases = [c for c in cases if c["level"] in args.levels]
    if args.limit:
        cases = [c for lvl in LEVELS for c in [x for x in cases if x["level"] == lvl][:args.limit]]
    thinking = args.thinking == "on"
    if args.penalties == "neutral":
        NEUTRAL_PENALTIES.update(presence_penalty=0, repetition_penalty=1)
    if "dllm" in args.arms:
        resolve_dllm_model()
    out = RESULTS / args.run / f"thinking-{args.thinking}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        done = {(r["id"], r["arm"]) for r in map(json.loads, out.open())}
    lock = threading.Lock()

    def one(case, arm):
        try:
            res = stream(arm, PROMPT.format(grid=case["puzzle"]), thinking, args.max_tokens)
            row = {"id": case["id"], "level": case["level"], "arm": arm, "thinking": thinking,
                   "model": ARMS[arm]["model"], "penalties": args.penalties if arm == "dllm" else None, **res, **score(case, res["content"])}
        except Exception as e:
            row = {"id": case["id"], "level": case["level"], "arm": arm, "thinking": thinking,
                   "error": repr(e)[:300]}
        with lock, out.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"{case['id']:9} {arm:5} solved={row.get('solved')} cells={row.get('cells_correct')}"
              f" t={row.get('elapsed')}s {row.get('error', '')}", flush=True)

    # Each arm runs its cases one at a time, so latency is batch 1. The two arms race in parallel.
    def arm_loop(arm):
        for c in cases:
            if (c["id"], arm) not in done:
                one(c, arm)

    with ThreadPoolExecutor(2) as ex:
        list(ex.map(arm_loop, args.arms))


def cmd_summarize(args):
    for f in sorted((RESULTS / args.run).glob("*.jsonl")):
        rows = [json.loads(l) for l in f.open()]
        print(f"\n{f.name}")
        print(f"{'arm':5} {'level':7} {'n':>2} {'solved':>6} {'givens':>6} {'cells%':>6} {'med s':>6} {'med tok':>7}")
        for arm in ARMS:
            for lvl in [*LEVELS, "all"]:
                rs = [r for r in rows if r["arm"] == arm and (lvl == "all" or r["level"] == lvl) and "error" not in r]
                if not rs:
                    continue
                cases = {c["id"]: c for c in json.loads(PUZZLES.read_text())}
                blanks = sum(cases[r["id"]]["puzzle"].count(".") for r in rs)
                toks = [(r.get("usage") or {}).get("completion_tokens") or 0 for r in rs]
                print(f"{arm:5} {lvl:7} {len(rs):2} {sum(r['solved'] for r in rs):6} "
                      f"{sum(r['givens_kept'] for r in rs):6} {100 * sum(r['cells_correct'] for r in rs) / blanks:6.1f} "
                      f"{statistics.median(r['elapsed'] for r in rs):6.2f} {statistics.median(toks):7.0f}")
        errs = [r for r in rows if "error" in r]
        if errs:
            print(f"errors: {len(errs)}: {errs[0]['error']}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("puzzles")
    r = sub.add_parser("run")
    r.add_argument("--run", required=True)
    r.add_argument("--thinking", choices=["off", "on"], default="off")
    r.add_argument("--limit", type=int, default=0, help="cases per level")
    r.add_argument("--max-tokens", type=int, default=512)
    r.add_argument("--levels", nargs="+", choices=list(LEVELS), default=list(LEVELS))
    r.add_argument("--arms", nargs="+", choices=list(ARMS), default=list(ARMS))
    r.add_argument("--penalties", choices=["server", "neutral"], default="server",
                   help="dLLM sampling penalties: the server defaults, or none")
    s = sub.add_parser("summarize")
    s.add_argument("--run", required=True)
    args = p.parse_args()
    {"puzzles": cmd_puzzles, "run": cmd_run, "summarize": cmd_summarize}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
