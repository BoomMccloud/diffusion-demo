# LLM-JEPA on a diffusion LM: findings, 2026-11-13

## Question

Does LLM-JEPA fine-tuning (Huang, LeCun, Balestriero 2025, arXiv 2509.14252) help diffusion
decoding more than it helps AR decoding? The test plan is the Claude Doc "LLM-JEPA on a diffusion
LM: test plan" (https://claude.ai/artifact/HX8FG4gKDh714H8jVkKoTa). The decision rule, fixed before
any run: the interaction (JEPA minus baseline in `diffusion`, minus the same in `ar`) must be at least
2 points with a 95% CI above zero on at least 2 of 3 tasks.

## Answer so far

No support, from one seed. The interaction was never positive. On exact match it was negative in 3 of
4 comparisons and about zero in the fourth. On content accuracy, which forgives an answer that is right
but keeps going, it was negative in all 4, by 7 to 10 points. JEPA left `ar` flat or slightly better and
made `diffusion` worse. The run was stopped after seed 82 by the user's choice, so these are single
training runs and the intervals below don't include training-seed variance.

## Setup

- Model: `nvidia/Nemotron-Labs-Diffusion-3B` at revision `0d51902`, bf16. The same weights decode as
  `ar` and as `diffusion` (32-token blocks, confidence threshold 0.9).
- Training: LoRA rank 16 on every attention and MLP projection, lr 1e-4, batch 1 with 4-step gradient
  accumulation, 1 epoch (8,000 examples, 2,000 steps), seed 82. Every arm trains the AR loss and a
  diffusion loss on one answer block, the way `generate` decodes.
- Arms: baseline (`--lbd 0`); JEPA bidirectional (lbd 2.0, the two views encoded with bidirectional
  attention); JEPA causal (lbd 2.0, views encoded causally, which is the paper's own setup). The JEPA
  term is 1 − cosine between the last `<|im_end|>` hidden states of the prompt view and the answer
  view, with no predictor tokens.
- Tasks: NL-RX-SYNTH and NL-RX-TURK from `galilai-group/llm-jepa` at `ea0017c` (Apache-2.0), full
  2,000-case test sets, exact string match as in its `evaluate.py`.
- Hardware: DGX Spark (GB10), docker image from `bench/jepa/Dockerfile` (NGC PyTorch 26.10,
  transformers 5.22.2, peft 0.21.2). Two jobs shared the GPU, so per-row seconds are not latencies.
- Code: `bench/jepa/smoke.py` (training and scoring) and `bench/jepa/run_main.sh` (the queue).
- Rows: `bench/results/jepa-main/`. Smoke test: `bench/results/jepa-smoke-2026-11-12/`. lbd pick:
  `bench/results/jepa-lbd-pick-2026-11-13/`. Adapters stay on the Spark under `~/diffusion-demo/runs/`.

## Results

Accuracy on the full test sets. "Overrun" is an answer that starts with the reference but keeps
going. "Content" is exact plus overrun. "Passes" is mean forward passes per answer.

| Task | Arm | `ar` exact | `diffusion` exact | `diffusion` overrun | `diffusion` content | `diffusion` passes |
|---|---|---|---|---|---|---|
| SYNTH | baseline | 78.3 | 44.5 | 17.1 | 61.6 | 9.0 |
| SYNTH | JEPA bidirectional | 77.5 | 36.2 | 14.9 | 51.1 | 12.2 |
| SYNTH | JEPA causal | 81.4 | 47.2 | 6.9 | 54.1 | 9.3 |
| TURK | baseline | 37.4 | 28.9 | 1.4 | 30.2 | 12.4 |
| TURK | JEPA bidirectional | 39.0 | 16.9 | 4.7 | 21.6 | 15.6 |
| TURK | JEPA causal | 38.2 | 21.8 | 1.9 | 23.8 | 15.2 |

JEPA minus baseline, in points, paired by test case, with 95% bootstrap CIs over cases.

| Task | Arm | `ar` exact | `diffusion` exact | Interaction, exact | Interaction, content |
|---|---|---|---|---|---|
| SYNTH | bidirectional | −0.8 (−2.4, +0.7) | −8.3 (−11.1, −5.5) | −7.5 (−10.4, −4.7) | −9.4 (−12.3, −6.8) |
| SYNTH | causal | +3.1 (+1.8, +4.5) | +2.7 (+0.1, +5.3) | −0.4 (−3.2, +2.4) | −10.2 (−12.8, −7.6) |
| TURK | bidirectional | +1.6 (−0.1, +3.1) | −12.1 (−14.2, −10.1) | −13.6 (−16.0, −11.3) | −10.2 (−12.5, −8.0) |
| TURK | causal | +0.8 (−0.8, +2.5) | −7.1 (−9.0, −5.3) | −8.0 (−10.1, −5.9) | −7.3 (−9.4, −5.2) |

The untrained model scored 0 of 200 in both modes on both tasks: it explains the regex in prose.
Every trained model stopped on effectively every case in both modes.

## What this shows

- JEPA made diffusion answers less often right in all four comparisons, measured on content, by 6.5
  to 10.4 points, while `ar` moved between −1.0 and +2.8.
- The JEPA arms also took more diffusion passes per answer (9.0 to 12.2 on SYNTH bidirectional, 12.4
  to about 15.5 on TURK) and wrote longer answers. They commit fewer tokens per pass, which reads as
  less confident parallel decoding.
- The one positive exact-match result, causal JEPA on SYNTH (+2.7 in `diffusion`), came from fewer
  overruns (17.1% to 6.9%), not better content (61.6% to 54.1%). On TURK, where the baseline rarely
  overruns, bidirectional JEPA raised overruns from 1.4% to 4.7%.
- Diffusion exact match on these short answers mixes regex quality with whether the model fills the
  rest of its 32-token block. AR overran under 1% of the time in every run.
- Causal JEPA's +3.1 in `ar` on SYNTH is the same size as the paper's +2.6 for Llama-3.2-3B.

## Limits

- One training seed per arm. Diffusion accuracy moves a lot between training runs: the same lbd 2.0
  bidirectional setup scored 51.2% on 500 validation cases in the lbd pick and 36.2% on the test set
  here, while `ar` moved from 75.8% to 77.5%. The CIs above cover test cases only, so the true
  uncertainty of every `diffusion` number is wider.
- 1 epoch with LoRA rank 16 and no predictor tokens. The paper trains 4 epochs with full fine-tuning
  and tuned predictors, and its main claim is that JEPA resists overfitting over epochs, which one
  epoch can't show.
- lbd 2.0 was picked from one run per value (0.5 and 2.0) on SYNTH.
- GSM8K and Spider were not run. GSM8K answers span several diffusion blocks, so it is the task where
  stop behaviour matters least.

## Next, if this resumes

1. Seeds 23 and 37 on SYNTH and TURK (`bench/jepa/run_main.sh` skips finished runs), to measure
   between-run variance. Seed 23 was started and stopped; its partial rows are on the Spark under
   `~/diffusion-demo/runs/aborted-s23/` and should not be used.
2. Score one adapter twice on the same cases to see whether diffusion decoding itself is deterministic.
3. A 4-epoch learning curve for baseline and causal JEPA on SYNTH, scored on held-out validation each
   epoch, which tests the paper's overfitting claim.
4. GSM8K on the first 500 test cases (`TASKS=gsm8k GSM8K_EVAL_CASES=500`).
