"""Cut recorded takes into one side-by-side race video: DiffuSpace vs. Qwen.

Each side plays the same tasks, from the same seed, back to back in real
order. Both sides run at the same playback speed, so the gap on screen is the
measured gap. Titles, clocks and task checklists are drawn with Pillow and
piped into ffmpeg, which overlays the two recorded sequences.

Usage:
    python3 bench/miniwob/make_race_video.py recordings/run-20261015 --seed 1002
"""
import argparse
import json
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

TASKS = [
    ("find-word", "Find a word in a paragraph"),
    ("copy-paste", "Copy and paste text"),
    ("login-user-popup", "Log in past a popup"),
    ("use-colorwheel", "Pick a color"),
    ("use-slider", "Set a slider"),
    ("click-scroll-list", "Choose from a scroll list"),
    ("form-sequence-2", "Fill a form in order"),
]
SIDES = [("ours", "DiffuSpace Clover", (110, 200, 255)), ("qwen", "Qwen 3.6 Flash", (255, 170, 90))]

W, H, FPS = 1920, 1080, 25
COL_W, COL_X = 900, (40, 980)
VID_Y, VID_H = 250, 302
LIST_Y, ROW_H = 590, 62
HOLD_TRIM = 1.0  # each take holds its final frame 1.5 s; keep 0.5 s of it
END_HOLD = 2.0  # video seconds to hold the final result after the slower side finishes

BG, FG, DIM = (21, 23, 28), (240, 240, 240), (120, 124, 132)
GREEN, RED, YELLOW = (90, 210, 120), (240, 95, 95), (240, 200, 80)


def font(size, bold=False):
    return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size, index=1 if bold else 0)


SYMBOLS = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 30)


def duration(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "csv=p=0", path])
    return float(out)


def take_path(run_dir, take):
    return os.path.join(run_dir, take["task"], f"seed-{take['seed']}", f"{take['model']}.webm")


def fit_length(run_dir, takes, speed):
    """Video length that lets the slower side finish all its tasks, plus a short hold."""
    totals = [sum(duration(take_path(run_dir, takes[(task, model)])) - HOLD_TRIM for task, _ in TASKS)
              for model, _, _ in SIDES]
    return max(totals) / speed + END_HOLD


def build_side(run_dir, takes, model, out_path, speed, length, size=(COL_W, VID_H)):
    """Concatenate one model's takes, trimmed and sped up, padded to the video length."""
    inputs, filters, segments, t = [], [], [], 0.0
    for i, (task, _) in enumerate(TASKS):
        r = takes[(task, model)]
        path = take_path(run_dir, r)
        d = duration(path) - HOLD_TRIM
        inputs += ["-i", path]
        filters.append(f"[{i}:v]trim=0:{d:.3f},setpts=PTS-STARTPTS,fps={FPS},"
                       f"scale={size[0]}:{size[1]}:flags=lanczos,setsar=1[v{i}]")
        segments.append({"task": task, "start": t, "end": t + d, "passed": r["passed"],
                         "elapsed_s": r["elapsed_s"], "take": r})
        t += d
    n = len(TASKS)
    chain = "".join(f"[v{i}]" for i in range(n))
    filters.append(f"{chain}concat=n={n}:v=1:a=0,setpts=PTS/{speed},"
                   f"tpad=stop_mode=clone:stop_duration={length}[out]")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(filters),
                    "-map", "[out]", "-t", str(length), "-r", str(FPS), "-c:v", "libx264", "-crf", "16",
                    "-pix_fmt", "yuv420p", out_path], check=True)
    return segments, t


