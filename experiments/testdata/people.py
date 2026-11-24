"""Smoke test: can each model generate a group of people whose attributes follow a target distribution?

Each request asks for 20 fictional adults. The targets, stated in the prompt:
  height  normal, men 171.0 cm (SD 6.5), women 159.5 cm (SD 6.0), one decimal place
  age     uniform integers 18 to 79
  BMI     about 23 (SD 3), via weight
Checks, all in code:
  per batch   valid JSON, 20 people, required fields, plausible values, men and women both present
  per cell    pooled over valid batches: mean error and SD ratio per sex, Kolmogorov-Smirnov distance
              to the target normal, share beyond 2 SD (target 4.6%), share of heights ending in .0
              (target about 10%), age KS distance to uniform, BMI mean and SD, mean within-batch SD
              ratio, and repeated names

Run from the repo root:
    PYTHONPATH=. python experiments/testdata/people.py --batches 10
"""
import argparse, asyncio, json, math, re, statistics, time
from collections import Counter
from pathlib import Path

from bench.synthdata import arms

TARGET = {"男": (171.0, 6.5), "女": (159.5, 6.0)}
AGE_LO, AGE_HI = 18, 79
N = 20
PROMPT = f"""请生成 {N} 位虚构的中国成年人，用作测试数据。要求：
- 性别大致各半；
- 年龄为 {AGE_LO} 到 {AGE_HI} 岁之间的整数，均匀分布；
- 身高服从正态分布：男性均值 171.0 厘米、标准差 6.5；女性均值 159.5 厘米、标准差 6.0；保留一位小数；
- 体重使 BMI 大致服从均值 23、标准差 3 的分布，保留一位小数；
- 姓名、职业、城市真实多样。
只输出一个 JSON 数组，每个元素为 {{"name": 姓名, "sex": "男"或"女", "age": 整数, "height_cm": 数字, "weight_kg": 数字, "occupation": 职业, "city": 城市}}，不要解释。"""


def norm_cdf(x, mu, sd):
    return 0.5 * (1 + math.erf((x - mu) / (sd * math.sqrt(2))))


def ks(values, cdf):
    """Kolmogorov-Smirnov distance between the sample and a target CDF."""
    xs = sorted(values)
    n = len(xs)
    return max(max(abs((i + 1) / n - cdf(x)), abs(i / n - cdf(x))) for i, x in enumerate(xs)) if n else None


def parse(text):
    t = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text.strip()).strip()
    m = re.search(r"\[.*\]", t, re.S)
    return json.loads(m.group(0) if m else t)


def check_batch(people):
    """Returns (clean people, reason or None). A batch fails as a whole if it isn't usable."""
    if not isinstance(people, list) or len(people) != N:
        return [], f"count {len(people) if isinstance(people, list) else 'n/a'}"
    out = []
    for p in people:
        try:
            sex, age, h, w = p["sex"], p["age"], float(p["height_cm"]), float(p["weight_kg"])
            if sex not in TARGET or not isinstance(age, int) or not str(p.get("name", "")).strip():
                return [], "field values"
            if not (AGE_LO <= age <= AGE_HI and 120 <= h <= 220 and 30 <= w <= 200):
                return [], "implausible value"
            out.append({**p, "height_cm": h, "weight_kg": w, "bmi": w / (h / 100) ** 2})
        except (KeyError, TypeError, ValueError):
            return [], "fields"
    if len({p["sex"] for p in out}) < 2:
        return [], "one sex only"
    return out, None


def cell_stats(batches):
    people = [p for b in batches for p in b]
    s = {"batches": len(batches), "people": len(people)}
    for sex, (mu, sd) in TARGET.items():
        hs = [p["height_cm"] for p in people if p["sex"] == sex]
        if len(hs) < 3:
            continue
        m, d = statistics.mean(hs), statistics.stdev(hs)
        s[sex] = {"n": len(hs), "mean": m, "mean_err": m - mu, "sd": d, "sd_ratio": d / sd,
                  "ks": ks(hs, lambda x: norm_cdf(x, mu, sd)),
                  "tails": sum(abs(h - mu) > 2 * sd for h in hs) / len(hs),
                  "within_sd_ratio": statistics.mean(
                      statistics.stdev(v) / sd for b in batches
                      if len(v := [p["height_cm"] for p in b if p["sex"] == sex]) >= 3)}
    hs = [p["height_cm"] for p in people]
    s["heaping_.0"] = sum(abs(h - round(h)) < 1e-9 for h in hs) / len(hs) if hs else None
    s["heaping_0or5"] = sum(round(h) % 5 == 0 and abs(h - round(h)) < 1e-9 for h in hs) / len(hs) if hs else None
    ages = [p["age"] for p in people]
    s["age_ks"] = ks(ages, lambda x: min(1, max(0, (x - AGE_LO + 1) / (AGE_HI - AGE_LO + 1))))
    bmis = [p["bmi"] for p in people]
    s["bmi_mean"], s["bmi_sd"] = statistics.mean(bmis), statistics.stdev(bmis)
    s["male_share"] = sum(p["sex"] == "男" for p in people) / len(people)
    names = Counter(p["name"] for p in people)
    s["repeated_name_share"] = sum(c for c in names.values() if c > 1) / len(people)
    return s


