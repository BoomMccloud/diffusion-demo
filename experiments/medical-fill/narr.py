"""Free-text synthetic case narratives, for distinctness as training data.

Each model writes many fictional inpatient summaries from the same prompt, with no patient name so
names can't inflate variety. Rows go to results/narr.jsonl; judge them with `--judge`, then
`--score` prints distinctness (distinct.py) on clean narratives at equal sample size.
"""
import argparse, asyncio, json, os, re, time
from pathlib import Path

from openai import AsyncOpenAI

import distinct
import smoke as s

PROMPT = ("请写一份虚构的中文住院病历摘要，用作模型训练数据。300 到 500 字，依次包含【主诉】【现病史】【既往史】"
          "【入院检查】【诊断】【诊疗经过】【出院医嘱】七个部分。不要写患者姓名，用“患者”指代。"
          "内容需临床上合理、前后一致。只输出病历正文。")

JUDGE_PROMPT = """You are checking a fictional Chinese inpatient summary written as model training data.
It should be clinically plausible and internally consistent, not real. Summary:

{text}

Return only a JSON object with these keys:
"real_diagnosis": true if every diagnosis is a real condition in recognisable medical terms.
"fake_drugs": array of drug names that do not exist as real drugs or drug classes (empty if none).
"consistent": true if history, findings, diagnosis and treatment agree with each other.
"treatment_fits": true if the treatment and discharge drugs are reasonable for the diagnosis.
"garbled": true if any part has broken, mixed-language or nonsense text.
"note": one short sentence naming the main problem, or "" if none."""

OUT = Path("results/narr.jsonl")
JOUT = Path("results/narr_judge.jsonl")
SECTIONS = ["【主诉】", "【现病史】", "【既往史】", "【入院检查】", "【诊断】", "【诊疗经过】", "【出院医嘱】"]


# Format repair. These only change headers and wrappers, never clinical content.
_ALIASES = {"患者主诉": "主诉", "入院诊断": "诊断", "初步诊断": "诊断", "出院诊断": "诊断"}
_HEAD = re.compile(
    r"^[ \t]*(?:#+[ \t]*)?(?:\*\*)?[ \t]*[【\[]?[ \t]*"
    r"(患者主诉|主诉|现病史|既往史|入院检查|入院诊断|初步诊断|出院诊断|诊断|诊疗经过|出院医嘱)"
    r"[ \t]*[】\]]?[ \t]*(?:\*\*)?[ \t]*[：:]?[ \t]*(?:\*\*)?[ \t]*", re.M)
_PREAMBLE = re.compile(r"^\s*(?:好的|以下|这是)[^\n]*[：:]\s*\n+")
_LEAD_COMPLAINT = re.compile(r"^(?P<lead>[^【]*?(?:因|主诉[：:]?)\s*[“\"](?P<cc>[^”\"]+)[”\"][^\n【]*)\n")


def normalize(text):
    """Rewrites header variants (**主诉：**, 主诉：, 【入院诊断】) to the required 【主诉】 form, drops a
    leading "好的，这是…：" line, and turns an opening "患者因“…”入院" sentence into 【主诉】."""
    t = _PREAMBLE.sub("", text)
    t = _HEAD.sub(lambda m: f"【{_ALIASES.get(m.group(1), m.group(1))}】", t)
    if "【主诉】" not in t:
        t = _LEAD_COMPLAINT.sub(lambda m: f"【主诉】{m.group('cc')}\n", t, count=1)
    return t.strip()


def code_check(text):
    if not 150 <= len(text) <= 1500:
        return f"length {len(text)}"
    missing = [x for x in SECTIONS if x not in text]
    return f"missing {''.join(missing)}" if missing else None


