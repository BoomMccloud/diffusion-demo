"""Judges each valid synthetic record from results/synth.jsonl for clinical plausibility.

The judge sees only the record, never the model or temperature, and returns JSON flags:
  real_diagnosis      the diagnosis is a real condition stated in recognisable terms
  fake_drugs          drug names in prescriptions or allergies that don't exist
  rx_fits             every prescription is a reasonable discharge drug for this diagnosis
  complaint_fits      the chief complaint fits the diagnosis
  demographics_fit    age and sex are plausible for the diagnosis
  garbled             any field has broken, mixed-language or nonsense text
A record is "clean" when real_diagnosis, rx_fits, complaint_fits and demographics_fit are true,
fake_drugs is empty and garbled is false.
"""
import asyncio, json, os
from pathlib import Path

from openai import AsyncOpenAI

import smoke as s

JUDGE = "gemini-3.8-flash"
PROMPT = """You are checking a fictional Chinese inpatient summary used as test data. It is meant to be
clinically plausible, not real. Judge only plausibility and internal consistency.

Record:
{record}

Return only a JSON object with these keys:
"real_diagnosis": true if the diagnosis names real condition(s) in recognisable medical terms.
"fake_drugs": array of drug names from prescriptions or allergies that do not exist as real drugs or
  drug classes (empty array if all are real).
"rx_fits": true if every prescription is a reasonable discharge medication for this diagnosis.
"complaint_fits": true if the chief complaint fits the diagnosis.
"demographics_fit": true if the age and sex are plausible for the diagnosis.
"garbled": true if any field contains broken, mixed-language or nonsense text.
"note": one short sentence naming the main problem, or "" if none."""


async def main():
    src = Path("results/synth.jsonl")
    out = Path("results/synth_judge.jsonl")
    done = {(r["arm"], r["temp"], r["i"]) for r in map(json.loads, open(out))} if out.exists() else set()
    rows = [r for r in map(json.loads, open(src)) if r["valid"] and (r["arm"], r["temp"], r["i"]) not in done]
    rows = rows[:int(os.environ.get("LIMIT", len(rows)))]
    client = AsyncOpenAI(base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                         api_key=os.environ["GEMINI_API_KEY"], timeout=120, max_retries=3)
    sem = asyncio.Semaphore(8)

    async def one(r):
        async with sem:
            try:
                resp = await client.chat.completions.create(
                    model=JUDGE, temperature=0, response_format={"type": "json_object"},
                    messages=[{"role": "user", "content": PROMPT.format(
                        record=json.dumps(r["record"], ensure_ascii=False, indent=1))}])
                v = s.parse_json(resp.choices[0].message.content)
            except Exception as e:
                v = {"error": repr(e)[:200]}
        row = {"arm": r["arm"], "temp": r["temp"], "i": r["i"], "judge": JUDGE, "verdict": v}
        with out.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    await asyncio.gather(*map(one, rows))
    print("judged", len(rows))


if __name__ == "__main__":
    asyncio.run(main())
