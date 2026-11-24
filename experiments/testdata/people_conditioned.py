"""Smoke test: code samples the numbers, the model writes the people around them.

For each batch, code draws 20 people from the target distributions (same draws for every model):
sex alternating, age uniform 18-79, height normal (men 171.0 / 6.5, women 159.5 / 6.0). The model
returns each person with name, occupation, city and weight added. Checks, all in code:
  copy        id, sex, age and height come back unchanged
  weight      BMI between 15 and 40; pooled BMI compared with the target normal (23, SD 3)
  occupation  fits the age: students 30 or under, retirees 50 or over
  fields      name 2 to 4 Chinese characters, non-empty occupation and city
Variety: repeated names, distinct occupations and cities, near-duplicate people.

With --sample-bmi, code also draws BMI (normal 23, SD 3, clipped to 16-38) and passes the weight in,
so the model writes only name, occupation and city, and must return the weight unchanged.

Run from the repo root:
    PYTHONPATH=. python experiments/testdata/people_conditioned.py --batches 10
"""
import argparse, asyncio, json, random, re, statistics, sys, time
from collections import Counter
from pathlib import Path

from bench.synthdata import arms

sys.path.insert(0, str(Path(__file__).parent))
from people import TARGET, AGE_LO, AGE_HI, N, ks, norm_cdf, parse  # noqa: E402

BMI_MU, BMI_SD = 23.0, 3.0
PROMPT = """下面是 {n} 位虚构中国成年人的基本信息（用于测试数据），性别、年龄、身高已经确定：
{people}

请为每个人补充姓名、职业、所在城市和体重：
- 姓名、职业、城市要真实多样，职业要与年龄相符；
- 体重保留一位小数，使 BMI 大致服从均值 23、标准差 3 的分布；
- id、sex、age、height_cm 必须原样保留。
只输出一个 JSON 数组，每个元素为 {{"id": 编号, "sex": 性别, "age": 年龄, "height_cm": 身高, "name": 姓名, "occupation": 职业, "city": 城市, "weight_kg": 体重}}，不要解释。"""

PROMPT_BMI = """下面是 {n} 位虚构中国成年人的基本信息（用于测试数据），性别、年龄、身高、体重已经确定：
{people}

请为每个人补充姓名、职业和所在城市：
- 姓名、职业、城市要真实多样，职业要与年龄相符；
- id、sex、age、height_cm、weight_kg 必须原样保留。
只输出一个 JSON 数组，每个元素为 {{"id": 编号, "sex": 性别, "age": 年龄, "height_cm": 身高, "weight_kg": 体重, "name": 姓名, "occupation": 职业, "city": 城市}}，不要解释。"""

STUDENT = re.compile(r"学生|研究生|博士生|本科生")
RETIRED = re.compile(r"退休")


def sample_batch(b, bmi=False):
    """Code-side draws for batch b, identical for every model. The BMI draw uses its own generator,
    so ages and heights are the same with or without it."""
    rng, brng = random.Random(1000 + b), random.Random(5000 + b)
    out = []
    for k in range(N):
        sex = "男" if k % 2 == 0 else "女"
        mu, sd = TARGET[sex]
        g = {"id": k + 1, "sex": sex, "age": rng.randint(AGE_LO, AGE_HI), "height_cm": round(rng.gauss(mu, sd), 1)}
        if bmi:
            g["weight_kg"] = round(min(38, max(16, brng.gauss(BMI_MU, BMI_SD))) * (g["height_cm"] / 100) ** 2, 1)
        out.append(g)
    return out


def check(given, returned):
    """Returns (people with bmi, list of per-person problems, batch-level reason or None)."""
    if not isinstance(returned, list) or len(returned) != len(given):
        return [], [], f"count {len(returned) if isinstance(returned, list) else 'n/a'}"
    by_id = {}
    for p in returned:
        if isinstance(p, dict) and "id" in p:
            by_id[int(p["id"])] = p
    people, problems = [], []
    for g in given:
        p = by_id.get(g["id"])
        if p is None:
            problems.append("missing id")
            continue
        try:
            if (p["sex"] != g["sex"] or int(p["age"]) != g["age"] or abs(float(p["height_cm"]) - g["height_cm"]) > 1e-6
                    or "weight_kg" in g and abs(float(p["weight_kg"]) - g["weight_kg"]) > 1e-6):
                problems.append("changed given value")
                continue
            w = float(p["weight_kg"])
            bmi = w / (g["height_cm"] / 100) ** 2
            name, occ, city = str(p["name"]).strip(), str(p["occupation"]).strip(), str(p["city"]).strip()
        except (KeyError, TypeError, ValueError):
            problems.append("fields")
            continue
        if not re.fullmatch(r"[一-鿿·]{2,4}", name) or not occ or not city:
            problems.append("name/occupation/city")
        elif not 15 <= bmi <= 40:
            problems.append("implausible weight")
        elif STUDENT.search(occ) and g["age"] > 30 or RETIRED.search(occ) and g["age"] < 50:
            problems.append("occupation vs age")
        else:
            people.append({**g, "name": name, "occupation": occ, "city": city, "weight_kg": w, "bmi": bmi})
    return people, problems, None


