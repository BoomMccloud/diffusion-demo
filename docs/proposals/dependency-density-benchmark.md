---
proposal_id: "dependency-density-benchmark"
state: PROVED
witness: independent
candidate: "dependency-density-pilot-20260907 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo; manifest sha256:adb5f5af8f63fa5bf15ee4b1816f298b12a11249fe609cc90cd371a29233f46f"
---

# Proposal: Dependency-density benchmark

## Proposal

### Intent

Start from the beginning and run a single benchmark on Google Colab with an A100 to establish how autoregressive and diffusion models perform on different workflows.

### Tentative primary claim

The benchmark establishes whether correctness-filtered performance differs between Gemma 4 AR and DiffusionGemma as output length and dependency density change.

### Why now

The existing schedule experiment does not yet establish which workflows suit each model approach.

### Known constraints

Run through the Colab CLI in Google Colab using an A100, and begin with the single dependency-density benchmark previously described.

### Non-goals

None stated.

### Open choices

None stated.

## Frame

Candidate: `harness-v2-20260907-frame @ /Users/jasonbxu/Documents/GitHub/diffusion-demo`

### Verified reality
- `python -m unittest discover -s bench -p 'test*.py'` passes the existing single benchmark contract test before changes; it does not cover request lifecycle.
- `bench/dependency_density_bench.py:DiffusionSession` buffers terminal output, raises before draining process-exit output, has no cancellation acknowledgment, and does not distinguish readiness from a non-null process handle.
- `docs/diffusion_density32_findings.md` establishes nine exactly correct 32-value runs; limit: three inputs per density.
- `docs/diffusion_softcap_repair_findings.md` establishes isolated integer-width improvement but unresolved native memory access; limit: full native repair is not claimed.

### Final primary claim
- The permanent diffusion benchmark can run matched cases through an observable reusable worker, retain exact outputs and terminal failures, and recover from cancellation/crash without treating a busy or dead runner as ready. Colab verifies the passing 32-value fixture set and exercises full-backend boundary diagnostics before further long model runs.

### Routing
- Witness: independent
- Why: Request completion and cancellation cross Python, a native subprocess, and persisted result boundaries.
- Human-owned irreversible action: None.

### Decisive witness
- Layer: subprocess lifecycle integration with a small native-protocol simulator, plus Colab replay.
- Permanent owner: `bench/test_dependency_density_bench.py` for independent lifecycle regression tests; `bench/test_diffusion_runtime.py` for builder supporting obligations.
- Witness: Timeout/cancel never leaves an untracked active generation; terminal stderr survives a crash; request IDs and readiness are truthful; subsequent valid requests succeed after explicit recovery. Existing exact-scoring tests remain intact.

### Guardrail claims
- Exact canonical scoring, reasoning preservation, original error/exit metadata, and common per-case budgets remain intact; no partial reasoning is scored as a final answer.
- A request starts only with its full time allowance available, and results retain unsuccessful GPU time; no AR or low-budget model sweep is introduced.
- Existing schedule and TPU flows remain unchanged; cached native builds and successful warm model reuse are preserved.

### Supporting obligations
- Versioned native patch and lightweight structured stop/block/channel/prefill timing events; repetition protection must not discard legitimate values. Detailed token/tensor traces are an explicit diagnostic mode.
- Consolidated diffusion-only matched-case CLI and worker with request IDs, status, cancellation and terminal result records. Full-budget gating, calibrated context sizes, seed/build identity, exact result classification and success/cost summary.
- Permanent integer-boundary tests and a full-backend CUDA graph probe; acceptance of the isolated softcap patch does not imply a complete long-generation fix.

### Allowed scope
- Reuse: extend `DiffusionSession`, `make_case`, `solve_records`, `evaluate_output`, `TokenizerService`, and existing JSONL helpers in `bench/dependency_density_bench.py`; consolidate prior artifact workers rather than retaining another run-specific driver.
- Cheaper alternative: another diagnostic script rejected because it repeats lifecycle and classification bugs.
- Include: `bench/dependency_density_bench.py`, `bench/diffusion_runtime.py`, `bench/test_dependency_density_bench.py` (Proof only), `bench/test_diffusion_runtime.py`, `bench/native/` versioned patch/probe/build helpers, `bench/README.md`, runbook/findings, this ledger, generated evidence.
- Exclude/protect: preexisting contract assertions, all old measured artifacts, exact evaluator, schedule/TPU/model weights. No promotion of unverified CUDA behavior into notebook setup. No claim that the original AR comparison is complete.

### Decisions required
- None.

## Proof

Candidate: `harness-v2-20260907-frame`; exact RED source identities and snapshots: `bench/results/dependency-density/harness-v2-20260907/proof/red-manifest.json`.

**Protected witness**

