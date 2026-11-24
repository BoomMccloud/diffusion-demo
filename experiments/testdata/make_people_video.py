"""Race video for the people test data, in the style of the other race videos.

Reads results/people_video.jsonl (people_conditioned.py --sample-bmi, dLLM 0.6 against Qwen 0.8 on a
pinned OpenRouter provider) and writes people_race.mp4 next to this file: a 3 s intro, the race at one
playback speed for both sides, and a 5 s outro.

Each side has a name wall: one tag per distinct name, appearing when its request finished, and a
repeated name grows into a colored tag with its count. A shared chart below plots distinct names found
so far against elapsed seconds.

Run from the repo root:
    uv run --no-project --with pillow python3 experiments/testdata/make_people_video.py
"""
import argparse, json, math, os, subprocess, sys
from collections import Counter

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "bench", "miniwob"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "bench", "webarena"))
from make_race_video import BG, DIM, FG, FPS, GREEN, H, SIDES, W, YELLOW, font  # noqa: E402
from make_webarena_race import nice_speed  # noqa: E402

CJK = "/System/Library/Fonts/Hiragino Sans GB.ttc"
ARMS = [("dllm", SIDES[0][1], SIDES[0][2], "Diffusion language model"),
        ("qwen", "Qwen3.6-35B-A3B", SIDES[1][2], "Autoregressive language model")]
PANEL_X, PANEL_W = (40, 980), 900
WALL_Y, WALL_H = 220, 480
CHART_Y, CHART_H = 770, 250
TILE, SINGLE = (36, 39, 46), (52, 56, 66)
RACE_TARGET, INTRO_SEC, OUTRO_SEC, END_HOLD = 24.0, 3.0, 5.0, 1.5
STAGGER = 0.4  # video seconds over which one request's 20 names appear
TASK = "Fill in name, occupation and city for 20 people with a given sex, age, height and weight."
_fonts = {}


def cjk(size):
    if size not in _fonts:
        _fonts[size] = ImageFont.truetype(CJK, size)
    return _fonts[size]


def load(path):
    rows = [json.loads(l) for l in open(path)]
    out = {}
    for arm, *_ in ARMS:
        rs = sorted((r for r in rows if r["arm"] == arm), key=lambda r: r["t_done"])
        out[arm] = {"temp": rs[0]["temp"], "provider": next((r.get("provider") for r in rs if r.get("provider")), None),
                    "batches": [(r["t_done"], [p["name"] for p in r["people"]], r["valid"]) for r in rs],
                    "end": rs[-1]["t_done"], "people": sum(len(r["people"]) for r in rs),
                    "requested": 20 * len(rs), "occupations": len({p["occupation"] for r in rs for p in r["people"]})}
    return out


def tag_size(count, scale):
    f = round((18, 22, 26)[min(count, 3) - 1] * scale)
    return f, round((28, 34, 40)[min(count, 3) - 1] * scale)


def layout(d, order, counts, x0, scale):
    """Positions for each tag in a flow layout, or None if the wall overflows."""
    pos, x, y, row_h, pad = {}, x0 + 12, WALL_Y + 12, 0, max(4, round(7 * scale))
    for n in order:
        c = counts[n]
        f, h = tag_size(c, scale)
        label = n if c == 1 else f"{n} ×{c}"
        w = d.textlength(label, font=cjk(f)) + round(16 * scale)
        if x + w > x0 + PANEL_W - 12:
            x, y, row_h = x0 + 12, y + row_h + pad, 0
        if y + h > WALL_Y + WALL_H - 10:
            return None
        pos[n] = (x, y, w, h, f, label)
        x += w + pad
        row_h = max(row_h, h)
    return pos


def fit_scale(d, data):
    """The largest tag scale at which both final walls fit, so both sides share one scale."""
    scale = 1.0
    while scale > 0.3:
        if all(layout(d, list(dict.fromkeys(n for _, ns, _ in v["batches"] for n in ns)),
                      Counter(n for _, ns, _ in v["batches"] for n in ns), PANEL_X[0], scale) for v in data.values()):
            return scale
        scale -= 0.04
    return scale


