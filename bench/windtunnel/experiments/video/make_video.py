"""Race video for WebMCP: DiffuSpace Clover vs. Gemini 3.6 Flash on WindTunnel tasks.

Same structure as bench/miniwob/make_race_grid_video.py: an intro card, a grid
race where each task's tile zooms up while it runs, a speed card, then the
agent-time bars from the full WindTunnel run. Each side plays its median take
of each task (by agent time, among passing takes when there are any), so the
clip is not the best case. Model calls were not streamed, so the panel under
the zoomed tile shows each model call's wait and the tools it called.

After --ff-at real seconds the race fast-forwards, with a scanline effect and
a flash, at whatever extra speed fits the whole video under --target seconds
(or at --ff times the base speed).

Usage:
    python3 make_video.py recordings/run-20261016 --speed 6 --ff-at 50 --target 30
"""
import argparse
import json
import os
import statistics
import subprocess
import sys
import textwrap
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "miniwob"))
from make_race_grid_video import (GEMINI, MONO, THINK_BG, TILE_BG, WEBMCP_GLOB, WEBMCP_SEC,  # noqa: E402
                                  draw_webmcp, ease, lerp_rect, webmcp_stats)
from make_race_video import BG, DIM, FG, FPS, GREEN, H, RED, SYMBOLS, W, YELLOW, font  # noqa: E402

TASKS = [
    ("id-6", "Create a draft invoice", "Create an invoice"),
    ("lh-7", "Enroll in a course and find the first lesson", "Enroll in a course"),
    ("id-8", "Report this month's total invoiced", "Total invoiced"),
    ("hev-8", "Report an event's status", "Event status"),
    ("ea-8", "Find the registered customer", "Find a customer"),
    ("id-1", "Find which client an invoice is billed to", "Invoice's client"),
]
SIDES = [("ours", "DiffuSpace Clover", (110, 200, 255)), ("gemini", "Gemini 3.6 Flash", GEMINI)]
INTRO = {"ours": "Diffusion language model", "gemini": "Autoregressive language model"}
BENCH_TASKS = 49  # WindTunnel tasks with results for both models

SRC_W, SRC_H = 640, 400
PANEL_X, PANEL_W = (40, 980), 900
GRID_Y, COLS, ROWS, GAP_X, GAP_Y = 235, 3, 3, 14, 12
TILE_W = (PANEL_W - GAP_X * (COLS - 1)) // COLS
THUMB_H = round(TILE_W * SRC_H / SRC_W)
LABEL_H = 34
CELL_H = THUMB_H + LABEL_H
GRID_H = ROWS * CELL_H + (ROWS - 1) * GAP_Y
ZOOM_W = 720
ZOOM_H = round(ZOOM_W * SRC_H / SRC_W)
ZOOM_TOP = 44  # room above the zoomed tile for the task heading
LOG_H = GRID_H - ZOOM_TOP - ZOOM_H - 14
ZOOM_SEC = 0.3
HOLD = 1.0  # real seconds kept after the last model call
INTRO_SEC, OUTRO_SEC, END_HOLD = 4.0, 7.0, 2.0


