# Benchmark harness

Use `diffusion_runtime.py` for diffusion-only verification. It reuses the exact
fixture generator, evaluator, tokenizer, and native session in
`dependency_density_bench.py`. It does not establish an AR comparison.
Use `business_benchmark.py` to prepare and run the frozen 36-case business
screen through that resident worker.

## Durable constraints

- Run `business_benchmark.py prepare` before the first business-screen generation.
  Do not launch if it refuses the fixture manifest, protocol, artifact identities,
  dual-tokenizer counts, output allowance, or context fit. Reuse its immutable
  registration and deterministic request IDs when resuming the same run.
  **Why:** The 2026-09-08 business launch integration showed that path-only or
  re-created registrations can silently change the work or repeat expensive cases.
  **Guarded by:** `tests/bench/test_diffusion_runtime.py::BusinessLaunchContractTest`.
- Treat `run-diffusion` as successful only when its final JSON and durable
  `summary.json` both report `"status":"completed"`, 36 attempts, and
  `"stop_reason":"all_cases_completed"`. Run the controller through the explicit
  repository path; do not depend on the notebook or shell working directory.
  **Why:** The 2026-09-08 launch review found that an early runtime gate returned
  process status zero and relative commands failed outside the repository.
  **Guarded by:** `tests/bench/test_diffusion_runtime.py::BusinessLaunchContractTest`.
- Reproduce every business fixture from its registered problem ID, fixture index,
  and seed. Keep exactly 48 scored string values in the canonical answer envelope,
  and score global assignments by hard constraints and their registered objective,
  not positional equality with one reference solution.
  **Why:** The 2026-09-07 business fixture conversion needs frozen inputs while
  allowing multiple valid schedules, allocations, and seating plans.
  **Guarded by:** `tests/bench/test_business_fixtures.py::BusinessFixtureContractTest`.
- Drain terminal pipes before reporting process exit. On timeout or cancellation,
  return only after native cancellation is acknowledged or the child is reaped.
  **Why:** The 2026-09-07 runs lost native errors and could leave generation alive
  after a timeout.
  **Guarded by:** `tests/bench/test_dependency_density_bench.py::DiffusionSessionLifecycleTest`
  and `tests/bench/test_diffusion_runtime.py::NativeCancellationTests`.
- Keep request IDs immutable and persist terminal results before declaring the
  worker idle. Never silently replay an interrupted request after worker restart.
  **Why:** The 2026-09-07 retained-model experiments needed an unambiguous owner
  and acknowledgment before warm reuse.
  **Guarded by:** `tests/bench/test_diffusion_runtime.py::DurableWorkerTests` and
  `NativeCancellationTests`.
- Preserve reasoning, original exceptions, native stop reasons, and incorrect
  outputs. Admit a case only with its full time allowance; include failed request
  time in cost per correct answer.
  **Why:** The 2026-09-07 short budgets and partial-reasoning failures could not
  answer the intended benchmark question.
  **Guarded by:** `tests/bench/test_diffusion_runtime.py::ResultContractTest` and the existing
  exact-scoring selftest in `dependency_density_bench.py`.
- Do not trim repeated tokens in benchmark mode. Stop at native EOG, explicit
  limits, cancellation, or generation failure.
  **Why:** The native repetition heuristic discarded legitimate repeated values
  on 2026-09-07.
  **Guarded by:** `tests/native/test_native_stopping.py` against the actual patched CLI
  source, including repeated-value and EOG fixtures.
- Use 64-bit element counts and index arithmetic for fused softcap. Verify the
  real backend before attempting long model runs.
  **Why:** At 8,192 positions times vocabulary 262,144, the original launcher
  overflowed signed 32-bit counts. An isolated fix did not prove full-model safety.
  **Guarded by:** `tests/native/test_softcap_boundary.py` against the patched source and
  the numerical `native/softcap_backend_probe.cpp` on CUDA.

## Colab execution

New operators must read the [operator handoff](../docs/operator_handoff.md)
before allocating an A100. It owns the prerequisite inventory and ordered pickup
sequence; this section owns the detailed harness constraints and launch commands.

Always mount Google Drive before setup and reuse the verified format-v4 runner
cache and the model cache used by Cell 3. Do not run
`cells/nvidia/cell_2_runner_setup.py` for the current business screen: it selects
a format-v3 cache and is retained as prior setup provenance, while this workflow
requires the instrumented format-v4 protocol-v2 runner. Do not download a model
or compile a runner until the corresponding cached artifact has been checked and
its metadata and SHA256 have been verified.

