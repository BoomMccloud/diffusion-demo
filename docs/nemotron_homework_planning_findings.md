# Nemotron-3B Homework Grading and Path Planning Screens (2026-09-29)

Exploratory screens of two workloads proposed as favorable to diffusion. Neither
is a `proposal-pipeline` run. One seed, greedy, batch 1, one L4.

## Setup

Nemotron-Labs-Diffusion-3B at revision `0d51902da1f8869f83413ce642fab402fa5641e0`,
bf16, torch 2.11.0+cu128, transformers 5.16.1, NVIDIA L4, thinking off. Modes on
the same weights: `ar`, `linear_spec` (block 32), `diffusion` (block 32,
threshold 0.9). Every prompt states the exact output format with one worked
example.

## Homework grading

**Hypothesis:** a worksheet is many independent verdicts, which parallel decoding
should produce faster without losing accuracy.

**Inputs.** 300 GSM8K test problems (`openai/gsm8k`, MIT license, seed
20260929). The student work was written by Llama 3.2 1B Instruct through
OpenRouter, so the mistakes are real ones; 97 of 300 final answers match the key.
The student's final answer is the marked answer, else the last number written.
18 worksheets: 6 each of 10, 25, and 50 questions, each question with the
problem, the answer key, and the student's work (up to about 33,000 characters
of prompt at 50). The grader writes `Q<n>: CORRECT|INCORRECT` per question and
a `SCORE: x/y` line.

| Mode | Size | Items right | Balanced accuracy | Median s | Speedup vs AR |
|---|---:|---:|---:|---:|---:|
| AR | 10 | 49/60 | 0.87 | 3.49 | 1.0x |
| Linear spec | 10 | 50/60 | 0.88 | 0.98 | 3.6x |
| Diffusion | 10 | 47/60 | 0.83 | 1.29 | 2.7x |
| AR | 25 | 121/150 | 0.85 | 8.78 | 1.0x |
| Linear spec | 25 | 120/150 | 0.85 | 2.51 | 3.5x |
| Diffusion | 25 | 115/150 | 0.84 | 3.14 | 2.8x |
| AR | 50 | 213/300 | 0.68 | 21.19 | 1.0x |
| Linear spec | 50 | 213/300 | 0.68 | 7.41 | 2.9x |
| Diffusion | 50 | 158/300 | 0.60 | 7.85 | 2.7x |

- Only about 32% of student answers are correct, so marking everything
  INCORRECT scores 69% item accuracy. Balanced accuracy (mean of the recall on
  each class) is the fair measure.
- At 10 and 25 questions, diffusion grades about as well as AR at 2.7x to 2.8x
  lower latency. Linear spec is faster still, at 2.9x to 3.6x, with AR's grades.
- At 50 questions every mode degrades, and diffusion breaks: 76 of 300 verdicts
  missing and 32 lines with wrong question numbers. This is the long-list
  numbering and duplication failure from the synthetic screens.
- No mode got a `SCORE` line right on any sheet, and at most 7 of 18 totals
  even matched the model's own verdicts. Counting is beyond this model without
  reasoning.

## Path planning

**Hypothesis:** a path with a constraint later in the route (pick up at one cell,
deliver at another; get the key before the door) favors a decoder that can see
the whole output.

**Inputs.** Generated warehouse grids with shelves, seed 20260929, 20 per tier.
`easy` 5x5 with 2 to 3 shelves; `reach` 6x6 with a forced detour; `pickup` 8x8
with a pickup off the direct route; `key_door` 10x10 with the goal behind a wall
whose only door needs a key. The model writes every cell as `PATH: (r,c) ...`.
Scoring replays the path. A BFS oracle solves all 80 optimally.

| Mode | Easy valid | Easy optimal | Hard valid (60) | Ends at goal (hard) | All moves single-step (hard) | Median s, easy | Median s, hard |
|---|---:|---:|---:|---:|---:|---:|---:|
| AR | 11/20 | 6 | 1 | 54 | 49 | 1.51 | 3.42 |
| Linear spec | 11/20 | 6 | 1 | 53 | 49 | 0.44 | 0.93 |
| Diffusion | 4/20 | 3 | 0 | 33 | 28 | 0.66 | 2.10 |

- The hard tiers are beyond this model in every mode. 56 of AR's 60 paths walk
  through a shelf.
- On easy grids diffusion is worse: 4 valid against 11, AR-only wins 9 against
  diffusion-only 2. Its distinctive failure is teleporting between non-adjacent
  cells (11 of 20 easy paths), which AR never does.
- Diffusion was not faster than linear spec on either tier, and on the hard
  tiers it wrote longer outputs (median 140 tokens against 90).

## Interpretation

Neither hypothesis holds for Nemotron-3B's plain diffusion mode. For grading,
diffusion does deliver a real speedup at similar accuracy up to 25 questions,
but linear speculation delivers more speed with AR's accuracy, and diffusion
fails first as the list grows. For planning, diffusion is less accurate and no
faster than linear spec.

