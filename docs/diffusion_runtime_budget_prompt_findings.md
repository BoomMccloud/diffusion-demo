# DiffusionGemma runtime, budget, and prompt findings (2026-09-28)

Exploratory proof-of-concept work on one A100-SXM4-40GB Colab session. None of
these rows belong to a registered business screen, and none may be merged with
the retained 2026-09-08 partial run.

## What changed

- **Incremental prefill** (`bench/native/prepare.py`, `bench/native/benchmark_trace.h`).
  The pinned CLI re-encoded the whole prompt plus every committed block from
  position 0 before each 256-token block. The runner now keeps the prefix-KV store
  across blocks, sizes it for the full context once, and encodes only tokens past
  the longest stored common prefix. `DIFFUSION_INCREMENTAL_PREFILL=0` restores the
  original behavior on the same binary. Traces record `reused_tokens`.
- **Decoupled ubatch.** With incremental prefill and `--diffusion-kv-cache on`, the
  CLI no longer grows ubatch to the whole context. `DIFFUSION_UBATCH` sets `-b` and
  `-ub`. The CLI's `output_tokens` buffer was sized by ubatch and overflowed once
  prefix plus canvas passed it; it is now sized by context.
- **Worker settings.** `DIFFUSION_MAX_TIMEOUT` raises the 600-second per-request cap.
  The worker configuration reports `incremental_prefill` and `ubatch`.
- **Build fix.** `bench/native/build.py` pointed at a moved softcap test.
- **Prompt formats** (`bench/business_fixtures.py`). Six instructions now name their
  exact output vocabulary or format: D2 (underscore joiner), D3 (APPROVE, REVIEW,
  REJECT), M1, M2, M3 (label names and per-line layout), and C2 (`STOCK:STATUS`).
  Inputs, seeds, and validators are unchanged; prompt hashes change, so any new run
  needs a fresh registration.

## Evidence

**Speed.** A/B on the same binary, seed, and 8,704-token allowance, in
`bench/results/business/ab-incremental-prefill-2026-09-28/`. Three long cases took
308.1 s with full re-prefill and 202.1 s with incremental prefill (34% less).
Prefill fell from 157.6 s to 9.2 s. Denoising cost per step was equal or lower.
The patched arm happened to take more denoising steps on two cases; at equal
steps the set would take about 146 s. Outputs diverge within the first block
because reused K/V change floating-point order; validity matched on all three.
The baseline reproduced 2026-09-08 closely (g1-001: 138.5 s against 138.9 s).

**Budget.** At 32,768 context and a 30,208-token allowance, in
`bench/results/business/budget-32k-2026-09-28/`, all nine tested cases stopped at
native EOG, including the eight that exhausted 8,704 tokens before. The longest
used about 24.8k tokens. Exhausted reasoning before was still making progress,
not looping. Peak sampled GPU memory was 34.5 GiB. A 65,536 context failed to
allocate: without flash attention the prefix-KV store is F32, about 450 KB per
token. Per-case wall time ranged from 23 s to 365 s.

**Prompt formats.** With the old prompts, every exact-valid row came from the six
fully specified problems (D1, C1, C3, G1, G2, G3). With the fixed prompts and the
30,208 allowance, in `bench/results/business/fixed-prompts-2026-09-28/`, five of
six previously invalid cases (d2-001, d3-001, m1-000, m2-001, c2-000) returned
48/48. m3-002 used the right labels but misaligned its per-group layout from
decision 14 (32/48).

**Sampler parity.** The pinned CLI's entropy-bound defaults match the released
`generation_config.json` (48 steps, temperature 0.8 to 0.4, entropy bound 0.1,
stability 1, confidence 0.005), but GGUF `diffusion.eb_*` keys can override them
and the startup line that reports the effective values is not retained. Its
sliding-window behavior follows Google's JAX sampler.

## Limits

One case per changed problem and three to nine cases per test are screens, not
estimates. The patched runner is a new identity and has not passed `prepare`.
Flash attention would allow about 64k context on this GPU but changes numerics.
The AR arm has not been given the larger allowance.
