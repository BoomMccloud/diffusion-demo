---
proposal_id: "workload-hypotheses"
state: ACCEPTED
witness: builder
candidate: "native-docs-sha256 6395e721f93ef8548188a93b615547b537680a99f8e16a58fb0829a8f94ee089 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo"
---

# Proposal: Replace the backlog with workload hypotheses

## Proposal

### Intent

Remove the project backlog and replace it with the discussion of how to discover workloads that work well for diffusion models versus autoregressive models.

### Tentative primary claim

Repository readers can find one canonical account of the hypothesized workflow strengths, the evidence needed to establish them, and the next benchmark to run.

### Why now

The hypothesized diffusion strengths are currently scattered across several files, and the backlog states some untested outcomes too confidently.

### Known constraints

Remove `BACKLOG.md` and replace it with the discussion in this thread.

### Non-goals

None stated.

### Open choices

None stated.

## Frame

Candidate: `workload-hypotheses/frame-v1 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo`

### Verified reality
- `python -m unittest bench/test_dependency_density_bench.py -v` — the existing dependency-density contract passes before the documentation change; limit: it does not evaluate documentation.
- `python bench/micro_bench.py selftest` and `python -m compileall -q .` — existing benchmark parser checks and Python compilation pass before the change; limit: they do not exercise Colab models.
- `BACKLOG.md:49-143` — mixes task status with hypotheses and describes untested diffusion outcomes as demonstrations; limit: it is not a falsifiable workload-selection guide.
- `docs/model_approach_demo_test_cases.md:588-709` — contains candidate workflows, measures, and fairness guidance; limit: it ranks workflows using presumed architectural advantages and is not the canonical status record.
- `docs/diffusion_optimization_findings.md:276-309,436-454` — labels the parallelism explanation unconfirmed and redirects attention toward quality and dependency probes; limit: it records one runtime investigation rather than the complete workload program.
- `docs/proposals/dependency-density-benchmark.md` and `bench/DEPENDENCY_DENSITY_RUNBOOK.md` — record the implemented nine-cell benchmark and stopped A100 attempt; limit: no model result has been collected.
- Relative Markdown link check across the repository — all current local relative links resolve; limit: it does not validate prose accuracy.

### Final primary claim
- Repository readers have one canonical workload-hypothesis document that distinguishes hypotheses from evidence and explains how workflows are screened, promoted, and confirmed for Gemma 4 AR versus DiffusionGemma.

### Routing
- Witness: `builder`
- Why: This is a contained, reversible documentation replacement with no runtime or service behavior change.
- Human-owned irreversible action: None.

### Decisive witness
- Layer: Repository documentation contract.
- Permanent owner: `README.md` research-document index and `docs/workload_hypotheses.md`.
- Witness: `BACKLOG.md` is absent, README and bootstrap references point to the replacement, all relative Markdown links resolve, and the replacement contains capability gates, falsifiable hypotheses, workflow tournament method, success criteria, current evidence, and restart status.

### Guardrail claims
- The replacement does not claim that unrun benchmarks have established a diffusion or AR advantage.
- Existing benchmark implementation, proposal history, and findings remain intact.
- Colab setup instructions no longer tell readers to upload or consult `BACKLOG.md`.

### Supporting obligations
- Preserve measured findings and current dependency-benchmark status while removing task IDs and predicted winners from the canonical planning surface.
- Test the document with a context-free reader for discoverability, ambiguity, and unsupported claims.

### Allowed scope
- Reuse: Replace the roadmap link in `README.md` with `docs/workload_hypotheses.md` and reuse the evidence already recorded in the findings and dependency benchmark proposal.
- Cheaper alternative: Editing `BACKLOG.md` in place was rejected because the user explicitly requested its removal and the intended replacement is not a task backlog.
- Include: Delete `BACKLOG.md`; add `docs/workload_hypotheses.md`; update `README.md`, `cells/colab_bootstrap.py`, and this proposal ledger; run documentation and existing benchmark gates.
- Exclude/protect: Benchmark Python behavior, model runtimes, generated results, existing proposal ledgers, and historical findings.

### Decisions required
- None.

## Proof

Candidate: `workload-hypotheses/frame-v1 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo`

Builder-owned documentation witness is deferred to Build. No independent Proof stage is required for this contained documentation change.

## Build

Candidate: `native-docs-sha256 6395e721f93ef8548188a93b615547b537680a99f8e16a58fb0829a8f94ee089 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo`

### Files changed

- `BACKLOG.md` — removed the task backlog and its untested outcome assertions.
- `docs/workload_hypotheses.md` — added the canonical workload-discovery question, capability gates, hypothesis register, tournament method, registered dependency-density rule, evidence boundaries, current status, and next actions.
- `README.md` — replaced the backlog layout and research link with the canonical workload-hypothesis document and removed obsolete task-ID wording from the runbook.
- `cells/colab_bootstrap.py` — removed `BACKLOG.md` from the required upload message.
- `docs/proposals/workload-hypotheses-reader-test.md` — persisted the context-free reader prompt, findings, final response, and resulting refinements.
- `docs/proposals/workload-hypotheses-candidate.manifest` — recorded the candidate file set and exact digest reproduction command.
- `docs/proposals/workload-hypotheses.md` — recorded the proposal-pipeline handoff.

### Unit evidence

