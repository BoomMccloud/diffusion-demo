# Dependency-Density Benchmark Restart Notes

## Current state

- Latest diagnostic: two diffusion-only eight-record cases with a 9,216-token
  allowance returned before the cap without final answers. The completion gate
  stopped further runs. Instrument the exact native stop branch/token before
  another batch; do not assume another budget increase resolves the problem.
  See [completion diagnostic findings](../docs/diffusion_completion_diagnostic_findings.md).
- The diagnostic allocated no AR runtime, ran no 512-token control, and stayed
  under an 11-minute allocation upper bound. Colab reports no active sessions.

- The 2026-09-07 A100 transport pilot completed 18 rows covering both models in
  all nine cells. Artifact validation passes, including paired inputs/order,
  exact scores, transcript decoding, token counts, and context bounds.
- AR passed 1/9 cases. Diffusion passed 0/9 and consumed every canvas budget
  inside an unclosed thought channel. There are no jointly valid pairs.
- The user requested an early stop rather than a multi-hour experiment. Neither
  the 180-row screen nor the full 360-row matrix was launched. Do not claim a
  dependency-density effect or valid-output latency advantage from this pilot.
- Findings: [`docs/dependency_density_pilot_findings.md`](../docs/dependency_density_pilot_findings.md).
- Results, manifests, validation, and a verified archive of the compiled runner
  and tokenizer helper: `bench/results/dependency-density/2026-09-07/`.
- The archive is local, not a Google Drive cache. No weights are included.
- Colab reports no active sessions after teardown on 2026-09-07.
- Proposal ledger: `docs/proposals/dependency-density-benchmark.md`.
- Protected contract: `tests/bench/test_dependency_density_bench.py`; do not modify it.

## Prerequisites for another run

1. Mount Google Drive first. Always resolve the diffusion model through Cell 3's
   persistent cache at
   `/content/drive/MyDrive/diffusiongemma-demo/huggingface_cache`; do not use a
   fresh `/content/hf-cache` download when the pinned snapshot is present.
2. Restore the instrumented protocol-v2 runner and backend probe from
   `/content/drive/MyDrive/diffusiongemma-demo/diffusion-runner/v4_sm_80_nvcc_12_8_src_daca8075d871_harness_v2`.
   Verify `build-info.json` and both SHA256 values before copying them to local
   NVMe. Compile only if this compatible entry is missing or invalid, then save a
   new versioned cache entry atomically before starting model runs.
   The same cache entry must contain `dependency-tokenizer` and its SHA256 in
   `build-info.json`. Copy it to local NVMe with the runner. Do not upload this
   helper through the Colab file endpoint on every session.
3. Start one resident worker and keep it loaded across the canary and accepted
   follow-on cases. Do not restart the worker or restage the model between cases.
   Pass a Drive-backed `--mirror-dir` to every benchmark run. The controller
   atomically mirrors registration, warmup, each terminal case, the cumulative
   JSONL, and the current summary as soon as they are written locally.

4. Diagnose reasoning-budget exhaustion on a few cases before a larger screen.
   The pinned runner hardcodes its native template and ignores thinking-disable
   settings. Register any new configuration before execution.
5. Use the exact tokenizer helper from the archived pinned build. The installed
   Python runtime cannot load the diffusion architecture even in vocab-only mode.
   Set `DEPENDENCY_BENCH_TOKENIZER_COMMAND` to the helper executable. The helper
   source and rebuild script are in the evidence directory and archive. A durable
   extracted Linux executable is stored locally at
   `bench/results/dependency-density/2026-09-07/evidence/dependency-tokenizer`.
   Its SHA256 is
   `4f79ab7b2fe1a1b495e69c343092c03d9c155dc579076e05a0c4bfaf28a76c1a`.
   Verify that hash, then upload this copy to the Colab VM instead of rebuilding
   or extracting it for every session. If the 66 MB upload returns HTTP 408,
   gzip and split it into smaller chunks, upload the chunks, concatenate them on
   the VM, decompress, and verify the same SHA256 before use.
6. Use `DEPENDENCY_BENCH_MEMORY_STRATEGY=phased` on the 40GB A100. Measured
   separate runtimes exceed device capacity when combined. The frozen phase plan
   preserves the actual model order of every paired case.
