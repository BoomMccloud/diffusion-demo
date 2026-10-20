"""Fill task with the model's real mask token against a plain-text placeholder.

On the hosted server (2026-10-20) the tokenizer still maps " それ" to id 151669, the model's mask id,
so writing " それ" in chat text sends a real mask. Each slot gets four masks. The control writes
" [MASK]" four times instead. Same instructions, same scorer as smoke.py's fill task.
"""
import argparse, asyncio, json, os, re, time
from pathlib import Path

from openai import AsyncOpenAI

import smoke as s

VARIANTS = {"real_mask": " それ" * 4, "text_mask": " [MASK]" * 4}
RULES = ("下面是一份病历，其中有六处内容被遮盖（姓名、性别、年龄、过敏药物、抗生素、再次确认的过敏药物）。"
         "请填写被遮盖的内容并输出完整病历。填写规则：姓名填一个虚构中文姓名；性别填“男”或“女”；年龄填“数字+岁”，如“58岁”；"
         "两处过敏药物都填“青霉素”；抗生素从“红霉素、阿奇霉素”中选一个。"
         "只输出完整病历正文，不要任何解释、标题或代码块，其余文字、标点、空格和换行与原文保持一致，被遮盖处只保留填写的内容。")
# v2 drops the line that may have invited deleting the labels after each slot, and says to keep them.
RULES_V2 = RULES.replace("被遮盖处只保留填写的内容。",
                         "只把被遮盖的部分替换为填写内容；紧跟其后的括号说明，如“（某种抗生素）”“（抗生素名称）”“（再次确认过敏药物）”，必须原样保留。")
PROMPTS = {"v1": RULES, "v2": RULES_V2}


def score(out):
    final = s.strip(out)
    pat = re.escape(s.MASKED)
    for k in s.SLOTS:
        pat = pat.replace(re.escape(f"[MASK_{k}]"), f"(?P<{k}>.+?)", 1)
    m = re.fullmatch(pat, final, re.S)
    if not m:
        return False, "body changed", None
    vals = {k: v.strip() for k, v in m.groupdict().items()}
    r = s.fill_ok(vals)
    return r is None, r or "ok", vals


async def main(a):
    client = AsyncOpenAI(base_url=os.environ["DIFFUSION_BASE_URL"].removesuffix("/chat/completions"),
                         api_key="none", timeout=600, max_retries=1)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(4)

    async def run(var, rep):
        rec = s.render(**{k: VARIANTS[var] for k in s.SLOTS})
        async with sem:
            t0 = time.time()
            r = await client.chat.completions.create(
                model="qwen36-iter22000-blk16-arverify-best", temperature=0.8, max_tokens=2048, seed=rep,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
                messages=[{"role": "user", "content": f"{rec}\n\n{PROMPTS[a.prompt]}"}])
        text = r.choices[0].message.content or ""
        ok, why, vals = score(text)
        row = {"prompt": a.prompt, "variant": var, "rep": rep, "pass": ok, "reason": why, "values": vals,
               "latency_s": round(time.time() - t0, 2), "completion_tokens": r.usage.completion_tokens,
               "prompt_tokens": r.usage.prompt_tokens, "output": text}
        with out.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(var, rep, ok, why, json.dumps(vals, ensure_ascii=False), flush=True)

    await asyncio.gather(*(run(v, r) for v in VARIANTS for r in range(a.reps)))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--reps", type=int, default=8)
    p.add_argument("--prompt", choices=["v1", "v2"], default="v1")
    p.add_argument("--out", default="results/real_mask.jsonl")
    asyncio.run(main(p.parse_args()))
