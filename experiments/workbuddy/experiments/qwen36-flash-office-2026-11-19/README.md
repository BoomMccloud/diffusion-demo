# Qwen3.6-Flash WorkBuddy Office serial run

Requested comparison: reproduce the 50-task Clover serial Office rollout with
Qwen3.6-Flash, using the same task names, CodeBuddy 2.109.3, one attempt per
task, 48-turn cap, 110,000-token harness context, 131,072-token route context,
serial execution, temperature zero, thinking and reasoning passback, published
timeouts, no explicit completion-token cap, and deterministic checks. The
model and provider differ. The provider has its own output and context limits.
Rubric judging is deferred during rollout, as in the Clover run; a combined
comparison requires matching the deferred evaluation and documenting any
remaining differences.

The Spark container is `workbuddy-qwen36-flash-office-20261119`. Its runner
uses the saved Clover task list, records checkpoints in
`~/diffusion-demo/runs/workbuddy-smoke/results/qwen36-flash-office-serial/queue.jsonl`,
and writes individual jobs under `results/qwen36-flash-office-*`. Rate-limit
retries stop after three attempts for a task, unlike the original Clover
runner's indefinite retry. Credentials were supplied in a private temporary
memory-backed file, consumed and deleted during bootstrap, never stored here.

Startup check: the Qwen route loaded and an Office task container reached its
health endpoint. The first task received three HTTP 200 model responses and
continued making requests. The first task's verification and final benchmark
results are pending; requests have taken several minutes each.

Status at 2026-11-19 08:58 UTC: the queue was running only Office v1.0
tasks. The first three completed rollouts produced rule-verifier judge errors:
the deterministic tests ran, but the rule runner did not collect their score
JSON. The resulting zero rewards are not valid task scores. Investigation
and recovery of the deterministic results are needed.

The root cause is the Harbor rule runner reading host-side score files before
downloading `/logs/verifier` from the Docker task container. The Spark checkout
was patched with a fallback to download the directory after rule execution and
before reading the payload. The initial base-class patch did not affect the
Harbor subclass and a live task still failed; the corrected subclass fallback
passed a focused simulated test and then produced valid live scores. As of
2026-11-19 10:20 UTC, 20 tasks had completed: the first 11 had judge errors
and tasks 12 through 20 had deterministic scores. Task 12 scored 17/127.
`verifier-transfer.patch` preserves the corrected change.
The initial eleven trial workspaces were not archived and their containers were
removed. Only channel-period comparison has an untruncated verifier log, which
records 22/22 checks; see `recovery/channel-period-compare.json`. The other
early logs are truncated and cannot establish their full scores.

Final rollout status: all 50 tasks completed and the runner exited 0 by
2026-11-19 12:28 UTC. The fixed verifier collected 39 scores, with a 70.80%
equal-weight mean over those 39 tasks. One of the 11 prior errors was recovered
as 22/22; the remaining ten have no reliable deterministic scores. Rubric
judging remains deferred. The 39-task mean is not the 50-task benchmark score.

Started the ten missing-score replacements in Spark container
`workbuddy-qwen36-office-recovery-20261119`, using the original model and
harness settings and stopping if verification fails. The first task received
HTTP 200. Checkpoints: `results/qwen36-flash-office-recovery/queue.jsonl` in
the Spark checkout. Original results remain unchanged. `rerun/queue.py` and
`rerun/compile_comparison.py` identify replacements and compile a 50-task
deterministic comparison once all ten scores are available; rubric judging is
separate.

The ten replacements completed successfully on 2026-11-19, with valid scores
on all ten. The 50-task deterministic means are Clover 74.44% and
Qwen3.6-Flash 72.14%, a 2.30 percentage-point difference. Qwen comprises 39
original fixed-verifier results, one recovered verifier log and ten fresh
replacement attempts. Both results are single attempts per scored task, with
different providers; rubric grading is excluded. Matched task data and summary:
`rerun/comparison/`.
