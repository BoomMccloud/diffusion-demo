# Diffusion completion diagnostic, 2026-09-07

Follow-up: [native stop repair findings](diffusion_stop_repair_findings.md) confirms repetition trimming caused the short-case cutoff and records two correct final answers after bypassing that heuristic.

Two diffusion-only cases with eight independent records each failed to reach a
final answer even with an accepted 9,216-token allowance. Both returned before
using that allowance. The low token budget is therefore not the only observed
blocker in this pinned runtime configuration.

## Results

| Case | Retokenized output | Canvas work | Allowed tokens | Warm seconds | Final answer |
|---|---:|---:|---:|---:|---|
| diagnostic-completion-00 | 425 | 512 | 9,216 | 3.20 | None |
| diagnostic-completion-01 | 596 | 768 | 9,216 | 4.65 | None |

Both outputs opened a thought channel and ended mid-text without closing it.
Each contained the correct expected eight-value list inside its reasoning, but
neither delivered the required final JSON response. Those reasoning fragments
are not counted as valid answers.

The startup log confirms `-n 9216` became 36 blocks with an 11,264-token context,
batch, and microbatch. Each formatted prompt used 135 tokens. The runner returned
after two and three blocks respectively, without a Python runtime error or wall
timeout. Prompt plus maximum allowance fits the context. Peak sampled device
memory was 30,393 MiB on the A100-SXM4-40GB.

## What this establishes

- A small requested allowance is not sufficient to explain all observed missing
  final answers. These two attempts stopped well below the generous allowance.
- The correct values appearing in reasoning do not establish reliable final
  answer correctness or a workload advantage.
- The existing CLI does not report the exact native stop cause. An end token,
  repetition cutoff, or another internal early-exit path cannot be distinguished
  conclusively from these saved logs. Do not relabel the result as budget
  exhaustion or assert a particular runner defect.
- Token counts are retokenized text counts, not captured emitted token IDs.
  Channel-phase timing is unavailable because the CLI buffers the response.

The next prerequisite is native stop-event instrumentation: block index, emitted
and committed token counts, cut position, stopping token ID when applicable, and
the explicit branch/reason for termination. Capture these before scheduling more
correctness, dependency, or length cases. Preserve the full canvas/token tail so
an early cutoff can be reproduced offline.

## Execution and stopping

The registered plan allowed at most 15 adaptive cases. The completion gate
required both short cases to reach a final answer. It failed, so the other 13
cases were not launched. No AR model and no low-budget control were run. Nine
saved pilot cutoff transcripts were classified offline before allocation.

The same diffusion checkpoint and cached runner were reused. The diffusion
checkpoint digest was verified after download. The runtime was kept resident
between the two cases, with conversation history cleared and seed/turn order
recorded. Model load and warmup were excluded from measured latency.

The entire allocation, including setup and teardown, was bounded above by 10.9 minutes against a 20-minute ceiling. Colab reports no active sessions.

## Saved evidence

Artifacts: [`bench/results/dependency-density/diffusion-diagnostic-2026-09-07/`](../bench/results/dependency-density/diffusion-diagnostic-2026-09-07/).

- [Frozen registration](../bench/results/dependency-density/diffusion-diagnostic-2026-09-07/registration.json)
- [Calibrated cases](../bench/results/dependency-density/diffusion-diagnostic-2026-09-07/calibrated-cases.json)
- [Raw scored rows and transcripts](../bench/results/dependency-density/diffusion-diagnostic-2026-09-07/results.jsonl)
- [Runtime and artifact identities](../bench/results/dependency-density/diffusion-diagnostic-2026-09-07/provenance.json)
- [Startup log confirming the allowance](../bench/results/dependency-density/diffusion-diagnostic-2026-09-07/startup-11264.log)
- [Saved artifact checks](../bench/results/dependency-density/diffusion-diagnostic-2026-09-07/validation.json)
- [Teardown confirmation](../bench/results/dependency-density/diffusion-diagnostic-2026-09-07/teardown.log)

This diagnostic is separate from the earlier 18-row pilot. It does not complete
the registered AR-versus-diffusion matrix or establish a dependency-density effect.
