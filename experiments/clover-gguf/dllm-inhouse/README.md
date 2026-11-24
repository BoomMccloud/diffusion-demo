# Clover on dllm.cpp-inhouse, DGX Spark workspace

This workspace builds DiffuSpace's native Clover runtime, converts the public
Clover checkpoint into a compatible GGUF, and compares autoregressive (AR)
generation with native self-speculative generation. It also investigates
repeated reasoning and answer text. These are exploratory single-attempt
experiments, not benchmark scores or a production deployment.

This file is also installed as `README.md` in the Spark workspace below.
Update both copies when changing the instructions.

## Locations and access

- Spark SSH: `jx25520@192.168.3.3` on LAN; `jx25520@100.67.126.100`
  over Tailscale.
- Canonical Spark workspace: `/home/jx25520/clover/`. Read its `README.md` for the shared storage layout. Runtime builds are in `dllm-inhouse/`, Preview weights in `models/clover-preview-35b-a3b/4b0402b/`, and decoder results in `benchmarks/inference/dllm-inhouse/`.
- Historical Spark workspace used by the commands below: `/home/jx25520/diffusion-demo/runs/dllm-inhouse-4257d3dd/`.
- Local panel runner: `bench/clover_gguf/self_spec_panel/run.py` in the
  diffusion-demo repository.
- Repository status and findings: `AGENTS.md`, beginning of Current work.

The weights and full experiment outputs live on the Spark. They are not
included in the local repository. Use Docker for builds, conversion, downloads,
Python, and inference on the Spark. Do not install dependencies on the host.
Check memory and existing containers before loading another model. Ask the
session owner before stopping any loaded model container.

## Workspace contents

| Path | Contents |
| --- | --- |
| `source/` | Source snapshot of `https://github.com/DiffuSpace/dllm.cpp-inhouse.git`, commit `4257d3dd6de5bbe4db1c8d9b45038009593b1bb3`. This transferred snapshot has no `.git` directory. |
| `build/bin/` | CUDA-enabled `llama-server`, `llama-quantize`, and required shared libraries. |
| `checkpoint/` | Public `Diffuspace/Clover-35B-A3B-Preview` checkpoint, revision `4b0402b`, including tokenizer and configuration files. |
| `clover-public-bf16.gguf` | Converter output, approximately 65 GiB, 853 tensors. |
| `clover-public-Q4_K_M.gguf` | Quantized output, approximately 19.7 GiB, used by all servers below. |
| `convert.log`, `quantize.log` | Conversion and quantization evidence. |
| `long-tps-comparison.json` | Two 2048-token-cap prose prompts per decoding mode. |
| `long-128k-self.json`, `long-128k-ar.json` | Full outputs and timings for the 128000-output-token-limit manual experiment. |
| `varied-long-comparison.json`, `varied-long-prose-comparison.json` | Long varied prompts, full answers, settings and timings. |
| `varied-64k-thinking-comparison.json` | Two prompts, both modes, thinking on/off, 65536 output-token cap; preserves reasoning and answers. |
| `loop-control-diagnostics.json` | AR thinking budget, penalties and combined controls; also records self-spec rejecting a thinking budget. |
| `loop-control-coding-16k.json` | Longer AR coding replay with a thinking budget. |
| `loop-control-sampling.json` | AR temperature 0.6 plus a thinking budget. |
| `model-card-penalties-comparison.json` | Matching penalty values on both endpoints, including HTTP rejection evidence for self-spec. |
| `task_panel.py` | Spark copy of the local panel runner. |
| `task-panel-20261120/manifest.json` | Twelve task definitions, expected structured results and run settings. |
| `task-panel-20261120/*.json` | One saved result per completed trial, with reasoning, answer, timings and assessments. |
| `task-panel-20261120/queue.jsonl` | Append-only completion summaries. Expected total: 48. |

Earlier short arithmetic and 512-token throughput probes were recorded in
the chat and AGENTS.md; not every early request has a standalone JSON file.
The historical incompatible official GGUF remains separately under
`/home/jx25520/clover/models/clover-official-q4km/`.

## Servers

All four model containers use the same converted Q4_K_M and source build.
Published ports bind only to Spark loopback, with OpenAI-compatible endpoints
under `/v1`. The two 128k-context servers are used by the task panel.

