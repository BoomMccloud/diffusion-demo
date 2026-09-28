# Repository Agent Instructions

## Start here

This file is the single source of truth for the repository's current work. Read
it before choosing a task. Use the linked documents for detail, but do not infer
the active task from older findings, proposal history, or runbooks. Update this
section when the active objective or its verified status changes.

## Current work

The dependency-density boundary investigation is complete enough to choose a
practical DiffusionGemma screen size. Under the pinned A100 harness,
DiffusionGemma produced exactly correct 48-value responses in 6 of 6 cases over
two fixture seeds. At 56 values it passed 4 of 6 cases, while chained cases
passed 0 of 2 despite returning complete canonical JSON and normal EOG stops.
Treat 48 output decisions as the current tested screen size, not as a universal
model or architecture limit.

The active objective is to compare the two pinned model-runtime systems on 12
recognizable business problems:

- Gemma 4 26B A4B autoregressive through `llama-cpp-python`.
- DiffusionGemma 26B A4B through the instrumented protocol-v2
  `llama-diffusion-cli`.
- Three direct, three mixed-dependency, three chained, and three global-constraint
  problems.
- Exactly 48 scored output decisions per case, using frozen inputs and a
  deterministic validator.
- Run both models on the same fixtures. Retain exact validity, per-decision
  accuracy, first error, constraint violations, request-to-final latency, raw
  output, reasoning, stop reason, token counts, model and runner identities, and
  fixture hashes.

The 12 problem definitions live in
`docs/business_dependency_benchmark_cases.md`. The active set is:

- Direct: accounts-payable classification, support-ticket routing, and
  purchase-order compliance screening.
- Mixed: invoice/subtotal validation, expense-policy review, and bundle-aware
  order fulfillment.
- Chained: cash-balance ledger, inventory-movement ledger, and loan
  amortization.
- Global: employee shift assignment, warehouse-to-order allocation, and
  conference seating.

The first implementation slice is complete in `bench/business_fixtures.py`.
It reproducibly generates three seeded fixtures for each problem, keeps exactly
48 scored string values in one canonical answer envelope, recomputes exact
answers for direct, mixed, and chained cases, and validates global cases by hard
constraints and a registered objective so multiple valid solutions are allowed.
`tests/bench/test_business_fixtures.py` guards the 36-fixture contract. This is offline
fixture evidence only; the staged token counts and context fit are now registered,
but both model systems remain untested on these business cases.

The DiffusionGemma launch path is implemented in `bench/business_benchmark.py`.
Its offline self-test and fake protocol-v2 integration cover immutable 36-case
registration, deterministic shuffled order and request IDs, strict native-channel
and canonical JSON scoring, complete terminal artifacts, context refusal, and
no-repeat resume. `prepare` performs the remaining staged-environment gate: it
measures every prompt and expected answer with both pinned model tokenizers,
hashes the actual model, runner, tokenizer, and harness artifacts, and sends no
generation request. `run-diffusion` is the explicit generation boundary.
The first-run hardening requires a real GPU identity, an exact completed native
warmup, and a complete 36-row summary before the launch command exits zero. The
documented commands use the explicit repository path and do not depend on the
shell working directory.

The staged A100 preparation gate passed on 2026-09-08. The immutable registration
contains all 36 fixtures, both pinned model hashes, exact dual-tokenizer counts,
an A100-SXM4-40GB identity, and reports `launch_ready` with zero generation RPCs.
The documented 9,216-token allowance was first refused because the 2,345-token
`business-m1-000` prompt exceeded the 11,264-token context; the registered shared
allowance is therefore 8,919 tokens, the measured maximum that fits every prompt.
Google Drive credential propagation failed, so the exact models were downloaded
to local NVMe and the protocol-v2 runner was rebuilt from the pinned source and
passed the native stopping and CUDA softcap checks. Its fresh binary hash differs
from the older format-v4 cache artifact and is recorded as a new staged identity.
The registration and preparation evidence are in
`bench/results/business/prepare-2026-09-08/`. No generation request has been sent.

