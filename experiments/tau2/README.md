# Tau-bench agent tasks

Runs customer-service tool-use tasks and records the evaluation setup.

## Run

Use the [API setup](../../docs/api-experiments.md), install `uv`, and put
`DIFFUSION_BASE_URL` and `GEMINI_API_KEY` in a shell-compatible
`.env.local`. The runner reads that file and expects the historical
diffusion model route without bearer authentication. It clones upstream
v1.0.1, applies the checked-in Gemini grader patch, and installs the upstream
environment on first use. Start in a checkout without an existing
`downloads/tau2-bench` or verify the existing checkout already has that
version, patch, and environment.

```sh
bash bench/tau2/run_tau2.sh replicate-retail-01 --domain retail --task-split-name test
```

Check the 40 retail trial outcomes and infrastructure errors under
`downloads/tau2-bench/data/simulations/`. This protocol uses one trial and
Gemini in the simulator and grader roles. The saved score combines the
original trial and targeted retries. The [findings](../../docs/tau2_hle_qwen36_findings.md#reproduce)
also document the banking setup and its embedding route.

## Contents

- [tau2](code/tau2): code; stored at `bench/tau2`.
- [tau2-bench](results/tau2-bench): results; stored at `downloads/tau2-bench`.
- [tau2_leaderboard](results/tau2_leaderboard): results; stored at `downloads/tau2_leaderboard`.
- [tau2_hle_qwen36_findings.md](findings/tau2_hle_qwen36_findings.md): findings; stored at `docs/tau2_hle_qwen36_findings.md`.

These links point to the original files, so existing commands and imports continue
to use their documented paths. Some result or download links refer to local,
untracked files and may be absent in another checkout. See the linked findings
or source README for methods, run status, and limitations before interpreting
results. Running model experiments may require the Spark, dependencies, and
credentials; this folder does not itself launch an experiment.
