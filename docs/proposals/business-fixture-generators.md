---
proposal_id: "business-fixture-generators"
state: ACCEPTED
witness: builder
candidate: "native-sha256:19c466b25f8342501f43d5133224f5a0351b2a1511f4d76b71b0588706b2b036 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo"
---

# Proposal: Frozen business benchmark fixture generators

## Proposal

### Intent

Convert the twelve business dependency benchmark definitions into frozen fixture generators.

### Tentative primary claim

The repository can reproducibly generate the initial three fixtures for each of the twelve defined business problems, with exactly 48 scored output decisions per fixture.

### Why now

Fixture generation is the next implementation task for the active paired business benchmark.

### Known constraints

Use the twelve definitions in `docs/business_dependency_benchmark_cases.md`; create three fixtures per problem for the initial screen; keep exactly 48 scored output decisions per fixture; use frozen inputs and deterministic validation.

### Non-goals

Do not start a larger confirmation set before the business screen identifies a useful and valid separation.

### Open choices

None stated.

## Frame

Candidate: `prebuild-sha256:a0fe319eb4b348bf31859e00357c01393fa865d4d7b374d3a53b9fbb53dec278 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo`

### Verified reality

- `python -m unittest bench/test_dependency_density_bench.py bench/test_diffusion_runtime.py -v` — proves the 12 existing offline benchmark and runtime tests passed before fixture implementation; limit: it does not cover business fixtures.
- `bench/dependency_density_bench.py:compact_json`, `stable_hash`, `make_case`, and `evaluate_output` — proves the repository already uses standard-library deterministic RNG, compact canonical JSON, content hashes, and strict evaluation; limit: the current schema only supports binary synthetic dependency cases.
- `bench/test_dependency_density_bench.py:DependencyDensityBenchmarkContractTest` — proves standalone CLI contract tests are the current permanent ownership pattern; limit: its matrix assertions do not cover the twelve business definitions.
- `docs/business_dependency_benchmark_cases.md` — defines twelve problems in four dependency classes and exactly 48 decisions per response; limit: it contains descriptions rather than executable fixture or validation contracts.
- `docs/workload_hypotheses.md:Measurement contract` — requires frozen identities, exact scoring, failure retention, and correctness-conditioned timing; limit: fixture generation alone does not execute or compare either model runtime.

### Final primary claim

- The repository reproducibly generates three frozen fixtures for each of the twelve registered business problems, and every fixture defines exactly 48 scored decisions with an independently recomputable expected result or registered constraint objective.

### Routing

- Witness: `builder`
- Why: The change adds offline deterministic data generation and validation without crossing a runtime, service, stored-user-data, or deployment boundary.
- Human-owned irreversible action: Any future model execution, publication, merge, or confirmation-set expansion.

### Decisive witness

- Layer: Standard-library offline contract test.
- Permanent owner: `bench/test_business_fixtures.py`.
- Witness: Two independent builds of the 36-fixture screen are byte-identical; all twelve problem IDs have three fixtures; each fixture has a valid content hash, exactly 48 decisions, a canonical answer contract, and a validator that accepts its registered solution and rejects a targeted mutation.

### Guardrail claims

- Existing dependency-density and diffusion-runtime offline tests continue to pass unchanged.
- Global-assignment fixtures accept valid noncanonical solutions by constraints and objective, rather than falsely requiring one positional reference answer.
- Fixture generation remains standard-library-only and performs no model, network, or accelerator work.

### Supporting obligations

- Reuse `compact_json` and `stable_hash` semantics while keeping the business fixture contract independent of runtime execution.
- Give each problem a deterministic seeded generator and solver/validator pair, with fixed-point integer arithmetic for monetary problems.
- Expose a CLI that emits or writes one canonical frozen manifest and verifies hashes on load.
- Record the durable 48-decision and global-scoring constraints in `bench/README.md`, and update `AGENTS.md` only with verified implementation status.

### Allowed scope

- Reuse: Extend the standalone benchmark pattern and canonical JSON/hash semantics established by `bench/dependency_density_bench.py`; no existing binary-value generator can represent the business domains.
- Cheaper alternative: Implementing only D1/M1/C1/G1 was rejected because the approved outcome explicitly covers all twelve definitions and domain-generalization fixtures.
- Include: `bench/business_fixtures.py`, `bench/test_business_fixtures.py`, `bench/README.md`, `AGENTS.md`, and this proposal ledger; test logs may be written under `/tmp`.
- Exclude/protect: Do not change `bench/dependency_density_bench.py`, `bench/diffusion_runtime.py`, their tests, native runner code, saved result artifacts, accelerator state, or model execution behavior.

