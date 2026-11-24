# Run experiments through model APIs

Run these commands from the repository root. You need Python 3.11 or newer,
Git, and access to the model routes used by your chosen experiment. The
hosted APIs do the inference. Browser and agent benchmarks may also need
local task environments.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install openai numpy
```

Sudoku and Addition in Words use the Python standard library. Install extra
dependencies only where the experiment guide calls for them. Record the
Python version and `python -m pip freeze` for each new run.

## Configure the routes

Export the settings for your chosen runner or put them in your own
Git-ignored `.env.local`. If you use a shell-compatible `.env.local`,
load it before running commands:

```sh
set -a
. ./.env.local
set +a
```

| Setting | Where it is used |
| --- | --- |
| `DIFFUSION_BASE_URL` | Authorized hosted diffusion API base ending in `/v1`, or its full `/v1/chat/completions` URL. Many historical runners expect the served model ID `qwen36-iter22000-blk16-arverify-best`. Throughput accepts `--model`. |
| `DIFFUSION_API_KEY` | Optional bearer key for Throughput, Addition in Words, MiniWoB's diffusion arm, and the shared client used by Synthetic Data, TabDLM, Taxloop, and Test Data. |
| `OPENROUTER_API_KEY` | Qwen comparison arm for Synthetic Data, TabDLM, Taxloop, Sudoku, and Test Data. Also used by the WorkBuddy OpenRouter probe. |
| `GEMINI_API_KEY` | Synthetic Data judging and embeddings, TabDLM judging, HLE judging, and Tau-bench's Gemini roles. |
| `DLLM_URL` | Sudoku's complete diffusion chat-completions URL. Its diffusion route also needs `/v1/models`. |
| `MINIWOB_DIFFUSION_URL`, `MINIWOB_DIFFUSION_MODEL`, `DASHSCOPE_API_KEY` | MiniWoB's diffusion route, optional explicit diffusion model ID, and Qwen comparison key. |

Use your own authorized routes and verify their model IDs, availability, and
quota with the smallest smoke. Record any model, route, judge, or sampling
changes when comparing with saved results.

## Shared API setup for the agent benchmarks

WebArena, Terminal-Bench, and WorkBuddy Office can share the same
OpenAI-compatible Chat Completions endpoint. Put these settings in
`.env.local` or export them in your shell. Set the URL to the provider's
API base, usually ending in `/v1`. Use `none` as the key only for an
endpoint that accepts unauthenticated requests.

```sh
BENCH_API_BASE_URL='https://your-provider.example/v1'
BENCH_API_MODEL='your-served-model-id'
BENCH_API_KEY='your-api-key'
```

Load the settings as shown above. From the repo root, run:

```sh
python -m bench.api_preflight
```

This issues two small requests and checks a native tool call followed by a
streamed reply containing the tool's result. Then run one scored task in
each harness before starting a larger batch:

1. [WebArena](../experiments/webarena/README.md#run) uses a dedicated set of
   WebArena fixture sites and the Python browser harness.
2. [Terminal-Bench](../experiments/terminal-bench/README.md#run) uses Harbor,
   Pi, and Docker on the machine running the benchmark.
3. [WorkBuddy Office](../experiments/workbuddy/README.md#run-office-via-api)
   uses the pinned Tencent runner, CodeBuddy, and Docker.

For a WebArena smoke, check the forum snapshot and disk space before
downloading fixtures. WorkBuddy also needs a Docker server that supports
image mounts and a task-container route to its job-private proxy. The
individual guides show how to verify these dependencies.

On 2026-11-24, GLM 5.3 Flash through OpenRouter passed the shared API probe.
The single-task Terminal-Bench run returned native reward 0.0 and
WorkBuddy Office passed 15/15. Both ran from a local Mac Linux VM.
WebArena passed a live API-to-browser diagnostic on a toy page. Its
benchmark task still needs a reachable official forum fixture.

## Start with one smoke

| Experiment | Guide |
| --- | --- |
| Hosted streaming throughput | [One request, then a concurrency sweep](../experiments/throughput/README.md) |
| Addition in words | [Input checksum, smoke, and deterministic scoring](../experiments/addition-in-words/README.md#reproduction) |
| Sudoku | [One bundled puzzle on each model and a local score](../experiments/sudoku/README.md#run) |
| Medical record editing | [An editing smoke with built-in fixtures and local scoring](../experiments/medical-fill/README.md#run) |
| Synthetic medical data | [Small generation, judging, and scoring grid](../bench/synthdata/README.md#run) |
| TabDLM | [One request per cell and model](../bench/tabdlm/README.md#run) |
| Taxloop | [Offline preview and a scored API smoke](../experiments/taxloop/README.md#run) |
| Synthetic people and customer data | [Generate a few batches and summarize the saved outputs](../experiments/testdata/README.md#run) |
| MiniWoB | [Pinned browser fixtures and one seeded task](../bench/miniwob/README.md#running) |
| Decision Index | [Build the inputs and smoke the SystemOne API](../experiments/decision-index/README.md#run) |
| HLE and Tau-bench | [HLE dataset and judge setup](../experiments/hle/README.md#run) and [Tau-bench setup](../experiments/tau2/README.md#run) |
| WorkBuddy Office | [Pinned setup, weekly-ticket smoke, and 50-task run](../experiments/workbuddy/README.md#run-office-via-api) |

[WindTunnel](../experiments/windtunnel/README.md) has separate pinned
upstream checkout and patch instructions.

Use a fresh run name or output path for each independent run. Keep the exact
command, Git revision, task selection, model and provider IDs, settings, and
raw and scored outputs together. Check row counts and errors before comparing
scores. Some runners write errors to JSONL and still exit successfully.
Historical outputs linked by the experiment index may live outside Git.