def draw_frame(t_video, speed, sides, seed):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((W // 2, 52), "Same 7 web tasks, run back to back", font=font(52, True), fill=FG, anchor="mm")
    d.text((W // 2, 112), f"MiniWoB++, seed {seed} for both models  ·  playback {speed:g}x  ·  "
           "Qwen via Alibaba's hosted API, October 15, 2026", font=font(26), fill=DIM, anchor="mm")
    t_real = t_video * speed
    for (model, label, color), x in zip(SIDES, COL_X):
        segs, total = sides[model]
        done = [s for s in segs if s["end"] <= t_real]
        finished = len(done) == len(segs)
        clock = total if finished else t_real
        d.text((x, 205), label, font=font(46, True), fill=color, anchor="lm")
        # Green only when the model finished and passed every task.
        won = finished and all(s["passed"] for s in segs)
        d.text((x + COL_W, 205), f"{clock:5.1f} s", font=font(46, True),
               fill=GREEN if won else FG, anchor="rm")
        for i, (seg, (_, name)) in enumerate(zip(segs, TASKS)):
            y = LIST_Y + i * ROW_H
            if seg["end"] <= t_real:
                mark, col = ("✓", GREEN) if seg["passed"] else ("✗", RED)
                d.text((x + 6, y), mark, font=SYMBOLS, fill=col, anchor="lm")
                d.text((x + 50, y), name, font=font(30), fill=FG, anchor="lm")
                d.text((x + COL_W, y), "passed" if seg["passed"] else "failed",
                       font=font(28), fill=col, anchor="rm")
            elif seg["start"] <= t_real:
                d.text((x + 6, y), "▶", font=SYMBOLS, fill=YELLOW, anchor="lm")
                d.text((x + 50, y), name, font=font(30, True), fill=YELLOW, anchor="lm")
                d.text((x + COL_W, y), "running", font=font(28), fill=YELLOW, anchor="rm")
            else:
                d.text((x + 50, y), name, font=font(30), fill=DIM, anchor="lm")
        passed = sum(s["passed"] for s in done)
        status = (f"All {len(segs)} tasks done in {total:.1f} s, {passed} passed" if finished
                  else f"{len(done)} of {len(segs)} tasks done, {passed} passed")
        d.text((x, LIST_Y + len(segs) * ROW_H + 8), status, font=font(32, True),
               fill=GREEN if won else FG, anchor="lm")
    return img


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", help="Directory written by record_takes.py")
    parser.add_argument("--seed", type=int, required=True, help="Seed whose takes both sides play")
    parser.add_argument("--speed", type=float, default=2.0, help="Playback speed for both sides")
    parser.add_argument("--length", type=float, help="Video length in seconds (default: until both sides finish)")
    parser.add_argument("--out", help="Output path (default <run_dir>/race_seed-<seed>.mp4)")
    args = parser.parse_args()

    run_dir = os.path.abspath(args.run_dir)
    takes = {}
    with open(os.path.join(run_dir, "takes.jsonl")) as f:
        for line in f:
            r = json.loads(line)
            if r["seed"] == args.seed:
                takes[(r["task"], r["model"])] = r
    out = args.out or os.path.join(run_dir, f"race_seed-{args.seed}.mp4")
    args.length = args.length or fit_length(run_dir, takes, args.speed)
    tmp = {m: os.path.join(run_dir, f".race_{m}.mp4") for m, _, _ in SIDES}

    sides = {}
    for model, label, _ in SIDES:
        segs, total = build_side(run_dir, takes, model, tmp[model], args.speed, args.length)
        sides[model] = (segs, total)
        print(f"{label}: {total:.1f} s real time for {len(segs)} tasks, "
              f"{sum(s['passed'] for s in segs)} passed, ends on screen at {total / args.speed:.1f} s")

    ff = subprocess.Popen([
        "ffmpeg", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", tmp["ours"], "-i", tmp["qwen"],
        "-filter_complex", f"[0][1]overlay={COL_X[0]}:{VID_Y}[a];[a][2]overlay={COL_X[1]}:{VID_Y}",
        "-t", str(args.length), "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", out,
    ], stdin=subprocess.PIPE)
    for i in range(int(args.length * FPS)):
        ff.stdin.write(draw_frame(i / FPS, args.speed, sides, args.seed).tobytes())
    ff.stdin.close()
    ff.wait()
    for p in tmp.values():
        os.remove(p)
    print(out)


if __name__ == "__main__":
    main()