The first `run-diffusion` attempt exposed a launch-safety defect and was stopped
after three terminal rows, before any M1 fixture ran. Although the worker was
registered with an 8,919-token maximum, the native runner rounded the exhausted
G1 response to 8,960 tokens, the next 256-token canvas boundary. That invalidates
the context-fit proof for the largest prompts. The retained partial run contains
zero valid outputs: one budget exhaustion, one incorrect response, and the
operator-cancelled active case. Its artifacts are in
`bench/results/business/diffusion-screen-v1-partial-2026-09-08/`.

Do not resume the unsafe registration. A corrected immutable registration with an
8,704-token shared allowance, the largest 256-token-aligned value below the measured
8,919-token context limit, passed `prepare` with zero generation RPCs and launched.
The corrected runner held the boundary exactly, including on `business-m1-000`, but
Colab terminated the Drive-less VM before completion. Only 21 terminal rows were
downloaded durably: six exact-valid, eight budget-exhausted canonical failures, and
seven complete but incorrect responses. The monitor observed progress through row
30, but rows 22-30 and their raw artifacts were lost with the VM and are not
evidence. The durable corrected registration and partial rows are in
`bench/results/business/prepare-v2-8704-2026-09-08/`.
The analysis, interpretation limits, confirmed accelerator shutdown, and
required follow-up are documented in
`docs/business_diffusion_partial_screen_findings.md`.

No usable accelerator session remains. Before another restart, establish durable
per-case persistence outside the VM and a reliable session keepalive path; do not
repeat another Drive-less long batch that can lose terminal rows. Because the
exact staged runner binary was not preserved, start a fresh immutable 36-case
registration and do not combine its rows with the retained partial run.
Do not start a larger confirmation set until the business screen identifies a
useful and valid separation.

A separate exploratory pilot on 2026-09-28 tested Nemotron-Labs-Diffusion-3B
against public AR endpoints. It found that the frozen business prompts never
state their exact value formats, which also affects the registered DiffusionGemma
screen, and that Nemotron's linear self-speculation matched its own AR accuracy
at 6.1x lower latency on a small keyed-output ladder. Findings and limits are in
`docs/nemotron_diffusion_pilot_findings.md`. The pilot does not change the active
objective. Use Colab CLI 0.7.4 or later: 0.6.0 drops sessions when their proxy
token expires after 60 minutes.

For a human takeover, start with the [operator handoff](docs/operator_handoff.md).
It enumerates the prior Colab and Drive state, the exact format-v4 runner cache,
the setup order, success and refusal signals, resume behavior, and the point at
which the unimplemented business AR phase becomes the next development task.

## Authoritative working files

- `AGENTS.md`: active objective, verified status, and immediate next task.
- `docs/business_dependency_benchmark_cases.md`: the 12 business problems and
  their validation intent.
- `docs/workload_hypotheses.md`: evidence labels, comparison rules, workflow-fit
  versus mechanism interpretation, and promotion criteria.
- `bench/business_benchmark.py`, `bench/diffusion_runtime.py`, and
  `bench/dependency_density_bench.py`: business controller and reusable
  diffusion worker, instrumentation, artifact, tokenizer, and exact-scoring
  contracts.
- `bench/README.md`: durable harness constraints and current Colab execution
  requirements.
- `docs/operator_handoff.md`: human pickup checklist, required staged state, and
  the ordered path from local verification through the next unimplemented phase.
- `bench/DEPENDENCY_DENSITY_RUNBOOK.md`: historical restart details. Consult it
  for operations, but do not use its older status section as the active task.
- `docs/proposals/`: decision and implementation history. Proposal ledgers do not
  replace the current-work section in this file.

Do not claim that the synthetic 48-value result proves performance on these
business problems. The paired business screen is required for that conclusion.

## Accelerator sessions

- Operate Google Colab through the locally installed `colab` CLI by default. Use
  `colab sessions` and `colab status` to discover and reuse an existing runtime,
  and use `colab exec`, `colab upload`, and `colab download` for remote work. Do
  not assume Colab requires browser automation. Use `colab url` and the regular
  Colab UI only when interactive authentication is required or CLI Drive
  credential propagation fails.
- Treat a running Colab or other accelerator session with a loaded model, compiled binary, or populated local cache as expensive state.
- Before stopping or closing such a session, ask the user whether they want to keep it running for additional tests. Explain what would need to be downloaded, compiled, or loaded again if the session is closed.
- Stop the session without asking only when the user has already explicitly instructed you to close it after the current work, or when leaving it running is not possible.
