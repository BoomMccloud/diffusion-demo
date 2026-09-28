---
proposal_id: "repository-cleanup"
state: ACCEPTED
witness: builder
candidate: "f9d27686fc1f2e7ecd0b5f53f53eebadb4f79b2ab63ad57f5ad15f2579583ac2 @ active-scope digest + archive manifest"
---

# Proposal: Repository cleanup

## Proposal

### Intent

Review the folder, reduce clutter, move unused or test files into an archive or test folder, and keep only the important files in the active project layout.

### Tentative primary claim

The folder presents the important active benchmark files directly, while test files are collected under a test folder and unused or historical files are clearly archived.

### Why now

The folder currently contains a lot of files.

### Known constraints

Move unused or test files into an archive or test folder, and keep only the important ones in the active layout.

### Non-goals

None stated.

### Open choices

None stated.

## Frame

Candidate: `d3b66136af9e879f85e6eb5e0140d1d9b509a62b5b5797d6ab4123ee5198d971 @ local source tree`

### Verified reality
- `AGENTS.md:Current work` and `AGENTS.md:Authoritative working files` name the business benchmark, fixture generator, diffusion runtime, dependency-density harness, business definitions, workload hypotheses, runbook, and proposal history as current or authoritative; limit: they do not classify every older demo file.
- `find . -type f | wc -l`, `find bench/results -type f | wc -l`, and cache counts reported 492 total files, 409 saved-result files, and 68 bytecode-cache files; limit: counts alone do not establish whether a file is important.
- `du` and archive-file inspection found 324 MB under `bench`, including about 247 MB of compressed artifact bundles beside extracted evidence; limit: size does not make retained scientific evidence disposable.
- `README.md`, `cells/`, `lab/`, `run_terminal_suite.py`, and `bench/micro_bench.py` describe the superseded schedule-demo and optimization workflow, while the active objective in `AGENTS.md` is the paired 12-problem business screen; limit: historical files remain useful for provenance and should be archived rather than discarded.
- `python -m unittest bench.test_business_fixtures bench.test_dependency_density_bench bench.test_diffusion_runtime -v`, `python bench/dependency_density_bench.py selftest --json`, and `python -m bench.business_benchmark self-test --json --output-dir /tmp/diffusion-demo-cleanup-baseline --url http://127.0.0.1:1` passed before cleanup; limit: these are offline checks and do not run either model or an accelerator.

### Final primary claim
- The repository's active layout exposes the current business benchmark and its authoritative documentation, collects maintained tests under `tests/`, and moves superseded demo material and bulky duplicate bundles into a documented `archive/`.

### Routing
- Witness: `builder`
- Why: The changes are local, reversible file moves and documentation updates with no service, data, authentication, payment, or product-lifecycle boundary.
- Human-owned irreversible action: None.

### Decisive witness
- Layer: Repository layout contract plus existing offline suites.
- Permanent owner: `tests/test_repository_layout.py` and the existing benchmark test modules after relocation under `tests/bench/`.
- Witness: The active tree contains the named authoritative files, maintained tests are discoverable under `tests/`, legacy demo material is under `archive/`, generated caches are absent, and the existing 16-test suite and self-tests still pass.

### Guardrail claims
- The current business benchmark, fixture, runtime, and dependency-density offline behavior remains unchanged and passing.
- Historical research and saved benchmark evidence remain retrievable, with moved material indexed from the archive.
- Current documentation and commands point to the relocated maintained tests and active entry points.

### Supporting obligations
- Add a small layout test, observe it fail before the moves, then make the minimum relocations and path adjustments needed for it and test discovery to pass.
- Remove generated Python bytecode caches, archive superseded schedule-demo files and duplicate artifact bundles, and add an archive index describing provenance and former locations.
- Refresh the root README around the current objective and update only current operational references, without rewriting historical proposal ledgers.

### Allowed scope
- Reuse: Extend the existing `archive` concept requested by the user, the current unittest suite, and the authoritative-file list in `AGENTS.md`; no new runtime component is needed.
- Cheaper alternative: Deleting only `__pycache__` was rejected because it would leave the superseded demo workflow, scattered tests, and 247 MB of duplicate bundles mixed into active paths.
- Include: `README.md`, `AGENTS.md`, `bench/README.md`, current non-proposal documentation path references, maintained test relocation and path fixes, new `tests/test_repository_layout.py`, `archive/README.md`, superseded demo files, compressed evidence bundles, the saved tokenizer binary, generated cache directories, and this ledger.
- Exclude/protect: Active benchmark implementations and fixtures, extracted JSON/JSONL/log evidence, historical proposal ledger contents, model files, external accelerator state, and benchmark semantics.

