# Partial DiffusionGemma Business Screen Findings

## Status

The corrected DiffusionGemma business screen did not complete. Google Colab
terminated the Drive-less A100 after 21 terminal rows had been downloaded. The
local monitor later observed progress through row 30, but rows 22 through 30 and
their raw terminal artifacts were lost with the VM. They are not evidence and
are excluded from every result below.

The orphaned A100 assignment was explicitly unassigned after the failure. A
server-side `colab sessions` check then returned `No active sessions found on
server.` No accelerator remains active.

## What this run can establish

This run provides partial, uncontrolled-screening evidence about the pinned
DiffusionGemma model-runtime system. It does not provide a complete DiffusionGemma
screen, a paired autoregressive comparison, or evidence for a general
architecture claim.

The retained rows support two operational findings:

1. An 8,704-token output allowance is safe under the tested 11,264-token context
   for all registered prompts and is enforced without the prior block-rounding
   overrun.
2. The tested DiffusionGemma runtime often spends most of its output budget in
   reasoning, and budget exhaustion is the largest failure category in the
   retained sample.

## Registered system

- Registration hash:
  `8b5681ac4f2cb397bbb5a2a646633acc986f11f6ab174bdbf0d5d52386ade5a4`
- Fixture manifest hash:
  `ac5ff6c38d4a9dd7e8f497d12e1938b7783909304101c03f48d67a183d977e83`
- Hardware: NVIDIA A100-SXM4-40GB, 40,960 MiB, driver 580.82.07
- Context: 11,264 tokens
- Shared output allowance: 8,704 tokens, or 34 complete 256-token blocks
- Seed: 20260909
- Protocol: native protocol v2, summary tracing, repetition policy disabled
- Prefill chunk: 2,048 tokens
- DiffusionGemma model SHA256:
  `24523b6c833c9ce9f5f34f9b333ab1517d73d6f1e76a103645353114c8028bc5`
- Gemma autoregressive model SHA256, tokenization only:
  `f2c28b3dc4776931ac6f879e11f203dec637ea0f14267a86ec8f6165f63f293f`
- Protocol-v2 runner SHA256:
  `b8db0f1fbe77cbe839b894afaf1bf5bb9466b1e20790abbfca43f2d199c815fb`
- Tokenizer SHA256:
  `4f79ab7b2fe1a1b495e69c343092c03d9c155dc579076e05a0c4bfaf28a76c1a`

The no-generation preparation gate registered all 36 fixtures and returned
`launch_ready` with `generation_rpc_calls: 0`.

## Why the allowance changed

The first preparation attempt used the documented 9,216-token allowance and was
correctly refused. The largest prompt, `business-m1-000`, contains 2,345 tokens,
so 9,216 output tokens would exceed the 11,264-token context.

An attempted 8,919-token registration also proved unsafe in execution because
the native runner committed complete 256-token blocks. It rounded an exhausted
response up to 8,960 tokens. The corrected allowance is 8,704 tokens, the largest
complete block below 8,919. On the corrected run, `business-m1-000` stopped at
exactly 8,704 tokens without a context overflow or native crash.

## Retained outcomes

| Outcome | Count | Rate |
|---|---:|---:|
| Exact-valid | 6 | 28.6% |
| Budget exhausted | 8 | 38.1% |
| Complete but incorrect | 7 | 33.3% |
| Runtime or context error | 0 | 0.0% |
| Total retained | 21 | 100.0% |

All eight budget-exhausted cases stopped with native reason `block_budget`, used
8,703 or 8,704 output tokens, produced no valid final answer, and failed the
canonical answer contract.

All seven complete-but-incorrect cases stopped with native EOG. Each was wrong
at decision zero and scored 0 of 48 decisions. The retained failures were not
near misses under the deterministic validators.

## Results by dependency class

| Dependency class | Valid | Attempted | Observed validity | Budget exhausted | Incorrect |
|---|---:|---:|---:|---:|---:|
| Direct | 1 | 6 | 16.7% | 1 | 4 |
| Mixed | 0 | 3 | 0.0% | 2 | 1 |
| Chained | 2 | 6 | 33.3% | 2 | 2 |
| Global | 3 | 6 | 50.0% | 3 | 0 |

These class rates are descriptive only. The retained sample is incomplete and
uneven, especially for mixed cases, and the result varies sharply by specific
problem.

## Results by problem