- Terminal failure retention and recovery: `bench/test_dependency_density_bench.py` / `DiffusionSessionLifecycleTest.test_crash_retains_terminal_output_and_recovers`.
  - Defect and boundary: polling process exit before draining pipes loses terminal output; native subprocess → Python result boundary.
  - Assertion: retained transcript contains fatal stderr and unfinished reasoning, exception retains exit code 37, explicit close/start recovers canonical output, and subsequent turns reuse the recovered process. Proves observable failure retention and recovery. Limit: a Python simulator exercises real subprocess pipes, not CUDA.
- Timeout termination and recovery: `bench/test_dependency_density_bench.py` / `DiffusionSessionLifecycleTest.test_timeout_stops_original_generation_and_recovers`.
  - Defect and boundary: timeout returns while native generation remains alive; Python deadline → native process lifecycle boundary.
  - Assertion: original process has terminated before TimeoutError returns, partial reasoning remains available, and explicit recovery returns the correct final and reasoning channels. Proves termination acknowledgment for legacy runners and recovery. Limit: does not exercise opt-in native cancellation acknowledgment.
- Recovery assertions additionally preserve the four-element generation tuple, positive elapsed time, and warm reuse.
- Existing deterministic matrix and exact-scoring contract assertions remain unchanged.
- Protected paths: `bench/test_dependency_density_bench.py`.
- Protected revision: `bench/results/dependency-density/harness-v2-20260907/proof/test_dependency_density_bench.py.red-snapshot`; SHA256 `22632fb7545ea4ab939b9f4ad7861d5d5b63f89b275992d59263ed3e2634bd52`.

**Red evidence**

- `python -m unittest bench.test_dependency_density_bench` → three expected assertion failures: missing terminal stderr, missing crash reasoning, and original process still alive following timeout. Existing contract, original exit metadata, explicit recovery, and warm reuse assertions pass. Log: `bench/results/dependency-density/harness-v2-20260907/proof/lifecycle-red.log`.
- Request identity, truthful worker readiness, native cancellation acknowledgment, persisted unsuccessful cost, full-budget admission, and Colab behavior remain unproved by this witness.

**Supporting test plan**

- Worker request identity, readiness transitions, persistence, full-budget admission, unsuccessful elapsed cost, and cancellation acknowledgment/fallback → Build: `bench/test_diffusion_runtime.py`; catches orchestration and result-classification defects.
- Native stop/channel events, repetition preservation, and integer-boundary/full-backend probes → Build: permanent owners under `bench/native/`; catches native instrumentation and arithmetic defects. Full-backend acceptance requires GPU evidence.
- Colab replay of the passing 32-value fixture set and boundary diagnostics remains required for acceptance.

## Build

Candidate: `harness-v2-proof-20260907`; source identities in `bench/results/dependency-density/harness-v2-proof-2026-09-07/candidate-sha256.txt` and `native-sha256.txt`; Colab packet SHA256 `207f1658af75f7a4ae23c350e736b1104d378457b288a869f55280ac8dddb5fc`.

### Files changed

- `bench/dependency_density_bench.py` — drains subprocess output before exit reporting, uses incremental UTF-8 decoding, acknowledges cancellation or process exit, preserves native events and errors, and defaults diffusion allowance to 9,216 tokens.
- `bench/diffusion_runtime.py` — adds the durable loopback worker, request identity, result persistence, matched fixtures, full-budget admission, exact classification, and successful/failed cost accounting.
- `bench/test_diffusion_runtime.py` — supporting lifecycle, cancellation, persistence, UTF-8 boundary, stop ambiguity, budget, and cost regressions.
- `bench/native/` — pinned native protocol patch, 64-bit softcap repair, source regressions, incremental build helper, and real CUDA backend graph probe.
- `bench/README.md` — durable harness constraints, execution contract, evidence limits, and permanent test owners.

### Unit evidence

- `python -m unittest bench.test_diffusion_runtime.ResultContractTest.test_duplicate_native_stops_cannot_be_reported_as_correct` — RED: duplicate stop events retained a `correct` outcome; log: `bench/results/dependency-density/harness-v2-2026-09-07/ambiguous-stop-red.log`.
- `python bench/native/test_native_stopping.py /tmp/dependency-diffusion-cli.cpp` — RED: pristine repetition trimming discarded a repeated-value fixture; log: `bench/results/dependency-density/harness-v2-2026-09-07/native-stopping-red.log`.
- `python -m unittest discover -s bench -p 'test*.py'` — GREEN: 11 tests pass; log: `bench/results/dependency-density/harness-v2-proof-2026-09-07/local-tests.log`.

### Green evidence

