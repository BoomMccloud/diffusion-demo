# TabDLM long-range consistency findings

Run `2026-10-21` of `bench/tabdlm/longrange.py`. The design and hypotheses are in
`bench/tabdlm/README.md`, fixed before the run. Output is in
`bench/results/tabdlm-longrange-2026-10-21/`: 348 requests, 17,400 records asked for.

## Result

The pre-registered "dLLM drifts more than AR" claim (H2) failed: the interval included zero in both
orders. The overall gap at 50 records (H3) failed in both orders too.

What held:
- **Both models drift (H1).** Failures rise from the first 10 records of a 50-record batch to the
  last 10, for the dLLM and Qwen alike.
- **The dLLM drifts more when the biography comes last in each record.** On returned records only,
  its drift minus Qwen's is +21 points (4 to 39). On all positions it's +15 (−3 to +33).
- **Putting the biography first removes the gap.** The dLLM goes from 41% failed to 15% at 50
  records, against Qwen's 18%.
- **The dLLM is 2.4 to 3.3x faster per request.** Qwen ran through OpenRouter.

## Numbers

Hosted dLLM `qwen36-iter22000-blk16-arverify-best` at 0.6 against Qwen3.6-35B-A3B on OpenRouter at
1.0, thinking off, 8 concurrent requests per arm. Failure is the share of positions asked for that
failed any check, including missing records.

| batch | order | dLLM fail % | Qwen fail % | dLLM by position (per 10) | Qwen by position (per 10) | latency s, dLLM / Qwen |
|---|---|---|---|---|---|---|
| 10 | fields | 16.7 | 14.5 | | | 5.8 / 11.1 |
| 10 | text | 14.4 | 6.5 | | | 6.0 / 10.2 |
| 30 | fields | 32.8 | 13.2 | 26.5 / 34.0 / 38.0 | 12.5 / 12.0 / 15.0 | 15.3 / 36.5 |
| 30 | text | 14.0 | 9.3 | 14.0 / 13.5 / 14.5 | 8.5 / 10.0 / 9.5 | 14.8 / 38.7 |
| 50 | fields | 40.8 | 24.0 | 25.0 / 38.3 / 44.2 / 45.8 / 50.8 | 19.2 / 24.2 / 23.3 / 23.3 / 30.0 | 22.9 / 76.5 |
| 50 | text | 15.3 | 17.7 | 12.5 / 12.5 / 12.5 / 12.5 / 26.7 | 14.2 / 10.8 / 18.3 / 13.3 / 31.7 | 19.9 / 51.6 |

Tests at 50 records, 95% bootstrap intervals over requests (n = 12 per arm per order):

| test | fields order | text order |
|---|---|---|
| H1 dLLM drift, last 10 minus first 10 | +25.8 (10.8 to 41.7) | +14.2 (9.2 to 19.2) |
| Qwen drift | +10.8 (0.8 to 20.8) | +17.5 (5.8 to 29.2) |
| H2 dLLM minus Qwen drift | +15.0 (−2.5 to 33.3) | −3.3 (−15.8 to 10.0) |
| same, returned records only | +21.4 (4.0 to 39.1) | −1.8 (−12.7 to 7.5) |
| H3 dLLM minus Qwen failure | +16.8 (−11.8 to 44.8) | −2.3 (−19.2 to 12.2) |

At 30 records in field order the dLLM fails 19.7 points more than Qwen (2.5 to 37.3). That wasn't
pre-registered as a primary test.

## What the errors are

- **Field order, both models.** The biography leaves out facts it was told to state. It gives a
  birth year but no age (dLLM 323 records, Qwen 193), or describes the job without naming the
  occupation ("teaches high school science" for `education professional`). For the dLLM these
  omissions grow with position, which is the drift.
- **Text order, dLLM.** 168 records put `birth_year` at exactly 2024 minus age, despite the prompt
  saying 2026. That's a fixed belief about the current year, not long-range drift, and it is most of
  the dLLM's text-order failures.
- **Text order, Qwen.** The biography omits the birth year (31 records at 10, 20 at 30).
- **Stopping short.** Both models often return 46 to 49 records when asked for 50. That's why the
  last bucket jumps in text order.
- **No-repeat rule.** The (college, occupation) rule almost never failed: at most 3 repeats per cell.
  Neither model loses track of earlier records in this sense.

## Limits

- 12 requests per arm per order at 50 records. The intervals are wide, and H2 in field order is
  close to the line.
- The checks are strict string matches, and the prompt asked for exact values. A lenient reader
  would accept an age implied by a birth year. The strictness measures instruction following as
  much as factual consistency.
- Qwen ran through OpenRouter, so latency includes provider queueing. Two Qwen requests ended with
  a provider error and were rerun. One of them failed to parse again and counts as 30 missing
  records.
- One temperature per model, the best ones from synthdata. There was no same-hardware AR arm.