### Decisions required

- None.

## Proof

Builder-route witness deferred to Build. The builder must create `bench/test_business_fixtures.py`, observe proposal-specific RED before implementation, and retain it as the permanent decisive witness.

## Build

Candidate: `native-sha256:19c466b25f8342501f43d5133224f5a0351b2a1511f4d76b71b0588706b2b036 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo`

### Files changed

- `bench/business_fixtures.py` — added deterministic standard-library generators, solvers, global constraint validators, content hashes, and manifest generate/validate CLI for all twelve problems.
- `bench/test_business_fixtures.py` — added the permanent 36-fixture contract, seed-reproduction witness, mutation checks, global alternative-solution checks, and CLI round-trip coverage.
- `bench/README.md` — recorded the durable seed identity, 48-decision envelope, and global constraint-scoring rules and their test owner.
- `AGENTS.md` — recorded the verified fixture-layer status and the remaining tokenizer-calibration and paired-runner work.
- `docs/proposals/business-fixture-generators.md` — maintained this proposal ledger.

### Unit evidence

- Builder-owned decisive witness: `python -m unittest bench/test_business_fixtures.py -v` — RED because `bench/business_fixtures.py` was absent; log: `/tmp/business-fixtures-red.log`.
- `python -m unittest bench.test_business_fixtures.BusinessFixtureContractTest.test_initial_screen_is_frozen_complete_and_self_validating -v` — RED because a tampered and rehashed fixture was accepted; log: `/tmp/business-fixtures-seed-red.log`.
- `python -m unittest bench.test_business_fixtures.BusinessFixtureContractTest.test_initial_screen_is_frozen_complete_and_self_validating -v` — RED because M2 omitted its cumulative-cap outcome and seeded G1/G3 inputs did not vary; log: `/tmp/business-fixtures-quality-red.log`.
- `python -m unittest bench/test_business_fixtures.py -v` — RED after audit because rehashed manifest registry-header changes were accepted while the twelve hand-calculated semantic oracles already passed; log: `/tmp/business-fixtures-audit-red.log`.
- `python -m unittest bench/test_business_fixtures.py -v` — GREEN, 3 tests passed; log: `/tmp/business-fixtures-revision-green.log`.

### Green evidence

- Decisive witness: `python -m unittest bench.test_business_fixtures bench.test_dependency_density_bench bench.test_diffusion_runtime -v` — pass, 15 tests including independent hand-calculated D1–G3 oracles and rehashed header rejection; log: `/tmp/business-fixtures-revision-green.log`.
- Manifest round trip: `python bench/business_fixtures.py generate --output /tmp/business-screen-v1-revision.json` followed by `python bench/business_fixtures.py validate /tmp/business-screen-v1-revision.json --json` — pass, 36 fixtures and status `ok`; artifact: `/tmp/business-screen-v1-revision.json`.
- Gate: `python bench/micro_bench.py selftest` — pass; log: `/tmp/business-fixtures-revision-micro.log`.
- Gate: `python -m compileall -q bench` — pass; log: `/tmp/business-fixtures-revision-compile.log`.
- Protected baseline: `shasum -a 256 bench/dependency_density_bench.py bench/results/dependency-density/density48-2026-09-07/dependency_density_bench.py bench/test_dependency_density_bench.py bench/results/dependency-density/harness-v2-20260907/proof/test_dependency_density_bench.py.red-snapshot` — source and saved harness copies both match `63bf3ca63265bc6563f16da70c551016ab06ed73fc96bec9532f8a7c685fef57`; protected test and Proof snapshot both match `22632fb7545ea4ab939b9f4ad7861d5d5b63f89b275992d59263ed3e2634bd52`.
- Candidate identity: `find AGENTS.md bench docs -type f ! -path '*/__pycache__/*' ! -path 'bench/results/*' ! -path 'docs/proposals/business-fixture-generators.md' -print0 | sort -z | xargs -0 shasum -a 256 | shasum -a 256` — reproduced `19c466b25f8342501f43d5133224f5a0351b2a1511f4d76b71b0588706b2b036`.

### Intervention record

- None; this change creates an offline benchmark fixture contract and no user-facing product outcome to measure.

### Deviations

- None.

## Audit

Candidate: `native-sha256:19c466b25f8342501f43d5133224f5a0351b2a1511f4d76b71b0588706b2b036 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo`

Independence: fresh-context — independent reviewer of the prior candidate; did not author or build the original candidate or R1 revision.