| Problem | Valid | Attempted | Outcomes |
|---|---:|---:|---|
| D1, accounts-payable classification | 1 | 1 | 1 correct |
| D2, support-ticket routing | 0 | 3 | 3 incorrect |
| D3, purchase-order compliance | 0 | 2 | 1 exhausted, 1 incorrect |
| M1, invoice validation | 0 | 1 | 1 exhausted |
| M2, expense-policy review | 0 | 1 | 1 incorrect |
| M3, bundle-aware fulfillment | 0 | 1 | 1 exhausted |
| C1, cash-balance ledger | 2 | 2 | 2 correct |
| C2, inventory ledger | 0 | 2 | 2 incorrect |
| C3, loan amortization | 0 | 2 | 2 exhausted |
| G1, employee shifts | 0 | 2 | 2 exhausted |
| G2, warehouse allocation | 1 | 1 | 1 correct |
| G3, conference seating | 2 | 3 | 2 correct, 1 exhausted |

The strongest observed task-level result is C1 at 2 of 2. D2, C2, C3, and G1
each failed multiple retained fixtures. This task variation prevents interpreting
the class ordering as a dependency-density effect.

## Timing and output use

- Median wall time across all retained attempts: 104.5 seconds
- Median wall time among exact-valid attempts: 80.7 seconds
- Total retained request-to-final time: 1,997.3 seconds
- Amortized time per exact-valid answer: 332.9 seconds
- Median output tokens among exact-valid attempts: 7,003
- Median final-answer tokens among exact-valid attempts: 230
- Median wall time for budget exhaustion: 137.3 seconds
- Median wall time for complete-but-incorrect output: 64.1 seconds
- Sampled peak device memory: 34,755 MiB

The six valid responses used between 6.8 and 50.7 total output tokens for every
final-answer token. This is a runtime-fit observation, not evidence that
diffusion architectures generally require the same reasoning overhead.

## Interpretation

The retained sample does not support a model recommendation. It contains no
paired AR output, is missing 15 of the 36 registered cases, and lost nine
terminal artifacts that were observed only by the monitor.

The useful preliminary signal is problem-specific rather than class-wide:

- DiffusionGemma solved both retained cash-ledger fixtures and two of three
  retained seating fixtures.
- It failed every retained support-routing, inventory-ledger, amortization,
  employee-shift, and mixed-dependency fixture.
- Eight of 21 cases never reached a usable final channel despite an allowance
  more than twenty times larger than the largest expected answer.

Those observations justify completing a controlled screen, but they do not yet
support or refute the registered AR-versus-diffusion dependency hypothesis.

## Data-loss incident

Google Drive credential propagation returned HTTP 400 through the Colab CLI, so
the run used local NVMe. The controller persisted each result on the VM, and a
separate monitor periodically downloaded checkpoints. Colab later terminated
the A100. The final durable checkpoint contained 21 rows. Monitor messages showed
rows 22 through 30 completing, but the terminal JSON, raw output, reasoning,
native events, and hashes for those rows were not downloaded before termination.

Do not reconstruct those rows from monitor summaries or combine them with a
future run. They lack the evidence required by the benchmark contract.

## Required follow-up

1. Establish per-case persistence outside the VM before allocating another A100.
   A working Drive mirror is preferred. Otherwise, use an independent downloader
   that copies every new result artifact immediately and verifies the local copy.
2. Preserve the exact staged runner binary as well as its source manifest. A new
   build can produce a different binary hash even when the patched source is the
   same.
3. Keep the output allowance block-aligned at 8,704 tokens unless a different
   context and allowance are registered and revalidated before generation.
4. Start a fresh immutable 36-case DiffusionGemma registration. Do not present a
   new run plus these 21 rows as one complete screen.
5. Complete all 36 DiffusionGemma rows with terminal artifacts and a completed
   summary, then implement and run the matching autoregressive phase.
6. Analyze paired outcomes only after both systems have complete evidence. Do
   not promote a larger confirmation set from this partial sample.

## Evidence files

- Corrected registration and durable rows:
  `bench/results/business/prepare-v2-8704-2026-09-08/`
- Earlier unsafe 8,919-token preparation and three-row stopped diagnostic:
  `bench/results/business/diffusion-screen-v1-partial-2026-09-08/`
- Initial preparation evidence and token envelope:
  `bench/results/business/prepare-2026-09-08/`
- Active workload definitions and interpretation rules:
  `docs/business_dependency_benchmark_cases.md` and
  `docs/workload_hypotheses.md`
