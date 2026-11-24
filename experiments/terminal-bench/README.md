# Terminal-Bench agent comparison

Evaluates Clover and MiniCPM on shell-based tasks and examines loops, context compaction, and agent harnesses.

## Run

Set up the [shared model API](../../docs/api-experiments.md#shared-api-setup-for-the-agent-benchmarks).
Use `uv` and a running Docker Engine with Compose. Start on an x86-64
Linux host or VM so Docker can use the published Linux task and verifier
images. Harbor installs Pi inside the trial container.

```sh
uv tool install --python 3.12 'harbor==0.26.0'
docker info --format '{{.OSType}} {{.Architecture}}'
docker compose version
```

Use the same pinned [Terminal-Bench registry dataset](https://hub.harborframework.com/datasets/terminal-bench/terminal-bench/5)
and the graph-isomorphism task from the historical pilot. From the repo root:

```sh
dataset='terminal-bench/terminal-bench@sha256:5881c1b1c74a96f07baef00a7c869e09802704bc0dc912c870e7acccc11440da'
run="$(mktemp -d)"
harbor run --dataset "$dataset" --include-task-name terminal-bench/vf2-speedup-networkx \
  --agent pi --agent-kwarg version=0.85.1 --agent-kwarg max_turns=48 \
  --model "openai/$BENCH_API_MODEL" --base-url "$BENCH_API_BASE_URL" \
  --api-key-name BENCH_API_KEY --api-format openai_chat_completions \
  --n-concurrent 1 --jobs-dir "$run" --job-name api-smoke
```

Use the API base without `/chat/completions` in the Harbor command.
Append `--print-config` to preview the resolved configuration before
starting Docker. After the run, inspect `$run/api-smoke/result.json`
and each trial's `result.json`. A graded trial has a verifier reward and
no trial exception. Keep the trajectory and verifier logs from the trial
directory.

The 2026-11-24 live smoke used the local Mac's Linux VM and GLM 5.3 Flash
through OpenRouter. Harbor and Pi completed one rollout in 4m 48s. The
native verifier returned reward 0.0 with no trial exception. The VM ran
the published amd64 task and verifier images under emulation. Use native
x86-64 for speed comparisons.

To repeat the three-task pilot, add separate `--include-task-name` flags
for `terminal-bench/music-harmony` and
`terminal-bench/layout-config-recreation`, then choose a fresh job name.
This path uses stock Pi with a 48-turn setup cap. The saved pilot used a
Clover-specific relay, custom compaction settings, and a different budget.

## Contents

- [terminal_bench](code/terminal_bench): code; stored at `bench/terminal_bench`.
- [clover-terminal-bench-4.1-pilot](results/clover-terminal-bench-4.1-pilot): results; stored at `bench/results/clover-terminal-bench-4.1-pilot`.
- [clover-terminal-bench-4.1-compaction](results/clover-terminal-bench-4.1-compaction): results; stored at `bench/results/clover-terminal-bench-4.1-compaction`.
- [clover-terminal-bench-4.1-pi](results/clover-terminal-bench-4.1-pi): results; stored at `bench/results/clover-terminal-bench-4.1-pi`.
- [clover-terminal-bench-4.1-pi-arm](results/clover-terminal-bench-4.1-pi-arm): results; stored at `bench/results/clover-terminal-bench-4.1-pi-arm`.
- [clover-terminal-bench-4.1-pi-32k](results/clover-terminal-bench-4.1-pi-32k): results; stored at `bench/results/clover-terminal-bench-4.1-pi-32k`.
- [minicpm-terminal-bench-4.1-pi-32k](results/minicpm-terminal-bench-4.1-pi-32k): results; stored at `bench/results/minicpm-terminal-bench-4.1-pi-32k`.

These links point to the original files, so existing commands and imports continue
to use their documented paths. Some result or download links refer to local,
untracked files and may be absent in another checkout. See the linked findings
or source README for methods, run status, and limitations before interpreting
results. Running model experiments may require the Spark, dependencies, and
credentials; this folder does not itself launch an experiment.
