"""Grid version of the race video: each side is a grid of task tiles.

An intro card names the two models, and an outro card shows their measured
speed from the same takes. Tiles start as "waiting". When a task starts, its tile zooms up to fill the
side and plays the recorded take live; when the task ends, it shrinks back
into its cell and reads "done" with the outcome. Tasks run back to back in
recorded real time, and both sides use the same playback speed.

Usage:
    python3 bench/miniwob/make_race_grid_video.py recordings/run-20261015 --seed 1002 --speed 3.3
"""
import argparse
import csv
import glob
import json
import os
import statistics
import subprocess
import textwrap
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from make_race_video import (BG, DIM, FG, FPS, GREEN, H, HERE, RED, SIDES, SYMBOLS, TASKS, W, YELLOW,
                             build_side, fit_length, font)

SRC_W, SRC_H = 640, 214  # even height for libx264
PANEL_X, PANEL_W = (40, 980), 900
GRID_Y, COLS, GAP_X, GAP_Y = 235, 2, 20, 14
TILE_W = (PANEL_W - GAP_X * (COLS - 1)) // COLS
THUMB_H = round(TILE_W * SRC_H / SRC_W)
LABEL_H = 36
CELL_H = THUMB_H + LABEL_H
ROWS = 4
GRID_H = ROWS * CELL_H + (ROWS - 1) * GAP_Y
ZOOM_W = PANEL_W
ZOOM_H = round(ZOOM_W * SRC_H / SRC_W)
ZOOM_SEC = 0.3  # video seconds for each zoom in or out
TILE_BG = (36, 39, 46)
INTRO_SEC, OUTRO_SEC, WEBMCP_SEC = 4.0, 7.0, 8.0
GEMINI = (180, 140, 255)
# WindTunnel WebMCP runs where Clover (wm-claude arm) and Gemini 3.6 Flash (wm-gemini) did the same tasks.
WEBMCP_GLOB = os.path.join(HERE, "..", "windtunnel", "results-diffuspace", "2026-10-15-*", "results.csv")
WEBMCP_MODELS = [("qwen36-iter22000-blk16-arverify-best", "DiffuSpace Clover", SIDES[0][2]),
                 ("gemini-3.6-flash", "Gemini 3.6 Flash", GEMINI)]
INTRO = {"ours": "Diffusion language model", "qwen": "Autoregressive language model"}
# Tile labels share a row with the status, so they need to be short.
SHORT = {"find-word": "Find a word", "copy-paste": "Copy and paste", "login-user-popup": "Log in",
         "use-colorwheel": "Pick a color", "use-slider": "Set a slider", "click-scroll-list": "Pick from a list",
         "form-sequence-2": "Fill a form"}


MONO = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 17)
MONO_COLS, MONO_LINE = 84, 21
THINK_BG = (13, 14, 17)


