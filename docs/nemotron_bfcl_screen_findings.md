# Nemotron-3B BFCL Live Function-Calling Screen (2026-09-28)

Exploratory screen for workload 4 (agent tool calls), single-call form. It is not
a `proposal-pipeline` run. One seed, greedy, batch 1, one L4.

## Setup

- Nemotron-Labs-Diffusion-3B at revision `0d51902da1f8869f83413ce642fab402fa5641e0`,
  bf16, torch 2.11.0+cu128, transformers 5.16.1, NVIDIA L4. Thinking off.
- Modes on the same weights: `ar`, `linear_spec` (block 32), `diffusion`
  (block 32, threshold 0.9). 512-token cap. No row hit the cap or errored.
- Inputs: BFCL v4 "live" categories from `bfcl-eval==2026.3.23` (Apache 2.0),
  which are user-contributed real queries. All of `live_simple` (258),
  `live_parallel` (16), `live_parallel_multiple` (24), and 100 of
  `live_multiple` sampled with seed 20260928. 398 cases.
- Prompt: BFCL's default prompting-mode system prompt, which asks for Python
  call syntax `[func(a=1)]`, sent as the system message. The runner gained an
  optional `system` field for this.
- Scoring: BFCL's own decoder and AST checker (strict). Lenient additionally
  accepts JSON call objects, because AR wrote JSON instead of Python syntax in
  122 of 398 cases.

## Results

| Mode | Strict valid | Lenient valid | Median s | Total s | Median forward passes |
|---|---:|---:|---:|---:|---:|
| AR | 127/398 | 202/398 | 1.21 | 592 | 32 |
| Linear spec | 127/398 | 204/398 | 0.53 | 255 | 11 |
| Diffusion | 107/398 | 108/398 | 0.66 | 286 | 13 |

Lenient valid by category:

| Mode | live_simple | live_multiple | live_parallel | live_parallel_multiple |
|---|---:|---:|---:|---:|
| AR | 155/258 | 32/100 | 10/16 | 5/24 |
| Linear spec | 158/258 | 31/100 | 10/16 | 5/24 |
| Diffusion | 82/258 | 19/100 | 5/16 | 2/24 |

Strict by category: AR 84/258, 28/100, 10/16, 5/24. Linear spec 85/258, 27/100,
10/16, 5/24. Diffusion 81/258, 19/100, 5/16, 2/24.

- **Linear spec keeps AR accuracy at 2.3x lower latency.** Output was
  byte-identical to AR in 368 of 398 cases, and the accuracy difference is 2
  cases. The median paired speedup was 2.3x, well below the 4.9x to 7.3x seen
  on long synthetic outputs, because tool calls are short (median 31 tokens)
  and prefill is a larger share of the wall time.
- **Plain diffusion is slightly slower than linear spec and much less accurate.**
  Lenient accuracy fell from 202 to 108. AR was right and diffusion wrong in
  114 cases; the reverse happened in 20. Diffusion's losses fall into three
  kinds: format collisions that mix JSON and Python (`[{"get_current_weather(location=...)}]`),
  corrupted values (`'"ShishirPatil/gorilla, ...'`, `"Bangkok Thailand, Thailand"`),
  and empty `[]` where AR produced a call. The adjacent-duplication defect from
  the synthetic screens shows up here too.
- Strict scores understate all modes because the 3B model often ignores the
  requested Python syntax. That affects AR and linear spec equally, so the
  comparison holds, but absolute numbers are not comparable with the BFCL
  leaderboard.

## Rerun with one worked example

BFCL's prompt shows only a placeholder template, and the function list is JSON.
The rerun (`bfcl_screen.py build --example`) adds one concrete example after the
format line: `[get_weather(city="Paris", unit="celsius"), get_time(city="Tokyo")]`.
Everything else is identical. It ran on a fresh L4 session because the first
one had idled out.

| Mode | Strict valid | Lenient valid | Median s | Total s | Median forward passes | Decode failures |
|---|---:|---:|---:|---:|---:|---:|
| AR | 218/398 | 229/398 | 1.12 | 528 | 29 | 31 |
| Linear spec | 217/398 | 228/398 | 0.48 | 221 | 9 | 31 |
| Diffusion | 190/398 | 190/398 | 0.56 | 258 | 10 | 45 |

Strict by category (simple, multiple, parallel, parallel_multiple): AR 152/258,
53/100, 5/16, 8/24. Linear spec 150/258, 54/100, 5/16, 8/24. Diffusion 136/258,
42/100, 2/16, 10/24.

- The example lifted strict accuracy for every mode: AR 127 to 218, diffusion
  107 to 190. The lenient gap between AR and diffusion shrank from 94 cases to
  39, so most of diffusion's first-run deficit was format, not content.
- Linear spec still tracks AR: identical output in 384 of 398, 3 AR-only wins
  against 2 spec-only, 2.4x median paired speedup.
- Diffusion is still 2.1x faster than AR and now 13% behind it. AR was right
  and diffusion wrong in 68 cases; the reverse in 40. Diffusion's losses are
  mostly value errors (32), including the duplication defect (`"ThBangkok"`,
  `"McMcDonald's"`), then decode failures (18) and empty or wrong calls.
- AR's `live_parallel` score fell from 10/16 to 5/16 with the example. The
  sample is small and the cause is unexamined.

## Limits

- Batch 1 only. No concurrency sweep, and no AR prompt-lookup baseline.
- Single-turn calls. The multi-turn agent loop, where per-call gains compound,
  is not tested.
- The 30 linear-spec outputs that differ from AR are not yet explained.

## Artifacts

`bench/results/bfcl-screen-2026-09-28/`: `bfcl_screen.py` (build and score),
`cases.jsonl`, `rows.jsonl`, `scored.jsonl`, `summary.jsonl`, `run.log`.
