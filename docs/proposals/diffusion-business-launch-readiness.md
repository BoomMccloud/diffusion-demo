---
proposal_id: "diffusion-business-launch-readiness"
state: ACCEPTED
witness: independent
candidate: "build-sha256:bd710b4471bc34cc8379e5e21e1b091519c7b3bd0ca28166db2f96dce4457265 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo"
---

# Proposal: DiffusionGemma business-screen launch readiness

## Proposal

### Intent

Do everything required so the twelve-problem business screen is ready to launch with DiffusionGemma.

### Tentative primary claim

The business screen can be launched with DiffusionGemma without additional harness implementation or fixture preparation.

### Why now

The fixture generators and deterministic validators are complete, and launch readiness is the next step.

### Known constraints

Use three fixtures per problem and exactly 48 scored decisions per case. Preserve strict canonical output, deterministic validation, timing, raw output, reasoning, native stop reason, token counts, model and runner identities, and fixture hashes.

### Non-goals

Do not start the DiffusionGemma model run or a larger confirmation set as part of launch preparation.

### Open choices

None stated.

## Frame

Candidate: `prebuild-sha256:db04b0d02b94d26f38208e87e89d7415be6e199e41d3d23f712bb9761cfdfdf1 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo`

### Verified reality

- `python -m unittest bench.test_business_fixtures bench.test_dependency_density_bench bench.test_diffusion_runtime -v` — proves all 15 existing offline fixture, worker, and runtime tests pass before launch-readiness work; limit: no test currently exercises business fixtures through the runtime boundary.
- `bench/business_fixtures.py:build_manifest`, `verify_manifest`, and `evaluate_answer` — proves 36 hash-bound fixtures and deterministic business scoring exist; limit: it accepts parsed objects and does not decode raw native model responses or retain runtime telemetry.
- `bench/diffusion_runtime.py:Worker`, `rpc`, `wait_result`, and `run_cases` — proves one resident protocol-v2 worker already owns durable requests, cancellation, timing, native events, mirroring, and batch admission; limit: its controller only generates and scores the synthetic dependency cases.
- `bench/dependency_density_bench.py:TokenizerService`, `split_native_response`, `artifact_identity`, and `GPUMemorySampler` — proves reusable tokenizer, native-channel, provenance, and memory instrumentation exist; limit: the business fixtures have not been calibrated through both pinned model tokenizers.
- `bench/DEPENDENCY_DENSITY_RUNBOOK.md:Prerequisites for another run` and `bench/README.md:Colab execution` — prove the staged model, runner, tokenizer cache, resident-worker, and Drive-mirroring prerequisites are documented; limit: they do not provide a business-screen launch command or immutable business registration.

### Final primary claim

- After the pinned artifacts are staged, an operator can run a preflight that freezes all 36 business cases, measures every prompt and expected answer with both pinned tokenizers, rejects an unsafe context or runtime configuration before generation, and then launches or safely resumes the DiffusionGemma phase through the resident worker with complete scored artifacts.

### Routing

- Witness: `independent`
- Why: The change connects the accepted fixture contract to the resident model-runtime controller and can otherwise launch expensive generation with an unsafe or mismatched registration.
- Human-owned irreversible action: Starting or stopping the accelerator session and initiating the model run remain explicit operator actions.

### Decisive witness

- Layer: Offline controller-to-worker contract with a fake tokenizer and synthetic terminal worker results.
- Permanent owner: `bench/test_diffusion_runtime.py`.
- Witness: A new business launch contract proves immutable 36-case registration with both tokenizer counts and context gating, strict native-channel/canonical scoring with required telemetry, deterministic resumable request ownership, and a CLI self-test that reaches launch-ready state without network, model, or accelerator work.

### Guardrail claims

- Preflight sends no generation request and refuses launch when fixture, tokenizer, worker protocol/configuration, context, or artifact identity evidence is missing or inconsistent.
- Every attempted case, including invalid, timed-out, cancelled, or crashed cases, retains the registered fixture identity, raw output, reasoning, final output, native stop reason, token counts, timing, and runtime provenance before the next case begins.
- Existing synthetic benchmark behavior and protected lifecycle/cancellation witnesses continue to pass unchanged.

### Supporting obligations

- Add one business controller that reuses the resident worker RPC, tokenizer service, native-channel decoder, artifact identity, memory sampler, atomic writes, mirroring, and admission policy.
- Define deterministic execution order and request IDs, immutable preflight/registration hashes, safe restart behavior, warmup gating, cumulative summaries, and per-case mirrored artifacts.
- Strictly parse one JSON object with only a 48-string `values` array, reject duplicate keys, and delegate business semantics to `evaluate_answer`.
- Provide exact staged-A100 preflight and launch commands, plus an offline self-test/dry run that makes no RPC or generation call.

