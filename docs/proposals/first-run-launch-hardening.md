---
proposal_id: "first-run-launch-hardening"
state: ACCEPTED
witness: independent
candidate: "build-source-sha256:f8c73e163e04a820ad69dac7a9fbff6b6acef29eda9acd640a268083d632a0f2 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo"
---

# Proposal: First-run launch hardening

## Proposal

### Intent

Increase the probability that the documented DiffusionGemma business-screen launch completes correctly on its first staged A100 attempt.

### Tentative primary claim

The documented commands are location-independent, reject incomplete environment evidence and unusable warmups, and report failure when the 36-case run does not complete.

### Why now

A post-implementation review found that the current commands assume the repository is the shell working directory, unavailable GPU identity can pass preparation, the warmup gate accepts weak terminal evidence, and a partial run exits with status zero.

### Known constraints

Keep preparation generation-free, preserve immutable registration and resume behavior, do not weaken the 36-fixture or 48-decision contracts, and do not start an accelerator or model run.

### Non-goals

Do not change fixture semantics, model parameters, the pinned runner, output allowance, context size, or claims about model correctness. Do not repair the concurrent repository-cleanup proposal beyond accounting for its current layout.

### Open choices

None stated.

## Frame

Candidate: `prebuild-sha256:5eeba9e129c6ce109e2701e1449f2350529b09c33821fdabe6c93fa0ad0d2547 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo`

### Verified reality

- `python -m unittest tests.bench.test_business_fixtures tests.bench.test_dependency_density_bench tests.bench.test_diffusion_runtime tests.test_repository_layout -v` passed 17 tests before hardening; `/tmp/first-run-hardening-targeted-baseline.log`; limit: the default discovery command in the current root README fails because `tests/bench` shadows the active namespace package when `-t .` is omitted.
- `bench/README.md:100-151` invokes both controllers through paths relative to the shell working directory, while the archived bootstrap only inserted the Drive repository into its own Python process and did not change directories or export a subprocess import path; limit: a human who already changed into the repository would not encounter this failure.
- `bench/business_benchmark.py:379-442` performs preparation without `/generate`, but `dependency_density_bench.py:hardware_identity` represents failed `nvidia-smi` lookup as a nonempty `unavailable:*` string that the registration currently accepts; limit: this does not show `nvidia-smi` will be unavailable on Colab.
- `bench/business_benchmark.py:490-504` persists warmup output and accepts any terminal state without an error, and `main:747-748` returns zero after `run_diffusion` even when its summary records an early runtime or budget stop; limit: the retained loopback candidate happened to complete all 36 cases and did not expose either failure.
- `tests/bench/test_diffusion_runtime.py:BusinessLaunchContractTest` is the existing public business-launch contract owner, and `bench/business_benchmark.py` already owns registration, warmup, summary, and exit behavior; limit: its current self-test does not exercise the real public `prepare` and `run-diffusion` command path.

### Final primary claim

- From any shell working directory, an operator can follow the staged-A100 commands and receive a trustworthy process result: preparation succeeds only with a real GPU identity, generation proceeds only after a completed native warmup, and `run-diffusion` exits successfully only after all 36 registered cases have durable terminal rows.

### Routing

- Witness: `independent`
- Why: The changes govern the controller-to-resident-worker boundary and whether an expensive model run is admitted or falsely reported complete.
- Human-owned irreversible action: Starting or stopping the accelerator and invoking real model generation remain operator actions.

### Decisive witness

- Layer: Public CLI against a synthetic protocol-v2 worker and isolated filesystem.
- Permanent owner: `tests/bench/test_diffusion_runtime.py`.
- Witness: Location-independent documented invocation reaches the controller; unavailable hardware is refused before registration; invalid warmup prevents case generation; an early runtime or budget stop returns nonzero with a durable incomplete summary; and a complete 36-case run returns zero and remains safely resumable.

### Guardrail claims

- `prepare` remains generation-free and preserves immutable dual-tokenizer, context, artifact, fixture, and registration gates.
- Every accepted terminal case remains durable and resumable, including when the overall command exits nonzero for an incomplete batch.
- Existing fixture, worker lifecycle, cancellation, native scoring, and repository-layout contracts remain passing.

### Supporting obligations

- Centralize launch-completion and warmup acceptance decisions in small named helpers with direct unit coverage.
- Emit a machine-readable final run report containing status, attempts, expected attempts, stop reason, and registration hash, and derive the CLI exit code from it.
- Make the A100 command block use an explicit repository path rather than relying on the current directory, and document that `summary.json`, not answer correctness, defines transport completion.

### Allowed scope

