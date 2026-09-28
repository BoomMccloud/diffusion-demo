# Matched 32-value diffusion comparison, 2026-09-07

## Harness-v2 verification

The permanent harness replayed the same nine prompts and expected answers on a
fresh Colab A100 after a clean pinned build. All 9/9 responses were exact, all
ended with one native EOG stop, no request recorded an error, and every result
contained native prefill, denoise, and commit events. Median valid wall times
were 21.54 seconds direct, 14.37 mixed, and 14.87 chained. The full measured
batch window was 163.51 seconds, or 18.17 allocation seconds per correct answer;
request time was 16.19 seconds per correct answer. Peak sampled device memory
was 30,992 MiB.

The real fused GGML/CUDA graph probe passed numerical sentinels at 256, 8,191,
8,192, 8,239, and 11,264 positions. This verifies the repaired 64-bit launch
path across the prior overflow boundary. It does not prove that every longer
full-model generation is free from an independent memory error.

Evidence is frozen under
[`harness-v2-proof-2026-09-07`](../bench/results/dependency-density/harness-v2-proof-2026-09-07/),
including the downloaded Colab packet, extracted results, build identity, native
events, backend logs, and local manifest. The A100 session was closed after the
packet was downloaded and validated.

All nine measured cases produced exactly correct final JSON and native EOG stops:
three direct, three mixed, and three chained. Within each trio, the expected
32-value answer was identical; the records encoded different dependency patterns.

| Dependency | Correct | Median warm seconds | Range | Median committed tokens |
|---|---:|---:|---:|---:|
| Direct | 3/3 | 21.48 | 18.02–31.61 | 2,719 |
| Mixed | 3/3 | 14.40 | 9.61–14.53 | 2,256 |
| Chained | 3/3 | 15.16 | 5.56–16.56 | 2,210 |

This sample does not support a simple claim that increasing dependency density
makes diffusion slower. Direct cases were slower than both alternatives in each
of the three matched trios. That is an exploratory observation, not a reliable
performance ranking: only three inputs were tested, reasoning lengths differ,
and prompt encodings change with the task. There is no AR comparison here.

The pinned runner's repetition heuristic was bypassed; reasoning, native EOG,
and the 9,216-token allowance remained enabled. A warmup preceded measurement,
and each case had the same 120-second limit. Density order followed a Latin
square across the three trios. The driver required enough batch time for a full
case before launching it, avoiding the shortened final-case limit in the earlier
ladder. The resident model was reused and conversation history cleared.

The sampler configuration used seed 20260909, and fixture construction used
20260910. This was a sequential resident execution, not a randomized multi-seed
reliability study. Timings include native trace writes and the full reasoning
phase, and exclude model load and warmup.

## Evidence

Artifacts: [density32-2026-09-07](../bench/results/dependency-density/density32-2026-09-07/).

- [Frozen matched cases](../bench/results/dependency-density/density32-2026-09-07/cases.json)
- [Registration and order](../bench/results/dependency-density/density32-2026-09-07/registration.json)
- [Measured rows and native events](../bench/results/dependency-density/density32-2026-09-07/remote/results.jsonl)
- [Independent audit](../bench/results/dependency-density/density32-2026-09-07/independent-review.md)
- [Independent solving and aggregate checks](../bench/results/dependency-density/density32-2026-09-07/validation.json)

The long chained CUDA failure is a separate runtime issue. The [softcap investigation](diffusion_softcap_repair_findings.md) confirms an integer overflow in isolated CUDA tests, but the native long-case replay still hits an illegal memory access. Long outputs remain unsuitable for model-quality conclusions until that runtime failure is resolved.
