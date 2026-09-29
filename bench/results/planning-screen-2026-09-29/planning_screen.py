#!/usr/bin/env python3
"""Warehouse path-planning screen for the Nemotron runner.

Each case is a grid with shelves (obstacles). The robot must reach the packing
station, and harder levels add a location that must be visited first:

  reach     6x6,  start -> goal
  pickup    8x8,  start -> pickup P -> goal, P off the shortest start-goal route
  key_door  10x10, start -> key K -> door D -> goal; the door is the only way in
            and is locked until the key is picked up

Grids are generated from a fixed seed. Scoring replays the path.

  build   write cases.jsonl (with the hidden grid) for bench/nemotron_runner.py
  score   score runner rows, print a per-arm summary, write scored.jsonl
"""

import argparse
from collections import Counter, defaultdict, deque
import json
from pathlib import Path
import random
import re
import statistics

SEED = 20260929
PER_LEVEL = 20
MAX_NEW_TOKENS = 768
MOVES = ((-1, 0), (1, 0), (0, -1), (0, 1))

PROMPT = """You control a warehouse robot on a grid. Rows and columns are numbered from 0. Row 0 is the top row.

Legend: S = start, G = packing station (goal), # = shelf (cannot enter), . = open floor{legend}
The robot moves one cell per step: up, down, left, or right. No diagonal moves.

Task: {task}

Map (the first line shows column numbers, and each row starts with its row number):
{grid}

Shelves at: {shelves}
Start S at {start}. Goal G at {goal}.{extra}

Answer with one line that starts with PATH: followed by every cell the robot occupies, in order, from S to G, each written as (row,col) and separated by spaces. Do not write anything else.

Example. For this 3x3 map with S at (0,0), G at (2,2), and a shelf at (1,1):
  012
0 S..
1 .#.
2 ..G
the answer is:
PATH: (0,0) (0,1) (0,2) (1,2) (2,2)"""

TASKS = {
    "easy": "Move the robot from S to G using the fewest steps.",
    "reach": "Move the robot from S to G using the fewest steps.",
    "pickup": "Move the robot from S to the pickup shelf P to collect an item, then to G to pack it. Use the fewest steps. The path must pass through P before it reaches G.",
    "key_door": "Move the robot from S to G. G is behind a locked door D, which is the only way in. The key is at K. The robot must step on K before it can step on D. Use the fewest steps.",
}


def neighbors(cell, n):
    r, c = cell
    for dr, dc in MOVES:
        if 0 <= r + dr < n and 0 <= c + dc < n:
            yield (r + dr, c + dc)


def bfs(n, blocked, start, goal):
    """Shortest path length from start to goal avoiding blocked, or None."""
    seen = {start: 0}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        if cell == goal:
            return seen[cell]
        for nxt in neighbors(cell, n):
            if nxt not in blocked and nxt not in seen:
                seen[nxt] = seen[cell] + 1
                queue.append(nxt)
    return None


def fmt(cell):
    return f"({cell[0]},{cell[1]})"


def make_reach(rng):
    n = 6
    while True:
        cells = [(r, c) for r in range(n) for c in range(n)]
        start, goal = rng.sample(cells, 2)
        shelves = {cell for cell in cells if cell not in (start, goal) and rng.random() < 0.22}
        best = bfs(n, shelves, start, goal)
        manhattan = abs(start[0] - goal[0]) + abs(start[1] - goal[1])
        if best and best >= 6 and best > manhattan:  # force at least one detour
            return {"n": n, "start": start, "goal": goal, "shelves": shelves, "optimal": best}


def make_pickup(rng):
    n = 8
    while True:
        cells = [(r, c) for r in range(n) for c in range(n)]
        start, goal, pickup = rng.sample(cells, 3)
        shelves = {cell for cell in cells if cell not in (start, goal, pickup) and rng.random() < 0.2}
        direct = bfs(n, shelves, start, goal)
        leg1, leg2 = bfs(n, shelves | {goal}, start, pickup), bfs(n, shelves, pickup, goal)  # G may not be crossed early
        if direct and leg1 and leg2 and leg1 + leg2 >= direct + 4 and direct >= 5:
            return {"n": n, "start": start, "goal": goal, "shelves": shelves, "pickup": pickup, "optimal": leg1 + leg2}


