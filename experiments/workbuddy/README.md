# Clover on WorkBuddy Bench

This project asks how well the Clover model performs on Tencent's
[WorkBuddy Bench](https://github.com/Tencent/workbuddy-bench), a collection of
realistic work tasks. An agent receives a task and produces files or code; the
benchmark checks its output. A **harness** is the agent software that gives the
model tools and runs its actions. A **verifier** grades the resulting work, and
a **judge** is a model used to grade criteria that need semantic or visual
assessment.

We want two answers: Clover's score under settings comparable to the published
benchmark, and how its score changes with the harness. This folder contains
earlier evidence and plans. Neither comparison has been completed.

## Run Office via API

Set up the [shared model API](../../docs/api-experiments.md#shared-api-setup-for-the-agent-benchmarks).
Use an x86-64 Linux machine or VM with Python 3.12, Bash 4 or newer on
`PATH`, Git, `uv`, `curl`, `sha256sum`, and `fuser`. The CodeBuddy
split mount requires Docker server API 1.48 or newer and Compose 2.35 or
newer. Docker recommends the [containerd image store](https://docs.docker.com/engine/storage/containerd/)
for image mounts. Check the server and client before staging the benchmark:

```sh
bash --version
docker version --format '{{.Server.APIVersion}}'
docker compose version --short
docker info --format '{{.DriverStatus}}'
```

From the root of diffusion-demo, stage the pinned public runner and Office
archive. The archival download runs Tencent's checksum check.

```sh
workbuddy="$PWD/downloads/workbuddy-bench"
git clone https://github.com/Tencent/workbuddy-bench.git "$workbuddy"
git -C "$workbuddy" checkout --detach 625b2233093ae4f23e76be28c1f341d41cc70373
uv sync --project "$workbuddy" --python 3.12 --locked
bash "$workbuddy/scripts/dataset/fetch-dataset.sh" office
git -C "$workbuddy" apply \
  "$PWD/experiments/workbuddy/experiments/qwen36-flash-office-2026-11-19/verifier-transfer.patch"
```

Run the weekly-ticket task. The same command builds the CodeBuddy 2.109.3
harness image if it is missing.

```sh
python -m experiments.workbuddy.run_office "$workbuddy" --run smoke-01 --dry-run
python -m experiments.workbuddy.run_office "$workbuddy" --run smoke-01
find "$workbuddy/results/hosted-office-smoke-01" -name result.json -o -name score.json -o -name reward.json
```

Check the trial for a saved workbook, a native deterministic score, and
the absence of a trial exception. The weekly-ticket rule verifier has 15
checks. A low score is valid if the verifier ran and recorded its outcome.
The dry run resolves the configuration without starting containers or
calling the model. The live launcher exits with an error if a requested
task lacks a verifier reward, or reports zero reward and zero model output
tokens. The upstream launcher can return success in either case. Keep the
results and effective job settings.

Run the WorkBuddy launcher on the Docker host when possible. If the
launcher and Docker run on different machines, the task containers need
both the shared task directory and a route to the job-private proxy.
Set `PROXY_HOST` to the address of that proxy or its relay as seen by
the task container. A local proxy health check alone does not verify that
the container can connect.

The 2026-11-24 live smoke passed 15/15 using GLM 5.3 Flash on OpenRouter
and CodeBuddy 2.109.3. Docker Engine 28.5.2 in the Mac's Linux VM
provided API 1.51. A private bridge relay connected the task to the
launcher’s proxy. The native verifier retained the scored workbook in
`verifier/raw_artifacts/weekly_workbook.xlsx`.

Use `--task TASK_SLUG` to select a different Office task, or `--all` with
a fresh `--run` name for all 50 Office tasks, serially. Use
`--context-window` for routes with a smaller window than the default 110,000
tokens. This run uses one attempt per task, a 48-turn cap, an 8,192-token
request output cap, and no rubric judge. Treat the results as a new
deterministic run. The historical OpenRouter comparison used a saved task
order, no request output cap, and provider-specific proxy settings.

## Start here

1. Read [analysis.md](analysis.md) for what we know and what is missing.
2. Open the [Office workbook example](experiments/full-rollout-2026-11-16/manual-review/office/weekly_workbook.xlsx)
   or the [Web task instruction](experiments/full-rollout-2026-11-16/manual-review/web/instruction.md)
   and its [generated submission](experiments/full-rollout-2026-11-16/manual-review/web/submission/help-center/).
   The copied Web task instruction is available in the local review bundle.
3. Read the planned [official reproduction](experiments/official-reproduction/)
   and [harness comparison](experiments/harness-comparison/) before running anything.

## Experiments

| Folder | Status | Contents |
| --- | --- | --- |
| [Office ten-task screen](experiments/office10-rule-2026-11-16/) | Complete, rules only | Ten per-task scores and run limits. |
| [Office and Web full rollout](experiments/full-rollout-2026-11-16/) | Office rules complete; Web and full judging incomplete at last check | Local review examples and pointers to the Spark artifacts. |
| [Official reproduction](experiments/official-reproduction/) | Planned | Protocol and readiness checks for CodeBuddy Code and Claude Code. |
| [Harness comparison](experiments/harness-comparison/) | Planned | Paired comparison of CodeBuddy, Pi, and a proposed Codex arm. |

[Analysis and demo](analysis.md) explains the available results, protocol gaps,
and a reviewable example. The authoritative running status remains the root
`AGENTS.md`; remote results are not duplicated here. Do not put credentials,
private configuration, or unredacted request headers in this directory.

## Where are the actual runs?

The ten-task score summary and two review examples are local. Most task
environments, logs, full artifacts, and the WorkBuddy runner are on the DGX
Spark at `~/diffusion-demo/runs/workbuddy-smoke/`, not in this folder. The
planned folders currently contain only README files: they are not runnable
configurations or result sets. The last recorded status is dated 2026-11-17;
check the Spark before assuming its jobs are still running or complete.

In the review examples, `result.json` records the task, settings, timing, and
verifier outcome. The Office `judge.yaml` is the saved judge configuration.
For Web, `instruction.md` is the task, `submission/` is the generated work,
`agent.patch` records changes, and the JSON evidence files capture checks or
observations. Copied task assets, test cases, and workspace archives stay
local. Obtain the upstream task materials using the
[reproduction instructions](AGENTS.md).
