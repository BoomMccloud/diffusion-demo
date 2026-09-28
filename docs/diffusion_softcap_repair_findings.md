# Softcap boundary investigation, 2026-09-07

The fused softcap implementation has a confirmed 32-bit size/index defect.
Widening those values fixes isolated CUDA boundary tests, but the full long-case
runtime still fails with an illegal memory access. The integrated repair is
therefore incomplete.

## What was proved

The model has 262,144 vocabulary entries. Its logit tensor reaches 2³¹ elements
at 8,192 positions. `ggml_nelements` supplies a 64-bit size, but the original
`softcap_f32_cuda` and kernel accept `int`, and block/index arithmetic also uses
32-bit values. The host test extracts the actual implementation's launch
arithmetic. At 8,192 positions it records a negative element count and block
count instead of the required positive values.

The isolated patch changes the host and device counts, block count, and index
multiplication to 64-bit arithmetic. It preserves the softcap formula.

Actual CUDA tests allocated full input and output tensors and sampled numerical
results at the beginning, midpoint, and final index:

| Positions | Original | 64-bit patch |
|---:|---|---|
| 8,191 | Numerical checks pass | Not rerun |
| 8,192 | Invalid configuration argument | Numerical checks pass |
| 8,239 | Not rerun | Numerical checks pass |
| 11,264 | Not rerun | Numerical checks pass |

The CUDA probe extracts the actual kernel and host launch function but replaces
the production launcher/PDL wrapper with a direct CUDA launch adapter. The A100
probe therefore establishes launch arithmetic and sampled numerical behavior,
not complete backend correctness or exhaustive tensor verification.

## Native integration result

The incremental native build succeeded. A previously passing 32-value chained
case again returned the exact final answer and EOG, in 23.75 seconds. This was a
correctness control, not a performance comparison across builds.

The same frozen 64-value chained case was then run with the 9,216-token allowance
and a full 240-second timeout, sufficient to observe beyond the earlier crash.
The runner completed 31 canvases, retaining 7,936 generated tokens, then exited
with code -6. The transcript reports **an illegal memory access** at
`cudaStreamSynchronize`, rather than the previous softcap invalid-launch error.
No final answer or native stop event was obtained.

This does not establish a second independent defect or its location. CUDA errors
are asynchronous; the synchronization stack is insufficient to attribute the
invalid access to a particular kernel. The 64-bit patch is not accepted as a
complete native-runtime fix and has not been promoted into shipped runner setup.
The isolated boundary finding remains valid.

## Next smallest diagnostic

Reproduce the large tensor through the full backend with synchronous CUDA launch
reporting or a memory checker. Start with a minimal graph around the boundary,
so locating the memory access does not require replaying minutes of reasoning.
Do not use the long chained runtime failure as evidence of model correctness or
dependency-density performance. The separate matched 32-value comparison passed
all nine cases.

## Saved artifacts and session

Artifacts: [softcap-repair-2026-09-07](../bench/results/dependency-density/softcap-repair-2026-09-07/).

- [Original source](../bench/results/dependency-density/softcap-repair-2026-09-07/softcap-original.cu)
- [Isolated patch](../bench/results/dependency-density/softcap-repair-2026-09-07/softcap-fixed.cu)
- [Host boundary witness](../bench/results/dependency-density/softcap-repair-2026-09-07/test-softcap-boundary.py)
- [CUDA probe generator](../bench/results/dependency-density/softcap-repair-2026-09-07/make-cuda-probe.py)
- [Native rows and full transcripts](../bench/results/dependency-density/softcap-repair-2026-09-07/remote/results.jsonl)
- [Native crash symbols](../bench/results/dependency-density/softcap-repair-2026-09-07/crash-symbols.log)
- [Cached experimental runner](../bench/results/dependency-density/softcap-repair-2026-09-07/runner.tar.gz)

The GPU allocation was retained at the user's request. After the native crash,
the model was reloaded in a replacement resident worker; no session teardown is
claimed. This experimental runner remains suitable only for the tested scope,
with the unresolved long-generation failure recorded above.