### Decisions required
- None.

## Proof

Builder-route witness deferred to Build. The builder must add `tests/test_repository_layout.py`, observe proposal-specific RED before moving files, and retain it as the permanent repository-layout witness.

## Build

Candidate: `f9d27686fc1f2e7ecd0b5f53f53eebadb4f79b2ab63ad57f5ad15f2579583ac2 @ active-scope digest + archive manifest`

### Files changed

- `tests/bench/` — relocated the three maintained Python benchmark contract modules and adjusted their repository-root lookup.
- `tests/native/` — relocated the two native source probes and preserved the active header lookup.
- `tests/test_repository_layout.py` — added the permanent active/test/archive separation witness.
- `archive/legacy-demo/` — moved superseded schedule-puzzle cells, the optimization lab, terminal runner, micro-benchmark, and three related historical documents out of the active layout; the two A100 staging helpers remain active under `cells/`.
- `archive/artifact-bundles/` — moved 16 compressed evidence bundles and the saved Linux tokenizer executable while preserving their former relative directory structure.
- `archive/README.md` — indexed archived contents, provenance, and current-use boundaries.
- `archive/MANIFEST.sha256` — records every archived file and verifies all 16 bundles, the saved executable, and 18 legacy-demo files by content hash.
- `README.md` — replaced the superseded schedule-demo overview with the active business-screen layout, checks, and durable archive policy.
- `AGENTS.md`, `bench/README.md`, `bench/DEPENDENCY_DENSITY_RUNBOOK.md`, and `docs/workload_hypotheses.md` — updated current operational and test references without changing historical proposal ledgers.
- Generated `__pycache__/` directories and `.pyc` files — removed 68 generated bytecode files; these are ignored and recoverable by rerunning Python.

### Unit evidence

- Builder-owned decisive witness: `python -m unittest tests.test_repository_layout -v` — RED with 15 failures because tests, legacy material, bundles, executable, and caches were still in active locations; log: `/tmp/repository-cleanup-red.log`.
- Revised active-cell witness: temporarily withholding the two A100 staging helpers and running `PYTHONDONTWRITEBYTECODE=1 python -B -m unittest tests.test_repository_layout -v` — RED on both required paths, after which the unchanged files were restored; log: `/tmp/repository-cleanup-r1-cells-red.log`.
- `PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -t . -p 'test*.py' -v` — GREEN, 26 tests passed including the restored cache assertion and all benchmark tests present after concurrent runtime hardening settled; log: `/tmp/repository-cleanup-r3-green.log`.

### Green evidence

- Decisive witness: `PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -t . -p 'test*.py' -v` — pass, 26 tests with zero resulting cache directories; log: `/tmp/repository-cleanup-r3-green.log`.
- Gate: `PYTHONDONTWRITEBYTECODE=1 python -B -m bench.business_benchmark self-test --json --output-dir /tmp/diffusion-demo-cleanup-r3 --url http://127.0.0.1:1` — pass with `launch_ready`, 36 fixtures, 48 decisions, and zero generation RPCs; log: `/tmp/repository-cleanup-r3-business.log`.
- Gate: `PYTHONDONTWRITEBYTECODE=1 python -B bench/dependency_density_bench.py selftest --json` — pass with all deterministic matrix checks true; log: `/tmp/repository-cleanup-r3-density.log`.
- Gate: the in-memory Python syntax command documented in `docs/workload_hypotheses.md` passed without creating bytecode; log: `/tmp/repository-cleanup-r3-syntax.log`.
- Gate: current-path scan recorded no obsolete active documentation references; log: `/tmp/repository-cleanup-r1-stale-paths.log`.
- Gate: `shasum -a 256 -c archive/MANIFEST.sha256` — pass for every archived file; log: `/tmp/repository-cleanup-r1-archive-manifest.log`.
- Candidate identity: `find AGENTS.md README.md bench cells docs tests archive -type f ! -path 'bench/results/*' ! -path 'docs/proposals/*' ! -path 'archive/artifact-bundles/*' ! -path 'archive/legacy-demo/*' ! -path '*/__pycache__/*' -print0 | LC_ALL=C sort -z | xargs -0 shasum -a 256 | shasum -a 256` reproduced `f9d27686fc1f2e7ecd0b5f53f53eebadb4f79b2ab63ad57f5ad15f2579583ac2` before and after all gates; `shasum -a 256 -c archive/MANIFEST.sha256` separately binds every archived payload; saved results and proposal ledgers are excluded because other active work may add evidence or ledgers concurrently, and no Git metadata is present in this folder.