- Builder-owned decisive witness: documentation contract Python assertion — RED: `BACKLOG.md` still existed and `docs/workload_hypotheses.md` was absent; log: `/tmp/workload-hypotheses-red.log`.
- Context-free reader test — RED: found ambiguous system identity, pilot evidence status, dependency effect, latency eligibility, bootstrap unit, and multi-block semantics; evidence: `docs/proposals/workload-hypotheses-reader-test.md`.
- Context-free reader retest — GREEN: no material blockers after refinement; evidence: `docs/proposals/workload-hypotheses-reader-test.md`.

### Green evidence

- Decisive witness: documentation contract Python assertion — pass, including replacement presence, reader evidence, candidate manifest, required sections, README/bootstrap references, and all relative Markdown links; log: `/tmp/workload-hypotheses-green-v2.log`.
- Candidate identity: `test ! -e BACKLOG.md && shasum -a 256 README.md docs/workload_hypotheses.md cells/colab_bootstrap.py | shasum -a 256` — reproduced `6395e721f93ef8548188a93b615547b537680a99f8e16a58fb0829a8f94ee089`; manifest: `docs/proposals/workload-hypotheses-candidate.manifest`.
- Gate: `python -m unittest bench/test_dependency_density_bench.py -v` — pass; log: `/tmp/workload-hypotheses-green-v2.log`.
- Gate: `python bench/micro_bench.py selftest` — pass; log: `/tmp/workload-hypotheses-green-v2.log`.
- Gate: `python -m compileall -q .` — pass; log: `/tmp/workload-hypotheses-green-v2.log`.

### Intervention record

- None, because this is a documentation replacement with no deployed user-facing intervention.

### Deviations

- None.

## Audit

Candidate: `native-docs-sha256 6395e721f93ef8548188a93b615547b537680a99f8e16a58fb0829a8f94ee089 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo`

Independence: fresh-context — this context performed the prior independent audit but did not build the candidate or author R1.

Primary-claim verdict: PROVED — evidence: `docs/workload_hypotheses.md` contains the canonical workload account, evidence labels, capability gates, hypothesis register, tournament stages, confirmation criteria, current evidence, and restart status; the independent documentation-contract assertion passed, and `docs/proposals/workload-hypotheses-reader-test.md` records a context-free retest with no material blockers; limit: this proves the documentation contract, not model performance.

Guardrail verdicts:
- The replacement does not claim that unrun benchmarks have established a diffusion or AR advantage: PROVED — evidence: hypotheses are explicitly labeled, establishment requires registered confirmation, and the document states that no dependency-density model run exists; limit: prose meaning was manually inspected.
- Existing benchmark implementation, proposal history, and findings remain intact: PROVED — evidence: `bench/test_dependency_density_bench.py` retains protected SHA-256 `22a41b73131ec3da114eaa48788ca77437a8e07714d50bb759d7a215b85c4775`; the benchmark proposal, runbook, and findings remain present; existing unit, self-test, and compilation gates pass; limit: absent Git metadata prevents a complete source-control comparison for unprotected historical files.
- Colab setup instructions no longer tell readers to upload or consult `BACKLOG.md`: PROVED — evidence: the documentation-contract assertion confirms `BACKLOG.md` is absent and neither `README.md` nor `cells/colab_bootstrap.py` references it; limit: external notebook copies are outside scope.

Scope and duty verdict: scope HELD; duties HELD — evidence: R1 adds only proposal evidence and identity metadata requested by the prior audit; `docs/proposals/workload-hypotheses-reader-test.md` makes the context-free prompts, findings, retest result, and resulting refinements retrievable; `docs/proposals/workload-hypotheses-candidate.manifest` records the candidate file set and digest command, which independently reproduces the supplied digest; protected benchmark behavior remains green; limit: candidate scope is reconstructed from the manifest and ledger because the repository has no Git metadata.

Test homes: `None — the candidate added no tests.`

Full gates: PASS — repository-root documentation-contract Python assertion: passed; `test ! -e BACKLOG.md && shasum -a 256 README.md docs/workload_hypotheses.md cells/colab_bootstrap.py | shasum -a 256`: reproduced `6395e721f93ef8548188a93b615547b537680a99f8e16a58fb0829a8f94ee089`; `python -m unittest bench/test_dependency_density_bench.py -v`: 1 test passed; `python bench/micro_bench.py selftest`: passed; `python -m compileall -q .`: passed; limit: these offline gates do not exercise model runtimes or an A100.

Residual risks:
- The first reader response is preserved as a findings summary rather than a raw transcript, limiting fine-grained wording review, but the material findings and exact final retest result are retrievable.
- No model benchmark result exists; the candidate correctly keeps workload conclusions provisional.
- Lack of Git metadata limits historical diff reconstruction, although the native candidate identity is now reproducible.

Recommendation: ACCEPT

Packet: Replace the ledger’s Audit placeholder with this section and close the proposal; no candidate file changes or additional evidence are required.

## Revisions

### R1 — 2026-09-05 — Context-free reader evidence and candidate identity were not independently retrievable
- Verdict: REVISE — the audit could not inspect agent-only reader-test transcripts or reproduce the native-docs digest from a recorded manifest and command.
- Changed: `docs/proposals/workload-hypotheses-reader-test.md`, `docs/proposals/workload-hypotheses-candidate.manifest`, and this ledger — persisted the reader prompt, findings, final response, affected-file manifest, and digest recipe.
- Re-audit: ACCEPT — reader evidence and digest recipe are independently retrievable; candidate `native-docs-sha256 6395e721f93ef8548188a93b615547b537680a99f8e16a58fb0829a8f94ee089 @ /Users/jasonbxu/Documents/GitHub/diffusion-demo`.
