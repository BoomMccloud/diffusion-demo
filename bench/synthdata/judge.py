"""Judge stage: one verdict per format-passing generation in judgments.jsonl, resumable.

The judge sees only the repaired text and, in seeded mode, the request. It never sees the model or
temperature.
"""
import asyncio, json, os

from openai import AsyncOpenAI

from . import tasks
from .generate import key


def _parse(text):
    import re
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0) if m else text)


async def run(cfg, gen_path, out_path):
    # A verdict that errored is retried on the next run; metrics read the last verdict per key.
    done = set()
    if out_path.exists():
        done = {tuple(j["key"]) for j in map(json.loads, open(out_path)) if "error" not in j["verdict"]}
    rows = [r for r in map(json.loads, open(gen_path))
            if r["format_ok"] and key(r) not in done and r["task"] in cfg.tasks and r["mode"] in cfg.modes]
    print(f"judge: {len(rows)} to run, {len(done)} already done", flush=True)
    client = AsyncOpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                         api_key=os.environ["GEMINI_API_KEY"], timeout=120, max_retries=3)
    sem = asyncio.Semaphore(cfg.judge_concurrency)

    async def one(r):
        async with sem:
            try:
                resp = await client.chat.completions.create(
                    model=cfg.judge_model, temperature=0, response_format={"type": "json_object"},
                    messages=[{"role": "user", "content": tasks.judge_prompt(r["task"], r["seed"], r["text"])}])
                v = _parse(resp.choices[0].message.content)
            except Exception as e:
                v = {"error": repr(e)[:200]}
        with out_path.open("a") as f:
            f.write(json.dumps({"key": list(key(r)), "judge": cfg.judge_model, "verdict": v,
                                "clean": tasks.is_clean(v)}, ensure_ascii=False) + "\n")

    await asyncio.gather(*map(one, rows))