async def gen(a):
    clients = {k: AsyncOpenAI(base_url=v["base"](), api_key=v["key"](), timeout=600, max_retries=1)
               for k, v in s.ARMS.items()}
    cells = [tuple(c.split(":")) for c in a.cells]

    async def run_cell(arm, temp):
        temp = float(temp)
        sem = asyncio.Semaphore(a.concurrency)
        t0 = time.time()

        async def one(i):
            async with sem:
                try:
                    r = await clients[arm].chat.completions.create(
                        model=s.ARMS[arm]["model"], temperature=temp, max_tokens=1024,
                        seed=7000 + 100 * int(temp * 10) + i, extra_body=s.ARMS[arm]["extra"],
                        messages=[{"role": "user", "content": PROMPT}])
                    text, toks = s.strip(r.choices[0].message.content or ""), r.usage.completion_tokens
                except Exception as e:
                    text, toks = f"ERROR {repr(e)[:200]}", None
            why = code_check(text)
            row = {"arm": arm, "temp": temp, "i": i, "valid": why is None, "reason": why or "ok",
                   "t_done": round(time.time() - t0, 3), "completion_tokens": toks, "text": text}
            with OUT.open("a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

        await asyncio.gather(*(one(i) for i in range(a.n)))
        print(arm, temp, "done in", round(time.time() - t0, 1), "s", flush=True)

    by_arm = {}
    for arm, temp in cells:
        by_arm.setdefault(arm, []).append(temp)

    async def arm_run(arm):
        for t in by_arm[arm]:
            await run_cell(arm, t)

    await asyncio.gather(*map(arm_run, by_arm))


async def judge():
    done = {(r["arm"], r["temp"], r["i"]) for r in map(json.loads, open(JOUT))} if JOUT.exists() else set()
    rows = [r for r in map(json.loads, open(OUT)) if r["valid"] and (r["arm"], r["temp"], r["i"]) not in done]
    client = AsyncOpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                         api_key=os.environ["GEMINI_API_KEY"], timeout=120, max_retries=3)
    sem = asyncio.Semaphore(8)

    async def one(r):
        async with sem:
            try:
                resp = await client.chat.completions.create(
                    model="gemini-3.8-flash", temperature=0, response_format={"type": "json_object"},
                    messages=[{"role": "user", "content": JUDGE_PROMPT.format(text=r["text"])}])
                v = s.parse_json(resp.choices[0].message.content)
            except Exception as e:
                v = {"error": repr(e)[:200]}
        with JOUT.open("a") as f:
            f.write(json.dumps({"arm": r["arm"], "temp": r["temp"], "i": r["i"], "verdict": v},
                               ensure_ascii=False) + "\n")

    await asyncio.gather(*map(one, rows))
    print("judged", len(rows))


def is_clean(v):
    return bool(v) and ("error" not in v and v["real_diagnosis"] and not v["fake_drugs"] and v["consistent"]
            and v["treatment_fits"] and not v["garbled"])


def score(n):
    J = {(j["arm"], j["temp"], j["i"]): j["verdict"] for j in map(json.loads, open(JOUT))}
    rows = list(map(json.loads, open(OUT)))
    cells = sorted({(r["arm"], r["temp"]) for r in rows})
    print("cell".ljust(10), "valid", "clean", "wall_s")
    for c in cells:
        rs = [r for r in rows if (r["arm"], r["temp"]) == c]
        cl = sum(is_clean(J.get((r["arm"], r["temp"], r["i"]))) for r in rs)
        print(f"{c[0]} {c[1]}".ljust(10), str(sum(r["valid"] for r in rs)).rjust(5), str(cl).rjust(5),
              max(r["t_done"] for r in rs))
    items = [{"cell": f"{r['arm']} {r['temp']}", "text": r["text"]} for r in rows
             if r["valid"] and is_clean(J.get((r["arm"], r["temp"], r["i"])))]
    cols = ["items", "distinct3", "gzip_ratio", "mean_cos", "nn_cos", "near_dup", "vendi"]
    print(f"\nclean narratives, N={n} per cell, 20 resamples")
    print("cell".ljust(10), *[c.rjust(10) for c in cols])
    for cell, m in distinct.score(items, n).items():
        print(cell.ljust(10), *([str(m.get(c, "")).rjust(10) for c in cols] if "skipped" not in m else [m["skipped"]]))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--cells", nargs="+", default=["dllm:0.6", "dllm:0.8", "qwen:0.8", "qwen:1.2"])
    p.add_argument("--n", type=int, default=100)
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--judge", action="store_true")
    p.add_argument("--score", type=int, metavar="N", help="score clean narratives at sample size N")
    a = p.parse_args()
    if a.score:
        score(a.score)
    elif a.judge:
        asyncio.run(judge())
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        asyncio.run(gen(a))