| Container | Port | Context | Mode |
| --- | --- | --- | --- |
| `dllm-clover-self-4257` | 18080 | 4096 | `--spec-type self` |
| `dllm-clover-ar-4257` | 18081 | 4096 | AR, one slot |
| `dllm-clover-self-128k` | 18082 | 131072 | `--spec-type self` |
| `dllm-clover-ar-128k` | 18083 | 131072 | AR, one slot |

The existing image is `clover-llamacpp:pr31306`; it supplies the environment,
but the executable comes from this workspace's `build/bin/`, not the image's
older build. Set `LD_LIBRARY_PATH` to the mounted `build/bin/` plus CUDA and
system libraries. The embedded web UI was unavailable during build; the API
works. These container names are not restart-managed services.

For laptop access, forward only the ports needed:

```sh
ssh -N -L 18082:127.0.0.1:18082 -L 18083:127.0.0.1:18083 jx25520@192.168.3.3
```

Then call `http://127.0.0.1:18082/v1/chat/completions` for self-spec or port
18083 for AR. Use model name `clover`. A basic request body is:

```json
{"model":"clover","messages":[{"role":"user","content":"What is 17 times 23?"}],"temperature":0,"max_tokens":256,"chat_template_kwargs":{"enable_thinking":false}}
```

## Reproducing conversion

Run these commands **inside a container**, with this workspace mounted at
`/work`. The existing `jepa:0.1` image supplied conversion dependencies.
Conversion used lazy loading, two CPU cores and a 10 GiB memory cap.

```sh
cd /work/source
PYTHONPATH=/work/source/gguf-py python3 convert_hf_to_gguf.py /work/checkpoint \
  --outfile /work/clover-public-bf16.gguf --outtype bf16
/work/build/bin/llama-quantize /work/clover-public-bf16.gguf \
  /work/clover-public-Q4_K_M.gguf Q4_K_M 2
```

CUDA build settings were Release, `GGML_CUDA=ON`,
`CMAKE_CUDA_ARCHITECTURES=121` (resolved to 121a), `LLAMA_CURL=OFF`,
and two build jobs. NVIDIA driver libraries were required during linking.
Do not overwrite the existing artifacts while they are being used by servers.

The official prebuilt Clover GGUF did not load in this build. Metadata
overrides passed the first missing-key error but exposed a tensor inventory
mismatch. The public BF16 weights converted by this repository did load.

## Task panel and progress

The panel uses twelve task instances across arithmetic, extraction, code edits,
explanations, fiction and simulated tool calls. Each runs once per mode with
thinking off and on: 48 requests. Requests are sequential and mode order
alternates. Settings: temperature 0, seed 42, 65536 output cap, 131072 context,
no repetition penalties and no thinking budget.

The runner saves each completed trial before advancing. It stops on
infrastructure errors, and on restart skips files already saved. Inspect any
saved error before resuming. Do not start a second runner against the same
directory. Current runner container: `dllm-task-panel-20261120`.

```sh
docker logs --tail 10 dllm-task-panel-20261120
docker inspect dllm-task-panel-20261120 --format '{{.State.Status}} {{.State.ExitCode}}'
```

At the README's creation, 34 of 48 results were saved and the panel was still
running. Read `queue.jsonl` and container status for the latest state.

## Interpreting results

- TPS is the server's output-token count divided by generation time; it may
  include reasoning. Prefill and total request time are separate fields.
- A 65536-token cap does not force a response to generate that many tokens.
- Repetition is measured separately in reasoning and answer: repeated
  12-word windows after their first appearance. This is a diagnostic metric,
  not a validated quality score; code and prose can legitimately reuse text.
- JSON tasks use parsed exact comparison. Code edits compare Python ASTs,
  accepting formatting differences but not every equivalent implementation.
  Prose has no automatic correctness score.
- Some speculative loops produce exceptionally high TPS because the output
  is highly predictable. Do not report those as useful-output speedups.
- Self-spec currently rejects penalties, DRY, nonzero temperature and thinking
  budgets. The model card's gradual ending biases are not implemented here;
  matching penalty numbers on AR is not full reference-runtime equivalence.
- Text differs between modes even with these settings. Model, quantization
  and runtime causes have not been isolated. A larger context was not shown
  to fix repetition.