- Reuse: Extend `bench/business_benchmark.py`, its permanent runtime contract owner, and `bench/README.md`; no new controller or runner is needed.
- Cheaper alternative: Documentation-only edits were rejected because they would leave false-zero exits, weak warmup admission, and unavailable hardware registration intact.
- Include: `bench/business_benchmark.py`, `tests/bench/test_diffusion_runtime.py` as the independently authored protected witness, `bench/README.md`, `AGENTS.md`, and this proposal ledger; `/tmp` may hold test and loopback evidence.
- Exclude/protect: Fixture generators and validators, `bench/diffusion_runtime.py`, `bench/dependency_density_bench.py`, native sources, model artifacts, saved benchmark results, archive contents, repository-cleanup files outside the named documentation overlap, and accelerator state.

### Decisions required

- None.

## Proof

Candidate: `prebuild-sha256:5eeba9e129c6ce109e2701e1449f2350529b09c33821fdabe6c93fa0ad0d2547 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo`

**Protected witness**
- Trustworthy public launch result — `tests/bench/test_diffusion_runtime.py` / six `BusinessLaunchContractTest` public CLI tests
  - Defect and boundary: the controller accepted unavailable GPU identity and invalid warmup output, returned zero for incomplete runs, and omitted completion fields; operator CLI and resident protocol-v2 worker boundary crossed.
  - Assertion: preparation refuses unavailable hardware before registration or generation; exact completed single-EOG warmup gates generation; budget/runtime stops return nonzero with durable incomplete reports; 36 durable rows return zero and resume without repeated generation; absolute-path invocation works from an unrelated directory. Proves the public launch contract with a synthetic worker and isolated filesystem; limit: no real CUDA, model, tokenizer, or accelerator lifecycle.
- Hardware identity policy — `tests/bench/test_diffusion_runtime.py` / `BusinessPolicyContractTest.test_hardware_identity_requires_an_available_gpu`
  - Defect and boundary: a nonempty `unavailable:*` probe result was accepted as GPU identity; hardware-admission policy crossed.
  - Assertion: a reported NVIDIA A100 identity is accepted while case-insensitive, whitespace-surrounded `unavailable:*` variants are rejected; proves the named helper enforces the framed availability distinction; limit: it does not execute `nvidia-smi` or authenticate the reported GPU.
- Native warmup policy — `tests/bench/test_diffusion_runtime.py` / `BusinessPolicyContractTest.test_warmup_acceptance_requires_exact_completed_native_result`
  - Defect and boundary: any error-free terminal warmup state was accepted regardless of state, output, or native stop; controller-to-worker admission boundary crossed.
  - Assertion: only completed, error-free, exact `{"values":["READY"]}` output with one EOG stop is accepted; failed state, error, wrong output, missing stop, duplicate stops, and wrong stop reason are rejected. Proves direct helper policy; limit: synthetic telemetry does not exercise native generation.
- Final report policy — `tests/bench/test_diffusion_runtime.py` / `BusinessPolicyContractTest.test_summary_classifies_complete_budget_and_runtime_stops`
  - Defect and boundary: summaries omitted completion classification, expected attempt count, and registration binding; durable result and process-exit boundary crossed.
  - Assertion: 36 rows with `all_cases_completed` classify as completed, while budget and runtime stops classify as incomplete, preserving attempts, expected attempts, stop reason, and registration hash. Proves direct summary policy; limit: CLI exit mapping remains covered by the public witnesses.
- Protected paths: `tests/bench/test_diffusion_runtime.py`.
- Protected revision: `sha256:7998b937c9a93a60457296555edf19267f48bf803fb90e8e05ed6f81e97c9d66`; retrievable snapshot: `/tmp/first-run-launch-hardening-r1-protected-test_diffusion_runtime.py`.

**Red evidence**
- Original six-test public CLI command → five semantic failures against the prebuild candidate: unavailable hardware, invalid warmup, budget stop, and runtime stop returned zero, while the completed summary lacked `status`; unrelated-directory invocation passed. No setup/import errors; log: `/tmp/first-run-launch-hardening-proof-red.log`.
- `DIFFUSION_BUSINESS_BENCHMARK_UNDER_TEST=/tmp/first-run-launch-hardening-r1-prebuild-business_benchmark.py python -B -m unittest tests.bench.test_diffusion_runtime.BusinessPolicyContractTest -v` → 11 semantic assertion failures: unavailable identities were accepted, invalid state/output/stop warmups were accepted, and completed, budget-stopped, and runtime-stopped summaries lacked classification. No setup/import errors; log: `/tmp/first-run-launch-hardening-r1-policy-red.log`.
- The temporary module, `sha256:f7e981bc408792c9df6952a311b84f8263214c34ad87b87acc6110d4f6b1e6fe`, retained the current import/helper surface and reversed only the recorded prebuild hardware, warmup, and summary policies, avoiding missing-symbol evidence.
- Current-production control: the same direct command without the module override passed 3 tests; `/tmp/first-run-launch-hardening-r1-policy-green.log`. The six public witnesses passed; `/tmp/first-run-launch-hardening-r1-public-green.log`. The complete runtime owner passed 19 tests; `/tmp/first-run-launch-hardening-r1-runtime-green.log`.
- Hardware, warmup, summary, and trustworthy public launch claims have no proof until the corresponding RED commands above are observed.