def names_at(batches, tv, speed):
    """Names visible at video time tv; each request's names appear over STAGGER seconds."""
    out = []
    for t, ns, _ in batches:
        age = tv - t / speed
        if age < 0:
            break
        out += ns[:max(1, math.ceil(len(ns) * min(1.0, age / STAGGER)))] if age < STAGGER else ns
    return out


def draw_side(img, d, arm, label, color, x0, side, tv, speed, scale):
    t = min(tv * speed, side["end"])
    done = tv * speed >= side["end"]
    names = names_at(side["batches"], tv, speed)
    counts = Counter(names)
    d.text((x0, 175), label, font=font(46, True), fill=color, anchor="lm")
    d.text((x0 + PANEL_W, 175), f"{t:5.1f} s", font=font(46, True), fill=GREEN if done else FG, anchor="rm")
    d.rounded_rectangle((x0, WALL_Y, x0 + PANEL_W, WALL_Y + WALL_H), radius=10, fill=TILE)
    pos = layout(d, list(dict.fromkeys(names)), counts, x0, scale) or {}
    for n, (x, y, w, h, f, text) in pos.items():
        rep = counts[n] > 1
        d.rounded_rectangle((x, y, x + w, y + h), radius=round(7 * scale), fill=color if rep else SINGLE)
        d.text((x + w / 2, y + h / 2), text, font=cjk(f), fill=BG if rep else FG, anchor="mm")
    share = sum(c for c in counts.values() if c > 1) / max(len(names), 1)
    status = (f"Finished {len(side['batches'])} requests" if done else
              f"{sum(1 for bt, _, _ in side['batches'] if bt <= t)} of {len(side['batches'])} requests done")
    d.text((x0, 728), f"{len(names)} people  ·  {len(counts)} distinct names  ·  {share:.0%} share a name",
           font=font(26), fill=DIM, anchor="lm")
    d.text((x0 + PANEL_W, 728), status, font=font(26, True), fill=GREEN if done else FG, anchor="rm")


def draw_chart(d, data, tv, speed, slow):
    cx0, cx1 = 140, W - 150
    d.rounded_rectangle((40, CHART_Y, W - 40, CHART_Y + CHART_H), radius=10, fill=TILE)
    ymax = max(len({n for _, ns, _ in v["batches"] for n in ns}) for v in data.values()) * 1.1
    step = 50 if ymax < 300 else 100
    px = lambda s: cx0 + (cx1 - cx0) * s / slow
    py = lambda v: CHART_Y + CHART_H - 42 - (CHART_H - 76) * v / ymax
    for v in range(0, int(ymax) + 1, step):
        d.line((cx0, py(v), cx1, py(v)), fill=(50, 54, 62))
        d.text((cx0 - 12, py(v)), str(v), font=font(22), fill=DIM, anchor="rm")
    tick = 5 if slow <= 50 else 10
    for s in range(0, int(slow) + 1, tick):
        d.text((px(s), CHART_Y + CHART_H - 20), f"{s} s", font=font(22), fill=DIM, anchor="mm")
    d.text((cx0, CHART_Y + 24), "Distinct names found so far", font=font(26, True), fill=FG, anchor="lm")
    t = tv * speed
    for (arm, label, color, _) in ARMS:
        seen, pts = set(), [(px(0), py(0))]
        for bt, ns, _ in data[arm]["batches"]:
            if bt > t:
                break
            pts.append((px(bt), pts[-1][1]))
            seen.update(ns)
            pts.append((px(bt), py(len(seen))))
        pts.append((px(min(t, data[arm]["end"])), pts[-1][1]))
        d.line(pts, fill=color, width=5, joint="curve")
        x, y = pts[-1]
        d.ellipse((x - 8, y - 8, x + 8, y + 8), fill=color)
        d.text((x + 14, y), f"{len(seen)}", font=font(28, True), fill=color, anchor="lm")