This decoder diffuses 32-token blocks left to right, so it only sees ahead
within a block. The planning hypothesis is about whole-output planning, which
this setup cannot test. A full-canvas model such as DiffusionGemma (256-token
canvas) is the better test of it.

## Nemotron-14B on the same cases

Nemotron-Labs-Diffusion-14B at revision `f8c3e2c078e193599b8882d965b1001c456ba738`,
bf16, same torch and transformers, NVIDIA A100-SXM4-40GB. Its config has the
same `block_size: 32` as the 3B. The first A100 session was reclaimed by Colab
after 151 of 180 hard-planning rows; the remaining 29 diffusion rows and all
homework rows ran on a second A100 of the same type, resuming by case and arm.

### Planning

| Mode | Easy valid (20) | Easy optimal | Hard valid (60): reach, pickup, key_door | Hard ends at goal | Hard all single-step | Hard shelf hits per path | Median s, easy / hard |
|---|---:|---:|---|---:|---:|---:|---|
| AR | 9 | 5 | 6: 3, 3, 0 | 56 | 58 | 3.6 | 2.05 / 4.29 |
| Linear spec | 10 | 5 | 6: 3, 3, 0 | 56 | 59 | 3.7 | 0.46 / 0.98 |
| Diffusion | 9 | 7 | 3: 3, 0, 0 | 43 | 38 | 8.3 | 0.78 / 2.69 |

- On easy grids the 14B's diffusion matches AR (9 valid each) and teleports far
  less than the 3B's (3 of 20 paths against 11).
- On the hard tiers AR improved from 1 to 6 valid, and diffusion did not keep
  up: 0 on pickup, twice the shelf hits, and 22 of 60 paths with teleports.
- No mode solved a key-door grid. Diffusion was slower than linear spec on
  every tier and wrote longer paths on the hard ones (median 132 tokens
  against 82).

### Homework

| Mode | Size | Items right | Balanced accuracy | Verdicts missing | Median s |
|---|---:|---:|---:|---:|---:|
| AR | 10 | 55/60 | 0.94 | 0 | 4.26 |
| Linear spec | 10 | 54/60 | 0.91 | 0 | 0.91 |
| Diffusion | 10 | 55/60 | 0.91 | 0 | 1.19 |
| AR | 25 | 72/150 | 0.96 on answered | 74 | 26.73 |
| Linear spec | 25 | 48/150 | 0.96 on answered | 99 | 7.28 |
| Diffusion | 25 | 142/150 | 0.95 | 0 | 2.70 |
| AR | 50 | 121/300 | 0.57 | 0 | 22.10 |
| Linear spec | 50 | 118/300 | 0.56 | 0 | 8.31 |
| Diffusion | 50 | 173/300 | 0.57 | 29 | 12.70 |

- At 10 questions the 14B grades better than the 3B in every mode (0.91 to
  0.94 against 0.83 to 0.88). Linear spec is fastest.
- At 25 questions AR and linear spec began 3 and 4 of 6 sheets with prose
  reasoning ("We need to grade each question...") despite thinking off and
  "Write nothing else", and ran out of the 512-token allowance. Diffusion
  answered all six in the format and got 142 of 150 right. On the verdicts AR
  did write, it was as accurate, so this is a format and budget effect, not a
  grading-skill one. A larger allowance would be needed for a fair speed
  comparison at this size.
- At 50 questions every mode is at chance. AR and linear spec collapse into a
  run of CORRECT (27 and 24 INCORRECT verdicts against 206 true ones).
  Diffusion keeps varying its verdicts but splits tokens (`COR\nRECTQ4`) and
  loses 29 of them. Marking every question INCORRECT would score 206 of 300.

### What changed with scale

The 14B raised the floors: AR hard planning 1 to 6 valid, and grading at 10
questions 0.87 to 0.94. It also narrowed the plain-diffusion gap on easy
tasks. It did not change the ordering on hard ones: diffusion still fails
planning with a pickup constraint and was never faster than linear spec on
planning. The one place diffusion came out ahead was the 25-question
worksheets, and that came from following the output format, not from grading
better.

## Artifacts

- `bench/results/homework-screen-2026-09-29/`: `homework_screen.py`,
  `student_cases.jsonl`, `student_rows.jsonl`, `cases.jsonl`, `rows.jsonl`,
  `scored.jsonl`, `summary.jsonl`, `run.log`.
- `bench/results/planning-screen-2026-09-29/`: `planning_screen.py`,
  `cases.jsonl` and `cases_easy.jsonl`, rows, scored rows, and summaries for
  each, `run.log` and `easy_run.log`.
- 14B rows, scored rows, and summaries use the `n14_` prefix in both
  directories.
