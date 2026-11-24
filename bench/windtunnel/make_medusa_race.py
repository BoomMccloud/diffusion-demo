"""Race video for WindTunnel md-8 on the Medusa storefront: DiffuSpace Clover vs. Gemini 3.6 Flash,
or vs. Qwen 3.6 Flash with --opponent qwen.

Reads a recording directory written by `cli.mjs --record-video` (timings.json
plus one .webm per arm, renamed clover.webm and gemini.webm or qwen.webm) and draws, in the
style of bench/miniwob/make_race_grid_video.py: an intro card with the task,
both recorded pages side by side in real time from each agent's first model
call, a live clock and the WebMCP tool calls per side, then an outro card with
the measured numbers and the earlier 3-run medians.

The clock starts at each side's first model call and stops at the harness's
own agent_s. After a side finishes, its recording keeps playing until the
harness closes the page (it stays open while the harness scores the attempt),
because the store navigates to the order confirmation about 150 ms after
complete_checkout returns and takes a second or two to render it. The page
then freezes on its last recorded frame.

The Qwen take runs the same wm-claude arm against DashScope's Anthropic-compatible
endpoint, so its timings.json entry must have its arm renamed to wm-qwen.

Usage:
    python3 bench/windtunnel/make_medusa_race.py bench/windtunnel/recordings/20261019/md-8
    python3 bench/windtunnel/make_medusa_race.py bench/windtunnel/recordings/20261021/md-8-qwen --opponent qwen
"""
import argparse
import csv
import json
import os
import statistics
import subprocess
import sys
import textwrap

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "miniwob"))
from make_race_grid_video import GEMINI, MONO, TILE_BG  # noqa: E402
from make_race_video import BG, DIM, FG, FPS, GREEN, H, RED, SYMBOLS, W, YELLOW, font  # noqa: E402

CLOVER = ("wm-claude", "clover", "DiffuSpace Clover", "Diffusion language model", (110, 200, 255))
OPPONENTS = {"gemini": ("wm-gemini", "gemini", "Gemini 3.6 Flash", "Autoregressive language model", GEMINI),
             "qwen": ("wm-qwen", "qwen", "Qwen 3.6 Flash", "Autoregressive language model", (255, 170, 90))}
SIDES = [CLOVER, OPPONENTS["gemini"]]  # main() swaps the opponent
EARLIER = os.path.join(HERE, "results-diffuspace", "2026-10-15-fill-dir-medusa-qwen36-vs-gemini", "results.csv")
TASK_ID = "md-8"

COL_X, COL_W = (40, 980), 900
SRC_W, SRC_H = 1280, 800
VID_W, VID_H = COL_W, round(COL_W * SRC_H / SRC_W)  # 900 x 562
VID_Y = 190
LIST_Y, ROW_H = VID_Y + VID_H + 66, 40
INTRO_SEC, OUTRO_SEC, END_HOLD = 4.0, 7.0, 2.0


def load_takes(rec_dir):
    timings = json.load(open(os.path.join(rec_dir, "timings.json")))
    sides = {}
    for arm, key, label, kind, color in SIDES:
        take = [t for t in timings["takes"] if t["arm"] == arm and t["task_id"] == TASK_ID][-1]
        models = [e for e in take["events"] if e["kind"] == "model"]
        tools = [e for e in take["events"] if e["kind"] == "tool"]
        t0 = models[0]["t_start"]  # agent clock starts at the first model call
        video = os.path.join(rec_dir, f"{key}.webm")
        if not os.path.exists(video):
            video = os.path.join(rec_dir, take["video"])
        sides[key] = {
            "label": label, "kind": kind, "color": color, "video": video, "take": take,
            "start_in_video": (t0 - video_start(take, video)) / 1000,
            "agent_s": float(take["agent_s"]), "passed": take["success"] in (True, "true"),
            "models": [((e["t_start"] - t0) / 1000, (e["t_end"] - t0) / 1000) for e in models],
            "tools": [{"name": e["name"], "args": e.get("args") or {}, "start": (e["t_start"] - t0) / 1000,
                       "end": (e["t_end"] - t0) / 1000, "error": tool_error(e)} for e in tools],
        }
    return sides


def video_start(take, path):
    """Wall-clock ms of the video's first frame: the file ends when the page closes."""
    if take.get("t_close"):
        dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                             "-of", "csv=p=0", path]))
        return take["t_close"] - dur * 1000
    return take["video_t0"]


def tool_error(event):
    """A tool result that reports an error (e.g. 'choose a shipping option') is not a failure of the call."""
    if event.get("error"):
        return True
    try:
        inner = json.loads(json.loads(event.get("result") or "null")["content"][0]["text"])
        return "error" in inner
    except (TypeError, KeyError, IndexError, ValueError):
        return False