- Decisive witness: `python -m unittest bench.test_dependency_density_bench bench.test_diffusion_runtime` — pass, including protected lifecycle and split UTF-8 pipe tests; log: `bench/results/dependency-density/harness-v2-proof-2026-09-07/local-tests.log`.
- Gate: `python bench/dependency_density_bench.py selftest --json` — pass; log: `bench/results/dependency-density/harness-v2-proof-2026-09-07/benchmark-selftest.log`.
- Gate: `python bench/micro_bench.py selftest` — pass; log: `bench/results/dependency-density/harness-v2-proof-2026-09-07/micro-selftest.log`.
- Colab A100 build and probe: pinned runner built; full GGML/CUDA numerical graph passed at 256, 8,191, 8,192, 8,239, and 11,264 positions; packet: `bench/results/dependency-density/harness-v2-proof-2026-09-07/harness-v2-proof.tar.gz`.
- Colab A100 matched replay: 9/9 exact outputs, one native stop per request, prefill/denoise/commit events present, and all cases completed; summary: `bench/results/dependency-density/harness-v2-proof-2026-09-07/harness-v2/matched32-proof/summary.json`.
- Session cleanup: `colab stop -s harness-v2-proof` then `colab sessions` — no active sessions.

### Intervention record

- None; benchmark infrastructure has no user-facing product outcome to measure.

### Deviations

- None.

## Audit

Candidate: `harness-v2-proof-20260907`. Verified `bench/results/dependency-density/harness-v2-proof-2026-09-07/candidate-sha256.txt` SHA256 `8e164251bcaa4f435e7e0f68c73871fd22534b8002c5f081c34e3722f12893a5` and `native-sha256.txt` SHA256 `0d477a2ad1fff4dfbf4f8e503e73b16d898e0a3dd9a13dc1f9869b61b8329a99`.

Independence: fresh-context, independent reviewer performed the preliminary audit and re-audit without building or editing the candidate.

Primary-claim verdict: PROVED. Evidence: independently reran the protected lifecycle tests and worker supporting tests; verified the Colab packet SHA256 `207f1658af75f7a4ae23c350e736b1104d378457b288a869f55280ac8dddb5fc` and all 37 extracted files against archive contents. Independently rescored all nine matched replay outputs, confirmed identical prior fixture prompts and expected answers, unique request IDs, persisted terminal results, one reused native process, one EOG stop per request, and prefill/denoise/commit events. All five full-backend numerical probe logs pass; limit: local subprocess simulators establish cancellation/crash recovery, while Colab establishes successful native reuse and boundary diagnostics, not universal long-generation safety.

Guardrail verdicts:

- Exact scoring, reasoning preservation, original failure metadata, and common budgets: PROVED. Evidence: protected lifecycle witness, exact evaluator selftest, supporting timeout/ambiguous-stop tests, split-UTF-8 subprocess regression, and independent transcript decoding and rescoring of nine Colab rows; limit: abrupt Python-worker termination cannot reconstruct unpersisted transcript data.
- Full-budget admission and unsuccessful request cost: PROVED. Evidence: `ResultContractTest` passes admission and failed-time accounting assertions; all saved requests receive 120 seconds and 9,216 tokens, contexts fit, and independently recomputed summaries match. No AR sweep appears in the replay; limit: allocation metrics exclude earlier build and idle time, as documented.
- Existing schedule/TPU flows, cached builds, and warm reuse: PROVED within audited scope. Evidence: schedule validation passes all 50 cases, micro selftest passes, native build helper preserves incremental builds, and all nine replay rows share one process generation. Candidate changes remain in approved owners; limit: no TPU hardware execution was required or performed.

Scope and duty verdict: scope HELD; duties HELD. Evidence: implementation extends the framed session, evaluator, fixture, tokenizer, and JSONL owners; native helpers and findings remain within approved scope. `bench/README.md` records durable constraints with **Why:** and existing **Guarded by:** tests. The UTF-8 defect is corrected and covered by a subprocess regression. The allowance change is recorded in Build; limit: this accepts the current infrastructure claim, not the superseded comparative scientific claim.

Test homes: `bench/test_dependency_density_bench.py`, permanent protected lifecycle/contract owner; `bench/test_diffusion_runtime.py`, permanent worker supporting-test owner; `bench/native/test_native_stopping.py` and `bench/native/test_softcap_boundary.py`, permanent native source-test owners.

Full gates: PASS. Independently executed: 11 Python tests, benchmark and micro selftests, schedule validation across 50 cases, both permanent native source tests against build-manifest-matching sources, in-memory compilation of all 57 repository Python files, and candidate/native/archive integrity checks. Protected witness SHA256 remains `22632fb7545ea4ab939b9f4ad7861d5d5b63f89b275992d59263ed3e2634bd52`, matching its retrievable RED snapshot.

Residual risks:

- Nine fixtures establish regression coverage, not statistical model rankings or an AR comparison.
- Backend boundary success does not establish that every longer full-model generation avoids memory errors.
- Abrupt Python-worker loss leaves unpersisted timing/output unavailable, explicitly documented as `WorkerInterrupted`.

Recommendation: ACCEPT

Packet: No corrective change or additional GPU execution is required for the current framed claim.

## Revisions

### Execution constraint and documentation scope, 2026-09-07

