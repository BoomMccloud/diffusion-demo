# Reproduce an experiment

Use the [experiment index](README.md) to find the project, then open its README
for the task inputs, runner, model settings, and evidence. The root
[AGENTS.md](../AGENTS.md) records known runs and their limitations.

1. Start with the smallest smoke command in the project README. Stage its
   pinned inputs and models, then check credentials and accelerator access
   before starting a larger run.
2. Use the [model runtime instructions](../bench/README.md) for local model
   launches and the [Spark workspace guide](../docs/spark-workspace.md) for
   container and storage setup on the DGX Spark. Use the host and credentials
   assigned to you.
3. Save fresh outputs in a separate run directory. Record the revision, model
   and provider, task selection, command, settings, and score or error. Keep
   the existing evidence available for comparison.

Many older experiment folders use relative symlinks to code, evidence, and
findings at their original locations. Keep the repository layout intact.
Models, some upstream inputs and some raw runs are stored separately. Follow
the experiment's setup instructions when a linked file is missing.

For WPS Office capture and grading, start with the
[WorkBuddy instructions](workbuddy/AGENTS.md). For viewing or rerunning launch
demos, see the [launch handoff](../go-live/AGENTS.md).