### Allowed scope

- Reuse: Extend `bench/diffusion_runtime.py` as the resident worker and shared transport owner; keep business-specific preparation/scoring/control in `bench/business_benchmark.py`; extend the existing runtime test owner.
- Cheaper alternative: Adding only a loop over fixture prompts was rejected because it would omit dual-tokenizer context proof, native-channel correctness, immutable registration, resumability, and required failure artifacts.
- Include: `bench/business_benchmark.py`, `bench/business_fixtures.py`, `bench/test_diffusion_runtime.py` as the independently authored protected witness, `bench/README.md`, `AGENTS.md`, and this proposal ledger; `/tmp` may hold test evidence and dry-run artifacts.
- Exclude/protect: Do not modify `bench/dependency_density_bench.py`, `bench/test_dependency_density_bench.py`, native runner source, saved result artifacts, model files, accelerator state, or existing `diffusion_runtime.py` behavior outside any minimal shared API required by the new controller.

### Decisions required

- None.

## Proof

Candidate: `prebuild-sha256:db04b0d02b94d26f38208e87e89d7415be6e199e41d3d23f712bb9761cfdfdf1 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo`

**Protected witness**
- Safe business preflight and immutable dual-tokenizer registration — `bench/test_diffusion_runtime.py` / `BusinessLaunchContractTest.test_self_test_proves_launch_ready_registration_scoring_and_resume`
  - Defect and boundary: no public business launch controller freezes the 36 fixtures, records both tokenizer measurements and runtime identities, or refuses an unsafe context before generation; offline CLI to resident-worker launch boundary.
  - Assertion: the CLI self-test succeeds against an unreachable worker URL, registers exactly 36 ordered 48-decision fixtures with both tokenizer counts, hashes, protocol-v2 configuration, deterministic request IDs, and complete identities, while an unsafe context produces refusal without registration or result artifacts; proves launch gating and no-RPC preflight behavior; limit: synthetic tokenizers do not establish staged-model token counts.
- Strict native scoring and terminal artifact retention — `bench/test_diffusion_runtime.py` / `BusinessLaunchContractTest.test_self_test_proves_launch_ready_registration_scoring_and_resume`
  - Defect and boundary: no business runtime path strictly decodes native channels, rejects duplicate JSON keys, delegates semantic scoring, and retains complete telemetry for every terminal outcome; native worker result to durable scored-artifact boundary.
  - Assertion: 36 persisted rows remain registration-bound and contain fixture identity, raw/reasoning/final channels, stop reason, token counts, timing, provenance, semantic scoring, and representative valid, invalid, timed-out, cancelled, and crashed outcomes, with duplicate-key rejection reported; proves the durable offline scoring contract; limit: it does not exercise a real native runner or model output.
- Deterministic resumable ownership — `bench/test_diffusion_runtime.py` / `BusinessLaunchContractTest.test_self_test_proves_launch_ready_registration_scoring_and_resume`
  - Defect and boundary: restarting a business run can otherwise mutate registration or repeat completed requests; durable controller state to resident-worker request boundary.
  - Assertion: rerunning the same self-test reports zero new and 36 resumed attempts while preserving registration and results byte-for-byte and making zero generation RPC calls; proves deterministic offline resume ownership; limit: accelerator interruption recovery still requires staged execution evidence.
- Protected paths: `bench/test_diffusion_runtime.py`.
- Protected revision: `/tmp/diffusion-business-launch-readiness-proof-db04b0d0/test_diffusion_runtime.py.red-snapshot`; SHA256 `f9878b047d949c894c980418c6ca45d8073dadc6bf7399de05d68cdf0f276f67`.

**Red evidence**
- `python -m unittest bench.test_diffusion_runtime.BusinessLaunchContractTest.test_self_test_proves_launch_ready_registration_scoring_and_resume -v` → one expected assertion failure because the required public `bench.business_benchmark` CLI does not exist; log: `/tmp/diffusion-business-launch-readiness-proof-db04b0d0/red.log`.
- `python -m unittest bench.test_diffusion_runtime.ResultContractTest bench.test_diffusion_runtime.DurableWorkerTests bench.test_diffusion_runtime.NativeCancellationTests bench.test_diffusion_runtime.Utf8PipeBoundaryTest -v` → all 9 existing runtime tests pass unchanged; log: `/tmp/diffusion-business-launch-readiness-proof-db04b0d0/existing-tests.log`.
- The primary and new guardrail claims have no proof until the business launch witness is observed RED as above and passes after implementation.