- Latest user instruction: "don't do it if it will take 2 hours, stop when we have good enoguh data".
- Execution decision: finish the 18-row transport pilot and stop. The screen and full matrix remain unrun. This curtails execution and does not establish the scientific hypothesis.
- Orchestrator-approved necessary documentation scope: `README.md` for the required durable native-channel scoring constraint; `docs/workload_hypotheses.md` and `bench/DEPENDENCY_DENSITY_RUNBOOK.md` for current status; `docs/dependency_density_pilot_findings.md` for the measured findings and evidence links. Existing schedule, micro-benchmark, TPU, UI, model weights, runner source, and the protected witness remain outside the modified scope.
- Evidence: `bench/results/dependency-density/2026-09-07/evidence/pilot-validation.json` and `colab-teardown.log`. No active Colab sessions remain.

### Diffusion-only diagnostic continuation, 2026-09-07

- User authorized continuation after removing the redundant 512-token GPU control and directing diffusion-first planning to minimize machine time.
- Frozen run artifacts: `bench/results/dependency-density/diffusion-diagnostic-2026-09-07/registration.json`, `cases.json`, and `run_diagnostic.py`. The existing benchmark source and protected witness are unchanged by this execution.
- Every measured generation has a 9,216-token allowance. Gates cover completion, basic correctness, dependency sensitivity, then length; maximum 15 generations, two minutes each, subject to a 20-minute total allocation ceiling and reserved cleanup time. No AR runtime is loaded.
- Offline cutoff validation reclassified all nine saved diffusion pilot outputs; no new low-budget GPU run is needed.
- The existing CLI cannot identify the exact EOS/repetition-stop reason or separate reasoning/final timestamps. These remain explicitly unavailable; token counts are labeled retokenized, and observed cap returns are recorded separately from timeouts and completed wrong answers.

- Diagnostic outcome: both eight-record completion cases returned before the accepted 9,216-token allowance without final answers. The registered completion gate stopped the other 13 cases. No AR or low-budget control ran.
- Evidence: `bench/results/dependency-density/diffusion-diagnostic-2026-09-07/results.jsonl`, `startup-11264.log`, `validation.json`, and `teardown.log`; findings in `docs/diffusion_completion_diagnostic_findings.md`. Allocation upper bound 10.9 minutes; no active sessions.
- The exact native stop cause is not exposed by this CLI. The next required diagnostic is explicit stop-branch/token instrumentation, not a claim that more budget or a reasoning-disable setting solves the failure.
- Necessary status documentation updated: `docs/workload_hypotheses.md`, `bench/DEPENDENCY_DENSITY_RUNBOOK.md`, and `docs/dependency_density_pilot_findings.md`. The earlier comparative scientific claim remains unproved and the original audit verdict remains unresolved.
- Independent diagnostic review: PASS for execution and bounded findings, with native stop cause unresolved. Evidence: `bench/results/dependency-density/diffusion-diagnostic-2026-09-07/independent-review.md`. This does not supersede the original comparative-scientific REVISE verdict.

### 2026-09-07: Authorized stop-repair experiment

User requested a new session to fix completion. Extend diagnostic scope to an isolated instrumented copy of the pinned native CLI under `bench/results/dependency-density/stop-repair-2026-09-07/`, a conditional repetition-heuristic bypass, and supporting diagnostic driver/tests. Existing shipped runner setup, model, benchmark evaluator, and protected witness remain unchanged. Primary bounded outcome: observe exact stop cause and test whether a targeted change yields canonical correct final answers on the two frozen completion cases. Preserve EOG and 9,216-token allowance, 120-second per-turn and 1,200-second session ceilings; no AR or low-budget runs. Baseline benchmark unit suite passes before edits. Reuse DiffusionSession and frozen cases. Budget-only rerun rejected because prior cases stopped below cap. Local trim witness reproduces cutoff and verifies bypass retains EOG; independent audit requested for the patch and measured artifacts. Original comparative claim remains unproved.

Session ceiling revision: user asked why not 25 minutes while CUDA compilation was ongoing. Raised this session's hard ceiling to 1,500 seconds from the original allocation start, with local watchdog and remote deadline updated. Per-turn limit remains 120 seconds, with early stop at failed gates.

Stop-repair evidence: baseline repeated both failures via the native repetition branch; opt-in bypass yielded two correct final answers and EOG. Full canvas IDs match through both baseline cuts. Native model source is isolated, evaluator and protected witness unchanged. First126-value case failed without a native stop; original exception was overwritten by trace-status validation, so exact wrapper cause is not claimed.

User explicitly requested keeping the GPU and more tests before teardown. Canceled automatic session teardown and launched a bounded330-second size ladder, retaining the model afterward. `run-ladder.py` preserves original exception/type/elapsed and separate native-stop state. Current allocation is intentionally active, not represented as shut down.