### Intervention record

- None, because this repository-organization change has no user-facing product outcome to measure.

### Deviations

- None. `tests/bench/test_diffusion_runtime.py` changed concurrently while this cleanup was audited; the cleanup did not edit or revert that content, and the final stable candidate records its SHA256 as `7998b937c9a93a60457296555edf19267f48bf803fb90e8e05ed6f81e97c9d66`.

## Audit

Candidate: `f9d27686fc1f2e7ecd0b5f53f53eebadb4f79b2ab63ad57f5ad15f2579583ac2 @ active-scope digest + archive manifest`

Independence: fresh-context — `this audit received only the ledger path, candidate identity, and repository, did not build the candidate, and read both prior Revisions before evaluating it`

Primary-claim verdict: PROVED — evidence: `/tmp/repository-cleanup-red.log` retains proposal-specific RED for the test relocation, archive separation, active-path removal, and cache-absence contract; `/tmp/repository-cleanup-r1-cells-red.log` independently retains RED for the revised requirement that both A100 staging helpers remain active; `tests/test_repository_layout.py` remains the permanent witness and passed within the 26-test cache-safe discovery gate; inspection confirms authoritative benchmark files remain active, maintained tests are under `tests/`, and legacy material and duplicate bundles are under `archive/`; limit: this proves repository organization and offline contracts, not staged artifacts, model quality, or accelerator behavior.

Guardrail verdicts:
- The current business benchmark, fixture, runtime, and dependency-density offline behavior remains unchanged and passing: PROVED — evidence: `PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -t . -p 'test*.py' -v` passed all 26 tests; `PYTHONDONTWRITEBYTECODE=1 python -B -m bench.business_benchmark self-test --json --output-dir /tmp/repository-cleanup-independent-r2-20260908 --url http://127.0.0.1:1` reported `launch_ready`, 36 fixtures, 48 decisions, and zero generation RPCs; `PYTHONDONTWRITEBYTECODE=1 python -B bench/dependency_density_bench.py selftest --json` passed every deterministic matrix check; and `tests/bench/test_diffusion_runtime.py` retained the settled concurrent-hardening hash `7998b937c9a93a60457296555edf19267f48bf803fb90e8e05ed6f81e97c9d66`; limit: these are offline witnesses and do not execute either pinned model or an accelerator.
- Historical research and saved benchmark evidence remain retrievable, with moved material indexed from the archive: PROVED — evidence: `shasum -a 256 -c archive/MANIFEST.sha256` passed all 36 indexed files, exactly covering `archive/README.md`, 16 compressed bundles, the saved tokenizer executable, and 18 legacy-demo files; extracted evidence remains under `bench/results/`; limit: the manifest proves present archive integrity and retrievability, not external accelerator state or artifacts never stored in the repository.
- Current documentation and commands point to the relocated maintained tests and active entry points: PROVED — evidence: inspection of `README.md`, `AGENTS.md`, `bench/README.md`, `bench/DEPENDENCY_DENSITY_RUNBOOK.md`, and `docs/workload_hypotheses.md` found the active staging helpers and relocated `tests/bench/` paths; the current-path `rg` scan, excluding saved results, proposal history, and archived payloads, returned no obsolete active test, runner, micro-benchmark, or lab paths; limit: path consistency does not validate external model or runner availability.

Scope and duty verdict: scope HELD; duties HELD — evidence: the candidate contains the framed test relocations, archive moves, archive index and manifest, current-documentation updates, active staging helpers, and generated-cache cleanup without a new runtime component; the settled runtime-test change retains its supplied hash and is recorded as concurrent work rather than cleanup authorship; `README.md` captures the durable archive and no-retained-cache policy with its `**Why:**` and existing `**Guarded by:** tests/test_repository_layout.py` witness; final inspection found zero `__pycache__` directories and zero `.pyc` files. Limit: no Git metadata exists for a historical diff, so scope is bounded by the reproducible active-scope digest, complete archive manifest, retained RED evidence, and inspected current tree.