def draw_intro(d, data):
    d.text((W // 2, 120), "Synthetic test data  ·  20 people per request", font=font(40), fill=DIM, anchor="mm")
    for k, line in enumerate(["“Fill in name, occupation and city for 20 people", "with a given sex, age, height and weight.”"]):
        d.text((W // 2, 230 + k * 70), line, font=font(54, True), fill=FG, anchor="mm")
    for (arm, label, color, kind), x0 in zip(ARMS, PANEL_X):
        d.rounded_rectangle((x0, 600, x0 + PANEL_W, 900), radius=18, fill=TILE)
        d.text((x0 + PANEL_W // 2, 710), label, font=font(68, True), fill=color, anchor="mm")
        d.text((x0 + PANEL_W // 2, 805), f"{kind}  ·  temperature {data[arm]['temp']:.1f}", font=font(38),
               fill=FG, anchor="mm")
    n = len(data["dllm"]["batches"])
    d.text((W // 2, 990), f"Same inputs for both, {n} requests each, 8 at a time. Ages, heights and weights drawn by code. "
           "One run, no retakes.", font=font(30), fill=DIM, anchor="mm")


def draw_outro(d, data):
    a, b = data["dllm"], data["qwen"]
    dn = {k: len({n for _, ns, _ in v["batches"] for n in ns}) for k, v in data.items()}
    head = (f"{b['end'] / a['end']:.1f}x faster, every record valid" if a["people"] == a["requested"]
            and b["people"] == b["requested"] else f"{b['end'] / a['end']:.1f}x faster")
    d.text((W // 2, H // 2 - 20), head, font=font(84, True), fill=FG, anchor="mm")
    d.text((W // 2, 960), f"Valid: {a['people']} of {a['requested']} people for both: the given values came back unchanged and "
           "every occupation fits its age.", font=font(26), fill=DIM, anchor="mm")
    d.text((W // 2, 1005), f"Distinct names {dn['dllm']} vs {dn['qwen']}, occupations {a['occupations']} vs "
           f"{b['occupations']}. Qwen via OpenRouter, provider {b['provider']} pinned.", font=font(26), fill=DIM,
           anchor="mm")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default=os.path.join(HERE, "results", "people_video.jsonl"))
    p.add_argument("--speed", type=float)
    p.add_argument("--out", default=os.path.join(HERE, "people_race.mp4"))
    p.add_argument("--frame", type=float, help="write one race frame at this video second as PNG and stop")
    args = p.parse_args()
    data = load(args.data)
    slow = max(v["end"] for v in data.values())
    speed = args.speed or nice_speed(slow / RACE_TARGET)
    length = slow / speed + END_HOLD
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    scale = fit_scale(probe, data)
    print(f"speed {speed:g}x, race {length:.1f} s, tag scale {scale:.2f}")

    def race_frame(tv):
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        d.text((W // 2, 50), f"“{TASK}”", font=font(36, True), fill=FG, anchor="mm")
        d.text((W // 2, 106), f"Same inputs for both  ·  playback {speed:g}x for both sides  ·  recorded October 20, 2026",
               font=font(28), fill=YELLOW, anchor="mm")
        for (arm, label, color, _), x0 in zip(ARMS, PANEL_X):
            draw_side(img, d, arm, label, color, x0, data[arm], tv, speed, scale)
        draw_chart(d, data, tv, speed, slow)
        return img

    if args.frame is not None:
        out = args.out.replace(".mp4", f"_{args.frame:g}.png")
        race_frame(args.frame).save(out)
        print(out)
        return
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18",
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", args.out], stdin=subprocess.PIPE)
    intro = Image.new("RGB", (W, H), BG)
    draw_intro(ImageDraw.Draw(intro), data)
    for _ in range(int(INTRO_SEC * FPS)):
        ff.stdin.write(intro.tobytes())
    for k in range(math.ceil(length * FPS)):
        ff.stdin.write(race_frame(k / FPS).tobytes())
    outro = Image.new("RGB", (W, H), BG)
    draw_outro(ImageDraw.Draw(outro), data)
    for _ in range(int(OUTRO_SEC * FPS)):
        ff.stdin.write(outro.tobytes())
    ff.stdin.close()
    ff.wait()
    print(args.out)


if __name__ == "__main__":
    main()