7. Set `DIFFUSION_RUNNER_COMMIT` to the actual pinned source identity. Retain
   hashes, exact native prompt counts, full generated output and raw transcripts.
8. Run the standalone file through a real file/module context so `__file__`
   identifies the executed harness. The archived `dependency-run-stage.py`
   demonstrates this and registers the environment explicitly.
9. The setup cell assumes `time` already exists in the notebook namespace.
   Execute `import time` first, or resume the already-running compiler if the
   progress loop raises `NameError`; do not start a second build.
10. The historical commands below need these prerequisites and a fresh
   registration before reuse. They are not a request to launch more compute.

## Historical setup commands

Create a named A100 session:

```bash
colab new -s bench-a100 --gpu A100
colab status -s bench-a100
```

Mount Drive from the attached Colab browser session if the model cache is stored there. The CLI Drive mount is interactive, so do this in the browser before unattended execution:

```bash
colab url -s bench-a100
```

Set the persistent Drive root in the kernel, replacing the path if needed:

```bash
echo "DRIVE_ROOT='/content/drive/MyDrive/diffusiongemma-demo'" | colab exec -s bench-a100 --timeout 120
```

Build or restore the diffusion runner and stage both models. Let the runner build finish completely:

```bash
colab exec -s bench-a100 -f cells/nvidia/cell_2_runner_setup.py --timeout 1800
colab exec -s bench-a100 -f cells/common/cell_3_model_setup.py --timeout 1800
```

Verify runtime paths and hardware without printing credentials:

```bash
echo "print(GPU_NAME, GPU_VRAM_GIB); print(AR_MODEL_PATH); print(DIFF_MODEL_PATH); print(RUNNER_LOCAL_PATH)" | colab exec -s bench-a100 --timeout 120
```

Run the remote offline contract:

```bash
colab exec -s bench-a100 -f bench/dependency_density_bench.py --timeout 120
```

After resolving the 40GB memory strategy and token calibration, configure a one-case-per-cell pilot in the persistent kernel:

```bash
echo "DEPENDENCY_BENCH_MODE='pilot'; DEPENDENCY_BENCH_CASES_PER_CELL=1; DEPENDENCY_BENCH_OUTPUT_DIR=DRIVE_ROOT + '/benchmark-results/dependency-density'" | colab exec -s bench-a100 --timeout 120
colab exec -s bench-a100 -f bench/dependency_density_bench.py --timeout 3600
```

The pilot must produce 18 rows, one result for each model in each of the nine matrix cells. Download or inspect the JSONL and summary before starting the full run.

For the full matrix, use 20 cases per cell only after the pilot passes:

```bash
echo "DEPENDENCY_BENCH_MODE='run'; DEPENDENCY_BENCH_CASES_PER_CELL=20" | colab exec -s bench-a100 --timeout 120
colab exec -s bench-a100 -f bench/dependency_density_bench.py --timeout 21600
```

When all artifacts have been copied to Drive, release the VM:

```bash
colab stop -s bench-a100
```

## Pilot acceptance gate

- Exactly 18 result rows exist, including invalid outputs.
- Every case has one AR row and one diffusion row with the same case and prompt hashes.
- All nine matrix cells are represented for both models.
- Actual prompt and output token counts are present or their absence is explicitly explained.
- Warm wall time uses the same request-to-final-output boundary for both models.
- Diffusion internal compute remains a separate optional field.
- Raw output inspection confirms transport text is not being mistaken for model output.
- No out-of-memory error or context truncation occurred.

Only after this gate passes should the 360-row full matrix run and the proposal proceed to Build evidence and independent Audit.

Latest stop-repair evidence: see [findings](../docs/diffusion_stop_repair_findings.md). Repetition trimming falsely cuts valid output in the pinned runner. The isolated cached diagnostic build supports `DIFFUSION_ALLOW_REPETITION=1`, preserving EOG. Direct16/32/64 and mixed64 final answers passed exact scoring; long chained64 hit a CUDA softcap runtime error. Keep original exception, native stop state, and any reduced time allowance separate. GPU session retention is currently explicit user intent; do not infer teardown from a finished driver.