**Why:** The 2026-09-08 operator-handoff review found that the active-looking
Cell 2 script creates a format-v3 cache even though the business screen requires
the separately verified format-v4 protocol-v2 artifacts.

**Guarded by:** `tests/test_operator_handoff.py`.

- Model cache: `/content/drive/MyDrive/diffusiongemma-demo/huggingface_cache`.
- The versioned runner cache also owns `dependency-tokenizer`; validate its
  metadata checksum and stage it with the runner.
  The pinned DiffusionGemma snapshot is already present there. Use the Cell 3
  `hf_hub_download(..., cache_dir=MODEL_CACHE)` flow so a cache hit resolves the
  model without another network download.
- Instrumented runner cache:
  `/content/drive/MyDrive/diffusiongemma-demo/diffusion-runner/v4_sm_80_nvcc_12_8_src_daca8075d871_harness_v2`.

For diffusion-only runs, pass `--mirror-dir` under the Drive benchmark-results
tree. Every completed case and the cumulative summary are copied atomically, so
an externally reclaimed VM cannot erase completed measurements.
  Verify `build-info.json`, copy `llama-diffusion-cli` and
  `softcap-backend-probe` to local NVMe, and verify their hashes before use.
- Pinned Linux tokenizer helper:
  `archive/artifact-bundles/bench/results/dependency-density/2026-09-07/evidence/dependency-tokenizer`,
  SHA256
  `4f79ab7b2fe1a1b495e69c343092c03d9c155dc579076e05a0c4bfaf28a76c1a`.
  Reuse this local copy for Colab uploads. The helper records exact prompt and
  output token counts and enforces the configured context bound.
- Keep older runner cache keys intact. A protocol, source, CUDA, architecture, or
  build-format change requires a new key; never overwrite an incompatible runner.

Only when a compatible cache entry is absent should `native/build.py` compile the
pinned checkout. After a successful build and native tests, atomically save the
runner, backend probe, build manifest, and hashes under a new Cell 2-style cache
key before running model cases. Reuse one allocated machine and one resident
worker for all accepted cases in the batch.

```sh
python bench/native/build.py /content/llama.cpp-diffusion
python tests/native/test_native_stopping.py /content/llama.cpp-diffusion/examples/diffusion/diffusion-cli.cpp
CUDA_LAUNCH_BLOCKING=1 /content/llama.cpp-diffusion/build/bin/softcap-backend-probe 8192
python bench/diffusion_runtime.py serve --runner /content/llama.cpp-diffusion/build/bin/llama-diffusion-cli --model "$DIFF_MODEL_PATH" --output-dir /content/worker-v2
python bench/diffusion_runtime.py run --tokenizer /content/dependency-tokenizer --output-dir /content/matched32-v2 --timeout 120 --batch-seconds 600
```

### Business screen launch

After the pinned artifacts have been verified and staged, expose their resolved
paths and the active repository to subprocesses from one Python cell:

```python
import os
repo_path = globals().get("REPO", "/content/drive/MyDrive/diffusiongemma-demo/code")
if not os.path.isfile(os.path.join(repo_path, "bench", "business_benchmark.py")):
    raise FileNotFoundError(f"Active benchmark repository not found: {repo_path}")
os.environ["BENCH_REPO"] = repo_path
os.environ["AR_MODEL_PATH"] = AR_MODEL_PATH
os.environ["DIFF_MODEL_PATH"] = DIFF_MODEL_PATH
os.environ["RUNNER_LOCAL_PATH"] = RUNNER_LOCAL_PATH
os.environ["TOKENIZER_LOCAL_PATH"] = TOKENIZER_LOCAL_PATH
```

Start the protocol-v2 owner. This starts the loopback controller but does not
load the model until the first generation request:

```sh
nohup python "$BENCH_REPO/bench/diffusion_runtime.py" serve \
  --runner "$RUNNER_LOCAL_PATH" \
  --model "$DIFF_MODEL_PATH" \
  --output-dir /content/business-worker-v1 \
  --max-tokens 9216 \
  --context 11264 \
  > /content/business-worker-v1.log 2>&1 &
```

Run the no-generation launch gate. It freezes all 36 cases and their execution
order, retokenizes every prompt and expected answer against both model files,
hashes the staged artifacts, and refuses unsafe context or protocol settings:

```sh
python "$BENCH_REPO/bench/business_benchmark.py" prepare \
  --url http://127.0.0.1:8765 \
  --output-dir /content/business-screen-v1 \
  --mirror-dir /content/drive/MyDrive/diffusiongemma-demo/benchmark-results/business-screen-v1 \
  --tokenizer "$TOKENIZER_LOCAL_PATH" \
  --ar-model "$AR_MODEL_PATH" \
  --ar-context-size 11264 \
  --timeout 300 \
  --batch-seconds 14400
```

