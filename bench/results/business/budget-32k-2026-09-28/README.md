# 32k output-budget probe (POC, 2026-09-28)

A100-SXM4-40GB, pinned `daca8075` runner with incremental prefill and a
2,048-token ubatch decoupled from context (`bench/native/prepare.py`). Context
32,768, output allowance 30,208 (118 blocks), same seed as the business screen.
Peak sampled GPU memory 34,510 MiB. Not a registered run.

Cases: `c1-001` as a sanity control, plus the eight cases that exhausted the
8,704-token allowance on 2026-09-08.

| Case | Blocks | ~Output tokens | Wall s | Stop | Valid | Note |
|---|---:|---:|---:|---|---|---|
| c1-001 | 26 | 6.6k | 23.3 | eog | yes | control, 48/48 |
| g1-001 | 42 | 10.7k | 94.2 | eog | yes | was budget-exhausted |
| g3-002 | 36 | 9.2k | 79.7 | eog | yes | was budget-exhausted |
| g1-000 | 79 | 20.2k | 365.0 | eog | no | 2 constraint violations |
| c3-001 | 97 | 24.8k | 228.2 | eog | no | chained arithmetic |
| c3-002 | 67 | 17.2k | 82.9 | eog | no | first error at decision 6 |
| m1-000 | 75 | 19.2k | 142.5 | eog | no | labels not given in prompt |
| m3-002 | 28 | 7.2k | 75.7 | eog | no | labels not given in prompt |
| d3-001 | 18 | 4.6k | 25.6 | eog | no | 46/48 right ignoring case |

All nine stopped at native EOG; none reached the allowance. The longest needed
97 blocks (about 24.8k tokens), so 30,208 covered every case with about 5k spare.

Six of the 12 problem prompts do not state the exact output vocabulary the
validator requires: D3 (label case), M1, M2, M3 (label names), D2 (joiner), C2
(`stock:DECISION` format). The model cannot be exactly right on those except by
guessing. Every exact-valid row so far, here and in the 2026-09-08 partial run,
comes from the six fully specified problems (D1, C1, C3, G1, G2, G3).

A first 32k attempt crashed on every case because the CLI sized
`output_tokens` by ubatch; those rows are in `crashed-output-buffer-bug/` and are
not evidence. A 64k attempt ran out of device memory: the prefix-KV store is F32
without flash attention (about 450 KB per token).
