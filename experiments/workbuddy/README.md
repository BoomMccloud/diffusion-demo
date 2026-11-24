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

## Start here

1. Read [analysis.md](analysis.md) for what we know and what is missing.
2. Open the [Office workbook example](experiments/full-rollout-2026-11-16/manual-review/office/weekly_workbook.xlsx)
   or the [Web task instruction](experiments/full-rollout-2026-11-16/manual-review/web/instruction.md)
   and its [generated submission](experiments/full-rollout-2026-11-16/manual-review/web/submission/help-center/).
   These are saved outputs, not an interactive demo.
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
observations. `public-assets/` and `www/_dataset_assets/` hold task inputs;
the `.tar.gz` files are archived workspace and source assets. Open the files
directly to inspect them; their presence alone does not mean the task passed.
