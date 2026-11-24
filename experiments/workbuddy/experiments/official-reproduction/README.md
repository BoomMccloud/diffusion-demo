# Official protocol reproduction

Status: planned. No paper-comparable Clover score exists in this folder.

The paper reports CodeBuddy Code and Claude Code separately on Code (80), Web
(70), Office (50), and Security (60), using three independent runs, thinking
mode, high reasoning effort, a 200,000-token context and common compaction
threshold, with WebSearch and AskUserQuestion disabled. Scores are per-track
means, not a cross-track average. Office uses each task's rule/judge weighting;
Web requires rule, LLM/VLM, and agent judge components as specified by its tasks.
See the [paper](https://arxiv.org/html/2607.20911).

Before launch, pin dataset checksums, the exact official harness builds, runner,
model identity and endpoint, tool settings, budgets, sampling, judge models and
routes, and judge settings. Resolve the endpoint's actual context limit and
document any difference from 200k. The paper's common compaction threshold and
exact builds must be verified from the release or authors, not guessed. Validate
the required judge routes and replay on one saved task per applicable track.

Run a small end-to-end pilot before the full three-repeat matrix. Record each
trial, errors, raw artifacts and grading evidence, including missing scores.
Keep any nonmatching configuration explicitly labeled as a deviation, rather
than presenting it as an exact reproduction. Existing full Office/Web rollouts
have one trial per task and are not substitutes for the official matrix.