Ladder outcome: five canonical correct EOG answers (direct16/32/64 twice; mixed64). Chained64 first reached the batch remainder timeout at40 seconds; a read-only pipe drain retained the same native generation, which later crashed in CUDA softcap after31 full canvases. No chained correctness or latency conclusion. Model was reloaded into a retained worker after the crash; allocation remains active at user request. Evidence: `bench/results/dependency-density/stop-repair-2026-09-07/ladder/`.

Independent reviews recorded: initial bounded stop repair ACCEPT, ladder PASS for five observed exact EOG completions, chained completion unproved due runtime crash. Reviews saved separately with their scope limitations. Original comparative acceptance remains UNPROVED. Replacement model readiness checked by parent after audit and retained in `retained-model.json` plus startup log; native PID16415 was sleeping with29,238MiB device memory allocated.

### 2026-09-07: Matched32-value comparison and softcap boundary repair

User authorized the proposed repeated32-value comparison and CUDA investigation. Isolated scope includes `bench/results/dependency-density/density32-2026-09-07/` and `softcap-repair-2026-09-07/`, source-only64-bit softcap size/index patch, boundary probe, incremental native build, and bounded GPU validation. Reuse resident model request worker for9 matched-output cases, Latin-square density order, full120-second case limit with130-second start reserve and720-second batch cap. Retain GPU per user. Preserve original benchmark/evaluator/witness.

Softcap framed claim: native launch count/index remains correct at and above2^31 tensor elements and the recorded long-case failure path can execute without integer-truncated launch dimensions. Builder-owned lowest-level witness uses actual softcap host launch source with a capture stub; original source fails at8192positions*262144vocabulary (negative element count and blocks). This contained, isolated CUDA patch uses builder witness with independent audit. GPU replay remains needed; no native fix acceptance from arithmetic alone. No decision required.

Matched32-value outcome: all9 canonical final answers with native EOG. Threecases/density and identicalexpectedtargetwithintrio; medianwarmseconds direct21.48, mixed14.40, chained15.16. No generalranking or originalARcomparison claim. Evidence and independent solves in `density32-2026-09-07/`.

Softcap GPUboundary evidence: originalreal kernel launch succeeds below2^31 and fails at2^31 with invalidconfiguration;64-bit patch passes numericalsentinels at8192/8239/11264 positions. Adapter uses actualkernel/host arithmetic with directCUDAlaunch, not the fullbackendwrapper. Native incrementalbuild completed; native32control + prior64chained replay is underway with full240-second limit, chosen to exceed prior139-secondcrash point.

Softcap native integration:32-value chainedcontrolpassed. Frozen64-value replay usedfull240seconds allowance but aborted with-6 after31fullcanvases, now CUDAillegalmemoryaccess at synchronization. Isolatedinteger-boundaryclaimproved; integratednativefixunproved, no productionpromotion. Stop longreplays pendingminimalfull-backend diagnostic; preserve botherrortraces. Replacementmodelreloadrequestedworker22009, allocationretained. Independent acceptance review pendingfinalrecord.

Independent final audit REVISE for complete native repair; PASS for9saved32value completions and isolatedintegerboundaryrepair. Review saved `softcap-repair-2026-09-07/independent-review.md`. Parent separatelyverified replacementrunnerPID22010 sleeping,29,238MiB allocated,0%GPUutilization and ready=true. Model/GPUremainactive by explicituserrequest.

### Harness consolidation revision, 2026-09-07

User approved the six prioritized testing changes and Colab verification. The current Frame covers those prerequisites; the original comparative scientific claim remains unproved. Superseded stages are preserved below as historical revision evidence.

## Frame

Candidate: `dependency-density-benchmark/frame-v1 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo`

### Verified reality
- `python bench/micro_bench.py selftest` — passes the existing diffusion telemetry parser and linear-fit checks; limit: it exercises neither model nor a Colab GPU.
- `python -m compileall -q .` — all existing Python files compile; limit: imports, model runtimes, and benchmark behavior are not exercised.
- `cells/nvidia/cell_5_benchmark_engine.py:294-378,964-1015` — provides warm AR and diffusion execution paths and durable JSONL output; limit: model order and diffusion sampler state are not paired or randomized.
- `cells/common/cell_4_schedule_puzzle.py:1038-1136` — provides strict evaluation machinery but permits a compact output for one workload; limit: it cannot own a canonical fixed-length dependency benchmark.
- `bench/micro_bench.py:85-219` — provides standalone A100 model setup and telemetry parsing patterns; limit: its task and timing boundaries do not test correctness across dependency density.
- `colab status -s bench-a100` — confirms an active A100 Colab session currently running runner setup; limit: it does not prove model artifacts or the new benchmark are ready.

### Final primary claim
- On one A100 session, the benchmark produces paired, exactly scored results that show whether Gemma 4 AR and DiffusionGemma correctness-filtered latency changes across three output sizes and three dependency densities.