Test homes: `tests/test_repository_layout.py` — permanent repository-layout, active-helper, archive-separation, and cache-boundary owner; `tests/bench/test_business_fixtures.py`, `tests/bench/test_dependency_density_bench.py`, and `tests/bench/test_diffusion_runtime.py` — relocated permanent benchmark contract owners; `tests/native/test_native_stopping.py` and `tests/native/test_softcap_boundary.py` — relocated permanent native source-probe owners.

Full gates: PASS — `find AGENTS.md README.md bench cells docs tests archive -type f ! -path 'bench/results/*' ! -path 'docs/proposals/*' ! -path 'archive/artifact-bundles/*' ! -path 'archive/legacy-demo/*' ! -path '*/__pycache__/*' -print0 | LC_ALL=C sort -z | xargs -0 shasum -a 256 | shasum -a 256`: reproduced `f9d27686fc1f2e7ecd0b5f53f53eebadb4f79b2ab63ad57f5ad15f2579583ac2` before and after all gates; cache-safe unittest discovery: 26 passed; business self-test: `launch_ready`, 36 fixtures, 48 decisions, zero generation RPCs; dependency-density self-test: all checks passed; `PYTHONDONTWRITEBYTECODE=1 python -B -c 'from pathlib import Path; [compile(path.read_bytes(), str(path), "exec") for path in Path(".").rglob("*.py")]'`: passed; `shasum -a 256 -c archive/MANIFEST.sha256`: all 36 entries passed; current-path scan: no obsolete current references; final `find` checks: zero `__pycache__` directories and zero `.pyc` files. Limit: the active digest intentionally excludes mutable saved results and proposal history, while the archive payload is bound separately by its complete manifest.

Residual risks:
- The gates remain offline and do not establish tokenizer context fit, real GPU identity, model quality, or accelerator behavior.
- Python commands run without the documented bytecode-suppression controls can recreate disposable caches.
- The two files under `tests/native/` are script-style probes and are syntax-checked here but are not executed by unittest discovery.

Recommendation: ACCEPT

Packet: No corrective action required. Preserve candidate `f9d27686fc1f2e7ecd0b5f53f53eebadb4f79b2ab63ad57f5ad15f2579583ac2`, `archive/MANIFEST.sha256`, and the cache-safe verification commands as the accepted evidence boundary; the next operational A100 `prepare` step remains separate and human-controlled.

## Revisions

### R1 — 2026-09-08 — restore the decisive layout witness and stable candidate identity
- Verdict: REVISE — the audit found the cache assertion weakened after RED, archived scripts still used by current instructions, concurrent unrelated test changes inside the submitted tree, and no stable manifest-backed identity.
- Changed: `tests/test_repository_layout.py`, `cells/`, `archive/README.md`, `archive/MANIFEST.sha256`, `README.md`, `bench/README.md`, `bench/DEPENDENCY_DENSITY_RUNBOOK.md`, `docs/workload_hypotheses.md`, and Build evidence — restored the exact cache assertion, returned required A100 setup cells to active paths, removed current archived-script invocations, preserved concurrent runtime tests unchanged, added a complete archive hash manifest, and established the same full-tree identity before and after all gates.
- Re-audit: REVISE — archive integrity and current paths passed, but caches from documented checks broke the layout witness, the revised active-cell expectation lacked its own RED, and the submitted full-tree identity included concurrently changing proposal history.

### R2 — 2026-09-08 — make the clean-tree gate self-consistent and concurrency-safe
- Verdict: REVISE — the re-audit required cache-safe current verification commands, R1-specific RED for active staging cells, and an exact identity that excludes concurrently changing proposal/evidence history while binding the archive separately.
- Changed: `README.md`, `bench/README.md`, `docs/workload_hypotheses.md`, and Build evidence — made all current verification commands bytecode-safe, replaced cache-writing `compileall` with in-memory compilation, retained RED for the required A100 setup-cell paths, documented the exact active-scope digest command, and separately verified every archived payload through `archive/MANIFEST.sha256`.
- Re-audit: ACCEPT — all claims proved, scope and duties held, all gates passed, the active-scope digest reproduced before and after gates, and all 36 archive-manifest entries verified.