**Supporting test plan**
- None.

## Build

Candidate: `build-source-sha256:f8c73e163e04a820ad69dac7a9fbff6b6acef29eda9acd640a268083d632a0f2 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo`

### Files changed

- `bench/business_benchmark.py` — rejects unavailable GPU identities, strictly validates both new and retained warmup artifacts, writes completion-bound summaries, prints the final report, and returns nonzero unless all 36 registered cases are durable and the stop reason is `all_cases_completed`.
- `bench/README.md` — makes the business launch commands independent of shell working directory, defines the durable completion signal, and records the first-run constraint with its permanent guard.
- `AGENTS.md` — records the hardened operational boundary and next staged-A100 action.
- `tests/bench/test_diffusion_runtime.py` — independently authored and protected public-boundary plus direct policy witnesses; Build did not modify it.

### Unit evidence

- `DIFFUSION_BUSINESS_BENCHMARK_UNDER_TEST=/tmp/first-run-launch-hardening-r1-prebuild-business_benchmark.py python -B -m unittest tests.bench.test_diffusion_runtime.BusinessPolicyContractTest -v` — RED: 11 semantic policy failures against the reconstructed prebuild behavior; `/tmp/first-run-launch-hardening-r1-policy-red.log`.
- `python -B -m unittest tests.bench.test_diffusion_runtime.BusinessPolicyContractTest -v` — GREEN: 3 permanent direct policy tests passed; `/tmp/first-run-launch-hardening-r1-policy-green.log`.

### Green evidence

- Decisive witnesses: six public CLI tests passed; `/tmp/first-run-launch-hardening-r1-public-green.log`. The complete runtime owner passed 19 tests; `/tmp/first-run-launch-hardening-r1-runtime-green.log`.
- Gate: `python -B -m unittest tests.test_repository_layout tests.bench.test_business_fixtures tests.bench.test_dependency_density_bench tests.bench.test_diffusion_runtime -v` — passed all 26 current tests; `/tmp/first-run-launch-hardening-r1-full-green.log`.
- Gate: `PYTHONPYCACHEPREFIX=/tmp/first-run-hardening-r1-pyc python -m compileall -q bench tests` — passed; `/tmp/first-run-launch-hardening-r1-compile.log`.
- Gate: `python -B -m bench.business_benchmark self-test --json --output-dir /tmp/first-run-launch-hardening-selftest --url http://127.0.0.1:1` — returned `launch_ready`, 36 fixtures, 48 decisions, and zero generation RPCs; `/tmp/first-run-launch-hardening-selftest.log`.
- Exact public-path loopback integration from `/private/tmp` used a fake tokenizer, fake GPU identity, and protocol-v2 worker. `prepare` returned `launch_ready` with zero generation calls, the first launch returned zero with 36 durable rows and `status=completed`, and the second launch returned zero without another generation. The worker observed exactly 37 calls total, one strict warmup plus 36 cases; `/tmp/first-run-hardening-integration`, `/tmp/first-run-hardening-integration-run.log`, and `/tmp/first-run-hardening-integration-resume.log`.
- Protected witness SHA256 is `7998b937c9a93a60457296555edf19267f48bf803fb90e8e05ed6f81e97c9d66`, byte-identical to `/tmp/first-run-launch-hardening-r1-protected-test_diffusion_runtime.py`.
- Candidate identity: `find AGENTS.md README.md bench docs tests -type f ! -path '*/__pycache__/*' ! -path 'bench/results/*' ! -path 'docs/proposals/*' -print0 | sort -z | xargs -0 shasum -a 256 | shasum -a 256` reproduced `f8c73e163e04a820ad69dac7a9fbff6b6acef29eda9acd640a268083d632a0f2`.

### Intervention record

- None, because this is an offline launch-controller and documentation hardening change with no user-facing product intervention.

### Deviations