def pick_median(takes):
    """The take with the median agent time, among passing takes when any passed."""
    pool = [t for t in takes if t["success"]] or takes
    pool = sorted(pool, key=lambda t: float(t["agent_s"]))
    return pool[(len(pool) - 1) // 2]


def take_end(take):
    """Seconds from the start of the take's video to the end of its last model call."""
    ends = [c["t_end"] for c in take["calls"]]
    return (max(ends) - take["video_t0"]) / 1000 + HOLD if ends else float(take["setup_s"]) + float(take["agent_s"]) + HOLD


class Clock:
    """Maps output video time to real recorded time: base speed, then fast-forward after ff_at."""

    def __init__(self, speed, ff_at=float("inf"), ff=1.0):
        self.speed, self.ff_at, self.ff = speed, ff_at, ff
        self.tv_ff = ff_at / speed

    def real(self, tv):
        return tv * self.speed if tv < self.tv_ff else self.ff_at + (tv - self.tv_ff) * self.speed * self.ff

    def video(self, t):
        return t / self.speed if t < self.ff_at else self.tv_ff + (t - self.ff_at) / (self.speed * self.ff)


def build_side(run_dir, takes, out_path, clock, length):
    inputs, filters, segments, t = [], [], [], 0.0
    for i, (task, _, _) in enumerate(TASKS):
        take = takes[task]
        d = take_end(take)
        inputs += ["-i", os.path.join(run_dir, take["video"])]
        filters.append(f"[{i}:v]trim=0:{d:.3f},setpts=PTS-STARTPTS,fps={FPS},"
                       f"scale={SRC_W}:{SRC_H}:flags=lanczos,setsar=1[v{i}]")
        segments.append({"task": task, "start": t, "end": t + d, "passed": take["success"], "take": take})
        t += d
    n = len(TASKS)
    chain = "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0"
    if clock.ff_at < t:
        # Two speeds: split the real-time sequence at ff_at and speed each part up separately.
        filters.append(f"{chain},split[a][b]")
        filters.append(f"[a]trim=end={clock.ff_at:.3f},setpts=(PTS-STARTPTS)/{clock.speed}[a1]")
        filters.append(f"[b]trim=start={clock.ff_at:.3f},setpts=(PTS-STARTPTS)/{clock.speed * clock.ff}[b1]")
        chain = "[a1][b1]concat=n=2:v=1:a=0"
    else:
        chain += f",setpts=PTS/{clock.speed}"
    filters.append(f"{chain},fps={FPS},tpad=stop_mode=clone:stop_duration={length}[out]")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(filters),
                    "-map", "[out]", "-t", str(length), "-r", str(FPS), "-c:v", "libx264", "-crf", "16",
                    "-pix_fmt", "yuv420p", out_path], check=True)
    return segments, t


class SideReader:
    def __init__(self, path):
        self.proc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "rawvideo",
                                      "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.last = Image.new("RGB", (SRC_W, SRC_H), TILE_BG)

    def next(self):
        buf = self.proc.stdout.read(SRC_W * SRC_H * 3)
        if len(buf) == SRC_W * SRC_H * 3:
            self.last = Image.frombytes("RGB", (SRC_W, SRC_H), buf)
        return self.last


def cell_rect(i, x0):
    r, c = divmod(i, COLS)
    return x0 + c * (TILE_W + GAP_X), GRID_Y + r * (CELL_H + GAP_Y), TILE_W, THUMB_H


def zoom_rect(x0):
    return x0 + (PANEL_W - ZOOM_W) // 2, GRID_Y + ZOOM_TOP, ZOOM_W, ZOOM_H


def call_lines(take, t_rel):
    """Log lines for what the agent had done t_rel seconds into the take's video."""
    lines, t0 = [], take["video_t0"]
    tools = {}
    for e in take["transcript"]:
        if "tool" in e:
            tools.setdefault(e["turn"], []).append(e)
    for k, call in enumerate(take["calls"], 1):
        start, end = (call["t_start"] - t0) / 1000, (call["t_end"] - t0) / 1000
        if t_rel < start:
            break
        if t_rel < end:
            lines.append((f"Step {k}: waiting for the model  {t_rel - start:.1f} s", YELLOW))
            break
        lines.append((f"Step {k}: model took {end - start:.2f} s, {call['output_tokens']} tokens", FG))
        for e in tools.get(k, []):
            args = ", ".join(f"{a}={json.dumps(v)}" for a, v in (e["input"] or {}).items())
            lines.append((f"  → {e['tool']}({args})", DIM))
        if k == len(take["calls"]) and not tools.get(k):
            lines.append(("  → Answer: " + " ".join(take["final_text"].split()), GREEN))
    return lines


def draw_log(d, x0, take, t_rel):
    top = GRID_Y + ZOOM_TOP + ZOOM_H + 14
    d.rectangle((x0, top, x0 + PANEL_W, top + LOG_H), fill=THINK_BG, outline=(60, 64, 72))
    rows = []
    for text, color in call_lines(take, t_rel):
        rows += [(line, color) for line in textwrap.wrap(text, 84, subsequent_indent="    ")]
    room = (LOG_H - 24) // 21
    for n, (line, color) in enumerate(rows[-room:]):
        d.text((x0 + 12, top + 12 + n * 21), line, font=MONO, fill=color)


