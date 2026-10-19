"""Rerun HLE questions that came back empty and keep the full raw response."""
import json, os, sys, asyncio
from pathlib import Path
import pyarrow.parquet as pq
from openai import AsyncOpenAI

HERE = Path(os.environ.get("HLE_DIR", Path(__file__).resolve().parents[2] / "downloads" / "hle"))
SYSTEM_PROMPT = "Your response should be in the following format:\nExplanation: {your explanation for your answer choice}\nAnswer: {your chosen answer}\nConfidence: {your confidence score between 0% and 100% for your answer}"
ids = sys.argv[1:]
(HERE / "probe").mkdir(exist_ok=True)
qs = {r["id"]: r for r in pq.read_table(HERE / "test.parquet", columns=["id", "question"]).to_pylist() if r["id"] in ids}
client = AsyncOpenAI(base_url=os.environ["DIFFUSION_BASE_URL"].removesuffix("/chat/completions"), api_key="none", timeout=7200, max_retries=0)

async def one(i, separate):
    r = await client.chat.completions.with_raw_response.create(
        model="qwen36-iter22000-blk16-arverify-best", temperature=0.0, max_tokens=120000,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": qs[i]["question"]}],
        extra_body={} if separate else {"separate_reasoning": False})
    (HERE / "probe" / f"{i}_{'sep' if separate else 'raw'}.json").write_text(r.text)
    d = json.loads(r.text); ch = d["choices"][0]; m = ch["message"]
    print(i, "sep" if separate else "raw", ch.get("finish_reason"), ch.get("matched_stop"), d.get("usage", {}).get("completion_tokens"),
          len(m.get("content") or ""), len(m.get("reasoning_content") or ""), flush=True)

async def main():
    await asyncio.gather(*(one(i, s) for i in ids for s in (True, False)))

asyncio.run(main())