**Supporting test plan**
- Business controller internals for manifest verification, canonical duplicate-key parsing, token-count normalization, registration hashing, request-ID derivation, and cumulative summaries → Build: `bench/business_benchmark.py` unit-level self-test checks exercised by the protected CLI witness; catches one-module computation defects.
- Existing lifecycle, cancellation, persistence, admission, classification, and UTF-8 behavior → Build: existing owners in `bench/test_diffusion_runtime.py`; catches regressions to the resident worker and synthetic benchmark behavior.

## Build

Candidate: `build-sha256:bd710b4471bc34cc8379e5e21e1b091519c7b3bd0ca28166db2f96dce4457265 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo`

### Implementation

- Added `bench/business_benchmark.py`, the business-screen controller. It builds a deterministic shuffled execution plan, derives stable request IDs, performs a no-generation preflight, measures all prompts and expected answers with both pinned model tokenizers, writes an immutable registration only after every context and provenance gate passes, strictly decodes and scores native responses, retains terminal failure evidence, and safely resumes existing result prefixes.
- Extended `bench/diffusion_runtime.py:Worker.status` with the native protocol version required by registration admission. Existing worker request, cancellation, persistence, and scoring behavior is unchanged.
- Extended `bench/README.md` with exact staged-A100 worker, preparation, launch, resume, and offline self-test commands. Updated `AGENTS.md` so the next operational step is the real staged preflight, not additional harness implementation.
- Preserved the independently authored protected witness in `bench/test_diffusion_runtime.py` without modification after proof. Its SHA256 remains `f9878b047d949c894c980418c6ca45d8073dadc6bf7399de05d68cdf0f276f67`, identical to `/tmp/diffusion-business-launch-readiness-proof-db04b0d0/test_diffusion_runtime.py.red-snapshot`.

### TDD evidence

- Independent RED: `python -m unittest bench.test_diffusion_runtime.BusinessLaunchContractTest.test_self_test_proves_launch_ready_registration_scoring_and_resume -v` failed because `bench.business_benchmark` did not exist; `/tmp/diffusion-business-launch-readiness-proof-db04b0d0/red.log`.
- Supporting provenance RED: the protected launch witness failed after its runtime-provenance assertion was tightened and before hardware plus supporting-harness identities were implemented; `/tmp/diffusion-business-provenance-red.log`.
- GREEN: `python -m unittest bench.test_business_fixtures bench.test_dependency_density_bench bench.test_diffusion_runtime -v` passed all 16 tests; `/tmp/diffusion-business-launch-candidate-green.log`.

### Verification

- `python -m compileall -q bench` passed; `/tmp/diffusion-business-launch-candidate-compile.log`.
- `python bench/micro_bench.py selftest` passed; `/tmp/diffusion-business-launch-candidate-micro.log`.
- `python -m bench.business_benchmark self-test --json --output-dir /tmp/diffusion-business-launch-candidate-selftest --url http://127.0.0.1:1` returned `status=launch_ready`, 36 fixtures, 48 decisions per fixture, all contract checks true, and zero generation RPC calls; `/tmp/diffusion-business-launch-candidate-selftest.log`.
- A loopback fake tokenizer and protocol-v2 worker exercised the public `prepare` and `run-diffusion` commands against the exact candidate. Preparation returned `launch_ready` with zero generation calls. The first run produced 36 valid durable rows plus a complete 12-group summary; the second run produced no new rows. The worker observed exactly 37 generation calls, one warmup plus 36 cases, across both invocations. Evidence: `/tmp/diffusion-business-launch-integration-candidate-prepare.log`, `/tmp/diffusion-business-launch-integration-candidate-run.log`, `/tmp/diffusion-business-launch-integration-candidate-resume.log`, `/tmp/diffusion-business-launch-integration-candidate-calls.json`, and `/tmp/business-launch-integration-candidate`.

### Intervention and deviations

- Intervention: none.
- Deviations: none. No real model, external network, or accelerator session was started. Real pinned-tokenizer counts, GPU identity, worker identity, and context admission remain intentionally owned by the staged A100 `prepare` gate.

## Audit

Candidate: `build-sha256:bd710b4471bc34cc8379e5e21e1b091519c7b3bd0ca28166db2f96dce4457265 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo`

Independence: fresh-context — this audit received only the ledger path, candidate identity, and repository, and did not author the Proof or Build.

