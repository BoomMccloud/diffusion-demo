# Model runtimes

This directory holds the code that runs each model. It contains no workload.
A workload supplies prompts and scores outputs.

- `gemma_runtimes.py`: Gemma 4 26B A4B AR through `llama-cpp-python`
  (`load_ar`, `ar_generate`, `ar_token_counter`), and the DiffusionGemma native
  session (`DiffusionSession`), tokenizer helper (`TokenizerService`), transcript
  parsing, artifact hashing, and GPU identity.
- `diffusion_runtime.py`: one resident DiffusionGemma process behind a loopback
  API, so a controller never competes for its pipes.
- `nemotron_runner.py`: Nemotron-Labs-Diffusion in `ar`, `linear_spec`, and
  `diffusion` modes on one GPU, plus an OpenRouter AR arm.
- `native/`: applies the benchmark patch to the pinned `llama.cpp` checkout,
  builds `llama-diffusion-cli`, and probes the CUDA softcap kernel.

## Runner constraints

- Drain terminal pipes before reporting process exit. On timeout or cancellation,
  return only after native cancellation is acknowledged or the child is reaped.
  **Why:** The 2026-09-07 runs lost native errors and could leave generation alive
  after a timeout.
  **Guarded by:** `tests/bench/test_runtimes.py::DiffusionSessionLifecycleTest`
  and `NativeCancellationTests`.
- Keep request IDs immutable and persist terminal results before declaring the
  worker idle. Never silently replay an interrupted request after worker restart.
  **Why:** Retained-model experiments on 2026-09-07 needed an unambiguous owner
  and acknowledgment before warm reuse.
  **Guarded by:** `tests/bench/test_runtimes.py::DurableWorkerTests`.
- Preserve reasoning, original exceptions, native stop reasons, and incorrect
  outputs in every row. Include failed request time in any cost per correct
  answer.
- Do not trim repeated tokens. Stop at native EOG, explicit limits,
  cancellation, or generation failure.
  **Why:** The native repetition heuristic discarded legitimate repeated values
  on 2026-09-07.
  **Guarded by:** `tests/native/test_native_stopping.py` against the patched CLI
  source.
- Use 64-bit element counts and index arithmetic for fused softcap, and verify
  the real backend before long runs.
  **Why:** At 8,192 positions times vocabulary 262,144, the original launcher
  overflowed signed 32-bit counts.
  **Guarded by:** `tests/native/test_softcap_boundary.py` and
  `native/softcap_backend_probe.cpp` on CUDA.
- The runner prefills incrementally by default: the prefix-KV store persists
  across blocks and only new tokens are encoded. `DIFFUSION_INCREMENTAL_PREFILL=0`
  restores full re-prefill for A/B checks. With incremental prefill,
  `DIFFUSION_UBATCH` sets `-b` and `-ub` independently of context; use 2048 above
  11,264 context. The prefix store is F32 without flash attention, about 450 KB
  per token, so an A100 40GB fits 32,768 context but not 65,536.
  `DIFFUSION_MAX_TIMEOUT` raises the 600-second request cap.
  **Why:** The 2026-09-28 A/B cut wall time 34%, and the decoupled batch removed
  a logits buffer that grew with context.
  **Guarded by:** `tests/native/test_incremental_prefill.py` for prefix reuse; the
  decoupled-batch path has no automated witness.
- A diffusion allowance must be a multiple of the 256-token canvas. The runner
  rounds up to the next canvas boundary, which broke a context-fit proof on
  2026-09-08 (`docs/business_diffusion_partial_screen_findings.md`).

## Gemma pair on Colab A100

1. Mount Google Drive first. Resolve both GGUF files through
   `cells/common/cell_3_model_setup.py`, which uses the persistent cache at
   `/content/drive/MyDrive/diffusiongemma-demo/huggingface_cache`.
2. Restore the protocol-v2 runner from
   `/content/drive/MyDrive/diffusiongemma-demo/diffusion-runner/v4_sm_80_nvcc_12_8_src_daca8075d871_harness_v2`.
   Check `build-info.json` (format 4, protocol 2, source commit
   `daca8075d871483545dd85d58ce11970b304b541`) and the SHA256 of
   `llama-diffusion-cli` and `softcap-backend-probe`, then copy them to local NVMe.
   Do not use `cells/nvidia/cell_2_runner_setup.py`; it builds the older
   format-v3 runner.
3. Stage the tokenizer helper `dependency-tokenizer` from the same cache, or the
   local fallback under `archive/artifact-bundles/`, SHA256
   `4f79ab7b2fe1a1b495e69c343092c03d9c155dc579076e05a0c4bfaf28a76c1a`. The
   installed Python runtime cannot load the diffusion vocabulary, so this helper
   is the only exact diffusion token count.
4. Compile only if the cache entry is missing or invalid, then save a new
   versioned cache key. Never overwrite an incompatible runner.

```sh
python bench/native/build.py /content/llama.cpp-diffusion
python tests/native/test_native_stopping.py /content/llama.cpp-diffusion/examples/diffusion/diffusion-cli.cpp
CUDA_LAUNCH_BLOCKING=1 /content/llama.cpp-diffusion/build/bin/softcap-backend-probe 8192
```

Start the worker. It loads the model on the first request:

```sh
DIFFUSION_UBATCH=2048 nohup python bench/diffusion_runtime.py serve \
  --runner "$RUNNER_LOCAL_PATH" --model "$DIFF_MODEL_PATH" \
  --output-dir /content/diffusion-worker --max-tokens 30208 --context 32768 \
  > /content/diffusion-worker.log 2>&1 &
```

`POST /generate` takes `request_id`, `prompt`, and `timeout_seconds`.
`GET /result/<request_id>`, `POST /cancel`, and `GET /status` report terminal
state and ownership. From Python, use `diffusion_runtime.rpc` and
`wait_result`. For AR, `gemma_runtimes.load_ar` and `ar_generate` run one
greedy chat turn from a clean state. The two runtimes do not fit together on a
40GB A100, so run them in phases.

## Nemotron on Colab L4

Nemotron-Labs-Diffusion-3B needs about 7.7 GB in bf16. Write cases as JSONL with
`case_id`, `prompt`, and optional `max_new_tokens`:

```sh
python bench/nemotron_runner.py nemotron --cases cases.jsonl --out rows.jsonl --modes ar,linear_spec,diffusion
python bench/nemotron_runner.py nemotron --cases cases.jsonl --out rows.jsonl --modes diffusion --arm-prefix nemotron-3b-t0.99-b8 --threshold 0.99 --block-length 8
python bench/nemotron_runner.py openrouter --cases cases.jsonl --out endpoint.jsonl --model qwen/qwen3.5-9b --reasoning-off
```

Rows resume by case and arm. Timing uses `torch.cuda.synchronize` around each
call and includes prefill. `nfe` counts forward passes.