async def run(a):
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cells = [tuple(c.split(":")) for c in a.cells]

    extra = {arm: dict(arms.ARMS[arm]["extra"]) for arm in arms.ARMS}
    if a.qwen_provider:
        # Pin one OpenRouter provider with no fallback, so Qwen's timing comes from one place.
        extra["qwen"]["provider"] = {"order": [a.qwen_provider], "allow_fallbacks": False}

    async def cell(arm, temp):
        client = arms.client(arm)
        sem = asyncio.Semaphore(a.concurrency)
        t0 = time.time()

        async def one(b):
            given = sample_batch(b, a.sample_bmi)
            prompt = (PROMPT_BMI if a.sample_bmi else PROMPT).format(n=N, people="\n".join(json.dumps(g, ensure_ascii=False) for g in given))
            async with sem:
                ts = time.time()
                row = {"arm": arm, "temp": float(temp), "batch": b}
                try:
                    r = await client.chat.completions.create(
                        model=arms.ARMS[arm]["model"], temperature=float(temp), max_tokens=3000, seed=9000 + b,
                        extra_body=extra[arm], messages=[{"role": "user", "content": prompt}])
                    row.update(raw=r.choices[0].message.content or "", completion_tokens=r.usage.completion_tokens,
                               provider=getattr(r, "provider", None) or (r.model_extra or {}).get("provider"))
                except Exception as e:
                    row.update(raw="", error=repr(e)[:200])
            row.update(latency_s=round(time.time() - ts, 2), t_done=round(time.time() - t0, 2))
            try:
                people, problems, why = check(given, parse(row["raw"]))
            except Exception as e:
                people, problems, why = [], [], f"json {type(e).__name__}"
            row.update(people=people, problems=problems, valid=why is None, reason=why or "ok")
            with out.open("a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        await asyncio.gather(*(one(b) for b in range(a.batches)))
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
    print("cell      | batches ok | people kept | problems | BMI mean±SD (KS) | repeated names | "
          "distinct names / occupations / cities | wall s")
    for c in sorted({(r["arm"], r["temp"]) for r in rows}):
        rs = [r for r in rows if (r["arm"], r["temp"]) == c]
        ok = [r for r in rs if r["valid"]]
        people = [p for r in ok for p in r["people"]]
        requested = N * len(rs)
        probs = Counter(p for r in ok for p in r["problems"]) + Counter(r["reason"] for r in rs if not r["valid"])
        if not people:
            print(f"{c[0]} {c[1]} | {len(ok)}/{len(rs)} | 0 | {dict(probs)}")
            continue
        bmis = [p["bmi"] for p in people]
        names = Counter(p["name"] for p in people)
        rep = sum(v for v in names.values() if v > 1) / len(people)
        print(f"{c[0]} {c[1]:<4}| {len(ok):2d}/{len(rs)} | {len(people):3d}/{requested} | {dict(probs.most_common(3))} | "
              f"{statistics.mean(bmis):.1f}±{statistics.stdev(bmis):.1f} ({ks(bmis, lambda x: norm_cdf(x, BMI_MU, BMI_SD)):.2f}) | "
              f"{rep:.0%} | {len(names)} / {len({p['occupation'] for p in people})} / {len({p['city'] for p in people})} | "
              f"{max(r['t_done'] for r in rs):.0f}")
    heights = [g for b in range(len({r['batch'] for r in rows})) for g in sample_batch(b)]
    for sex, (mu, sd) in TARGET.items():
        hs = [g["height_cm"] for g in heights if g["sex"] == sex]
        print(f"code-sampled {sex} heights: mean {statistics.mean(hs):.1f} SD {statistics.stdev(hs):.1f} "
              f"KS {ks(hs, lambda x: norm_cdf(x, mu, sd)):.2f}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--cells", nargs="+", default=["dllm:0.6", "dllm:0.8", "qwen:0.6", "qwen:0.8", "qwen:1.0", "qwen:1.2"])
    p.add_argument("--batches", type=int, default=10)
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--out", default="experiments/testdata/results/people_conditioned.jsonl")
    p.add_argument("--report", action="store_true")
    p.add_argument("--sample-bmi", action="store_true", help="code samples BMI too; the model writes text only")
    p.add_argument("--qwen-provider", help="pin this OpenRouter provider for Qwen, no fallback (e.g. CoreWeave)")
    a = p.parse_args()
    if not a.report:
        asyncio.run(run(a))
    report(a.out)
