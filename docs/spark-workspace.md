# DGX Spark workspace

Use `/home/jx25520/clover/` as the entry point on the Spark. This guide is
installed there as `README.md`. All paths in the table are relative to that
directory.

| What you are saving | Directory | Examples |
|---|---|---|
| Reusable model weights | `models/<model>/<revision>/` | Original checkpoint, tokenizer, quantized GGUFs and reusable adapters. Existing model folders keep their names. |
| Runtime implementation | `dllm-inhouse/<revision>/` | Source, compiled binaries and libraries, runtime patches, conversion and build logs. |
| Direct model and decoder experiments | `benchmarks/inference/<suite>/` | AR versus self-speculation, verifier settings, throughput, accuracy, repetition and model comparisons. |
| Application or agent experiments | `benchmarks/applications/<app-or-suite>/` | WorkBuddy Office/Web, Pi on Terminal-Bench and WPS Office pilots, across all models. |

## Where to find existing work

- **Clover Preview weights:** `models/clover-preview-35b-a3b/4b0402b/checkpoint/`
  is the native BF16 checkpoint for training and conversion. Its sibling
  `gguf/` holds `clover-public-bf16.gguf`, `clover-public-Q4_K_M.gguf`
  and `clover-Q4_0.gguf`. The last two are the tested inference weights.
  AR and self-speculation can load the same model file.
- **Other models:** the existing Clover, MiniCPM, Qwen and Gemma folders and
  the Dark-Craving, Dark-Scarlett, Omega-Arsenal, Vesper and Wicked-Tutu
  weights are all under `models/`. The older Clover official and Bartowski
  quantizations are distinct from the in-house Preview conversion.
- **Runtime builds:** `dllm-inhouse/4257d3dd/build/bin/` holds the original
  CUDA build. `dllm-inhouse/pr4-6a3f36ed/` holds the upstream PR build,
  tuned and fused builds, source and patches. Preserve the matching libraries
  when selecting a binary.
- **Decoder evidence:** `benchmarks/inference/dllm-inhouse/4257d3dd/` holds
  the original panels and ferry replays. The PR results are under
  `benchmarks/inference/dllm-inhouse/pr4-6a3f36ed/`, including
  `larger-pr4-20261120/`. Other inference suites include
  `model-comparisons/{runner,results,logs}/` and `jepa/{runner,runs}/`.
- **Application evidence:** WorkBuddy keeps its upstream checkout, datasets,
  configs and results together at `benchmarks/applications/workbuddy/workspace/`,
  with the Qwen batch and recovery scripts in the adjacent `runners/`.
  Terminal-Bench has `runner/` and `results/`. Spark-side WPS weekly ticket
  outputs and trajectories are under `benchmarks/applications/wps-office/weekly-ticket/`.
  Mac recordings and the wider WPS pilot remain in the diffusion-demo repo.

## Adding a run

For new results use `benchmarks/{inference,applications}/<suite>/<date>-<run-name>/`.
Keep compared models under the same task or suite. Record the model revision
and quantization, runtime commit, decoder or harness settings, prompts or
dataset version, scoring method, outputs and timings. For speed comparisons,
record output-token counts and distinguish decode time from end-to-end time.
Use the same model path across runs and give any newly trained weights their
own version. Keep serving credentials outside model and benchmark artifacts.

## Docker and historical paths

Use the canonical host directories above as Docker bind sources. Mount
the required model and binaries read-only, and the run output separately
with write access. For example, the original runtime can mount
`$HOME/clover/dllm-inhouse/4257d3dd/build/bin` at `/runtime` and
`$HOME/clover/models/clover-preview-35b-a3b/4b0402b/gguf` at `/models`.
Mount a selected directory directly when it is a symlink. A container that
mounts only the workspace root may be unable to follow an outward link.

Historical launchers and stopped containers still use `~/diffusion-demo/`,
including the original `runs/dllm-inhouse-4257d3dd/` bind at `/work`.
Versioned runtime and benchmark directories have write-through aliases so
old and new callers see the same files inside the existing mount boundaries.
Legacy weight filenames and the published model files are hard links to the
same data on disk. Treat archived model versions as immutable; replacing a
file by rename affects only that name. Put new conversions in a new version
directory. Preserve the legacy paths while old container definitions and
archived runners depend on them. The BF16 conversion intermediate is retained.