Do not continue unless it returns `"status":"launch_ready"` and
`"generation_rpc_calls":0`. The following command is the explicit launch point:

```sh
python "$BENCH_REPO/bench/business_benchmark.py" run-diffusion \
  --url http://127.0.0.1:8765 \
  --output-dir /content/business-screen-v1 \
  --mirror-dir /content/drive/MyDrive/diffusiongemma-demo/benchmark-results/business-screen-v1 \
  --tokenizer "$TOKENIZER_LOCAL_PATH"
```

Rerunning `run-diffusion` with the same registration skips completed rows and
uses the same deterministic request IDs. A changed worker configuration,
controller, model, runner, tokenizer, fixture, or registration is refused. The
controller stops after a runtime error or missing/ambiguous native stop so the
retained worker state can be inspected before resuming. Such a partial run exits
nonzero after persisting `"status":"incomplete"`; incorrect model answers remain
valid benchmark observations and do not by themselves make the command fail.

Run probes at 256, 8191, 8192, 8239, and 11264 in separate processes. They allocate
up to roughly 11 GiB each, so first release the resident model process, keeping the
GPU allocation. Numerical tolerance is explicit: absolute 1e-5 plus relative 1e-5.
The initial absolute-only 1e-4 check failed by about 1.5e-4 below the boundary;
that diagnostic attempt is retained with the Colab evidence.

The worker listens on loopback port 8765. `GET /status`, `POST /generate`,
`POST /cancel`, and `GET /result/<request_id>` expose ownership and terminal state.
Generate accepts `request_id`, `prompt`, and `timeout_seconds`; cancel accepts
`request_id`. A repeated ID with different content is rejected. A timeout first
requests native cancellation, then terminates the child if acknowledgment fails.
The next request can reload a failed process. SIGTERM gracefully closes the
worker's child; the benchmark controller deliberately leaves the worker loaded.

Default output allowance is 9,216 tokens with context 11,264. Native summary traces
record real phase boundaries, per-block commits, native stop reasons, and thought
and final channel transitions observed at block commit, not token-arrival latency.
`--trace-mode diagnostic` additionally retains committed token IDs and step output.
`DIFFUSION_PREFILL_CHUNK` defaults to 2048 in benchmark mode and caps the upstream
causal prefill chunks. Its value is reported in registration. This is an explicit
experimental execution setting, not proof of equivalence for every workload.

The runner prefills incrementally by default: the prefix-KV store persists across
blocks and only new tokens are encoded. `DIFFUSION_INCREMENTAL_PREFILL=0` restores
full re-prefill for A/B checks. With incremental prefill and the KV cache on,
`DIFFUSION_UBATCH` sets `-b` and `-ub` independently of context; use 2048 for
contexts above 11,264. `DIFFUSION_MAX_TIMEOUT` raises the 600-second request cap.
The prefix store is F32 without flash attention, about 450 KB per token, so an
A100 40GB fits 32,768 context but not 65,536.
**Why:** The 2026-09-28 A/B cut wall time 34%, and the decoupled batch removed a
logits buffer that grew with context. An `output_tokens` buffer sized by ubatch
overflowed until it was sized by context.
**Guarded by:** `tests/native/test_incremental_prefill.py` for prefix reuse; the
decoupled-batch path has no automated witness.

Results preserve the raw runner transcript separately from extracted model output.
The batch summary includes failed request time and the measured allocation window,
including warmup, divided by correct answers. It does not include earlier build or
idle allocation time and is not a dollar-cost estimate. Density medians use only
correct final answers. The nine-case screen has three inputs per density and is a
regression screen, not a statistically conclusive model comparison.

If the Python worker itself is abruptly terminated, its in-memory request timing
and transcript cannot be reconstructed unless the native process persisted them
first. Such requests are marked `WorkerInterrupted` and are never replayed.

## Local checks

```sh
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest tests.bench.test_dependency_density_bench tests.bench.test_diffusion_runtime
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest tests.bench.test_business_fixtures
PYTHONDONTWRITEBYTECODE=1 python -B -m bench.business_benchmark self-test --json --output-dir /tmp/business-launch-selftest
PYTHONDONTWRITEBYTECODE=1 python -B bench/dependency_density_bench.py selftest --json
```

The independent lifecycle witness in `tests/bench/test_dependency_density_bench.py` is
protected by the proposal ledger. Do not edit it to make the implementation pass.