- None. No accelerator, model, external network, native runner, fixture semantics, or saved benchmark result was changed or executed.

## Audit

Candidate: `build-source-sha256:f8c73e163e04a820ad69dac7a9fbff6b6acef29eda9acd640a268083d632a0f2 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo`

Independence: fresh-context — the auditor previously reviewed R0 but did not author the production change, R1 witness, reconstructed prebuild control, or Build evidence.

Primary-claim verdict: PROVED — all six protected public CLI witnesses independently passed, proving unavailable-GPU refusal, strict completed single-EOG warmup admission, durable incomplete reports and nonzero exits for budget/runtime stops, successful 36-row completion, no-repeat resume, and absolute-path execution from an unrelated directory. Limit: the worker and artifacts are synthetic, with no real accelerator or model execution.

Guardrail verdicts:

- `prepare` remains generation-free and preserves immutable registration gates: PROVED — the public refusal witness performs only `/status`, the offline self-test returned `launch_ready` for 36 fixtures and 48 decisions with zero generation RPCs, and the full suite preserves registration, tokenizer-count, context, identity, and fixture contracts. Limit: staged production tokenizers and artifacts were not exercised.
- Accepted terminal cases remain durable and resumable after incomplete batches: PROVED — the runtime-stop witness persisted its terminal row before returning failure, while the complete-resume witness preserved `results.jsonl` byte-for-byte and issued no repeated generation. Limit: abrupt host loss was not simulated.
- Existing fixture, lifecycle, cancellation, native scoring, and repository-layout contracts remain passing: PROVED — the exact-digest clean copy passed all 26 tests in the required full-suite command. Limit: native CUDA execution remains outside scope.

Scope and duty verdict: scope HELD; duties HELD. The candidate digest reproduced exactly. R1 changed the approved permanent test owner and refreshed its protected snapshot without changing production behavior. `BusinessPolicyContractTest` directly covers `_valid_hardware_identity`, `_warmup_accepted`, and completion, budget-stop, and runtime-stop `summarize` classifications. This resolves R0's missing permanent direct-coverage duty. `bench/README.md` retains the durable constraint with its rationale and permanent guard. Limit: `.git` metadata is absent, so scope was assessed through exact source identities, the R1 revision, and inspected surfaces rather than a VCS diff.

Test home: `tests/bench/test_diffusion_runtime.py` — permanent owner for the public controller/runtime boundary and direct launch-policy contracts; SHA-256 `7998b937c9a93a60457296555edf19267f48bf803fb90e8e05ed6f81e97c9d66`, byte-identical to `/tmp/first-run-launch-hardening-r1-protected-test_diffusion_runtime.py`.

Full gates: PASS — candidate digest exact; protected witness SHA-256 and byte comparison exact; reconstructed prebuild policy command produced the expected semantic RED with 11 assertion failures; current direct policy command passed 3 tests; public witness command passed 6 tests; clean-tree full suite passed 26 tests; compileall passed; offline self-test returned `launch_ready`, 36 fixtures, 48 decisions, and zero generation RPCs. Limit: the repository-layout test must run before subprocess tests because those tests can generate `__pycache__`.

Residual risks:

- The direct RED control is a SHA-identified reconstruction that differs from production only at the three recorded prebuild policies, corroborated by the original public RED evidence; it is not a retained full-tree prebuild checkout.
- No real accelerator, model, tokenizer, or native runner was exercised, as required.
- Retained loopback artifacts do not independently preserve the worker's claimed 37-call request log.

Recommendation: ACCEPT. No corrective work remains. Preserve protected witness SHA-256 `7998b937c9a93a60457296555edf19267f48bf803fb90e8e05ed6f81e97c9d66`; the human operator retains authority over any staged A100 preparation or model launch.

## Revisions

### R1 — 2026-09-08 — add permanent direct helper-policy coverage
- Verdict: REVISE — the audit proved every runtime claim and passed all gates, but found that direct warmup, hardware, and completion-summary helper checks existed only in an ephemeral command rather than the permanent test owner.
- Changed: `tests/bench/test_diffusion_runtime.py` — the independent Proof owner added three permanent direct policy tests, observed 11 semantic RED failures against a reconstructed prebuild-policy module, passed them against current production, and refreshed the protected snapshot to SHA256 `7998b937c9a93a60457296555edf19267f48bf803fb90e8e05ed6f81e97c9d66`.
- Re-audit: ACCEPT — the independent auditor proved the primary claim and all guardrails against candidate `build-source-sha256:f8c73e163e04a820ad69dac7a9fbff6b6acef29eda9acd640a268083d632a0f2`.
