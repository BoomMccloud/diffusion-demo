# Diffusion 64-value controls, 2026-09-07

The repaired runtime passed its safety gate but the model did not pass the
64-value correctness gate. Four targeted controls produced zero exact answers.
The planned nine-case batch was therefore not launched.

| Encoding | Prefill chunk | Outcome | Seconds | Native stop | Canvas work |
|---|---:|---|---:|---|---:|
| Chained, pair 0 | 2,048 | Canonical but 63/64 values | 43.16 | EOG | 4,864 |
| Direct, pair 0 | 2,048 | Incorrect | 29.54 | EOG | 4,096 |
| Chained, pair 1 | 2,048 | Incorrect | 39.92 | EOG | 4,864 |
| Chained, pair 0 | 11,264 | Incorrect | 104.20 | EOG | 5,888 |
| Direct, pair 0 | 11,264 | Timed out | 120 limit | Cancelled | unavailable |

The first chained response reasoned through all 64 records correctly but emitted
only 63 final values, omitting the expected `A` at zero-based index 62. It ended
with native EOG, so the harness did not trim it. The fixture contains 64 records
and the independent solver produces 64 expected values.

Full prefill did not restore chained correctness and made the direct case exceed
the 120-second limit. The 2,048-token prefill cap is therefore not the sole cause
of the correctness failure. These results support a 64-value reliability limit
for this configuration, rather than an intentional defect in the fixture. They
do not estimate a success rate because only four targeted controls were run.

The resident full-prefill model remained loaded after evidence capture. The
instrumented runner and CUDA probe were cached in Google Drive under
`diffusiongemma-demo/diffusion-runner/v4_sm_80_nvcc_12_8_src_daca8075d871_harness_v2`.
The already-cached pinned model remains under
`diffusiongemma-demo/huggingface_cache`.

Evidence is stored locally in
[`density64-2026-09-07`](../bench/results/dependency-density/density64-2026-09-07/)
and in Drive under
`diffusiongemma-demo/benchmark-results/dependency-density/density64-controls-2026-09-07`.
The combined archive SHA256 is
`c7911ed496958ce1bd66a3b2f15d841841f605ed40c4d76b60ad435518edc137`.
