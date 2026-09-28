---
proposal_id: "operator-handoff-readiness"
state: ACCEPTED
witness: builder
candidate: "4c58d38cc0724f04311158729a20f19a34aa2e11f408f3beba5714c2365d56cc @ active-source digest"
---

# Proposal: Operator handoff readiness

## Proposal

### Intent

Get the repository to a state where someone else can come in and know where to pick up, with particular attention to the A100 onboarding path and its undocumented prior state.

### Tentative primary claim

An incoming operator can identify the repository's verified state, immediate next action, required prior state, and the point at which the current workflow stops and unimplemented work begins.

### Why now

The repository audit found that A100 onboarding depends on undocumented prior state, even though the current cleanup order puts onboarding first.

### Known constraints

The handoff must make clear where another person should pick up.

### Non-goals

None stated.

### Open choices

None stated.

## Frame

Candidate: `b31f45c7fa51e701a9656b1cdbc4ca45d3617c606914b6fd676b834e991cdfe1 @ active-source digest`

### Verified reality

- `PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -t . -p 'test*.py' -v` passed all 26 discovered tests before the change; log: `/tmp/operator-handoff-baseline.log`; limit: this is offline evidence and does not exercise Colab, an A100, staged artifacts, or either model.
- `AGENTS.md:Current work` identifies staged A100 `prepare` as the immediate next step and explicitly says real tokenizer counts and context fit do not yet exist; limit: `AGENTS.md` is agent-oriented and does not enumerate the prior state a new human operator must supply.
- `bench/README.md:Colab execution` provides the worker, `prepare`, and `run-diffusion` commands and their success gates; limit: it begins after Drive, repository, cache, model, runner, tokenizer, CUDA, and Python-cell state have already been established.
- `cells/common/cell_3_model_setup.py` can resolve both pinned GGUF files into the Drive cache and exports `AR_MODEL_PATH` and `DIFF_MODEL_PATH`; limit: it assumes Colab packages and Drive state and does not stage the current protocol-v2 runner.
- `cells/nvidia/cell_2_runner_setup.py:97-130` creates a format-v3 runner cache key, while `bench/README.md:76-77` requires the verified format-v4 protocol-v2 cache `v4_sm_80_nvcc_12_8_src_daca8075d871_harness_v2`; limit: the active-looking Cell 2 file cannot safely reconstruct or select the currently documented business-screen runner.
- `docs/workload_hypotheses.md:31-41` records the DiffusionGemma staged preparation and run as next and the matching autoregressive business phase as not started; limit: this backlog is not a standalone operator handoff.

### Final primary claim

- Starting from the root README, an incoming operator can determine the verified repository state, supply every prerequisite for the staged A100 workflow, execute the exact next gate, recognize success or refusal, resume safely, and identify the unimplemented autoregressive phase without relying on prior conversation.

### Routing

- Witness: `builder`
- Why: The change is contained to local documentation and a documentation contract; it does not alter model execution, stored benchmark evidence, or an external service boundary.
- Human-owned irreversible action: Allocating or stopping an accelerator and launching real model generation remain operator-owned actions.

### Decisive witness

- Layer: Repository documentation contract plus existing offline gates.
- Permanent owner: `tests/test_operator_handoff.py` and the existing benchmark test suite.
- Witness: The root README links one handoff entry point whose checked structure names the verified state, exact A100 prerequisites, stale v3 Cell 2 hazard, setup order, `prepare` success gate, resume and accelerator-retention behavior, and the unimplemented AR boundary; every referenced repository path exists and the existing offline suite remains green.

### Guardrail claims

- The handoff distinguishes offline evidence from missing staged-A100 and model-run evidence, so documentation cannot imply the business screen has run.
- The format-v3 Cell 2 script is explicitly excluded from the current protocol-v2 business launch path, while its provenance remains untouched.
- Existing benchmark behavior, fixture contracts, operational commands, results, archives, and accelerator state remain unchanged.

### Supporting obligations

- Add a concise human-facing handoff document with a state table, prerequisite inventory, ordered setup and launch checklist, expected outputs, failure and resume guidance, and the next unimplemented phase.
- Link that document prominently from `README.md`, and align `AGENTS.md` and `bench/README.md` so all current entry points identify the same operator path and the Cell 2 mismatch.
- Add a focused documentation contract that checks the durable handoff facts and repository path references without duplicating benchmark logic.

### Allowed scope

- Reuse: Extend `README.md`, `AGENTS.md`, and `bench/README.md`; reuse `business_benchmark.py prepare` as the executable preflight and the existing unittest suite as the gate.
- Cheaper alternative: Adding one README sentence was rejected because it would not expose the hidden environment inventory, contradictory Cell 2 cache identity, success and refusal states, resume rules, or AR implementation boundary.
- Include: `README.md`, `AGENTS.md`, `bench/README.md`, new `docs/operator_handoff.md`, new `tests/test_operator_handoff.py`, and this proposal ledger; `/tmp` may hold deterministic test logs.
- Exclude/protect: Model and runtime code, fixture semantics, native source and binaries, staging-cell implementation, benchmark results, archive payloads and manifest, real accelerator state, model generation, and implementation of the autoregressive business phase.

### Decisions required

- None.

## Proof

Builder-route witness deferred to Build. The builder must add `tests/test_operator_handoff.py`, observe proposal-specific RED before the handoff document and entry-point updates exist, and retain that test as the permanent documentation-contract owner.

## Build