def make_key_door(rng):
    n = 10
    while True:
        wall_c = rng.randint(5, 7)
        door = (rng.randint(1, n - 2), wall_c)
        wall = {(r, wall_c) for r in range(n)} - {door}
        left = [(r, c) for r in range(n) for c in range(wall_c)]
        right = [(r, c) for r in range(n) for c in range(wall_c + 1, n)]
        start, key = rng.sample(left, 2)
        goal = rng.choice(right)
        shelves = wall | {cell for cell in left + right if cell not in (start, key, goal) and rng.random() < 0.15}
        shelves -= {(door[0], wall_c - 1), (door[0], wall_c + 1)}  # keep the door reachable
        leg1 = bfs(n, shelves | {door}, start, key)
        leg2 = bfs(n, shelves, key, door)
        leg3 = bfs(n, shelves, door, goal)
        direct = bfs(n, shelves, start, door)
        if leg1 and leg2 and leg3 and direct and leg1 + leg2 >= direct + 4:
            return {"n": n, "start": start, "goal": goal, "shelves": shelves, "key": key, "door": door,
                    "optimal": leg1 + leg2 + leg3}


def make_easy(rng):
    n = 5
    while True:
        cells = [(r, c) for r in range(n) for c in range(n)]
        start, goal = rng.sample(cells, 2)
        shelves = set(rng.sample([cell for cell in cells if cell not in (start, goal)], rng.randint(2, 3)))
        best = bfs(n, shelves, start, goal)
        manhattan = abs(start[0] - goal[0]) + abs(start[1] - goal[1])
        if best and 4 <= best <= 8 and manhattan >= 4:
            return {"n": n, "start": start, "goal": goal, "shelves": shelves, "optimal": best}


MAKERS = {"reach": make_reach, "pickup": make_pickup, "key_door": make_key_door, "easy": make_easy}


def render(case):
    n = case["n"]
    marks = {case["start"]: "S", case["goal"]: "G"}
    for name, mark in (("pickup", "P"), ("key", "K"), ("door", "D")):
        if name in case:
            marks[case[name]] = mark
    lines = ["  " + "".join(str(c) for c in range(n))]
    for r in range(n):
        row = "".join(marks.get((r, c), "#" if (r, c) in case["shelves"] else ".") for c in range(n))
        lines.append(f"{r} {row}")
    return "\n".join(lines)


def prompt_for(level, case):
    legend, extra = "", ""
    if level == "pickup":
        legend, extra = ", P = pickup shelf", f" Pickup P at {fmt(case['pickup'])}."
    if level == "key_door":
        legend = ", K = key, D = locked door"
        extra = f" Key K at {fmt(case['key'])}. Door D at {fmt(case['door'])}."
    return PROMPT.format(
        legend=legend, task=TASKS[level], grid=render(case),
        shelves=" ".join(fmt(cell) for cell in sorted(case["shelves"])),
        start=fmt(case["start"]), goal=fmt(case["goal"]), extra=extra,
    )


def to_json(case):
    return {key: sorted(list(cell) for cell in value) if isinstance(value, set)
            else list(value) if isinstance(value, tuple) else value
            for key, value in case.items()}


def cmd_build(args):
    rng = random.Random(SEED)
    with open(args.out, "w") as handle:
        for level in args.levels.split(","):
            make = MAKERS[level]
            for i in range(PER_LEVEL):
                case = make(rng)
                handle.write(json.dumps({
                    "case_id": f"{level}-{i:02d}", "level": level, "prompt": prompt_for(level, case),
                    "max_new_tokens": MAX_NEW_TOKENS, "grid": to_json(case),
                }) + "\n")


def replay(grid, output):
    """Return (valid, reason, steps). Steps counts moves in the proposed path."""
    match = re.search(r"PATH:(.*)", output)
    if not match:
        return False, "no_path_line", None
    path = [tuple(map(int, m)) for m in re.findall(r"\((\d+)\s*,\s*(\d+)\)", match.group(1))]
    if not path:
        return False, "no_cells", None
    n = grid["n"]
    shelves = {tuple(cell) for cell in grid["shelves"]}
    start, goal = tuple(grid["start"]), tuple(grid["goal"])
    must_visit = tuple(grid.get("pickup") or grid.get("key") or ()) or None
    door = tuple(grid["door"]) if "door" in grid else None
    steps = len(path) - 1
    if path[0] != start:
        return False, "wrong_start", steps
    visited = False
    for i, cell in enumerate(path):
        if i and abs(cell[0] - path[i - 1][0]) + abs(cell[1] - path[i - 1][1]) != 1:
            return False, "not_adjacent", steps
        if not (0 <= cell[0] < n and 0 <= cell[1] < n):
            return False, "out_of_bounds", steps
        if cell in shelves:
            return False, "hit_shelf", steps
        if cell == must_visit:
            visited = True
        if door and cell == door and not visited:
            return False, "door_before_key", steps
        if cell == goal:
            if must_visit and not visited:
                return False, "goal_before_visit", steps
            if i != len(path) - 1:
                return False, "continued_past_goal", steps
    if path[-1] != goal:
        return False, "did_not_reach_goal", steps
    return True, None, steps


