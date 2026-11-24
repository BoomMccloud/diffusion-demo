"""GSM8K accuracy against an OpenAI-compatible server, one JSON line per question.

Takes the first N questions of the GSM8K test split (openai/gsm8k, MIT license) in file order,
asks for the final number on the last line, and scores an exact numeric match. Also records
tokens and latency, so quality sits next to speed.
Usage: gsm8k_eval.py --base-url URL --model NAME --data test.jsonl --n 100 --out rows.jsonl
"""
import argparse, asyncio, json, re, time
from pathlib import Path

from openai import AsyncOpenAI

INSTRUCTION = ("Solve the problem. End your reply with a final line of the form "
               "'Answer: <number>' with no units.\n\n")


def number(s):
    s = s.replace(",", "").replace("$", "").strip().rstrip(".")
    try:
        v = float(s)
    except ValueError:
        return None
    return int(v) if v == int(v) else v


def extract(text):
    m = re.findall(r"Answer:\s*\**\s*\$?(-?[\d,]*\.?\d+)", text or "")
    if m:
        return number(m[-1])
    nums = re.findall(r"-?[\d,]*\.?\d+", text or "")
    return number(nums[-1]) if nums else None


async def main(a):
    rows = [json.loads(l) for l in open(a.data)][: a.n]
    client = AsyncOpenAI(base_url=a.base_url, api_key="none", timeout=3600, max_retries=0)
    out = Path(a.out)
    done = {json.loads(l)["idx"] for l in out.open()} if out.exists() else set()
    sem = asyncio.Semaphore(a.concurrency)
    extra = {"chat_template_kwargs": {"enable_thinking": a.thinking == "on"}}

    async def run(i, row):
        async with sem:
            t0 = time.time()
            rec = {"idx": i, "gold": number(row["answer"].split("####")[-1])}
            try:
                r = await client.chat.completions.create(
                    model=a.model, max_tokens=a.max_tokens, temperature=0.0, extra_body=extra,
                    messages=[{"role": "user", "content": INSTRUCTION + row["question"]}])
                msg = r.choices[0].message
                rec.update(content=msg.content, reasoning=getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None),
                           finish_reason=r.choices[0].finish_reason,
                           completion_tokens=r.usage.completion_tokens,
                           prompt_tokens=r.usage.prompt_tokens)
                rec["pred"] = extract(msg.content)
                rec["correct"] = rec["pred"] == rec["gold"]
            except Exception as e:
                rec["error"] = repr(e)[:300]
                rec["correct"] = False
            rec["latency_s"] = round(time.time() - t0, 3)
            with out.open("a") as f:
                f.write(json.dumps(rec) + "\n")

    t = time.time()
    await asyncio.gather(*(run(i, r) for i, r in enumerate(rows) if i not in done))
    recs = [json.loads(l) for l in out.open()]
    print(json.dumps({"model": a.model, "n": len(recs), "correct": sum(r["correct"] for r in recs),
                      "errors": sum("error" in r for r in recs),
                      "length_stops": sum(r.get("finish_reason") == "length" for r in recs),
                      "completion_tokens": sum(r.get("completion_tokens") or 0 for r in recs),
                      "wall_s": round(time.time() - t, 1)}))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--n", type=int, default=100)
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--max-tokens", type=int, default=8192)
    p.add_argument("--thinking", choices=["on", "off"], default="on")
    p.add_argument("--out", required=True)
    asyncio.run(main(p.parse_args()))