### Routing
- Witness: `independent`
- Why: The benchmark crosses the local harness, Colab CLI, two model runtimes, and persisted result artifacts.
- Human-owned irreversible action: None.

### Decisive witness
- Layer: Standalone benchmark contract plus an A100 pilot execution.
- Permanent owner: `bench/test_dependency_density_bench.py`, because the repository has no existing benchmark-contract test owner.
- Witness: The self-test proves deterministic case construction, exact evaluation, balanced conditions, and canonical-output enforcement, then a Colab pilot produces one scored result for both models in every matrix cell with recorded warm wall time and execution order.

### Guardrail claims
- Every paired case gives both models the same semantic prompt, canonical output requirement, maximum output allowance, and expected answer.
- Results retain failures and record model artifact, hardware, seed, prompt hash, output tokens, wall time, internal compute when available, and randomized execution order.
- Existing schedule and micro-benchmark behavior remains unchanged.

### Supporting obligations
- Add a deterministic case generator with direct, mixed, and chained symbol workflows at fixed output sizes, an exact canonical parser/evaluator, and offline unit-style self-tests.
- Add a Colab runner that reuses staged model paths, warms both runtimes, randomizes paired order deterministically, and writes incremental JSONL plus a condition-level summary.
- Separate common warm wall timing from runner-specific compute telemetry and never treat invalid output as a performance win.

### Allowed scope
- Reuse: Extend the standalone pattern and model/telemetry conventions in `bench/micro_bench.py`; no existing test owner fits, so add the benchmark-contract owner named above without modifying the schedule benchmark engine.
- Cheaper alternative: Reusing the schedule suite alone was rejected because it cannot isolate dependency density at fixed output length.
- Include: One standalone benchmark script, its permanent contract test, proposal ledger updates, and generated run artifacts outside source control.
- Exclude/protect: Existing schedule cases, UI, TPU implementation, model weights, runner source, Drive data, and claims about all AR or diffusion architectures.

### Decisions required
- None.

#### Proof

Candidate: `dependency-density-benchmark/frame-v1 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo`

**Protected witness**
- Paired, exactly scored dependency-density matrix contract — `bench/test_dependency_density_bench.py` / `DependencyDensityBenchmarkContractTest.test_selftest_reports_the_complete_deterministic_matrix_contract`
  - Defect and boundary: the standalone dependency-density benchmark CLI does not exist; repository CLI contract to the A100 benchmark workflow and persisted result boundary.
  - Assertion: two independent `selftest --json` executions must succeed identically and report nine balanced cells spanning three output sizes and `direct`, `mixed`, and `chained` densities; proves deterministic construction and balanced-condition prerequisites; limit: it does not prove real model execution or comparative latency.
- Equal paired inputs and exact canonical scoring — `bench/test_dependency_density_bench.py` / `DependencyDensityBenchmarkContractTest.test_selftest_reports_the_complete_deterministic_matrix_contract`
  - Defect and boundary: no benchmark currently enforces equal paired contracts or rejects non-canonical answers; generated-case contract to scoring boundary.
  - Assertion: the public self-test must report successful deterministic-case, exact-scoring, canonical-output, and paired-contract checks; proves the offline contract exercises these invariants; limit: it does not prove unseen model outputs satisfy them.
- Failure retention, telemetry schema, and randomized order — `bench/test_dependency_density_bench.py` / `DependencyDensityBenchmarkContractTest.test_selftest_reports_the_complete_deterministic_matrix_contract`
  - Defect and boundary: no dependency-density result format currently retains invalid outputs with required provenance, timing, and execution-order fields; model-runner output to durable-result boundary.
  - Assertion: the public self-test must report successful invalid-output-retention, complete-result-schema, and seeded-balanced-order checks; proves these offline contract checks are mandatory; limit: only the A100 pilot can prove real rows contain valid model, hardware, seed, prompt-hash, token, timing, internal-compute, and order data.
- Existing benchmark behavior remains unchanged — `bench/test_dependency_density_bench.py` / `DependencyDensityBenchmarkContractTest.test_selftest_reports_the_complete_deterministic_matrix_contract`
  - Defect and boundary: the proposal must not alter existing schedule or micro-benchmark behavior; new standalone benchmark to existing benchmark boundary.
  - Assertion: the witness addresses only the standalone `bench/dependency_density_bench.py` CLI and requires no existing benchmark mutation; proves ownership isolation; limit: Build and Audit must still rerun existing schedule and micro-benchmark checks and inspect protected scope.
- Protected paths: `bench/test_dependency_density_bench.py`.
- Protected revision: `sha256:22a41b73131ec3da114eaa48788ca77437a8e07714d50bb759d7a215b85c4775`.

**Red evidence**
- `python -m unittest bench/test_dependency_density_bench.py -v` → fails the witness assertion because `bench/dependency_density_bench.py` is missing; log: `docs/proposals/dependency-density-benchmark-red.log`.
- The primary and guardrail claims have no proof until this command is observed RED and, after implementation, the required A100 pilot completes.