def task_prompt():
    text = open(os.path.join(HERE, "tasks", "nextjs-starter-medusa.yaml")).read()
    block = text.split(f"- id: {TASK_ID}\n", 1)[1]
    return block.split("prompt:", 1)[1].split("\n", 1)[0].strip()


def earlier_medians():
    rows = [r for r in csv.DictReader(open(EARLIER)) if r["task_id"] == TASK_ID]
    out = {}
    for arm, key, *_ in SIDES:
        mine = [r for r in rows if r["arm"] == arm]
        if not mine:
            continue
        out[key] = {"agent_s": statistics.median(float(r["agent_s"]) for r in mine),
                    "turns": statistics.median(int(r["model_turns"]) for r in mine),
                    "passed": sum(r["success"] == "true" for r in mine), "runs": len(mine)}
    return out


def short_args(args):
    def val(v):
        s = v if isinstance(v, str) else json.dumps(v)
        return s if len(s) <= 22 else s[:20] + "…"
    return ", ".join(f"{k}: {val(v)}" for k, v in args.items())


class Frames:
    """Streams one recorded page from the agent's start, scaled, holding its last frame."""

    def __init__(self, side):
        self.proc = subprocess.Popen(
            ["ffmpeg", "-loglevel", "error", "-ss", f"{max(0.0, side['start_in_video']):.3f}", "-i", side["video"],
             "-vf", f"fps={FPS},scale={VID_W}:{VID_H}:flags=lanczos", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            stdout=subprocess.PIPE)
        self.last = Image.new("RGB", (VID_W, VID_H), TILE_BG), 0

    def next(self):
        buf = self.proc.stdout.read(VID_W * VID_H * 3)
        if len(buf) == VID_W * VID_H * 3:
            self.last = Image.frombytes("RGB", (VID_W, VID_H), buf)
        return self.last

    def close(self):
        self.proc.kill()


def draw_intro(d, task_prompt):
    d.text((W // 2, 150), "WindTunnel: guest checkout on a Medusa store", font=font(64, True), fill=FG, anchor="mm")
    lines = textwrap.wrap(task_prompt, 78)
    for i, line in enumerate(lines):
        d.text((W // 2, 250 + i * 46), line, font=font(34), fill=DIM, anchor="mm")
    top = 290 + len(lines) * 46
    for (_, key, label, kind, color), x0 in zip(SIDES, COL_X):
        d.rounded_rectangle((x0, top, x0 + COL_W, top + 300), radius=18, fill=TILE_BG)
        d.text((x0 + COL_W // 2, top + 120), label, font=font(72, True), fill=color, anchor="mm")
        d.text((x0 + COL_W // 2, top + 220), kind, font=font(38), fill=FG, anchor="mm")
    d.text((W // 2, 1010), "Both models call the store's WebMCP tools. Real time, one take each.",
           font=font(30), fill=DIM, anchor="mm")


def draw_race(img, d, t, sides, frames):
    d.text((W // 2, 46), "Buy a black T-shirt, size L, and check out as a guest", font=font(46, True),
           fill=FG, anchor="mm")
    d.text((W // 2, 98), "WindTunnel md-8  ·  same store reset, seed and tools for both  ·  real time",
           font=font(26), fill=DIM, anchor="mm")
    for (_, key, label, _, color), x0 in zip(SIDES, COL_X):
        s = sides[key]
        done = t >= s["agent_s"]
        clock = min(t, s["agent_s"])
        d.text((x0, 150), label, font=font(44, True), fill=color, anchor="lm")
        result_col = (GREEN if s["passed"] else RED) if done else FG
        d.text((x0 + COL_W, 150), f"{clock:4.1f} s", font=font(44, True), fill=result_col, anchor="rm")
        img.paste(frames[key].next(), (x0, VID_Y))
        d.rectangle((x0, VID_Y, x0 + COL_W - 1, VID_Y + VID_H - 1), outline=(70, 74, 82), width=2)
        turn = sum(1 for a, _ in s["models"] if a <= clock)
        thinking = any(a <= clock < b for a, b in s["models"])
        ntools = sum(1 for c in s["tools"] if c["start"] <= clock)
        if done:
            status, col = (f"Final answer  ·  {'passed' if s['passed'] else 'failed'}", GREEN if s["passed"] else RED)
        elif thinking:
            status, col = f"Model turn {turn} thinking…", YELLOW
        elif any(c["start"] <= clock < c["end"] for c in s["tools"]):
            status, col = "Calling a store tool", FG
        else:
            status, col = "Harness pause between turns", DIM
        d.text((x0, VID_Y + VID_H + 30), status, font=font(30, True), fill=col, anchor="lm")
        d.text((x0 + COL_W, VID_Y + VID_H + 30), f"turn {turn}  ·  {ntools} tool calls", font=font(28),
               fill=DIM, anchor="rm")
        shown = [c for c in s["tools"] if c["start"] <= clock][-6:]
        for i, c in enumerate(shown):
            y = LIST_Y + i * ROW_H
            running = clock < c["end"]
            mark, mcol = ("▶", YELLOW) if running else (("!", YELLOW) if c["error"] else ("✓", GREEN))
            d.text((x0 + 6, y), mark, font=SYMBOLS, fill=mcol, anchor="lm")
            d.text((x0 + 44, y), c["name"], font=font(28, True), fill=FG, anchor="lm")
            ax = x0 + 44 + d.textlength(c["name"], font=font(28, True)) + 16
            args = short_args(c["args"])
            while args and ax + d.textlength(args, font=MONO) > x0 + COL_W:
                args = args[:-2] + "…" if len(args) > 2 else ""
            d.text((ax, y), args, font=MONO, fill=DIM, anchor="lm")
        if done:
            ov = Image.new("RGBA", (COL_W, 110), (0, 0, 0, 0))
            od = ImageDraw.Draw(ov)
            od.rounded_rectangle((0, 0, COL_W, 110), radius=14, fill=(21, 23, 28, 225))
            col = GREEN if s["passed"] else RED
            od.text((COL_W // 2, 55), f"{'Passed' if s['passed'] else 'Failed'} in {s['agent_s']:.1f} s",
                    font=font(54, True), fill=col, anchor="mm")
            img.paste(ov, (x0, VID_Y + VID_H - 130), ov)


def draw_outro(d, sides, earlier, overlap_note):
    ours, other = sides["clover"], sides[SIDES[1][1]]
    d.text((W // 2, 110), f"{ours['label']} finished {other['agent_s'] / ours['agent_s']:.1f}x faster",
           font=font(66, True), fill=FG, anchor="mm")
    for (_, key, label, _, color), x0 in zip(SIDES, COL_X):
        s, e = sides[key], earlier.get(key)
        d.rounded_rectangle((x0, 200, x0 + COL_W, 860), radius=18, fill=TILE_BG)
        d.text((x0 + COL_W // 2, 265), label, font=font(48, True), fill=color, anchor="mm")
        d.text((x0 + COL_W // 2, 410), f"{s['agent_s']:.1f} s", font=font(170, True), fill=color, anchor="mm")
        d.text((x0 + COL_W // 2, 525), "agent time, this take", font=font(36, True), fill=color, anchor="mm")
        rows = [("Result (harness check)", "passed" if s["passed"] else "failed"),
                ("Model turns", str(len(s["models"]))),
                ("WebMCP tool calls", str(len(s["tools"])))]
        if e:
            rows.append((f"Earlier median, {e['runs']} runs", f"{e['agent_s']:.1f} s, {e['passed']} of {e['runs']} passed"))
        for k, (name, value) in enumerate(rows):
            y = 625 + k * 58
            d.text((x0 + 60, y), name, font=font(32), fill=DIM, anchor="lm")
            d.text((x0 + COL_W - 60, y), value, font=font(32, True), fill=FG, anchor="rm")
    d.text((W // 2, 940), "Agent time runs from the first model call to the final answer and excludes "
           "store reset and page load." + (" Earlier runs: October 15, 2026." if earlier else ""),
           font=font(26), fill=DIM, anchor="mm")
    d.text((W // 2, 985), overlap_note, font=font(26), fill=DIM, anchor="mm")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rec_dir")
    ap.add_argument("--out", help="default <rec_dir>/race.mp4")
    ap.add_argument("--note", default="No other traffic on the diffusion endpoint during either take.",
                    help="Footnote on endpoint load during the takes")
    ap.add_argument("--opponent", choices=sorted(OPPONENTS), default="gemini")
    args = ap.parse_args()
    SIDES[1] = OPPONENTS[args.opponent]
    rec = os.path.abspath(args.rec_dir)
    sides, earlier = load_takes(rec), earlier_medians()
    prompt = task_prompt()
    race_sec = max(s["agent_s"] for s in sides.values()) + END_HOLD
    total = INTRO_SEC + race_sec + OUTRO_SEC
    out = args.out or os.path.join(rec, "race.mp4")
    for key, s in sides.items():
        print(f"{s['label']}: {s['agent_s']:.2f} s, {len(s['models'])} turns, {len(s['tools'])} tool calls, "
              f"{'passed' if s['passed'] else 'failed'}")
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18",
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    frames = None
    for i in range(int(round(total * FPS))):
        tv = i / FPS
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        if tv < INTRO_SEC:
            draw_intro(d, prompt)
        elif tv < INTRO_SEC + race_sec:
            frames = frames or {k: Frames(s) for k, s in sides.items()}
            draw_race(img, d, tv - INTRO_SEC, sides, frames)
        else:
            draw_outro(d, sides, earlier, args.note)
        ff.stdin.write(img.tobytes())
    for f in (frames or {}).values():
        f.close()
    ff.stdin.close()
    ff.wait()
    print(f"{out} ({total:.1f} s)")


if __name__ == "__main__":
    main()