async def run(a):
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cells = [tuple(c.split(":")) for c in a.cells]

    async def cell(arm, temp):
        client = arms.client(arm)
        sem = asyncio.Semaphore(a.concurrency)
        t0 = time.time()

        async def one(i):
            async with sem:
                ts = time.time()
                row = {"arm": arm, "temp": float(temp), "i": i}
                try:
                    r = await client.chat.completions.create(
                        model=arms.ARMS[arm]["model"], temperature=float(temp), max_tokens=3000, seed=9000 + i,
                        extra_body=arms.ARMS[arm]["extra"], messages=[{"role": "user", "content": PROMPT}])
                    row.update(raw=r.choices[0].message.content or "", completion_tokens=r.usage.completion_tokens,
                               finish_reason=r.choices[0].finish_reason)
                except Exception as e:
                    row.update(raw="", error=repr(e)[:200])
            row.update(latency_s=round(time.time() - ts, 2), t_done=round(time.time() - t0, 2))
            try:
                people, why = check_batch(parse(row["raw"]))
            except Exception as e:
                people, why = [], f"json {type(e).__name__}"
            row.update(people=people, valid=why is None, reason=why or "ok")
            with out.open("a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        await asyncio.gather(*(one(i) for i in range(a.batches)))
        print(arm, temp, "done in", round(time.time() - t0, 1), "s", flush=True)

    by_arm = {}
    for arm, temp in cells:
        by_arm.setdefault(arm, []).append(temp)

    async def arm_run(arm):
        for t in by_arm[arm]:
            await cell(arm, t)

    await asyncio.gather(*map(arm_run, by_arm))


def report(path):
    rows = [json.loads(l) for l in open(path)]
    print("cell      | valid | sex | height mean err (M/F) | SD ratio (M/F) | within-batch SD | KS (M/F) | "
          "tails >2SD | .0 heaping | age KS | BMI | repeated names | wall s")
    for c in sorted({(r["arm"], r["temp"]) for r in rows}):
        rs = [r for r in rows if (r["arm"], r["temp"]) == c]
        good = [r["people"] for r in rs if r["valid"]]
        fails = Counter(r["reason"] for r in rs if not r["valid"])
        if not good:
            print(f"{c[0]} {c[1]} | 0/{len(rs)} | {dict(fails)}")
            continue
        s = cell_stats(good)
        M, F = s.get("男", {}), s.get("女", {})
        f2 = lambda k, fmt: f"{format(M.get(k, float('nan')), fmt)}/{format(F.get(k, float('nan')), fmt)}"
        print(f"{c[0]} {c[1]:<4}| {len(good):2d}/{len(rs)} | {s['male_share']:.0%} | {f2('mean_err', '+.1f')} | "
              f"{f2('sd_ratio', '.2f')} | {f2('within_sd_ratio', '.2f')} | {f2('ks', '.2f')} | "
              f"{(M.get('tails', 0) * M.get('n', 0) + F.get('tails', 0) * F.get('n', 0)) / s['people']:.1%} | "
              f"{s['heaping_.0']:.0%} | {s['age_ks']:.2f} | {s['bmi_mean']:.1f}±{s['bmi_sd']:.1f} | "
              f"{s['repeated_name_share']:.0%} | {max(r['t_done'] for r in rs):.0f}"
              + (f"  fails {dict(fails)}" if fails else ""))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--cells", nargs="+", default=["dllm:0.6", "dllm:0.8", "qwen:0.6", "qwen:0.8", "qwen:1.0", "qwen:1.2"])
    p.add_argument("--batches", type=int, default=10)
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--out", default="experiments/testdata/results/people.jsonl")
    p.add_argument("--report", action="store_true")
    a = p.parse_args()
    if not a.report:
        asyncio.run(run(a))
    report(a.out)
