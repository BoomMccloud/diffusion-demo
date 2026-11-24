"""Mock frames for the people video: a name wall per model and a shared discovery curve.

Uses the smoke rows in results/people_bmi.jsonl (dLLM 0.6 against Qwen 0.8) and the race-video
style constants. Writes mock_mid.png and mock_end.png next to this file.

Run from the repo root:
    python experiments/testdata/mock_frame.py
"""
import json, os, sys
from collections import Counter

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "bench", "miniwob"))
from make_race_video import BG, DIM, FG, GREEN, H, SIDES, W, YELLOW, font  # noqa: E402

CJK = "/System/Library/Fonts/Hiragino Sans GB.ttc"
ARMS = [("dllm", 0.6, SIDES[0][1], SIDES[0][2]), ("qwen", 0.8, "Qwen3.6-35B-A3B", SIDES[1][2])]
PANEL_X, PANEL_W = (40, 980), 900
WALL_Y, WALL_H = 230, 470
CHART_Y, CHART_H = 760, 250
TILE = (36, 39, 46)


def cjk(size):
    return ImageFont.truetype(CJK, size)


def load():
    rows = [json.loads(l) for l in open(os.path.join(HERE, "results", "people_bmi.jsonl"))]
    out = {}
    for arm, temp, *_ in ARMS:
        rs = sorted((r for r in rows if (r["arm"], r["temp"]) == (arm, temp) and r["valid"]), key=lambda r: r["t_done"])
        out[arm] = [(r["t_done"], [p["name"] for p in r["people"]]) for r in rs]
    return out


def draw_wall(d, x0, names, color):
    """Flow layout of name tags; a repeated name is one bigger tag with a count."""
    counts = Counter(names)
    order = list(dict.fromkeys(names))
    x, y, row_h = x0 + 14, WALL_Y + 14, 0
    for n in order:
        c = counts[n]
        f = cjk(22 if c == 1 else 26 if c == 2 else 30)
        label = n if c == 1 else f"{n} ×{c}"
        w = d.textlength(label, font=f) + 20
        h = (34 if c == 1 else 40 if c == 2 else 46)
        if x + w > x0 + PANEL_W - 14:
            x, y, row_h = x0 + 14, y + row_h + 8, 0
        if y + h > WALL_Y + WALL_H - 10:
            break
        fill = (52, 56, 66) if c == 1 else color
        text = FG if c == 1 else BG
        d.rounded_rectangle((x, y, x + w, y + h), radius=8, fill=fill)
        d.text((x + w / 2, y + h / 2), label, font=f, fill=text, anchor="mm")
        x += w + 8
        row_h = max(row_h, h)


def draw_frame(data, t, out):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((W // 2, 50), "“Fill in name, occupation and city for 20 people.”", font=font(38, True), fill=FG, anchor="mm")
    d.text((W // 2, 108), "Ages, heights and weights drawn from target distributions  ·  same inputs for both  ·  "
           "real completion times", font=font(28), fill=YELLOW, anchor="mm")
    end = max(b[-1][0] for b in data.values())
    for (arm, temp, label, color), x0 in zip(ARMS, PANEL_X):
        batches = data[arm]
        done = [n for tt, ns in batches if tt <= t for n in ns]
        fin = t >= batches[-1][0]
        d.text((x0, 180), label, font=font(46, True), fill=color, anchor="lm")
        d.text((x0 + PANEL_W, 180), f"{min(t, batches[-1][0]):5.1f} s", font=font(46, True),
               fill=GREEN if fin else FG, anchor="rm")
        d.rounded_rectangle((x0, WALL_Y, x0 + PANEL_W, WALL_Y + WALL_H), radius=10, fill=TILE)
        draw_wall(d, x0, done, color)
        rep = sum(c for c in Counter(done).values() if c > 1)
        d.text((x0, 728), f"{len(done)} people  ·  {len(set(done))} distinct names  ·  "
               f"{rep / max(len(done), 1):.0%} share a name", font=font(32), fill=DIM, anchor="lm")
    # Shared discovery curve: distinct names found so far against elapsed seconds.
    cx0, cx1 = 140, W - 60
    d.rounded_rectangle((40, CHART_Y, W - 40, CHART_Y + CHART_H), radius=10, fill=TILE)
    ymax = 180
    px = lambda s: cx0 + (cx1 - cx0) * s / end
    py = lambda v: CHART_Y + CHART_H - 40 - (CHART_H - 70) * v / ymax
    for v in (0, 50, 100, 150):
        d.line((cx0, py(v), cx1, py(v)), fill=(50, 54, 62))
        d.text((cx0 - 12, py(v)), str(v), font=font(22), fill=DIM, anchor="rm")
    for s in range(0, int(end) + 1, 10):
        d.text((px(s), CHART_Y + CHART_H - 18), f"{s} s", font=font(22), fill=DIM, anchor="mm")
    d.text((cx0, CHART_Y + 22), "Distinct names found so far", font=font(26, True), fill=FG, anchor="lm")
    for (arm, temp, label, color), _ in zip(ARMS, PANEL_X):
        seen, pts = set(), [(px(0), py(0))]
        for tt, ns in data[arm]:
            if tt > t:
                break
            pts.append((px(tt), pts[-1][1]))
            seen.update(ns)
            pts.append((px(tt), py(len(seen))))
        if t < data[arm][-1][0]:
            pts.append((px(t), pts[-1][1]))
        d.line(pts, fill=color, width=5, joint="curve")
        d.ellipse((pts[-1][0] - 8, pts[-1][1] - 8, pts[-1][0] + 8, pts[-1][1] + 8), fill=color)
        d.text((pts[-1][0] + 14, pts[-1][1]), f"{len(seen)}", font=font(28, True), fill=color, anchor="lm")
    img.save(out)


def main():
    data = load()
    ends = {a: b[-1][0] for a, b in data.items()}
    print("batch completion ends:", {a: round(e, 1) for a, e in ends.items()})
    draw_frame(data, ends["qwen"] * 0.45, os.path.join(HERE, "mock_mid.png"))
    draw_frame(data, ends["qwen"] + 1, os.path.join(HERE, "mock_end.png"))


if __name__ == "__main__":
    main()