Candidate: `4c58d38cc0724f04311158729a20f19a34aa2e11f408f3beba5714c2365d56cc @ active-source digest`

### Files changed

- `docs/operator_handoff.md`: added the single human pickup path with verified state, missing evidence, prerequisites, exact format-v4 artifact verification and staging, ordered A100 execution, success and refusal signals, resume guidance, accelerator-retention rules, and the AR development boundary.
- `README.md`: linked the handoff from the opening status and corrected the active-layout description so the format-v3 runner cell is not presented as the current setup path.
- `AGENTS.md`: linked the human handoff from the authoritative current-work section and indexed it as an authoritative working file.
- `bench/README.md`: routed new operators through the handoff, explicitly excluded the format-v3 Cell 2 script from the current business launch, and recorded the durable format-v4 constraint with its reason and test owner.
- `tests/test_operator_handoff.py`: added the builder-owned documentation contract for entry-point links, handoff structure, durable operational facts, and referenced repository paths.

### Unit evidence

- Builder-owned decisive witness: `PYTHONDONTWRITEBYTECODE=1 python -B -m unittest tests.test_operator_handoff -v`: RED because the root README had no handoff link and the handoff did not exist; log: `/tmp/operator-handoff-red.log`.
- `PYTHONDONTWRITEBYTECODE=1 python -B -m unittest tests.test_operator_handoff -v`: GREEN after the handoff and entry-point alignment; log: `/tmp/operator-handoff-green.log`.

### Green evidence

- Decisive witness: `PYTHONDONTWRITEBYTECODE=1 python -B -m unittest tests.test_operator_handoff -v`: pass, one test; log: `/tmp/operator-handoff-green.log`.
- Gate: `PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -t . -p 'test*.py' -v`: pass, 27 tests; log: `/tmp/operator-handoff-suite.log`.
- Gate: `PYTHONDONTWRITEBYTECODE=1 python -B -m bench.business_benchmark self-test --json --output-dir <fresh-temp-dir>`: pass with `launch_ready`, 36 fixtures, 48 decisions, and zero generation RPCs; log: `/tmp/operator-handoff-business.log`.
- Gate: `PYTHONDONTWRITEBYTECODE=1 python -B bench/dependency_density_bench.py selftest --json`: pass with all deterministic matrix checks true; log: `/tmp/operator-handoff-density.log`.
- Documentation check: in-memory Python parsing of all three handoff Python blocks plus local Markdown target verification for the four changed documents: pass; log: `/tmp/operator-handoff-doc-check.log`.

### Intervention record

- None, because this is a repository operator handoff with no deployed product surface.

### Deviations

- None.

## Audit

Candidate: `4c58d38cc0724f04311158729a20f19a34aa2e11f408f3beba5714c2365d56cc @ active-source digest`

Independence: same-context: the auditing context framed and built the documentation candidate; no fresh-context audit was run.

Primary-claim verdict: PROVED: evidence: `tests/test_operator_handoff.py` verifies the root entry point, handoff structure, current state, setup hazard, launch and resume gates, AR boundary, and repository paths; `docs/operator_handoff.md` supplies the prerequisite inventory and ordered pickup sequence; limit: its embedded setup cells were syntax-checked but not executed in Colab or against the Drive cache.

Guardrail verdicts:
- Offline evidence remains distinct from missing staged-A100 and model-run evidence: PROVED: evidence: the handoff states that no real business-screen result exists and enumerates missing token, context, accelerator, quality, latency, and paired-run evidence; limit: future results must still be recorded in `AGENTS.md`.
- The format-v3 Cell 2 script is excluded from the current protocol-v2 launch path without altering its provenance: PROVED: evidence: `README.md`, `bench/README.md`, and `docs/operator_handoff.md` identify the mismatch, while the cell implementation remains unchanged; limit: the stale file remains physically present.
- Existing benchmark behavior, fixtures, results, archives, and accelerator state remain unchanged: PROVED: evidence: the candidate changes only approved documentation, the new test, and the ledger; all 27 discovered tests and both self-tests pass; limit: no live accelerator state was inspected.

Scope and duty verdict: scope HELD; duties HELD: evidence: changed paths are `README.md`, `AGENTS.md`, `bench/README.md`, `docs/operator_handoff.md`, `tests/test_operator_handoff.py`, and this ledger; the durable format-v4 rule is recorded in the nearest `bench/README.md` with its reason and guard test; limit: no Git metadata exists, so scope was checked by path inspection and the reproducible active-source digest.

Test homes: `tests/test_operator_handoff.py`: permanent repository-level owner for the human handoff entry point and durable operator facts.

Full gates: PASS: the 27-test discovery suite passed; the business self-test reported `launch_ready`, 36 fixtures, 48 decisions, and zero generation calls; the dependency-density self-test passed all deterministic checks; embedded Python parsing and local-link checks passed; limit: all are offline gates.

Residual risks:
- The exact format-v4 Drive cache and model cache still require verification on the next A100 allocation.
- The documented Colab staging snippets have not yet been executed as one live notebook sequence.
- The stale format-v3 Cell 2 file could still confuse someone who bypasses the root README.

Recommendation: ACCEPT

Packet: No candidate revision required. The next operator should start at `docs/operator_handoff.md`, complete the staged A100 `prepare` gate, and preserve its resulting evidence.

## Revisions

<!-- Append-only, written by the orchestrator. One entry per audit REVISE and the
work that answered it. Never delete an entry, never edit an earlier one, and never
move Frame, Proof, Build or Audit history into it. Empty until the first REVISE. -->
