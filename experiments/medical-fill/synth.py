"""Synthetic record generation: how much distinct, valid data does each model produce?

Both models get the same prompt many times and return one fictional inpatient summary as JSON.
Code checks each record (fields, age range, and no prescribed drug in the same class as an allergy).
A record is a duplicate when its (diagnosis, allergies, prescriptions) key was already seen in the cell.

Each (arm, temperature) cell runs as its own timed batch at fixed concurrency, so `t_done` is seconds
since that cell started. The two arms run at the same time against different endpoints; temperatures
run one after another within an arm.
"""
import argparse, asyncio, json, os, re, time
from pathlib import Path

from openai import AsyncOpenAI

import smoke as s

PROMPT = ("请生成一份虚构的中文住院病历摘要，用作测试数据。只输出一个 JSON 对象，字段如下："
          "name（虚构中文姓名）、sex（“男”或“女”）、age（18 到 95 的整数）、chief_complaint（主诉，一句话）、"
          "diagnosis（主要诊断）、allergies（过敏药物名称数组，没有则为空数组）、"
          "prescriptions（出院带药名称数组，1 到 4 个）。处方不得包含患者过敏的药物或与其同类的药物。不要解释。")

# Drug classes for the allergy check. Unknown drugs are not flagged.
CLASSES = {
    "penicillin": ["青霉素", "阿莫西林", "氨苄西林", "哌拉西林", "苯唑西林", "西林"],
    "cephalosporin": ["头孢"],
    "macrolide": ["红霉素", "阿奇霉素", "克拉霉素", "罗红霉素"],
    "quinolone": ["沙星"],
    "sulfonamide": ["磺胺"],
    "nsaid": ["阿司匹林", "布洛芬", "双氯芬酸", "萘普生", "吲哚美辛"],
    "tetracycline": ["环素"],
    "aminoglycoside": ["庆大霉素", "阿米卡星", "链霉素"],
}


def drug_class(name):
    return {c for c, keys in CLASSES.items() if any(k in name for k in keys)}


def validate(text):
    """Returns (record, None) or (None, reason)."""
    try:
        d = s.parse_json(text)
    except Exception:
        return None, "json"
    if not isinstance(d, dict):
        return None, "json"
    for k in ["name", "sex", "age", "chief_complaint", "diagnosis", "allergies", "prescriptions"]:
        if k not in d:
            return None, f"missing {k}"
    if not isinstance(d["name"], str) or not 2 <= len(d["name"]) <= 4:
        return None, "name"
    if d["sex"] not in ("男", "女"):
        return None, "sex"
    if not isinstance(d["age"], int) or not 18 <= d["age"] <= 95:
        return None, "age"
    for k in ["chief_complaint", "diagnosis"]:
        if not isinstance(d[k], str) or not d[k].strip():
            return None, k
    al, rx = d["allergies"], d["prescriptions"]
    if not isinstance(al, list) or not isinstance(rx, list) or not all(isinstance(x, str) for x in al + rx):
        return None, "lists"
    if not 1 <= len(rx) <= 4:
        return None, "rx count"
    allergy_classes = set().union(*map(drug_class, al)) if al else set()
    for p in rx:
        if any(a and (a in p or p in a) for a in al) or drug_class(p) & allergy_classes:
            return None, "allergy conflict"
    return d, None


def key(d):
    norm = lambda x: re.sub(r"\s", "", x)
    return (norm(d["diagnosis"]), tuple(sorted(map(norm, d["allergies"]))),
            tuple(sorted(map(norm, d["prescriptions"]))))


ARMS = s.ARMS


async def cell(client, arm, temp, n, conc, out):
    a = ARMS[arm]
    sem = asyncio.Semaphore(conc)
    t0 = time.time()

    async def one(i):
        async with sem:
            ts = time.time()
            try:
                r = await client.chat.completions.create(
                    model=a["model"], temperature=temp, max_tokens=512, seed=1000 * int(temp * 10) + i,
                    extra_body=a["extra"], messages=[{"role": "user", "content": PROMPT}])
                text = r.choices[0].message.content or ""
                toks = r.usage.completion_tokens
            except Exception as e:
                text, toks = f"ERROR {repr(e)[:200]}", None
        rec, why = validate(text)
        row = {"arm": arm, "temp": temp, "i": i, "valid": rec is not None, "reason": why or "ok",
               "key": [key(rec)[0], *map(list, key(rec)[1:])] if rec else None, "record": rec,
               "t_start": round(ts - t0, 3), "t_done": round(time.time() - t0, 3),
               "completion_tokens": toks, "output": text}
        with out.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    await asyncio.gather(*(one(i) for i in range(n)))
    print(arm, temp, "done in", round(time.time() - t0, 1), "s", flush=True)


async def main(a):
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    clients = {k: AsyncOpenAI(base_url=v["base"](), api_key=v["key"](), timeout=600, max_retries=1)
               for k, v in ARMS.items() if k in a.arms}

    async def arm_run(arm):
        for t in a.temps:
            await cell(clients[arm], arm, t, a.n, a.concurrency, out)

    await asyncio.gather(*(arm_run(arm) for arm in a.arms))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--arms", nargs="+", default=list(ARMS))
    p.add_argument("--temps", nargs="+", type=float, default=[0.6, 0.8, 1.0, 1.2])
    p.add_argument("--n", type=int, default=50)
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--out", default="results/synth.jsonl")
    asyncio.run(main(p.parse_args()))
