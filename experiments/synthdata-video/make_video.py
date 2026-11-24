"""Race video for the synthetic-data benchmark, in the style of the other race videos.

Reads data.json (from build_data.py) and writes race.mp4: a 3 s intro card, the race at one
playback speed for both sides, and a 5 s outro. Each side is a map of usable summaries placed by
content (shared t-SNE layout), filling in at the real completion times from the benchmark run.

Run from the repo root:
    uv run --no-project --with pillow python3 experiments/synthdata-video/make_video.py
"""
import argparse
import json
import math
import os
import subprocess
import sys
import textwrap

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "bench", "miniwob"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "bench", "webarena"))
from make_race_video import BG, DIM, FG, FPS, GREEN, H, RED, SIDES, SYMBOLS, W, YELLOW, font  # noqa: E402
from make_webarena_race import nice_speed  # noqa: E402

CJK = "/System/Library/Fonts/Hiragino Sans GB.ttc"
ARMS = [("dllm", SIDES[0][1], SIDES[0][2], "Diffusion language model"),
        ("qwen", "Qwen3.6-35B-A3B", SIDES[1][2], "Autoregressive language model")]
PANEL_X, PANEL_W = (40, 980), 900
MAP_Y, MAP_H = 240, 540
STRIP_Y, STRIP_H = 800, 26
TILE_BG = (36, 39, 46)
REPEAT = (150, 155, 165)
RACE_TARGET = 24.0
INTRO_SEC, OUTRO_SEC, END_HOLD = 3.0, 5.0, 1.5
SS = 2  # map supersampling, for smooth dots
TASK = "Write a fictional inpatient summary for a given department, sex and age range."


def cjk(size):
    return ImageFont.truetype(CJK, size)


def place(x, y, w, h, pad=0.06):
    return w * (pad + x * (1 - 2 * pad)), h * (pad + y * (1 - 2 * pad))


