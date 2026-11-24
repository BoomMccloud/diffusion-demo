"""Side-by-side race video for one WebArena task: diffusion model vs. autoregressive model.

Reads a take folder written by the race runs (see run_race.sh):
    <dir>/diffusion.webm, <dir>/qwen.webm, <dir>/timings.json
timings.json holds export_timings.py's output for each arm under "diffusion" and "qwen".

Both recordings start when the task's first observation is ready (after
WebArena's own setup, such as logging in) and play at the same speed-up. A side
that finishes freezes on its last frame with its result while the other keeps
playing. Each side shows a real-time clock, a model-time clock, and a strip
that marks model time and page time step by step.

Usage:
    python3 bench/webarena/make_webarena_race.py bench/webarena/recordings/20261019/224
"""
import argparse
import json
import math
import os
import subprocess
import sys
import textwrap
from datetime import datetime

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "miniwob"))
from make_race_video import BG, DIM, FG, FPS, GREEN, H, RED, SIDES, SYMBOLS, W, YELLOW, font  # noqa: E402

ARMS = [("diffusion", SIDES[0][1], SIDES[0][2], "Diffusion language model"),
        ("qwen", SIDES[1][1], SIDES[1][2], "Autoregressive language model")]
PANEL_X, PANEL_W = (40, 980), 900
VID_Y, VID_H = 250, 506  # 1280x720 viewport scaled to 900 wide
STRIP_Y, STRIP_H = 790, 26
TILE_BG = (36, 39, 46)
PAGE = (95, 100, 112)
RACE_TARGET = 24.0  # race seconds the slower side should take
INTRO_SEC, OUTRO_SEC, END_HOLD = 3.0, 5.0, 1.5
SITES = {"224": "OpenStreetMap", "767": "OpenStreetMap", "742": "GitLab", "580": "Reddit-style forum"}


def nice_speed(x):
    """Smallest of 1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12.5, 15, 20, ... at or above x."""
    steps = [1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 8]
    mag = 1
    while True:
        for s in steps:
            if s * mag >= x - 1e-9:
                return s * mag
        mag *= 10


def arm_timeline(t):
    """Real-time segments relative to the race start (first observation ready).

    Step k's model segment picks action k+1 (1-based); env step k+1 then runs
    it, so both carry the same step number. The race ends when the last action
    has run. The final env step also runs WebArena's evaluator, which is left out.
    """
    steps = t["steps"]
    t0 = steps[0]["env_stop"]
    segs = []  # (kind, start, end, step number)
    for s in steps:
        if s["step"] > 0 and s["env_start"] and s["env_stop"]:
            last = s is steps[-1]
            stop = s["action_exec_stop"] if last else s["env_stop"]
            segs.append(("page", s["env_start"] - t0, stop - t0, s["step"]))
        if s["agent_start"] and s["agent_stop"]:
            segs.append(("model", s["agent_start"] - t0, s["agent_stop"] - t0, s["step"] + 1))
    end = max(e for _, _, e, _ in segs)
    model = sum(e - b for k, b, e, _ in segs if k == "model")
    page = sum(e - b for k, b, e, _ in segs if k == "page")
    calls = [c for c in t["llm_calls"] if "error" not in c]
    errors = [c for c in t["llm_calls"] if "error" in c]
    sm = t["summary"]
    return {"t0": t0, "offset": t0 - t["video_t0"], "segs": segs, "total": end, "model": model,
            "page": page, "steps": sum(1 for s in steps if s["agent_start"]),
            "passed": (sm.get("cum_reward") or 0) > 0, "err": sm.get("err_msg"),
            "truncated": bool(sm.get("truncated")),
            "calls": calls, "errors": errors,
            "out_tokens": sum((c.get("usage") or {}).get("completion_tokens") or 0 for c in calls)}


def clocks_at(tl, tr):
    model = page = 0.0
    phase, step = "model", 1
    for kind, b, e, n in tl["segs"]:
        if tr >= b:
            dur = min(tr, e) - b
            if kind == "model":
                model += dur
            else:
                page += dur
            if tr < e:
                phase, step = kind, n
    return model, page, phase, step


def build_clip(path, offset, total, speed, length, out):
    """Trim one recording to the race, speed it up, scale it, and hold its last frame."""
    vf = (f"trim={offset:.3f}:{offset + total:.3f},setpts=(PTS-STARTPTS)/{speed},fps={FPS},"
          f"scale={PANEL_W}:{VID_H}:flags=lanczos,setsar=1,tpad=stop_mode=clone:stop_duration={length}")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", path, "-vf", vf, "-t", f"{length:.3f}",
                    "-r", str(FPS), "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", out], check=True)


class Reader:
    def __init__(self, path):
        self.proc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "rawvideo",
                                      "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.last = Image.new("RGB", (PANEL_W, VID_H), TILE_BG)

    def next(self):
        buf = self.proc.stdout.read(PANEL_W * VID_H * 3)
        if len(buf) == PANEL_W * VID_H * 3:
            self.last = Image.frombytes("RGB", (PANEL_W, VID_H), buf)
        return self.last