def draw_side(img, d, label, color, x0, segs, total, frame, prev, thumbs, tv, clock):
    t_real = clock.real(tv)
    finished = all(s["end"] <= t_real for s in segs)
    won = finished and all(s["passed"] for s in segs)
    d.text((x0, 190), label, font=font(46, True), fill=color, anchor="lm")
    d.text((x0 + PANEL_W, 190), f"{total if finished else t_real:5.1f} s", font=font(46, True),
           fill=GREEN if won else FG, anchor="rm")
    active = None
    for i, seg in enumerate(segs):
        x, y, w, h = cell_rect(i, x0)
        name = TASKS[i][2]
        ts, te = clock.video(seg["start"]), clock.video(seg["end"])
        d.rectangle((x, y + h, x + w, y + h + LABEL_H), fill=TILE_BG)
        if tv >= te:
            if i not in thumbs:
                thumbs[i] = prev.resize((w, h), Image.LANCZOS)
            img.paste(thumbs[i], (x, y))
            ok = seg["passed"]
            d.text((x + 8, y + h + LABEL_H // 2), name, font=font(21), fill=FG, anchor="lm")
            d.text((x + w - 8, y + h + LABEL_H // 2), "passed" if ok else "failed", font=font(20, True),
                   fill=GREEN if ok else RED, anchor="rm")
            d.text((x + w - 10, y + 8), "✓" if ok else "✗", font=SYMBOLS, fill=GREEN if ok else RED, anchor="rt")
        else:
            d.rectangle((x, y, x + w, y + h), fill=TILE_BG)
            if tv >= ts:
                active = (i, ts, te)
                d.text((x + 8, y + h + LABEL_H // 2), name, font=font(21), fill=FG, anchor="lm")
                d.text((x + w - 8, y + h + LABEL_H // 2), "running", font=font(20, True), fill=YELLOW, anchor="rm")
            else:
                d.text((x + w // 2, y + h // 2), "waiting", font=font(24), fill=DIM, anchor="mm")
                d.text((x + 8, y + h + LABEL_H // 2), name, font=font(21), fill=DIM, anchor="lm")
    # The seventh cell holds the running tally.
    x, y, w, h = cell_rect(len(segs), x0)
    done = [s for s in segs if s["end"] <= t_real]
    d.text((x + 8, y + 40), f"{len(done)} of {len(segs)} done", font=font(30, True), fill=GREEN if won else FG,
           anchor="lm")
    d.text((x + 8, y + 84), f"{sum(s['passed'] for s in done)} passed", font=font(26), fill=DIM, anchor="lm")
    if active:
        i, ts, te = active
        zoom = min(ZOOM_SEC, (te - ts) / 3)  # tasks shown in fast-forward are short on screen
        p = min(ease((tv - ts) / zoom), ease((te - tv) / zoom))
        shade = Image.new("RGBA", (PANEL_W, GRID_H), (*BG, round(220 * p)))
        img.paste(shade, (x0, GRID_Y), shade)
        x, y, w, h = lerp_rect(cell_rect(i, x0), zoom_rect(x0), p)
        img.paste(frame.resize((w, h), Image.LANCZOS), (x, y))
        if p > 0.5:
            d.text((x0 + PANEL_W // 2, GRID_Y + ZOOM_TOP // 2), TASKS[i][1], font=font(28, True), fill=YELLOW,
                   anchor="mm")
            draw_log(d, x0, segs[i]["take"], t_real - segs[i]["start"])


CHEVRON = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 54)


def draw_ff_banner(img, factor, t):
    """Big banner under the race while it fast-forwards, with chevrons that march left to right."""
    big = font(64, True)
    text = f"{factor:g}x SPEED-UP"
    tw = ImageDraw.Draw(img).textlength(text, font=big)
    w, h = round(tw) + 260, 112
    x, y = (W - w) // 2, 925
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=(40, 34, 12, 235), outline=(*YELLOW, 255), width=4)
    lead = (t * 6) % 3  # one chevron lights up at a time, cycling twice a second
    for k in range(3):
        glow = 1.0 if int(lead) == k else 0.35
        d.text((60 + k * 48, h // 2), "▶", font=CHEVRON, fill=(*YELLOW, round(255 * glow)), anchor="mm")
    d.text((210, h // 2), text, font=big, fill=(*YELLOW, 255), anchor="lm")
    img.paste(layer, (x, y), layer)


def speed_stats(all_takes, key):
    calls = [c for t in all_takes if t["model_key"] == key for c in t["calls"] if c["status"] == 200]
    secs = sum(c["t_end"] - c["t_start"] for c in calls) / 1000
    # Attempts where the site failed before the first model call say nothing about the model.
    mine = [t for t in all_takes if t["model_key"] == key and t["calls"]]
    return {"skipped": sum(t["model_key"] == key and not t["calls"] for t in all_takes),"tok_s": sum(c["output_tokens"] for c in calls) / secs, "per_call": secs / len(calls),
            "calls": len(calls), "passed": sum(t["success"] for t in mine), "attempts": len(mine)}


def draw_intro(d):
    d.text((W // 2, 260), "WebMCP", font=font(96, True), fill=FG, anchor="mm")
    d.text((W // 2, 360), f"Selected {len(TASKS)} samples from {BENCH_TASKS} WindTunnel tasks", font=font(40),
           fill=DIM, anchor="mm")
    for (key, label, color), x0 in zip(SIDES, PANEL_X):
        d.rounded_rectangle((x0, 490, x0 + PANEL_W, 830), radius=18, fill=TILE_BG)
        d.text((x0 + PANEL_W // 2, 615), label, font=font(72, True), fill=color, anchor="mm")
        d.text((x0 + PANEL_W // 2, 720), INTRO[key], font=font(38), fill=FG, anchor="mm")


def draw_speed(d, stats):
    ours, theirs = stats["ours"], stats["gemini"]
    d.text((W // 2, 130), f"Each model call: {ours['per_call']:.2f} s vs. {theirs['per_call']:.2f} s",
           font=font(68, True), fill=FG, anchor="mm")
    for (key, label, color), x0 in zip(SIDES, PANEL_X):
        st = stats[key]
        d.rounded_rectangle((x0, 230, x0 + PANEL_W, 880), radius=18, fill=TILE_BG)
        d.text((x0 + PANEL_W // 2, 300), label, font=font(48, True), fill=color, anchor="mm")
        d.text((x0 + PANEL_W // 2, 450), f"{st['tok_s']:.0f}", font=font(220, True), fill=color, anchor="mm")
        d.text((x0 + PANEL_W // 2, 575), "tokens per second (TPS)", font=font(48, True), fill=color, anchor="mm")
        for k, (name, value) in enumerate([("Model time per call", f"{st['per_call']:.2f} s"),
                                           ("Model calls", f"{st['calls']}"),
                                           ("Attempts passed", f"{st['passed']} of {st['attempts']}")]):
            y = 700 + k * 56
            d.text((x0 + 60, y), name, font=font(32), fill=DIM, anchor="lm")
            d.text((x0 + PANEL_W - 60, y), value, font=font(32, True), fill=FG, anchor="rm")
    d.text((W // 2, 950), "Tokens per second = output tokens ÷ model call time, over every recorded call. "
           "Calls were not streamed,", font=font(26), fill=DIM, anchor="mm")
    d.text((W // 2, 995), "so call time includes the wait for the first token. Gemini thinks before it returns "
           "anything; its thinking tokens are counted.", font=font(26), fill=DIM, anchor="mm")
    skipped = [f"{n} {label} attempt{'s' * (n > 1)}" for (key, label, _) in SIDES if (n := stats[key]["skipped"])]
    if skipped:
        d.text((W // 2, 1040), f"Left out: {' and '.join(skipped)} where the site's tools never loaded, "
               "before any model call.", font=font(26), fill=DIM, anchor="mm")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", help="Directory written by record.mjs")
    parser.add_argument("--speed", type=float, default=6.0, help="Playback speed for both sides")
    parser.add_argument("--ff-at", type=float, default=50.0, help="Real seconds into the race to start fast-forward")
    parser.add_argument("--ff", type=float, help="Fast-forward factor on top of --speed (default: fit --target)")
    parser.add_argument("--target", type=float, default=30.0, help="Whole-video length to fit under, in seconds")
    parser.add_argument("--outro-sec", type=float, default=OUTRO_SEC, help="Seconds for the speed card")
    parser.add_argument("--bars-sec", type=float, default=WEBMCP_SEC, help="Seconds for the agent-time card")
    parser.add_argument("--webmcp", default=WEBMCP_GLOB, help="WindTunnel results.csv glob for the agent-time card")
    parser.add_argument("--out", help="Output path (default <run_dir>/race_webmcp.mp4)")
    args = parser.parse_args()

    run_dir = os.path.abspath(args.run_dir)
    all_takes = [json.loads(line) for line in open(os.path.join(run_dir, "takes.jsonl"))]
    out = args.out or os.path.join(run_dir, "race_webmcp.mp4")
    picked = {key: {task: pick_median([t for t in all_takes if t["model_key"] == key and t["task_id"] == task])
                    for task, _, _ in TASKS} for key, _, _ in SIDES}
    totals = {key: sum(take_end(t) for t in picked[key].values()) for key, _, _ in SIDES}
    longest = max(totals.values())
    cards = INTRO_SEC + args.outro_sec + (args.bars_sec if webmcp_stats(args.webmcp) else 0)
    ff = args.ff
    if ff is None:
        budget = args.target - 0.2 - cards - END_HOLD - args.ff_at / args.speed
        if budget <= 0:
            sys.exit(f"Cannot fit under {args.target} s: the cards and the first {args.ff_at} s already take too long")
        ff = max(1.0, (longest - args.ff_at) / (budget * args.speed))
    clock = Clock(args.speed, args.ff_at, ff) if longest > args.ff_at and ff > 1 else Clock(args.speed)
    length = clock.video(longest) + END_HOLD
    print(f"Fast-forward {clock.ff:.1f}x after {args.ff_at:g} s (playback {args.speed * clock.ff:.0f}x), "
          f"race {length:.1f} s, video {length + cards:.1f} s")
    recorded = datetime.fromtimestamp(min(t["video_t0"] for t in all_takes) / 1000)

    sides, readers = {}, {}
    for key, label, _ in SIDES:
        tmp = os.path.join(run_dir, f".side_{key}.mp4")
        sides[key] = build_side(run_dir, picked[key], tmp, clock, length)
        readers[key] = (SideReader(tmp), tmp)
        segs, total = sides[key]
        print(f"{label}: {total:.1f} s real time, {sum(s['passed'] for s in segs)}/{len(segs)} passed, "
              f"takes {[s['take']['take'] for s in segs]}, ends on screen at {clock.video(total):.1f} s")
    stats = {key: speed_stats(all_takes, key) for key, _, _ in SIDES}
    ws = webmcp_stats(args.webmcp)

    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18",
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)

    def card(seconds, draw):
        for k in range(int(seconds * FPS)):
            img = Image.new("RGB", (W, H), BG)
            draw(img, ImageDraw.Draw(img), k / FPS)
            ff.stdin.write(img.tobytes())

    card(INTRO_SEC, lambda img, d, t: draw_intro(d))
    scan = Image.new("RGBA", (W, H - 150), (0, 0, 0, 0))
    ImageDraw.Draw(scan).rectangle((0, 0, W, H), fill=(110, 200, 255, 10))
    for y in range(0, H - 150, 4):
        ImageDraw.Draw(scan).line((0, y, W, y), fill=(0, 0, 0, 70), width=1)
    thumbs = {key: {} for key, _, _ in SIDES}
    prev = {key: readers[key][0].last for key, _, _ in SIDES}
    for k in range(int(length * FPS)):
        tv = k / FPS
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        d.text((W // 2, 52), f"Same {len(TASKS)} WebMCP tasks, run back to back", font=font(52, True), fill=FG,
               anchor="mm")
        fast = clock.ff > 1 and clock.tv_ff <= tv and clock.real(tv) < longest
        if fast:
            d.text((W // 2 - 175, 112), "▶▶", font=SYMBOLS, fill=YELLOW, anchor="mm")
            d.text((W // 2 + 20, 112), f"FAST FORWARD  ·  {args.speed * clock.ff:.0f}x", font=font(30, True),
                   fill=YELLOW, anchor="mm")
        else:
            d.text((W // 2, 112), f"WindTunnel  ·  median of 3 takes per task  ·  playback {args.speed:g}x  ·  "
                   f"Gemini via Google's API, recorded {recorded:%B} {recorded.day}, {recorded.year}",
                   font=font(26), fill=DIM, anchor="mm")
        for (key, label, color), x0 in zip(SIDES, PANEL_X):
            frame = readers[key][0].next()
            draw_side(img, d, label, color, x0, *sides[key], frame, prev[key], thumbs[key], tv, clock)
            prev[key] = frame
        if fast:
            img.paste(scan, (0, 150), scan)
            flash = 1 - (tv - clock.tv_ff) / 0.25
            if flash > 0:
                white = Image.new("RGBA", (W, H), (255, 255, 255, round(170 * flash)))
                img.paste(white, (0, 0), white)
            draw_ff_banner(img, clock.ff, tv - clock.tv_ff)
        ff.stdin.write(img.tobytes())
    card(args.outro_sec, lambda img, d, t: draw_speed(d, stats))
    if ws:
        card(args.bars_sec, lambda img, d, t: draw_webmcp(img, d, ws, t))
    ff.stdin.close()
    ff.wait()
    for reader, tmp in readers.values():
        reader.proc.kill()
        os.remove(tmp)
    print(out)


if __name__ == "__main__":
    main()