**Supporting test plan**
- Deterministic case generation and exact canonical parsing/evaluation → Build: `bench/dependency_density_bench.py selftest`, exercised through `bench/test_dependency_density_bench.py`; catches nondeterministic construction, matrix imbalance, permissive scoring, and unequal paired contracts.
- Result serialization, failure retention, timing separation, and seeded order planning → Build: `bench/dependency_density_bench.py selftest`, exercised through `bench/test_dependency_density_bench.py`; catches dropped failures, incomplete provenance, conflated timing, and biased execution order.
- Existing schedule and micro-benchmark regression guardrail → Build: existing schedule checks plus `python bench/micro_bench.py selftest`; catches unintended behavior changes outside the standalone benchmark.

#### Build

Candidate: `dependency-density-pilot-20260907 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo`; source manifest SHA256: `adb5f5af8f63fa5bf15ee4b1816f298b12a11249fe609cc90cd371a29233f46f`.

The candidate manifest is `bench/results/dependency-density/2026-09-07/evidence/candidate-manifest.json`. It identifies 28 native Python/Markdown files, excluding the proposal ledger and generated artifacts. Artifact paths below are relative to `bench/results/dependency-density/2026-09-07/`.

### Files changed

- `bench/dependency_density_bench.py`, implemented actual tokenizer calibration, exact diffusion prompt counts, shared output allowances, context gates, warmup, artifact identities, failure retention, paired metrics, and sampled device memory.
- Same file, implemented persistent tokenizer transport and phased model allocation with frozen execution plans preserving each case's model order.
- Same file, corrected diffusion stream capture and native channel decoding. Complete generated text remains retained and counted; malformed channels and final prose remain invalid.
- `README.md`, added the durable scoring constraint with **Why** and **Guarded by**. The orchestrator explicitly approved this exact scope expansion.
- `docs/workload_hypotheses.md`, `bench/DEPENDENCY_DENSITY_RUNBOOK.md`, and `docs/dependency_density_pilot_findings.md`, updated by the parent to record execution, findings, limitations, and stopping status. The orchestrator explicitly approved these necessary benchmark status/evidence documentation paths.
- Generated run artifacts and supporting evidence retained under the artifact directory identified above.

### Unit evidence

- `python bench/dependency_density_bench.py selftest --json`, RED for missing calibration; log: `evidence/dependency-density-builder-red.log`.
- Same command, RED for missing tokenizer service; log: `evidence/dependency-density-tokenizer-service-red.log`.
- Same command, RED for missing phased planner; log: `evidence/dependency-density-phased-red.log`.
- Same command, RED for observed runner transport; log: `evidence/dependency-density-real-transport-red.log`.
- Same command, RED for native channel decoding; log: `evidence/dependency-density-native-channel-red.log`.
- Same command, GREEN; log: `evidence/dependency-density-native-channel-green.log`.
- Actual subprocess transport exercise, GREEN; log: `evidence/dependency-density-builder-transport.log`.
- Replay of all three real diffusion probe transcripts, GREEN; log: `evidence/dependency-density-real-log-replay.log`.

### Green evidence

- Decisive offline witness: `python -m unittest bench/test_dependency_density_bench.py -v`, pass; log: `evidence/dependency-density-builder-witness.log`.
- Protected witness SHA256 remains `22a41b73131ec3da114eaa48788ca77437a8e07714d50bb759d7a215b85c4775`.
- Gate: `python bench/micro_bench.py selftest`, pass; log: `evidence/dependency-density-builder-micro.log`.
- Gate: `python -m compileall -q .`, pass; log: `evidence/dependency-density-builder-compile.log`.
- Parent-executed schedule gate: `uv run --with matplotlib python -m cells.common.cell_4b_validation`, pass; log: `evidence/dependency-schedule-validation.log`.
- A100 transport pilot: 18 rows, nine complete pairs, all nine matrix cells represented; artifact: `dependency-density-20260907T050355645694Z.jsonl`.
- Independent parent validation, PASS: zero runtime errors or context overflow, paired order verified, raw transcripts decoded again, and exact scores recomputed; evidence: `evidence/pilot-validation.json`.
- Pilot harness SHA256 matches the manifest: `334886cacceeea28f83364b4d31da477c7c1703145840bd196e847f2985e9f1c`. Exact tokenizer prompt counts were remotely validated; all pilot contexts fit. The response contract was registered before execution in `evidence/run-registration.json`.
- Parent verified downloaded archive hashes before releasing the runtime. Colab reports no active sessions; evidence: `evidence/colab-teardown.log`.

### Intervention record

- None. This work produced benchmark evidence rather than a deployed product intervention.

### Deviations

