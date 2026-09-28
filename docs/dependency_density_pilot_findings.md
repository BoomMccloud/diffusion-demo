# Dependency-density pilot findings

The A100 transport pilot completed on 2026-09-07 with all 18 scored rows. AR produced one exactly valid answer out of nine; DiffusionGemma produced none. No pair had two valid answers, so valid-output latency ratios are unavailable.

The user asked to stop once enough diagnostic data was available rather than run a multi-hour experiment. The 180-row screen and 360-row full matrix were not launched. This is a completed transport pilot, not a completed controlled performance benchmark or evidence of a dependency-density effect.

A later [generous-budget diagnostic](diffusion_completion_diagnostic_findings.md)
found early returns before the 9,216-token cap on two simpler cases. Budget
exhaustion is therefore not the only observed blocker; the native stop cause
still needs direct instrumentation.

## Observed results

| Nominal output tokens | Dependency | AR result | AR warm seconds | Diffusion result | Diffusion warm seconds |
|---:|---|---|---:|---|---:|
| 256 | direct | valid | 2.51 | noncanonical_output | 4.89 |
| 256 | mixed | wrong_length | 2.14 | noncanonical_output | 3.95 |
| 256 | chained | noncanonical_output | 5.10 | noncanonical_output | 3.28 |
| 1,024 | direct | wrong_length | 11.16 | noncanonical_output | 14.04 |
| 1,024 | mixed | noncanonical_output | 14.26 | noncanonical_output | 20.43 |
| 1,024 | chained | wrong_length | 10.12 | noncanonical_output | 27.01 |
| 2,048 | direct | wrong_length | 22.06 | noncanonical_output | 41.55 |
| 2,048 | mixed | noncanonical_output | 29.79 | noncanonical_output | 67.78 |
| 2,048 | chained | noncanonical_output | 29.95 | noncanonical_output | 31.36 |

Each table entry is one case, not a rate estimate or reliable latency distribution. Invalid-output timings do not establish a performance advantage.

All nine diffusion responses consumed their entire 512-, 1,280-, or 2,304-token canvas budget while still inside an unclosed native thought channel. None reached a final answer. AR had four wrong-length answers, four noncanonical answers, and one valid small direct answer.

This makes reasoning-budget exhaustion a concrete next diagnostic for this runtime configuration. It does not establish that dependency density caused the failures, or that AR or diffusion is generally superior.

## Controls and runtime

- GPU: NVIDIA A100-SXM4-40GB, driver 580.82.07. Sampled peak device memory was 28,111 MiB during the pilot.
- AR: `gemma-4-26B-A4B-it-UD-Q4_K_M.gguf`, `llama-cpp-python` 0.3.34.
- Diffusion: `diffusiongemma-26B-A4B-it-Q4_K_M.gguf`, runner source `daca8075d871483545dd85d58ce11970b304b541`, 256-token canvas, KV cache enabled, entropy-bound maximum 48 steps.
- Actual tokenizer calibration selected 126, 510, and 1,022 values, yielding 255, 1,023, and 2,047 expected answer tokens in both tokenizers.
- Both models received the same semantic case prompt, expected answer, and output allowance. Exact native prompt counts include each runtime's formatting.
- One generation runtime was resident at a time. A frozen three-phase plan per size preserved every case's seeded model order. Load and warmup were excluded from warm request-to-response timing.
- Native thought/final channel boundaries were decoded structurally. The sole final JSON object was scored exactly; final prose, extra keys, wrong values, wrong lengths, and malformed channels failed. Complete generated text, reasoning, and transport logs were retained. Entire generation, including reasoning, counted toward the common output budget and timing.
- The pinned diffusion runner hardcodes the native chat template and does not propagate a thinking-disable setting. AR and diffusion therefore retain runtime-specific reasoning behavior; these are model-runtime findings.

Colab reports no active sessions after teardown. The result archive and both compiled tool hashes were verified locally before releasing the runtime.

## Validation and artifacts

The independent artifact check recomputed all scores, decoded every saved diffusion transcript, verified the 18 paired condition/model cells and actual model order, and found zero runtime errors or context overflows. Offline contract tests, micro-benchmark self-tests, compilation, and the existing 50-case schedule validation also passed.

- [Raw result rows](../bench/results/dependency-density/2026-09-07/dependency-density-20260907T050355645694Z.jsonl)
- [Condition summary and artifact hashes](../bench/results/dependency-density/2026-09-07/dependency-density-20260907T050355645694Z-summary.json)
- [Frozen cases](../bench/results/dependency-density/2026-09-07/dependency-density-20260907T050355645694Z-cases.json)
- [Frozen execution plan](../bench/results/dependency-density/2026-09-07/dependency-density-20260907T050355645694Z-execution-plan.json)
- [Artifact validation](../bench/results/dependency-density/2026-09-07/evidence/pilot-validation.json)
- [Pre-pilot registration and later execution limit](../bench/results/dependency-density/2026-09-07/evidence/run-registration.json)

Revalidate the saved run from the repository root:

```bash
python3 bench/results/dependency-density/2026-09-07/evidence/dependency-validate-results.py bench/results/dependency-density/2026-09-07 18 bench/dependency_density_bench.py
```

Before a larger experiment, test a supported reasoning control or a deliberately registered shared budget on a few diagnostic cases. Freeze that configuration before screening; do not combine such results with this pilot as one unchanged experiment.