def wrap_lines(text, width):
    return [l for para in text.split("\n") for l in (textwrap.wrap(para, width) or [""])]


def draw_intro(d, goal, task, site, take_no=""):
    take = f"  ·  take {take_no}" if take_no else ""
    d.text((W // 2, 120), f"WebArena task {task}{take}  ·  {site}", font=font(40), fill=DIM, anchor="mm")
    lines = wrap_lines(f"“{goal}”", 52)
    for k, line in enumerate(lines[:4]):
        d.text((W // 2, 230 + k * 70), line, font=font(54, True), fill=FG, anchor="mm")
    for (arm, label, color, kind), x0 in zip(ARMS, PANEL_X):
        d.rounded_rectangle((x0, 600, x0 + PANEL_W, 900), radius=18, fill=TILE_BG)
        d.text((x0 + PANEL_W // 2, 710), label, font=font(68, True), fill=color, anchor="mm")
        d.text((x0 + PANEL_W // 2, 805), kind, font=font(38), fill=FG, anchor="mm")
    note = (f"Same agent, prompt, tools and browser. Take {take_no}: one fresh run per model." if take_no
            else "Same agent, prompt, tools and browser. One run each, no retakes.")
    d.text((W // 2, 990), note, font=font(30), fill=DIM, anchor="mm")


def draw_side(img, d, arm, label, color, x0, tl, frame, tv, speed, span):
    tr = tv * speed
    done = tr >= tl["total"]
    t = min(tr, tl["total"])
    model, page, phase, step = clocks_at(tl, t)
    d.text((x0, 200), label, font=font(46, True), fill=color, anchor="lm")
    d.text((x0 + PANEL_W, 200), f"{t:5.1f} s", font=font(46, True),
           fill=(GREEN if tl["passed"] else RED) if done else FG, anchor="rm")
    img.paste(frame, (x0, VID_Y))
    # Strip: each step's model time in the side's color, page time in gray, drawn as time passes.
    # Both strips share one scale, the slower side's total, so their lengths compare.
    scale = PANEL_W / span
    d.rectangle((x0, STRIP_Y, x0 + PANEL_W, STRIP_Y + STRIP_H), fill=TILE_BG)
    for kind, b, e, _ in tl["segs"]:
        if b < t:
            d.rectangle((x0 + b * scale, STRIP_Y, x0 + min(e, t) * scale, STRIP_Y + STRIP_H),
                        fill=color if kind == "model" else PAGE)
    rows = [("Real time", f"{t:.1f} s", FG), ("Model time", f"{model:.1f} s", color),
            ("Page time", f"{page:.1f} s", (170, 175, 185))]
    for k, (name, value, col) in enumerate(rows):
        y = 860 + k * 52
        d.text((x0, y), name, font=font(34), fill=DIM, anchor="lm")
        d.text((x0 + 330, y), value, font=font(38, True), fill=col, anchor="rm")
    if done:
        ok = tl["passed"]
        status = (f"Stopped at the {tl['steps']}-step limit, failed" if tl["truncated"]
                  else f"Finished in {tl['steps']} steps, {'passed' if ok else 'failed'}")
        d.text((x0 + 420, 912), status, font=font(34, True), fill=GREEN if ok else RED, anchor="lm")
        badge = Image.new("RGBA", (PANEL_W, VID_H), (*BG, 110))
        img.paste(badge, (x0, VID_Y), badge)
        d.text((x0 + PANEL_W // 2, VID_Y + VID_H // 2), "✓" if ok else "✗",
               font=SYMBOLS.font_variant(size=160), fill=GREEN if ok else RED, anchor="mm")
        d.text((x0 + PANEL_W // 2, VID_Y + VID_H // 2 + 120), f"{tl['total']:.1f} s",
               font=font(60, True), fill=FG, anchor="mm")
    else:
        if phase == "model":
            what, col = f"Step {step}: model thinking", color
        else:
            what, col = f"Step {step}: browser acting", (200, 204, 212)
        d.text((x0 + 420, 912), what, font=font(34, True), fill=col, anchor="lm")


def draw_outro(d, tls, task):
    diff, ar = tls["diffusion"], tls["qwen"]
    if diff["passed"] and ar["passed"]:
        head = f"Both passed. {SIDES[0][1]} finished {ar['total'] / diff['total']:.1f}x faster"
    else:
        head = f"Task {task} results"
    d.text((W // 2, 110), head, font=font(60, True), fill=FG, anchor="mm")
    for (arm, label, color, kind), x0 in zip(ARMS, PANEL_X):
        tl = tls[arm]
        d.rounded_rectangle((x0, 200, x0 + PANEL_W, 900), radius=18, fill=TILE_BG)
        d.text((x0 + PANEL_W // 2, 270), label, font=font(52, True), fill=color, anchor="mm")
        d.text((x0 + PANEL_W // 2, 330), kind, font=font(32), fill=DIM, anchor="mm")
        ok = tl["passed"]
        d.text((x0 + PANEL_W // 2, 440), "Passed" if ok else "Failed", font=font(84, True),
               fill=GREEN if ok else RED, anchor="mm")
        if not ok:
            why = "hit the 30-step limit" if tl["truncated"] else ("run error" if tl["err"] else "wrong result")
            d.text((x0 + PANEL_W // 2, 500), why, font=font(30), fill=DIM, anchor="mm")
        rows = [("Total time", f"{tl['total']:.1f} s"), ("Model time", f"{tl['model']:.1f} s"),
                ("Page time", f"{tl['page']:.1f} s"), ("Steps", f"{tl['steps']}"),
                ("Model time per step", f"{tl['model'] / max(tl['steps'], 1):.2f} s"),
                ("Output tokens", f"{tl['out_tokens']:,}")]
        for k, (name, value) in enumerate(rows):
            y = 550 + k * 56
            d.text((x0 + 60, y), name, font=font(34), fill=DIM, anchor="lm")
            d.text((x0 + PANEL_W - 60, y), value, font=font(34, True), fill=FG, anchor="rm")
    d.text((W // 2, 960), "Pass or fail is WebArena's own evaluator. Model time is the agent's model calls; "
           "page time is the browser executing actions and loading pages.", font=font(26), fill=DIM, anchor="mm")
    d.text((W // 2, 1005), "Qwen 3.6 Flash via Alibaba's hosted API with thinking on. Both models ran the "
           "same AgentLab GenericAgent.", font=font(26), fill=DIM, anchor="mm")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("take_dir")
    p.add_argument("--speed", type=float, help="playback speed for both sides (default: fit ~24 s)")
    p.add_argument("--out", help="default <take_dir>/race.mp4")
    args = p.parse_args()
    take = os.path.abspath(args.take_dir)
    # A retake lives in <task>-take<N>/.
    task, _, take_no = os.path.basename(take).partition("-take")
    timings = json.load(open(os.path.join(take, "timings.json")))
    tls = {arm: arm_timeline(timings[arm]) for arm, *_ in ARMS}
    slow = max(tl["total"] for tl in tls.values())
    speed = args.speed or nice_speed(slow / RACE_TARGET)
    length = slow / speed + END_HOLD
    goal = timings["diffusion"].get("goal") or timings["qwen"].get("goal") or ""
    when = datetime.fromtimestamp(tls["diffusion"]["t0"])
    when = f"{when:%B} {when.day}, {when.year}"

    readers, tmps = {}, []
    for arm, label, *_ in ARMS:
        tmp = os.path.join(take, f".clip_{arm}.mp4")
        build_clip(os.path.join(take, f"{arm}.webm"), tls[arm]["offset"], tls[arm]["total"], speed, length, tmp)
        readers[arm] = Reader(tmp)
        tmps.append(tmp)
        tl = tls[arm]
        print(f"{label}: {tl['total']:.1f} s total, {tl['model']:.1f} s model, {tl['page']:.1f} s page, "
              f"{tl['steps']} steps, {'pass' if tl['passed'] else 'fail'}, {len(tl['errors'])} call errors")
    print(f"speed {speed:g}x, race {length:.1f} s")

    out = args.out or os.path.join(take, "race.mp4")
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18",
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    intro = Image.new("RGB", (W, H), BG)
    draw_intro(ImageDraw.Draw(intro), goal, task, SITES.get(task, "WebArena"), take_no)
    for _ in range(int(INTRO_SEC * FPS)):
        ff.stdin.write(intro.tobytes())
    head = textwrap.shorten(f"“{goal}”", 95, placeholder="…”")
    for k in range(math.ceil(length * FPS)):
        tv = k / FPS
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        d.text((W // 2, 50), head, font=font(38, True), fill=FG, anchor="mm")
        d.text((W // 2, 108), f"WebArena task {task}{f', take {take_no}' if take_no else ''}  ·  playback {speed:g}x for both sides  ·  "
               f"recorded {when}", font=font(28), fill=YELLOW, anchor="mm")
        for (arm, label, color, _), x0 in zip(ARMS, PANEL_X):
            draw_side(img, d, arm, label, color, x0, tls[arm], readers[arm].next(), tv, speed, slow)
        ff.stdin.write(img.tobytes())
    outro = Image.new("RGB", (W, H), BG)
    draw_outro(ImageDraw.Draw(outro), tls, task)
    for _ in range(int(OUTRO_SEC * FPS)):
        ff.stdin.write(outro.tobytes())
    ff.stdin.close()
    ff.wait()
    for r in readers.values():
        r.proc.kill()
    for tmp in tmps:
        os.remove(tmp)
    print(out)


if __name__ == "__main__":
    main()