def diagnostics(grid, output):
    """Partial credit that keeps scanning past the first violation."""
    match = re.search(r"PATH:(.*)", output)
    path = [tuple(map(int, m)) for m in re.findall(r"\((\d+)\s*,\s*(\d+)\)", match.group(1))] if match else []
    shelves = {tuple(cell) for cell in grid["shelves"]}
    start, goal = tuple(grid["start"]), tuple(grid["goal"])
    bad = [i for i, cell in enumerate(path)
           if cell in shelves or not (0 <= cell[0] < grid["n"] and 0 <= cell[1] < grid["n"])
           or (i and abs(cell[0] - path[i - 1][0]) + abs(cell[1] - path[i - 1][1]) != 1)]
    return {
        "cells": len(path),
        "starts_ok": bool(path) and path[0] == start,
        "ends_at_goal": bool(path) and path[-1] == goal,
        "all_moves_single_step": all(abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1 for a, b in zip(path, path[1:])),
        "shelf_hits": sum(cell in shelves for cell in path),
        "clean_prefix": (bad[0] if bad else len(path)) if path and path[0] == start else 0,
    }


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def cmd_score(args):
    cases = {case["case_id"]: case for case in read_jsonl(args.cases)}
    by_arm = defaultdict(list)
    with open(args.scored, "w") as handle:
        for row in read_jsonl(args.rows):
            case = cases[row["case_id"]]
            valid, reason, steps = (False, "runner_error", None) if row["error"] else replay(case["grid"], row["final_output"])
            scored = {**{k: row[k] for k in ("arm", "case_id", "output_tokens", "nfe", "elapsed_seconds", "stop_reason", "final_output")},
                      "level": case["level"], "valid": valid, "optimal": valid and steps == case["grid"]["optimal"],
                      "reason": reason, "steps": steps, "optimal_steps": case["grid"]["optimal"],
                      **diagnostics(case["grid"], "" if row["error"] else row["final_output"])}
            handle.write(json.dumps(scored) + "\n")
            by_arm[row["arm"]].append(scored)
    for arm, rows in by_arm.items():
        levels = defaultdict(list)
        for row in rows:
            levels[row["level"]].append(row)
        print(json.dumps({
            "arm": arm, "n": len(rows), "valid": sum(r["valid"] for r in rows), "optimal": sum(r["optimal"] for r in rows),
            "by_level": {k: f"{sum(r['valid'] for r in v)} valid, {sum(r['optimal'] for r in v)} optimal / {len(v)}" for k, v in levels.items()},
            "failures": dict(Counter(r["reason"] for r in rows if r["reason"])),
            "ends_at_goal": sum(r["ends_at_goal"] for r in rows),
            "all_moves_single_step": sum(r["all_moves_single_step"] for r in rows),
            "mean_shelf_hits": round(statistics.mean(r["shelf_hits"] for r in rows), 2),
            "mean_clean_prefix_over_optimal": round(statistics.mean(min(r["clean_prefix"] / (r["optimal_steps"] + 1), 1) for r in rows), 3),
            "median_s": round(statistics.median(r["elapsed_seconds"] for r in rows), 3),
            "total_s": round(sum(r["elapsed_seconds"] for r in rows), 1),
            "median_output_tokens": statistics.median(r["output_tokens"] for r in rows),
            "hit_cap": sum(r["stop_reason"] == "max_new_tokens" for r in rows),
        }))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("build")
    p.add_argument("--out", required=True)
    p.add_argument("--levels", default="reach,pickup,key_door")
    p.set_defaults(func=cmd_build)
    p = sub.add_parser("score")
    p.add_argument("rows")
    p.add_argument("--cases", required=True)
    p.add_argument("--scored", required=True)
    p.set_defaults(func=cmd_score)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