Primary-claim verdict: PROVED — evidence: the protected `bench/test_diffusion_runtime.py::BusinessLaunchContractTest.test_self_test_proves_launch_ready_registration_scoring_and_resume` passed independently; fresh `self-test` executions produced immutable registration for 36 fixtures with exactly 48 decisions each, dual-tokenizer counts, deterministic request IDs, strict scoring, complete terminal rows, and a byte-stable zero-new-attempt resume; `bench/business_benchmark.py` keeps `prepare` limited to status, tokenizer, context, and provenance checks and reserves `/generate` for `run-diffusion`; the retained loopback integration artifacts at `/tmp/business-launch-integration-candidate` independently revalidated as one valid registration, 36 ordered registration-bound rows, 12 summary groups, and `all_cases_completed`; limit: synthetic tokenizers and a fake protocol-v2 worker do not establish staged A100 token counts, hardware behavior, or model quality, which remain owned by the operator-run `prepare` and subsequent launch.

Guardrail verdicts:
- Preflight sends no generation request and refuses missing or inconsistent launch evidence: PROVED — evidence: the protected witness passed against an unreachable worker URL with `generation_rpc_calls=0`; an independent unsafe-context invocation refused before creating registration or results; `build_registration`, `validate_registration`, and `prepare` enforce fixture regeneration, dual positive token counts, protocol-v2/native configuration, both context bounds, complete SHA256 artifact identities, hardware identity, and supporting-harness identities; the retained public fake-worker preparation reports `launch_ready` with zero generation calls; limit: actual tokenizer counts and artifact identities require the staged environment.
- Every attempted terminal outcome retains fixture identity, native channels, scoring, timing, token counts, and provenance before progression: PROVED — evidence: the protected witness persisted 36 registration-bound rows and asserted the complete field contract across correct, invalid, timed-out, cancelled, native-crash, duplicate-key, and reasoning-bearing outcomes; `classify_business_result` and `_append_row` use the registered fixture/request identity and persist the JSONL plus per-case artifact before the loop advances; limit: abrupt host loss within a filesystem write or mirror operation is outside the offline witness.
- Existing synthetic behavior and lifecycle/cancellation witnesses remain unchanged: PROVED — evidence: the protected witness SHA256 is `f9878b047d949c894c980418c6ca45d8073dadc6bf7399de05d68cdf0f276f67`, byte-identical to `/tmp/diffusion-business-launch-readiness-proof-db04b0d0/test_diffusion_runtime.py.red-snapshot`; its retrievable RED log shows the expected missing-module failure, and all existing lifecycle, cancellation, durability, classification, and UTF-8 tests pass; limit: no real native runner was started.

Scope and duty verdict: scope HELD; duties HELD — evidence: the implementation is confined to the framed controller, minimal worker status extension, runtime test owner, launch documentation, and active-work status; protected runtime witness is unchanged, and the candidate digest matches; `bench/README.md` records the immutable-preflight rule with its `**Why:**` and existing `**Guarded by:**` test, plus exact staged worker, prepare, launch, resume, and self-test commands; limit: the repository has no Git metadata, so scope comparison relies on the frozen digest, protected snapshot, ledger-declared paths, and source inspection rather than a Git diff.

Test homes: `bench/test_diffusion_runtime.py` — permanent resident-worker and business runtime boundary owner, appropriate for the independently authored launch, scoring, and resume witness.

Full gates: PASS — `find AGENTS.md bench docs -type f ! -path '*/__pycache__/*' ! -path 'bench/results/*' ! -path 'docs/proposals/diffusion-business-launch-readiness.md' -print0 | sort -z | xargs -0 shasum -a 256 | shasum -a 256`: exact candidate digest matched; `python -m unittest bench.test_diffusion_runtime.BusinessLaunchContractTest.test_self_test_proves_launch_ready_registration_scoring_and_resume -v`: 1 passed; `python -m unittest bench.test_business_fixtures bench.test_dependency_density_bench bench.test_diffusion_runtime -v`: 16 passed; `python -m compileall -q bench`: passed; `python bench/micro_bench.py selftest`: passed; fresh `python -m bench.business_benchmark self-test` launch-ready, resume, and unsafe-context runs produced the expected results; limit: these are deterministic offline and loopback gates, not accelerator evidence.

Residual risks:
- Staged DiffusionGemma and Gemma tokenizer counts, context fit, GPU identity, model and runner hashes, and live protocol configuration remain unknown until `prepare` succeeds on the A100.
- Fake-worker success proves the controller contract, not real model validity, latency, output quality, or accelerator interruption behavior.
- The paired autoregressive business phase and any larger confirmation set remain outside this proposal.

Recommendation: ACCEPT

Packet: On the staged A100, start the unloaded protocol-v2 worker and run the documented `python -m bench.business_benchmark prepare` command. Proceed to the human-owned `run-diffusion` action only if it returns `status=launch_ready` with `generation_rpc_calls=0`; retain the resulting immutable registration and staged provenance as environment-specific evidence.

## Revisions

<!-- Append-only. -->
