"""HLE text-only runner: official prompts, diffusion endpoint as the model, Gemini as judge.

Writes one JSON line per question as it completes, so a run can resume.
Missing or truncated answers count as wrong, matching the official accuracy (correct / n).
Expects the gated parquet and the official repo clone under HLE_DIR (default downloads/hle).
"""
import argparse, asyncio, json, math, os, random, re, time
from pathlib import Path

import pyarrow.parquet as pq
from openai import AsyncOpenAI, BadRequestError

HLE_DIR = Path(os.environ.get("HLE_DIR", Path(__file__).resolve().parents[2] / "downloads" / "hle"))
CONTEXT = 131072
SYSTEM_PROMPT = "Your response should be in the following format:\nExplanation: {your explanation for your answer choice}\nAnswer: {your chosen answer}\nConfidence: {your confidence score between 0% and 100% for your answer}"

# Official judge prompt and schema, read from the cloned repo so they stay verbatim.
_src = (HLE_DIR / "repo" / "hle_eval" / "run_judge_results.py").read_text()
JUDGE_PROMPT = _src.split('JUDGE_PROMPT = """', 1)[1].split('"""', 1)[0]
from typing import Literal
from pydantic import BaseModel, ValidationError


class ExtractedAnswer(BaseModel):
    extracted_final_answer: str
    reasoning: str
    correct: Literal["yes", "no"]
    confidence: int
    strict: Literal[True]


def load_questions(n, seed):
    rows = pq.read_table(HLE_DIR / "test.parquet",
                         columns=["id", "question", "image", "answer", "answer_type", "category"]).to_pylist()
    rows = [r for r in rows if not r["image"]]
    random.Random(seed).shuffle(rows)
    return rows[:n] if n else rows


async def solve(model_client, model, q, max_tokens):
    t0 = time.time()
    # The endpoint's context (131,072) includes the prompt, so leave room for it (~3 chars/token, conservative).
    max_tokens = min(max_tokens, CONTEXT - (len(SYSTEM_PROMPT) + len(q["question"])) // 3 - 256)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": q["question"]}]
    try:
        r = await model_client.chat.completions.create(
            model=model, max_tokens=max_tokens, temperature=0.0, messages=messages)
    except BadRequestError as e:
        # Symbol-heavy prompts run under 3 chars/token; retry with the exact budget the server reports.
        m = re.search(r"(\d+) tokens from the input", str(e))
        if not m:
            raise
        r = await model_client.chat.completions.create(
            model=model, max_tokens=CONTEXT - int(m.group(1)) - 16, temperature=0.0, messages=messages)
    m = r.choices[0].message
    return {"response": m.content or "", "reasoning_chars": len(getattr(m, "reasoning_content", None) or ""),
            "finish_reason": r.choices[0].finish_reason, "usage": r.usage.model_dump() if r.usage else None,
            # SGLang's stop token: 248046 is <|im_end|>, 248044 is <|endoftext|> (the empty-answer signature).
            "matched_stop": (r.choices[0].model_extra or {}).get("matched_stop"),
            "latency_s": round(time.time() - t0, 2)}


async def judge(judge_client, judge_model, q, response):
    # Gemini occasionally returns strict=false, which the official schema rejects; ask again.
    for attempt in range(3):
        try:
            r = await judge_client.beta.chat.completions.parse(
                model=judge_model, max_completion_tokens=4096, response_format=ExtractedAnswer,
                messages=[{"role": "user", "content": JUDGE_PROMPT.format(
                    question=q["question"], correct_answer=q["answer"], response=response)}])
            break
        except ValidationError:
            if attempt == 2:
                raise
    p = r.choices[0].message.parsed
    return {"model_answer": p.extracted_final_answer, "judge_reasoning": p.reasoning,
            "correct": p.correct, "confidence": p.confidence}


async def main(a):
    model_client = AsyncOpenAI(base_url=os.environ["DIFFUSION_BASE_URL"].removesuffix("/chat/completions"),
                               api_key="none", timeout=3600, max_retries=1)
    judge_client = AsyncOpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                               api_key=os.environ["GEMINI_API_KEY"], timeout=300, max_retries=2)
    out = Path(a.out)
    recs = [json.loads(l) for l in out.read_text().splitlines()] if out.exists() else []
    if a.redo_errors:
        # Drop errored rows: model errors rerun the model, judge errors keep the response and rerun only the judge.
        out.write_text("".join(json.dumps(r) + "\n" for r in recs if "error" not in r))
        rejudge = {r["id"]: r for r in recs if r.get("error", "").startswith("judge:")}
        recs = [r for r in recs if "error" not in r]
    else:
        rejudge = {}
    done = {r["id"] for r in recs}
    qs = [q for q in load_questions(a.n, a.seed) if q["id"] not in done]
    print(f"{len(done)} done, {len(qs)} to run", flush=True)
    sem = asyncio.Semaphore(a.workers)

    async def one(q):
        async with sem:
            rec = {"id": q["id"], "category": q["category"], "answer_type": q["answer_type"],
                   "correct_answer": q["answer"], "model": a.model, "judge": a.judge}
            if q["id"] in rejudge:
                rec.update({k: v for k, v in rejudge[q["id"]].items() if k != "error"})
            else:
                try:
                    rec.update(await solve(model_client, a.model, q, a.max_tokens))
                except Exception as e:
                    rec["error"] = f"model: {e!r}"[:500]
            if rec.get("response") and rec.get("finish_reason") != "length":
                try:
                    rec.update(await judge(judge_client, a.judge, q, rec["response"]))
                except Exception as e:
                    rec["error"] = f"judge: {e!r}"[:500]
            with out.open("a") as f:
                f.write(json.dumps(rec) + "\n")
            print(rec["id"], rec.get("finish_reason"), rec.get("correct"), rec.get("latency_s"), rec.get("error", ""), flush=True)

    await asyncio.gather(*(one(q) for q in qs))
    recs = [json.loads(l) for l in out.read_text().splitlines()]
    n = len(recs)
    acc = 100 * sum(r.get("correct") == "yes" for r in recs) / n
    print(f"Accuracy {acc:.1f}% +/- {1.96 * math.sqrt(acc * (100 - acc) / n):.1f} | n={n} | "
          f"truncated={sum(r.get('finish_reason') == 'length' for r in recs)} errors={sum('error' in r for r in recs)}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="qwen36-iter22000-blk16-arverify-best")
    p.add_argument("--judge", default="gemini-3.8-flash")
    p.add_argument("--n", type=int, default=20, help="0 = all text-only questions")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--max-tokens", type=int, default=32768)
    p.add_argument("--workers", type=int, default=10)
    p.add_argument("--out", required=True)
    p.add_argument("--redo-errors", action="store_true", help="rerun model errors and re-judge judge errors")
    asyncio.run(main(p.parse_args()))
