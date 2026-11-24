# Model runtimes

This directory holds model runtimes, benchmark-specific workload code, and
saved results. The runtime files below run models; workload directories such
as `jepa/`, `terminal_bench/`, and `taxloop/` supply tasks or evaluation code.
`results/` contains saved outputs from multiple experiments. WorkBuddy's local
evidence and comparison plans are in `../experiments/workbuddy/`. For an
experiment-by-experiment guide to scripts, results, and findings, start at
`../experiments/README.md`.

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

## DGX Spark

Sync the checkout and workload inputs to `~/diffusion-demo` on the Spark.
SSH to `jx25520@192.168.3.3` on the LAN or `jx25520@100.67.126.100` over
Tailscale. From the Spark checkout, open a container with the repo and model
cache mounted:

```sh
docker build -t jepa:0.1 -f bench/jepa/Dockerfile bench/jepa
docker run --rm -it --gpus all --ipc=host \
  -v "$PWD":/work -w /work \
  -v "$HOME/.cache/huggingface":/root/.cache/huggingface jepa:0.1 bash
```

Run the commands below inside the container. Store build artifacts under
`runs/` and write result rows to the mounted checkout so they survive exit.

### Models already on the Spark

These paths were checked on 2026-11-13. `~` is `/home/jx25520` on the Spark
host. Mount model directories into the container when using them.

| Model | Spark host path |
| --- | --- |
| Clover-35B-A3B Preview, official Q4_K_M | `~/clover/models/clover-official-q4km/Clover-35B-A3B-Preview-Q4_K_M.gguf` |
| Clover-35B-A3B Preview, Bartowski AR-only Q4_K_M | `~/clover/models/clover-bartowski-q4km/Diffuspace_Clover-35B-A3B-Preview-Q4_K_M.gguf` |
| Nemotron-Labs-Diffusion-3B, base weights | `~/.cache/huggingface/hub/models--nvidia--Nemotron-Labs-Diffusion-3B/snapshots/0d51902da1f8869f83413ce642fab402fa5641e0/model.safetensors` |
| MiniCPM-V 4.7 35B-A3B, Q4_K_M thinking | `~/clover/models/minicpmv47-q4km/thinking/MiniCPM-V-4_7-35B-A3B-Q4_K_M-thinking.gguf` |
| MiniCPM vision projector | `~/clover/models/minicpmv47-q4km/mmproj-model-f16.gguf` |
| MiniCPM DSpark Q8_0 draft | `~/clover/models/minicpmv47-dspark/dspark-MiniCPM-V-4_7-35B-A3B-Q8_0.gguf` |
| Qwen3.6-35B-A3B, Unsloth UD-Q4_K_M | `~/clover/models/qwen36-unsloth-ud-q4km/Qwen3.6-35B-A3B-UD-Q4_K_M.gguf` |
| Qwen3.6-35B-A3B, Unsloth NVFP4 Fast | `~/clover/models/qwen36-unsloth-nvfp4-fast/` (five safetensors shards) |
| Gemma 4 26B-A4B Instruct, Unsloth UD-Q4_K_M | `~/clover/models/gemma4-26b-a4b-ud-q4km/gemma-4-26B-A4B-it-UD-Q4_K_M.gguf` |
| Gemma 4 vision projector, F16 | `~/clover/models/gemma4-26b-a4b-ud-q4km/mmproj-F16.gguf` |

The container command above mounts the Nemotron cache. The Nemotron LoRA
adapters are under `~/diffusion-demo/runs/main/{synth,turk}/` and
`~/diffusion-demo/runs/lbd-pick/`, in each run's `adapter/` directory. The Gemma
files are from Unsloth revision `c099eb48e663fd284577b04978a94ffccb261841`.
DiffusionGemma weights were absent from the checked paths.

## Nemotron on DGX Spark

Nemotron-Labs-Diffusion-3B needs about 7.7 GB in bf16. Write cases as JSONL with
`case_id`, `prompt`, and optional `max_new_tokens`:

```sh
python bench/nemotron_runner.py nemotron --cases cases.jsonl --out rows.jsonl --modes ar,linear_spec,diffusion
python bench/nemotron_runner.py nemotron --cases cases.jsonl --out rows.jsonl --modes diffusion --arm-prefix nemotron-3b-t0.99-b8 --threshold 0.99 --block-length 8
python bench/nemotron_runner.py openrouter --cases cases.jsonl --out endpoint.jsonl --model qwen/qwen3.5-9b --reasoning-off
```

Rows resume by case and arm. Timing uses `torch.cuda.synchronize` around each
call and includes prefill. `nfe` counts forward passes.

## Gemma pair on DGX Spark (deferred)

The Gemma pair still needs a generation smoke test on the Spark. The container
above provides Git, CMake, Make, a C++ compiler, and a CUDA toolkit with GB10
support. Configure with Unix Makefiles because the helper builds reuse CMake's
`link.txt`.

```sh
source_dir=/work/runs/llama.cpp-diffusion
git init "$source_dir"
git -C "$source_dir" fetch --depth=1 https://github.com/ggml-org/llama.cpp.git daca8075d871483545dd85d58ce11970b304b541
git -C "$source_dir" checkout --detach FETCH_HEAD
cmake -G "Unix Makefiles" -S "$source_dir" -B "$source_dir/build" \
  -DGGML_CUDA=ON -DBUILD_SHARED_LIBS=OFF -DLLAMA_CURL=OFF \
  -DCMAKE_CUDA_ARCHITECTURES=121 -DCMAKE_BUILD_TYPE=Release
python bench/native/build.py "$source_dir"
python tests/native/test_native_stopping.py "$source_dir/examples/diffusion/diffusion-cli.cpp"
CUDA_LAUNCH_BLOCKING=1 "$source_dir/build/bin/softcap-backend-probe" 8192
```

Mount the downloaded Gemma 4 directory from the inventory at `/models/gemma4`.
Stage the DiffusionGemma GGUF in the mounted Hugging Face cache:

```sh
ar_model=/models/gemma4/gemma-4-26B-A4B-it-UD-Q4_K_M.gguf
diff_model=$(hf download unsloth/diffusiongemma-26B-A4B-it-GGUF diffusiongemma-26B-A4B-it-Q4_K_M.gguf)
```

Use the built `dependency-tokenizer` with `gemma_runtimes.TokenizerService`
to verify exact counts on a sample prompt and completion. For the AR arm,
install `llama-cpp-python` with CUDA support inside the container and pass
`ar_model` to `gemma_runtimes.load_ar`. Start with one arm at a time and verify
a short generation before running a workload.

```sh
DIFFUSION_UBATCH=2048 python bench/diffusion_runtime.py serve \
  --runner "$source_dir/build/bin/llama-diffusion-cli" --model "$diff_model" \
  --output-dir runs/diffusion-worker --max-tokens 30208 --context 32768
```

`POST /generate` takes `request_id`, `prompt`, and `timeout_seconds`.
`GET /result/<request_id>`, `POST /cancel`, and `GET /status` report terminal
state and ownership. From Python, use `diffusion_runtime.rpc` and
`wait_result`. For AR, `gemma_runtimes.load_ar` and `ar_generate` run one
greedy chat turn from a clean state.