def reasoning_tokens(step):
    usage = step.get("usage") or {}
    return (usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or usage.get("reasoning_tokens") or 0


def thinking_at(take, t_rel):
    """What the model had streamed t_rel seconds into the take's video, or None without stream data."""
    steps, t0 = take.get("step_log") or [], take.get("video_t0")
    if not t0 or not steps or not all(st.get("timeline") is not None for st in steps):
        return None
    current = None
    for k, st in enumerate(steps):
        start = st["t_start"] - t0
        if t_rel < start:
            break
        current = (k, st, start)
    if current is None:
        return {"phase": "loading", "tokens": 0}
    k, st, start = current
    before = sum(reasoning_tokens(x) for x in steps[:k])
    dt, full, rt = t_rel - start, st["reasoning"], reasoning_tokens(st)
    if dt >= st["latency_s"]:
        return {"phase": "acting", "step": k + 1, "reasoning": full, "content": st["content"],
                "tokens": before + rt, "step_tokens": rt}
    r_len = c_len = 0
    for e_t, e_r, e_c in st["timeline"]:
        if e_t > dt:
            break
        r_len, c_len = e_r, e_c
    step_tok = round(rt * r_len / len(full)) if full else 0
    phase = "waiting" if not r_len and not c_len else ("thinking" if not c_len else "answering")
    return {"phase": phase, "step": k + 1, "wait": dt, "reasoning": full[:r_len],
            "content": st["content"][:c_len], "tokens": before + step_tok, "step_tokens": step_tok}


def draw_thinking(d, x0, state):
    zx, zy, zw, zh = zoom_rect(x0)
    top, bottom = zy + zh + 14, GRID_Y + GRID_H
    d.rectangle((x0, top, x0 + PANEL_W, bottom), fill=THINK_BG, outline=(60, 64, 72))
    if state["phase"] == "loading":
        return
    if state["phase"] == "waiting":
        head, col = f"Step {state['step']}: waiting for the first token  {state['wait']:.1f} s", DIM
    elif state["phase"] == "acting":
        head, col = f"Step {state['step']}: thought for {state['step_tokens']:,} tokens, acting", FG
    else:
        head, col = f"Step {state['step']}: thinking  {state['step_tokens']:,} tokens", YELLOW
    d.text((x0 + 12, top + 18), head, font=font(24, True), fill=col, anchor="lm")
    lines = []
    for para in state["reasoning"].strip().split("\n"):
        lines += textwrap.wrap(para, MONO_COLS) or [""]
    answer = state["content"].strip()
    if answer:
        lines += textwrap.wrap("→ " + answer.replace("\n", " "), MONO_COLS)
    room = (bottom - top - 44) // MONO_LINE
    shade = DIM if state["phase"] == "acting" else (200, 200, 200)
    for n, line in enumerate(lines[-room:]):
        is_answer = answer and n >= len(lines[-room:]) - len(textwrap.wrap("→ " + answer.replace("\n", " "), MONO_COLS))
        d.text((x0 + 12, top + 40 + n * MONO_LINE), line, font=MONO, fill=GREEN if is_answer else shade)


def cell_rect(i, x0):
    r, c = divmod(i, COLS)
    x = x0 + c * (TILE_W + GAP_X)
    y = GRID_Y + r * (CELL_H + GAP_Y)
    return x, y, TILE_W, THUMB_H


def zoom_rect(x0):
    return x0, GRID_Y + (GRID_H - ZOOM_H) // 2, ZOOM_W, ZOOM_H


def ease(p):
    p = min(max(p, 0.0), 1.0)
    return p * p * (3 - 2 * p)


def lerp_rect(a, b, p):
    return tuple(round(a[k] + (b[k] - a[k]) * p) for k in range(4))


def speed_stats(takes, model):
    """Decode speed, time to first token and pass count from one model's streamed takes.

    Decode speed is completion tokens over the time after the first token, so
    network and queueing before the first token are left out of it.
    """
    tokens = decode_s = model_s = calls = 0
    ttfts = []
    rows = [r for (_, m), r in takes.items() if m == model]
    for r in rows:
        for st in r.get("step_log") or []:
            first = next((e[0] for e in st.get("timeline") or [] if e[1] or e[2]), None)
            if first is None:
                return None
            tokens += (st.get("usage") or {}).get("completion_tokens") or 0
            decode_s += st["latency_s"] - first
            model_s += st["latency_s"]
            calls += 1
            ttfts.append(first)
    return {"tok_s": tokens / decode_s, "ttft": statistics.median(ttfts), "per_step": model_s / calls,
            "calls": calls, "passed": sum(r["passed"] for r in rows), "tasks": len(rows)}


def draw_intro(img, d, n_tasks):
    d.text((W // 2, 260), "MiniWoB++", font=font(96, True), fill=FG, anchor="mm")
    d.text((W // 2, 360), f"Selected {len(TASKS)} samples from {n_tasks} tasks",
           font=font(40), fill=DIM, anchor="mm")
    for (model, label, color), x0 in zip(SIDES, PANEL_X):
        d.rounded_rectangle((x0, 490, x0 + PANEL_W, 830), radius=18, fill=TILE_BG)
        d.text((x0 + PANEL_W // 2, 615), label, font=font(72, True), fill=color, anchor="mm")
        d.text((x0 + PANEL_W // 2, 720), INTRO[model], font=font(38), fill=FG, anchor="mm")


def webmcp_stats(pattern):
    """Agent-time median, mean and p90 per model over the tasks both models ran."""
    rows = [r for f in sorted(glob.glob(pattern)) for r in csv.DictReader(open(f))]
    by_model = {m: [r for r in rows if r["model"] == m] for m, _, _ in WEBMCP_MODELS}
    if not all(by_model.values()):
        return None
    shared = set.intersection(*({r["task_id"] for r in v} for v in by_model.values()))
    out = {}
    for m, v in by_model.items():
        v = [r for r in v if r["task_id"] in shared]
        times = sorted(float(r["agent_s"]) for r in v)
        out[m] = {"Median": statistics.median(times), "Mean": statistics.mean(times),
                  "90th percentile": times[int(0.9 * len(times))],
                  "passed": sum(r["success"] == "true" for r in v), "attempts": len(v)}
    return {"models": out, "tasks": len(shared), "repeats": round(out[WEBMCP_MODELS[0][0]]["attempts"] / len(shared))}


def draw_webmcp(img, d, ws, t):
    """Horizontal bars for agent time, growing in over the first second."""
    grow = ease(t / 1.0)
    d.text((W // 2, 100), "WebMCP agent time", font=font(64, True), fill=FG, anchor="mm")
    d.text((W // 2, 165), f"WindTunnel, {ws['tasks']} tasks × {ws['repeats']} attempts each  ·  "
           "seconds per attempt, lower is better", font=font(30), fill=DIM, anchor="mm")
    lx = 300
    for k, (m, label, color) in enumerate(WEBMCP_MODELS):
        st = ws["models"][m]
        x = lx + k * 700
        d.rounded_rectangle((x, 228, x + 28, 256), radius=4, fill=color)
        d.text((x + 44, 242), label, font=font(32, True), fill=FG, anchor="lm")
        d.text((x + 44 + d.textlength(label, font=font(32, True)) + 16, 242),
               f"{st['passed']} of {st['attempts']} passed", font=font(28), fill=DIM, anchor="lm")
    metrics = ["Median", "Mean", "90th percentile"]
    top = max(ws["models"][m][k] for m, _, _ in WEBMCP_MODELS for k in metrics)
    x0, max_w, bar_h, gap = 470, 1180, 58, 6
    for g, metric in enumerate(metrics):
        y = 320 + g * 230
        ours, theirs = (ws["models"][m][metric] for m, _, _ in WEBMCP_MODELS)
        d.text((120, y + bar_h + gap // 2), metric, font=font(38, True), fill=FG, anchor="lm")
        d.text((120, y + bar_h + gap // 2 + 48), f"{theirs / ours:.1f}x faster", font=font(30), fill=DIM,
               anchor="lm")
        for k, (m, _, color) in enumerate(WEBMCP_MODELS):
            v = ws["models"][m][metric]
            by = y + k * (bar_h + gap)
            w = max(8, round(max_w * v / top * grow))
            # Square at the baseline, 4 px rounded at the data end.
            d.rounded_rectangle((x0, by, x0 + w, by + bar_h), radius=4, fill=color)
            d.rectangle((x0, by, x0 + min(w, 4), by + bar_h), fill=color)
            if grow > 0.9:
                d.text((x0 + w + 16, by + bar_h // 2), f"{v:.2f} s", font=font(34, True), fill=FG, anchor="lm")
    d.line((x0, 300, x0, 320 + 2 * 230 + 2 * bar_h + gap + 20), fill=(70, 74, 82), width=2)
    d.text((W // 2, 1030), "Agent time excludes site reset and setup. Runs from October 15, 2026, "
           "with the same WebMCP tools and prompts for both models.", font=font(24), fill=DIM, anchor="mm")


def draw_outro(img, d, stats):
    ours, qwen = stats["ours"], stats["qwen"]
    labels = {m: (label, color) for m, label, color in SIDES}
    d.text((W // 2, 130), f"{labels['ours'][0]} decodes {ours['tok_s'] / qwen['tok_s']:.1f}x faster",
           font=font(68, True), fill=FG, anchor="mm")
    for (model, label, color), x0 in zip(SIDES, PANEL_X):
        st = stats[model]
        d.rounded_rectangle((x0, 230, x0 + PANEL_W, 880), radius=18, fill=TILE_BG)
        d.text((x0 + PANEL_W // 2, 300), label, font=font(48, True), fill=color, anchor="mm")
        d.text((x0 + PANEL_W // 2, 450), f"{st['tok_s']:.0f}", font=font(220, True), fill=color, anchor="mm")
        d.text((x0 + PANEL_W // 2, 575), "tokens per second (TPS)", font=font(48, True), fill=color, anchor="mm")
        rows = [("Time to first token", f"{st['ttft']:.2f} s"),
                ("Model time per step", f"{st['per_step']:.2f} s"),
                ("Tasks passed", f"{st['passed']} of {st['tasks']}")]
        for k, (name, value) in enumerate(rows):
            y = 700 + k * 56
            d.text((x0 + 60, y), name, font=font(32), fill=DIM, anchor="lm")
            d.text((x0 + PANEL_W - 60, y), value, font=font(32, True), fill=FG, anchor="rm")
    d.text((W // 2, 950), "Tokens per second = output tokens ÷ (call time − time to first token), "
           f"over all {ours['calls']} and {qwen['calls']} model calls above.", font=font(26), fill=DIM, anchor="mm")
    d.text((W // 2, 995), "Time to first token includes the network round trip to each endpoint.",
           font=font(26), fill=DIM, anchor="mm")


class SideReader:
    """Streams one side's sped-up frames in step with the output frames."""

    def __init__(self, path):
        self.proc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "rawvideo",
                                      "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.last = Image.new("RGB", (SRC_W, SRC_H), TILE_BG)

    def next(self):
        buf = self.proc.stdout.read(SRC_W * SRC_H * 3)
        if len(buf) == SRC_W * SRC_H * 3:
            self.last = Image.frombytes("RGB", (SRC_W, SRC_H), buf)
        return self.last


def draw_label(d, x, y, name, status, color):
    d.text((x + 10, y + THUMB_H + LABEL_H // 2), name, font=font(24), fill=FG, anchor="lm")
    d.text((x + TILE_W - 10, y + THUMB_H + LABEL_H // 2), status, font=font(22, True),
           fill=color, anchor="rm")


def draw_side(img, d, model, label, color, x0, segs, total, frame, prev, thumbs, tv, speed):
    t_real = tv * speed
    finished = all(s["end"] <= t_real for s in segs)
    won = finished and all(s["passed"] for s in segs)
    clock = total if finished else t_real
    d.text((x0, 190), label, font=font(46, True), fill=color, anchor="lm")
    d.text((x0 + PANEL_W, 190), f"{clock:5.1f} s", font=font(46, True),
           fill=GREEN if won else FG, anchor="rm")

    active = None
    for i, seg in enumerate(segs):
        name = SHORT[seg["task"]]
        x, y, w, h = cell_rect(i, x0)
        ts, te = seg["start"] / speed, seg["end"] / speed
        if tv >= te:
            if i not in thumbs:
                # The current frame already belongs to the next task, so keep the one before.
                thumbs[i] = prev.resize((w, h), Image.LANCZOS)
            img.paste(thumbs[i], (x, y))
            ok = seg["passed"]
            d.rectangle((x, y + h, x + w, y + h + LABEL_H), fill=TILE_BG)
            draw_label(d, x, y, name, "done · passed" if ok else "done · failed", GREEN if ok else RED)
            d.text((x + w - 12, y + 10), "✓" if ok else "✗", font=SYMBOLS, fill=GREEN if ok else RED,
                   anchor="rt")
        else:
            d.rectangle((x, y, x + w, y + h + LABEL_H), fill=TILE_BG)
            if tv >= ts:
                active = (i, ts, te)
                draw_label(d, x, y, name, "running", YELLOW)
            else:
                d.text((x + w // 2, y + h // 2), "waiting", font=font(28), fill=DIM, anchor="mm")
                draw_label(d, x, y, name, "", DIM)

    # The eighth cell holds the running tally.
    x, y, w, h = cell_rect(len(segs), x0)
    done = [s for s in segs if s["end"] <= t_real]
    d.text((x + 10, y + 40), f"{len(done)} of {len(segs)} done", font=font(36, True),
           fill=GREEN if won else FG, anchor="lm")
    d.text((x + 10, y + 90), f"{sum(s['passed'] for s in done)} passed", font=font(30), fill=DIM,
           anchor="lm")
    states = {}
    for s in segs:
        if s["start"] <= t_real < s["end"]:
            states[s["task"]] = thinking_at(s["take"], t_real - s["start"])
    if all(thinking_at(s["take"], 0) is not None for s in segs):
        spent = sum(sum(reasoning_tokens(st) for st in s["take"]["step_log"]) for s in done)
        spent += sum(st["tokens"] for st in states.values() if st)
        d.text((x + 10, y + 140), f"{spent:,} thinking tokens", font=font(30), fill=DIM, anchor="lm")

    if active:
        i, ts, te = active
        p = min(ease((tv - ts) / ZOOM_SEC), ease((te - tv) / ZOOM_SEC))
        x, y, w, h = lerp_rect(cell_rect(i, x0), zoom_rect(x0), p)
        shade = Image.new("RGBA", (PANEL_W, GRID_H), (*BG, round(200 * p)))
        img.paste(shade, (x0, GRID_Y), shade)
        img.paste(frame.resize((w, h), Image.LANCZOS), (x, y))
        if p > 0.5:
            d.text((x, y - 12), TASKS[i][1], font=font(30, True), fill=YELLOW, anchor="lb")
            state = states.get(segs[i]["task"])
            if state:
                draw_thinking(d, x0, state)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", help="Directory written by record_takes.py")
    parser.add_argument("--seed", type=int, required=True, help="Seed whose takes both sides play")
    parser.add_argument("--speed", type=float, default=3.3, help="Playback speed for both sides")
    parser.add_argument("--length", type=float, help="Video length in seconds (default: until both sides finish)")
    parser.add_argument("--out", help="Output path (default <run_dir>/race_grid_seed-<seed>.mp4)")
    parser.add_argument("--webmcp", default=WEBMCP_GLOB, help="WindTunnel results.csv glob for the closing card")
    args = parser.parse_args()

    run_dir = os.path.abspath(args.run_dir)
    takes = {}
    with open(os.path.join(run_dir, "takes.jsonl")) as f:
        for line in f:
            r = json.loads(line)
            if r["seed"] == args.seed:
                takes[(r["task"], r["model"])] = r
    out = args.out or os.path.join(run_dir, f"race_grid_seed-{args.seed}.mp4")
    recorded = datetime.fromtimestamp(min(r["video_t0"] for r in takes.values()))
    recorded = f"{recorded:%B} {recorded.day}, {recorded.year}"
    args.length = args.length or fit_length(run_dir, takes, args.speed)

    sides, readers = {}, {}
    for model, label, _ in SIDES:
        tmp = os.path.join(run_dir, f".grid_{model}.mp4")
        segs, total = build_side(run_dir, takes, model, tmp, args.speed, args.length, size=(SRC_W, SRC_H))
        sides[model] = (segs, total)
        readers[model] = (SideReader(tmp), tmp)
        print(f"{label}: {total:.1f} s real time, {sum(s['passed'] for s in segs)}/{len(segs)} passed, "
              f"ends on screen at {total / args.speed:.1f} s")

    ff = subprocess.Popen([
        "ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", out,
    ], stdin=subprocess.PIPE)
    stats = {m: speed_stats(takes, m) for m, _, _ in SIDES}
    if not all(stats.values()):
        print("No stream timeline in these takes, so the outro is skipped; record with MINIWOB_STREAM=1")
    n_tasks = len(glob.glob(os.path.join(HERE, "miniwob-plusplus", "miniwob", "html", "miniwob", "*.html")))
    for k in range(int(INTRO_SEC * FPS)):
        img = Image.new("RGB", (W, H), BG)
        draw_intro(img, ImageDraw.Draw(img), n_tasks)
        ff.stdin.write(img.tobytes())
    thumbs = {m: {} for m, _, _ in SIDES}
    prev = {m: readers[m][0].last for m, _, _ in SIDES}
    for k in range(int(args.length * FPS)):
        tv = k / FPS
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        d.text((W // 2, 52), "Same 7 web tasks, run back to back", font=font(52, True), fill=FG, anchor="mm")
        d.text((W // 2, 112), f"MiniWoB++, seed {args.seed} for both models  ·  playback {args.speed:g}x  ·  "
               f"Qwen via Alibaba's hosted API, recorded {recorded}", font=font(26), fill=DIM, anchor="mm")
        for (model, label, color), x0 in zip(SIDES, PANEL_X):
            frame = readers[model][0].next()
            draw_side(img, d, model, label, color, x0, *sides[model], frame, prev[model], thumbs[model],
                      tv, args.speed)
            prev[model] = frame
        ff.stdin.write(img.tobytes())
    if all(stats.values()):
        for k in range(int(OUTRO_SEC * FPS)):
            img = Image.new("RGB", (W, H), BG)
            draw_outro(img, ImageDraw.Draw(img), stats)
            ff.stdin.write(img.tobytes())
    ws = webmcp_stats(args.webmcp)
    if ws:
        for k in range(int(WEBMCP_SEC * FPS)):
            img = Image.new("RGB", (W, H), BG)
            draw_webmcp(img, ImageDraw.Draw(img), ws, k / FPS)
            ff.stdin.write(img.tobytes())
    else:
        print(f"No WindTunnel results for both models at {args.webmcp}, so the WebMCP card is skipped")
    ff.stdin.close()
    ff.wait()
    for reader, tmp in readers.values():
        reader.proc.kill()
        os.remove(tmp)
    print(out)


if __name__ == "__main__":
    main()