def draw_intro(d, cells):
    d.text((W // 2, 120), "Synthetic training data  ·  fictional inpatient summaries", font=font(40), fill=DIM,
           anchor="mm")
    for k, line in enumerate(textwrap.wrap(f"“{TASK}”", 52)):
        d.text((W // 2, 230 + k * 70), line, font=font(54, True), fill=FG, anchor="mm")
    for (arm, label, color, kind), x0 in zip(ARMS, PANEL_X):
        d.rounded_rectangle((x0, 600, x0 + PANEL_W, 900), radius=18, fill=TILE_BG)
        d.text((x0 + PANEL_W // 2, 710), label, font=font(68, True), fill=color, anchor="mm")
        d.text((x0 + PANEL_W // 2, 805), f"{kind}  ·  temperature {cells[arm]['temp']:.1f}", font=font(38),
               fill=FG, anchor="mm")
    n = cells["dllm"]["requests"]
    d.text((W // 2, 990), f"Same prompts, {n} requests each, 8 at a time. Each model at its best temperature. "
           "One held-out run, no retakes.", font=font(30), fill=DIM, anchor="mm")


def map_layer(cell, departments, color, tv, speed, kept):
    """The side's map at video time tv, drawn at SS times size and scaled down."""
    w, h = PANEL_W * SS, MAP_H * SS
    img = Image.new("RGB", (w, h), TILE_BG)
    d = ImageDraw.Draw(img)
    f = cjk(24 * SS)
    for dept, (x, y) in departments.items():
        px, py = place(x, y, w, h)
        d.text((px, py), dept, font=f, fill=(78, 82, 92), anchor="mm")
    for e in cell["events"]:
        age = tv - e["t"] / speed
        if age < 0:
            break
        pop = min(1.0, age / 0.3)
        if e["kind"] == "new":
            px, py = place(e["x"], e["y"], w, h)
            r = (7 + 6 * (1 - pop)) * SS
            d.ellipse((px - r, py - r, px + r, py + r), fill=color)
        elif e["kind"] == "dup":
            tw = kept[e["twin"]] if e.get("twin") is not None else e
            px, py = place(tw["x"], tw["y"], w, h)
            r = (15 + 8 * (1 - pop)) * SS
            d.ellipse((px - r, py - r, px + r, py + r), outline=REPEAT, width=3 * SS)
    return img.resize((PANEL_W, MAP_H), Image.LANCZOS)


def draw_side(img, d, arm, label, color, x0, cell, departments, tv, speed):
    tr = tv * speed
    end = cell["end"]
    done = tr >= end
    t = min(tr, end)
    kept = [e for e in cell["events"] if e["kind"] == "new"]
    d.text((x0, 190), label, font=font(46, True), fill=color, anchor="lm")
    d.text((x0 + PANEL_W, 190), f"{t:5.1f} s", font=font(46, True), fill=GREEN if done else FG, anchor="rm")
    img.paste(map_layer(cell, departments, color, tv, speed, kept), (x0, MAP_Y))
    # Strip: one slot per request in completion order: new case, repeat, or rejected.
    n = cell["requests"]
    slot = PANEL_W / n
    d.rectangle((x0, STRIP_Y, x0 + PANEL_W, STRIP_Y + STRIP_H), fill=TILE_BG)
    seen = [e for e in cell["events"] if e["t"] <= t]
    for k, e in enumerate(seen):
        c = {"new": color, "dup": REPEAT, "failed": RED}[e["kind"]]
        d.rectangle((x0 + k * slot, STRIP_Y, x0 + (k + 1) * slot - 1, STRIP_Y + STRIP_H), fill=c)
    dist = sum(e["kind"] == "new" for e in seen)
    usable = sum(e["kind"] != "failed" for e in seen)
    rej = len(seen) - usable
    rows = [("Distinct usable", f"{dist}", color), ("Usable incl. repeats", f"{usable}", FG),
            ("Rejected", f"{rej}", RED)]
    for k, (name, value, col) in enumerate(rows):
        y = 862 + k * 52
        d.text((x0, y), name, font=font(34), fill=DIM, anchor="lm")
        d.text((x0 + 420, y), value, font=font(38, True), fill=col, anchor="rm")
    if done:
        d.text((x0 + 480, 914), f"Finished {n} requests", font=font(34, True), fill=GREEN, anchor="lm")
        veil = Image.new("RGBA", (PANEL_W, MAP_H), (*BG, 70))
        img.paste(veil, (x0, MAP_Y), veil)
        d.text((x0 + PANEL_W - 30, MAP_Y + 40), f"{end:.1f} s", font=font(48, True), fill=GREEN, anchor="rm")
        tw = d.textlength(f"{end:.1f} s", font=font(48, True))
        d.text((x0 + PANEL_W - 44 - tw, MAP_Y + 40), "✓", font=SYMBOLS.font_variant(size=48), fill=GREEN,
               anchor="rm")
    else:
        d.text((x0 + 480, 914), f"Request {len(seen)} of {n} done", font=font(34, True), fill=FG, anchor="lm")


def draw_legend(d):
    """One line under both panels: what a dot, a ring and a strip color mean."""
    items = [("●", (200, 204, 212), "new case"), ("○", REPEAT, "repeat of an earlier case"),
             ("▮", RED, "rejected: failed checks or review")]
    sym, txt = SYMBOLS.font_variant(size=30), font(28)
    widths = [d.textlength(s_, font=sym) + 10 + d.textlength(t, font=txt) for s_, _, t in items]
    x = (W - sum(widths) - 60 * (len(items) - 1)) / 2
    for (s_, col, t), wd in zip(items, widths):
        d.text((x, 1040), s_, font=sym, fill=col, anchor="lm")
        d.text((x + d.textlength(s_, font=sym) + 10, 1040), t, font=txt, fill=DIM, anchor="lm")
        x += wd + 60


def draw_outro(d, cells):
    a, b = cells["dllm"], cells["qwen"]
    d.text((W // 2, H // 2 - 20), f"{b['end'] / a['end']:.1f}x faster, same distinct output", font=font(84, True),
           fill=FG, anchor="mm")
    d.text((W // 2, 960), "Distinct usable: passed format checks and a gemini-3.8-flash review, and isn't a near-copy "
           "of an earlier summary.", font=font(26), fill=DIM, anchor="mm")
    d.text((W // 2, 1005), "One held-out run of three. Across all three: 1.3 to 1.6x faster, 59 vs 63 distinct per "
           "100 requests. Qwen via OpenRouter.", font=font(26), fill=DIM, anchor="mm")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--speed", type=float, help="playback speed for both sides (default: fit ~24 s)")
    p.add_argument("--out", default=os.path.join(HERE, "race.mp4"))
    args = p.parse_args()
    data = json.load(open(os.path.join(HERE, "data.json")))
    cells, departments = data["cells"], data["departments"]
    slow = max(c["end"] for c in cells.values())
    speed = args.speed or nice_speed(slow / RACE_TARGET)
    length = slow / speed + END_HOLD
    print(f"speed {speed:g}x, race {length:.1f} s")

    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18",
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", args.out], stdin=subprocess.PIPE)
    intro = Image.new("RGB", (W, H), BG)
    draw_intro(ImageDraw.Draw(intro), cells)
    for _ in range(int(INTRO_SEC * FPS)):
        ff.stdin.write(intro.tobytes())
    for k in range(math.ceil(length * FPS)):
        tv = k / FPS
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        d.text((W // 2, 50), f"“{TASK}”", font=font(38, True), fill=FG, anchor="mm")
        d.text((W // 2, 108), f"Held-out run 2 of 3  ·  playback {speed:g}x for both sides  ·  "
               "recorded October 20, 2026", font=font(28), fill=YELLOW, anchor="mm")
        for (arm, label, color, _), x0 in zip(ARMS, PANEL_X):
            draw_side(img, d, arm, label, color, x0, cells[arm], departments, tv, speed)
        draw_legend(d)
        ff.stdin.write(img.tobytes())
    outro = Image.new("RGB", (W, H), BG)
    draw_outro(ImageDraw.Draw(outro), cells)
    for _ in range(int(OUTRO_SEC * FPS)):
        ff.stdin.write(outro.tobytes())
    ff.stdin.close()
    ff.wait()
    print(args.out)


if __name__ == "__main__":
    main()
