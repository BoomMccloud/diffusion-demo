# Diffusion stop repair, 2026-09-07

Follow-ups: [matched32-value comparison](diffusion_density32_findings.md) passes all9cases; [softcap boundary investigation](diffusion_softcap_repair_findings.md) proves an isolated integer defect but does not complete the long-runtime repair.

The pinned runner's repetition heuristic prematurely discarded valid generation.
An isolated build with that heuristic bypassed produced two exactly correct
final JSON answers on the previously failing eight-record cases. Native EOG,
the 9,216-token allowance, and the reasoning channel remained enabled.

## Direct evidence

| Case | Original heuristic | Bypass | Bypass seconds |
|---|---|---|---:|
| completion-00 | Repetition stop, 425 committed tokens, no final | EOG, 545 committed tokens, correct final | 4.67 |
| completion-01 | Repetition stop, 596 committed tokens, no final | EOG, 634 committed tokens, correct final | 4.24 |

The full canvas IDs match between baseline and treatment through the baseline
stopping block for both cases. This isolates the truncation behavior. In case 01,
the same canvas already contained the correct final JSON after the native
`<channel|>` boundary, but the repetition heuristic discarded it at position 84.

The heuristic checks short-stride token recurrence without checking whether an
answer has completed. Repeated output values and punctuation can therefore
trigger a false stop. `DIFFUSION_ALLOW_REPETITION=1` bypasses this heuristic in the
isolated diagnostic runner; it does not suppress reasoning or disable EOG.
The default diagnostic mode retains the original behavior for reproduction.

## Larger case and limits

The first 126-value direct case did not complete. Its trace contains 23 full
canvases, 5,888 committed tokens, with repeated input transcription and recounting
inside reasoning. No native stop event was captured. The driver had a 120-second
per-generation limit, but its trace check overwrote the original exception with
`missing_native_stop_event`. The saved row therefore cannot establish the exact
wrapper failure cause. Do not call this native EOG, budget exhaustion, or a proven
model correctness failure.

The follow-up size ladder preserved original exceptions, elapsed time, and native
stop presence separately. It established five more correct final answers:

| Records | Dependency | Correct final | Warm seconds |
|---:|---|---|---:|
| 16 | Direct | Yes, native EOG | 13.96 |
| 32 | Direct | Yes, native EOG | 21.16 |
| 64 | Direct, input 0 | Yes, native EOG | 89.66 |
| 64 | Direct, input 1 | Yes, native EOG | 87.36 |
| 64 | Mixed | Yes, native EOG | 60.69 |
| 64 | Chained | No completed answer; native runtime crashed | Not a completed latency |

The chained case initially received only 40 seconds because the 330-second batch
ceiling reduced its allowance. Preserve that row as a batch-limited timeout,
not a failure under the full 120-second case limit. The native process continued
generating. A separate reader drained the same process without sending a new
prompt or changing the generation, retaining the later failure transcript.

After 31 full canvases (7,936 committed tokens), it crashed with
`CUDA error: invalid configuration argument`. Symbol resolution identifies
`ggml_cuda_op_softcap` through `ggml_cuda_try_fuse`. This localizes a runtime
investigation; it does not yet identify the defective launch dimensions or prove
a repair. The crash occurred before a native EOG or budget stop and is not a
model correctness verdict.

[All ladder rows](../bench/results/dependency-density/stop-repair-2026-09-07/ladder/results.jsonl)
and the [same-generation continuation and crash](../bench/results/dependency-density/stop-repair-2026-09-07/ladder/completion-after-batch.json)
are retained. Independent local solving and exact evaluator replay verified all
five passing answers and their native EOG events.

Next useful work: isolate the CUDA softcap failure before retrying long chained
outputs, and use 32-value matched direct/mixed/chained cases with distinct inputs
for a cheaper dependency comparison. Current sample counts do not establish a
latency ranking.

These are instrumented diagnostics, including trace-write overhead. They do not
establish comparative performance, general reliability, or the full
dependency-density claim. The change is retained as an isolated runner artifact;
it has not changed the shipped runner setup or weakened the benchmark evaluator.

## Evidence and reuse

Artifacts: [stop-repair-2026-09-07](../bench/results/dependency-density/stop-repair-2026-09-07/).

- [Measured rows](../bench/results/dependency-density/stop-repair-2026-09-07/remote/results.jsonl)
- [Decoded full canvases](../bench/results/dependency-density/stop-repair-2026-09-07/remote/decoded-canvases.json)
- [Instrumented native source](../bench/results/dependency-density/stop-repair-2026-09-07/instrumented-diffusion-cli.cpp)
- [Compiled runner and helpers](../bench/results/dependency-density/stop-repair-2026-09-07/repair-tools.tar.gz)
- [Local trim witness](../bench/results/dependency-density/stop-repair-2026-09-07/trim-test.cpp)

The original 20-minute allocation ceiling was extended to 25 minutes during
compilation. The user then explicitly requested retaining the GPU for more tests;
automatic teardown was canceled. The follow-up ladder has its own 330-second
batch limit. The chained runtime subsequently crashed, freeing its GPU memory.
The GPU allocation remained active; a separate worker reloaded the model and
exposes a request file for subsequent use. No teardown is claimed.
