# Incremental prefill A/B (POC, 2026-09-28)

One A100-SXM4-40GB Colab session, one CUDA build of pinned `daca8075` with the
incremental-prefill patch in `bench/native/prepare.py`. Arms differ only by
`DIFFUSION_INCREMENTAL_PREFILL` (0 = full re-prefill per block, 1 = encode only
new tokens). Same seed, 8,704-token allowance, 11,264 context, warmup excluded.
Not a registered run; do not merge these rows with business-screen evidence.

| Case | Arm | Wall s | Prefill s | Denoise s | Steps | ms/step | Stop | Valid |
|---|---|---:|---:|---:|---:|---:|---|---|
| c1-001 | off | 58.4 | 30.7 | 27.5 | 156 | 176 | eog | yes |
| c1-001 | on | 23.6 | 1.4 | 22.1 | 148 | 149 | eog | yes |
| g1-001 | off | 138.5 | 60.9 | 77.4 | 391 | 198 | block_budget | no |
| g1-001 | on | 112.3 | 3.4 | 108.9 | 594 | 183 | block_budget | no |
| m1-000 | off | 111.3 | 66.0 | 45.2 | 212 | 213 | block_budget | no |
| m1-000 | on | 66.2 | 4.4 | 61.6 | 329 | 187 | block_budget | no |

Totals: wall 308.1 s off, 202.1 s on (34% less). Prefill 157.6 s to 9.2 s (94%
less). Denoise cost per step is equal or lower with the patch; the patched arm
took more denoising steps on g1 and m1. At equal step counts the patched arm
would take about 146 s for this set (about 53% less).

Outputs diverge within the first block (first differing character 35 to 128),
because reused prefix K/V and different chunk boundaries change floating-point
order and the sampler amplifies small differences. Validity matched on all three
cases. Three cases cannot show whether the step-count increase is systematic.

The baseline reproduced the 2026-09-08 run closely: g1-001 took 138.5 s with
60.9 s prefill, against 138.9 s and 61.3 s then.
