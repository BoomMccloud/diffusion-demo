"""Streaming throughput probe for the hosted diffusion endpoint.

Splits each request into time to first token (TTFT) and decode rate, so short replies
don't hide the decode speed behind fixed startup cost. Writes one JSON line per request.

Decode tok/s = (completion_tokens - first chunk's tokens) / (last chunk time - first chunk time).
The first chunk's token count is unknown, so this uses completion_tokens - 1; with diffusion
blocks the first chunk may hold up to a block, which slightly understates the rate on short replies.
"""
import argparse, asyncio, json, os, time
from pathlib import Path

from openai import AsyncOpenAI

PROMPTS = {
    "essay": "Write a long, detailed technical article (at least 4,000 words) explaining how modern "
             "database query optimizers work: parsing, logical plans, cost models, join ordering, "
             "cardinality estimation, and adaptive execution. Use headings and examples.",
    "code": "Write a complete, well-commented single-file Python implementation of a key-value store "
            "with a write-ahead log, an in-memory memtable, SSTable flushing, compaction, and a CLI. "
            "Include unit tests at the end. Output only the code.",
    "story": "Write a long short story (at least 3,000 words) about a lighthouse keeper who finds a "
             "radio that receives messages from the future. Include dialogue.",
    "math": "Prove that there are infinitely many primes congruent to 3 mod 4, then prove the same for "
            "1 mod 4, then explain Dirichlet's theorem and sketch its proof in detail.",
}


async def one(client, model, name, prompt, max_tokens, thinking):
    t0 = time.time()
    first = last = None
    chunks = 0
    usage = None
    finish = None
    extra = {} if thinking is None else {"chat_template_kwargs": {"enable_thinking": thinking}}
    stream = await client.chat.completions.create(
        model=model, max_tokens=max_tokens, temperature=0.0, stream=True,
        stream_options={"include_usage": True}, extra_body=extra,
        messages=[{"role": "user", "content": prompt}])
    async for ev in stream:
        if ev.usage:
            usage = ev.usage
        for c in ev.choices:
            d = c.delta
            if (d.content or getattr(d, "reasoning_content", None)):
                now = time.time()
                first = first or now
                last = now
                chunks += 1
            finish = c.finish_reason or finish
    toks = usage.completion_tokens if usage else None
    rec = {"prompt": name, "max_tokens": max_tokens, "thinking": thinking, "finish_reason": finish,
           "completion_tokens": toks, "prompt_tokens": usage.prompt_tokens if usage else None,
           "chunks": chunks, "latency_s": round(time.time() - t0, 3),
           "ttft_s": round(first - t0, 3) if first else None}
    if toks and first and last > first:
        rec["decode_tps"] = round((toks - 1) / (last - first), 1)
        rec["e2e_tps"] = round(toks / rec["latency_s"], 1)
    return rec


async def main(a):
    client = AsyncOpenAI(base_url=os.environ["DIFFUSION_BASE_URL"].removesuffix("/chat/completions"),
                         api_key="none", timeout=3600, max_retries=0)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    thinking = {"on": True, "off": False, "default": None}[a.thinking]
    jobs = [(n, PROMPTS[n], mt) for mt in a.max_tokens for n in a.prompts for _ in range(a.reps)]
    for conc in a.concurrency:
        sem = asyncio.Semaphore(conc)

        async def run(job):
            async with sem:
                try:
                    rec = await one(client, a.model, *job, thinking)
                except Exception as e:
                    rec = {"prompt": job[0], "max_tokens": job[2], "error": repr(e)[:300]}
                rec["concurrency"] = conc
                with out.open("a") as f:
                    f.write(json.dumps(rec) + "\n")
                print(conc, rec.get("prompt"), rec.get("max_tokens"), rec.get("completion_tokens"),
                      rec.get("ttft_s"), rec.get("decode_tps"), rec.get("e2e_tps"), rec.get("finish_reason"),
                      rec.get("error", ""), flush=True)

        t = time.time()
        await asyncio.gather(*(run(j) for j in jobs))
        print(f"concurrency {conc}: {len(jobs)} requests in {time.time() - t:.0f}s", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="qwen36-iter22000-blk16-arverify-best")
    p.add_argument("--prompts", nargs="+", default=list(PROMPTS))
    p.add_argument("--max-tokens", nargs="+", type=int, default=[8192])
    p.add_argument("--concurrency", nargs="+", type=int, default=[1])
    p.add_argument("--reps", type=int, default=1)
    p.add_argument("--thinking", choices=["on", "off", "default"], default="off")
    p.add_argument("--out", required=True)
    asyncio.run(main(p.parse_args()))