- The user explicitly curtailed further execution. The screening set and full matrix were not run.
- Pilot validity was AR 1/9 and diffusion 0/9. Every diffusion response exhausted its allowance inside an unclosed thought channel. There were no jointly valid pairs, so no correctness-conditioned latency endpoint can be estimated.
- The transport pilot is complete. It does not establish the dependency-density hypothesis or a model-performance recommendation.
- README and status-document scope expansions were explicitly approved and completed; no unresolved scope request remains.

#### Audit

Candidate: `dependency-density-pilot-20260907 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo; source manifest sha256:adb5f5af8f63fa5bf15ee4b1816f298b12a11249fe609cc90cd371a29233f46f`

Independence: fresh-context, independent auditor received the ledger and candidate identity and did not build the candidate.

Primary-claim verdict: UNPROVED. evidence: independently reran `python bench/results/dependency-density/2026-09-07/evidence/dependency-validate-results.py bench/results/dependency-density/2026-09-07 18 bench/dependency_density_bench.py`, which passed. Additional independent assertions solved every frozen case, recomputed scores from saved output, checked recorded A100 provenance and execution plans, and confirmed 18 rows across nine complete pairs. AR validity is 1/9; diffusion validity is 0/9. Every paired valid-latency ratio is null; limit: this proves completion of the diagnostic transport pilot, not correctness-filtered comparative latency or a dependency-density effect. The user-authorized early stop is appropriate and does not establish the original scientific claim.

Guardrail verdicts:

- Equal paired semantic prompts, expected answers, canonical requirements, and maximum allowances: UNPROVED as a reusable contract. evidence: independent inspection of the frozen cases and rows proves matching contracts for all nine saved pairs. However, `bench/dependency_density_bench.py:selftest_report` implements `paired_contract_equal` through comparisons of each prompt and answer with itself. The protected CLI witness therefore cannot detect unequal model contracts; limit: this is an offline witness weakness, not evidence that the saved pilot used unequal pairs.
- Failure retention and required provenance, timing, and order: PROVED for the saved pilot. evidence: the validator and independent artifact assertions verified all 18 retained rows, prompt hashes, model identities, hardware, seeds, output-token fields, positive warm timings, diffusion compute telemetry, shared allowances, and actual frozen execution order. All nine diffusion transcripts remain inside unclosed thought channels and consumed their full canvas allowances; limit: the pilot had no runtime errors, so its artifacts do not establish every runtime-error recovery path.
- Existing schedule and micro-benchmark behavior remains unchanged: UNPROVED historically. evidence: `python bench/micro_bench.py selftest` and `uv run --with matplotlib python -m cells.common.cell_4b_validation` independently passed, including all 50 schedule cases. All 28 candidate manifest hashes match; limit: this checkout has no Git repository or retrievable pre-build source baseline. Current hashes and passing checks establish current identity and tested behavior, not historical absence of changes.

Scope and duty verdict: scope HELD; duties HELD. evidence: inspected implementation follows the standalone benchmark approach, and README plus findings/runbook/status documentation are covered by the explicit Revisions scope approval. `README.md` records the native-channel rule with **Why:** and **Guarded by:** pointing to existing checks. The curtailed execution and unproved scientific endpoint are disclosed; limit: historical changed-file scope cannot be conclusively reconstructed without a pre-build baseline.

Test homes: `bench/test_dependency_density_bench.py`. permanent standalone benchmark-contract owner named by Frame and Proof; its SHA256 remains `22a41b73131ec3da114eaa48788ca77437a8e07714d50bb759d7a215b85c4775`. Supporting implementation self-tests reside in `bench/dependency_density_bench.py`.

Full gates: FAIL. required deterministic commands passed independently: `python -m unittest bench/test_dependency_density_bench.py -v`, `python bench/micro_bench.py selftest`, schedule validation, and the saved-pilot validator. Candidate manifest verification passed for all 28 entries. Inspected the recorded `compileall` evidence and independently compiled all 28 Python files in memory without writing bytecode. Inspected the original RED witness log at `docs/proposals/dependency-density-benchmark-red.log`; limit: aggregate acceptance fails because the scientific claim remains unproved and the reusable paired-contract check is non-proving despite green execution.

Residual risks:

- One case per condition cannot establish reliable rates or latency distributions.
- Native reasoning exhausted every diffusion allowance; results apply to this recorded runtime configuration.
- Phased allocation preserves per-case model order but leaves possible session and phase effects.
- The current manifest identifies the candidate but cannot establish its pre-build history.

Recommendation: REVISE

Packet: Preserve the completed pilot and record the original scientific claim as incomplete under the user’s execution constraint. No further model run is authorized this turn. Before a future acceptance attempt, repair the tautological paired-contract self-test in `bench/dependency_density_bench.py` with evidence that an unequal contract fails, preserving the protected witness; provide a retrievable baseline for any historical unchanged-source claim. Comparative scientific acceptance requires separately authorized evidence with eligible valid pairs.