Primary-claim verdict: PROVED — evidence: the prescribed digest command reproduced the exact candidate identity; `bench/test_business_fixtures.py` now combines byte-identical generation, 36-fixture registry coverage, exactly 48 string decisions per fixture, mutation rejection, and independent hand-calculated D1 through G3 rule oracles. `/tmp/business-fixtures-audit-red.log` records all three rehashed registry headers failing before the correction, and the revised witness passes. Independent probes confirmed altered and rehashed `base_seed`, `schema_version`, `problem_ids`, and invalid `cases_per_problem` are rejected; limit: this proves the frozen offline fixture contract, not tokenizer comparability or either model’s performance.

Guardrail verdicts:
- Existing dependency-density and diffusion-runtime offline tests continue to pass unchanged: PROVED — evidence: all 12 existing tests passed independently. Current SHA256 values for `bench/dependency_density_bench.py`, `bench/diffusion_runtime.py`, `bench/test_dependency_density_bench.py`, and `bench/test_diffusion_runtime.py` match those independently recorded during the first audit. The density implementation and protected witness also match their retrievable saved snapshots at `bench/results/dependency-density/density48-2026-09-07/dependency_density_bench.py` and `bench/results/dependency-density/harness-v2-20260907/proof/test_dependency_density_bench.py.red-snapshot`; limit: saved snapshots exist only for the density implementation and protected test, while the unchanged diffusion files are established by the prior independent audit hashes.
- Global-assignment fixtures accept valid noncanonical solutions by constraints and objective: PROVED — evidence: the decisive witness passed distinct alternate-answer checks for all nine generated global fixtures, and its hand-calculated G1, G2, and G3 cases independently exercise skills, rest, capacity, stock, delivery, accessibility, separation, host, and objective violations; limit: proof covers the registered fixture schema and validators, not arbitrary future constraint types.
- Fixture generation remains standard-library-only and performs no model, network, or accelerator work: PROVED — evidence: inspection of `bench/business_fixtures.py` found only standard-library imports and offline generation, hashing, validation, and file I/O; limit: this verdict applies to the fixture module and CLI only.

Scope and duty verdict: scope HELD; duties HELD — evidence: R1 changes are confined to `bench/business_fixtures.py`, `bench/test_business_fixtures.py`, and ledger evidence, directly answering the prior verdict. Protected implementation and test hashes remain unchanged, the implementation reuses compact canonical JSON and SHA256 semantics without runtime coupling, every problem has a seeded generator and solver or validator, the CLI generates and validates the canonical manifest, and `bench/README.md` records the durable 48-decision and global-scoring rule with an existing `**Guarded by:**` test; limit: acceptance covers only the framed offline fixture slice.

Test homes: `bench/test_business_fixtures.py` — permanent standard-library offline owner for deterministic generation, registry integrity, independent problem-rule oracles, global alternate solutions, mutation rejection, and CLI round trips.

Full gates: PASS — `python -m unittest bench.test_business_fixtures bench.test_dependency_density_bench bench.test_diffusion_runtime -v`: 15 tests passed; `python bench/business_fixtures.py generate --output /tmp/business-screen-audit-r1.json` followed by `python bench/business_fixtures.py validate /tmp/business-screen-audit-r1.json --json`: passed with 36 fixtures and status `ok`; `python bench/micro_bench.py selftest`: passed; `python -m compileall -q bench`: passed; candidate digest and protected snapshot comparisons matched. Limit: these are deterministic offline gates and do not execute tokenizers, models, or accelerators.

Residual risks:
- The fixtures are synthetic and establish benchmark input correctness, not performance on real business data.
- Output-token comparability and both pinned model-runtime systems remain untested on these fixtures.
- Global cases establish feasibility against registered bounds, not uniqueness of an optimum.

Recommendation: ACCEPT

Packet: No corrective change is required for the framed fixture-generator claim. The next human-owned step is the separately framed tokenizer calibration and paired-runner integration.

## Revisions

### R1 — 2026-09-07 — independently proving problem semantics and frozen manifest metadata

- Verdict: REVISE — the first audit found shared-solver oracle weakness, acceptance of rehashed registry headers, and incomplete protected-baseline evidence.
- Changed: `bench/test_business_fixtures.py`, `bench/business_fixtures.py`, and this ledger's Build evidence — added hand-calculated D1–G3 rule oracles, rejected false schema/seed/problem headers, and cited retrievable protected harness/test snapshots.
- Re-audit: pending fresh-context review; candidate `native-sha256:19c466b25f8342501f43d5133224f5a0351b2a1511f4d76b71b0588706b2b036 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo`.
- Re-audit result: ACCEPT — all claims proved, scope and duties held, and full gates passed for candidate `native-sha256:19c466b25f8342501f43d5133224f5a0351b2a1511f4d76b71b0588706b2b036 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo`.
