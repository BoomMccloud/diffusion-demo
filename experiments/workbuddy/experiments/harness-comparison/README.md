# Alternative harness comparison

Status: planned. No WorkBuddy Pi or Codex results have been produced here.

Candidate arms are CodeBuddy Code as the reference, Pi, and Codex as the second
alternative. Codex is a candidate because this repository already has a Clover
adapter; confirm its maintained source and compatibility before integration.
Claude Code belongs in the official reproduction as the paper's second arm.

Start with the same small, fixed Office and Web task set across all arms; then
expand after verifying artifacts, scoring, and reliability. Use the same Clover
endpoint and model revision, tasks, repetitions, verifier, judge and task
timeouts. Match context and output limits to the smallest supported value and
record all harness-specific differences in prompts, tools, compaction and
termination. This controlled comparison is distinct from the paper protocol if
those settings differ. Run requests serially while the Clover account enforces
a concurrency limit of one.

For each task and repeat, retain the configuration, trajectory, termination
reason, timing, token counts, artifact and native verifier evidence. Report
paired per-task rewards and missing/error counts, then task-level means; never
silently drop failed or ungraded trials. Pilot Pi's tool calls and compaction
through the Clover relay, and verify each harness is isolated from grading
assets. `bench/terminal_bench/pi_agent.py` is prior Pi integration evidence,
not a ready-made WorkBuddy adapter.
