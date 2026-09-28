# Repository Agent Instructions

## Start here

This file is the single source of truth for the repository's current work. Read
it before choosing a task. Update this section when the active objective or its
verified status changes. Do not infer the active task from findings documents or
git history.

## Current work

The objective is a realistic workload comparison between autoregressive (AR) and
diffusion decoding. The earlier screens used synthetic tasks: copy a code, apply
a threshold, look up a category, and business problems given as clean JSON with
exact rules. Code would solve those without a model, so they could only show
that speculative decoding is faster on predictable output at batch 1. They
could not show where diffusion helps on work people actually send to a model.

That synthetic workload code was removed on 2026-09-28. Its raw rows, fixtures,
and harnesses remain in git history at commit `545c985`. The findings documents
in `docs/` stay as the record of how the models and runners behave.

### Systems

- **Nemotron-Labs-Diffusion-3B**, one set of weights in three modes: `ar`,
  `linear_spec` (diffusion draft, AR verify), and `diffusion`. This isolates the
  decoding method from the model. Runner: `bench/nemotron_runner.py`. Fits an L4.
- **Gemma 4 26B A4B** AR through `llama-cpp-python` against **DiffusionGemma 26B
  A4B** through the instrumented protocol-v2 `llama-diffusion-cli`. Runners:
  `bench/gemma_runtimes.py` and `bench/diffusion_runtime.py`. Needs an A100.

### The four workloads

1. **Unstructured text to JSON.** Pull fields from messy emails, invoices,
   contracts, or support chats into a fixed schema. Output is long, structured,
   and fairly predictable, but the values need reading, not copying. This tests
   whether the diffusion speedup survives once values stop being trivial. Score
   per field against a hand-labelled reference.
2. **Code or document edits.** Rewrite a file or contract with a few requested
   changes. Most output copies the input, which is the best case for diffusion
   and also for AR with prompt-lookup speculation, so it is the fairest
   head-to-head. Score by applying the result (tests pass, or the diff touches
   only the requested regions).
3. **Short free-form answers.** Chat replies, summaries, and emails of 50 to 300
   tokens. This is most real traffic. Tokens are less predictable, so fewer drafts
   are accepted. If the speedup mostly disappears here, that bounds where
   diffusion is worth deploying. Score quality with a fixed rubric and a pinned
   judge, or pairwise preference, and report it next to latency.
4. **Agent tool-call loops.** Many short structured calls in sequence, where
   end-to-end latency is the sum of the steps. Diffusion's per-call gain is
   small but compounds. Score task completion and total wall time.

### Controls every workload needs

- **Concurrency sweep.** Run at 1, 8, and 32 concurrent requests and report
  throughput next to single-request latency. Batch 1 is where parallel decoding
  helps most, and the gap usually narrows as AR batching fills the GPU.
- **Strong AR baseline.** Add AR with prompt-lookup or n-gram speculative
  decoding on the same weights. Without it, a copy-heavy speedup cannot be
  credited to diffusion.
- **Matched budgets.** Give every arm the same output-token allowance, context,
  prompts, and hardware.
- **Record** raw output, reasoning, stop reason, prompt and output tokens,
  forward passes, request-to-final latency, model revision or hash, runner
  identity, and GPU. Copy every row off the accelerator as it completes.
- Use realistic inputs rather than generated JSON. Where inputs are sampled from
  public data, record the source and license.

### Next step

Start a `proposal-pipeline` run for this comparison. The first decisions are the
input sources for each workload, the quality scoring for workload 3, and which
system pair goes first. Nemotron-3B on an L4 is the cheapest way to shake out
the harness.

## What earlier work established

These are screens with small samples, not registered evidence. See the named
findings for limits.

- On the pinned A100 harness, DiffusionGemma returned exactly correct 48-value
  outputs on 6 of 6 synthetic cases and passed 4 of 6 at 56. The run summaries
  are in `bench/results/dependency-density/` at commit `545c985`; 64 values is in
  `docs/diffusion_density64_findings.md`.
- The protocol-v2 runner needed fixes for native stopping, 64-bit softcap
  indexing, and incremental prefill. Incremental prefill cut wall time 34% on a
  three-case A/B. With 32,768 context and a 30,208-token allowance, nine cases
  that had exhausted 8,704 tokens stopped at native EOG
  (`docs/diffusion_runtime_budget_prompt_findings.md`,
  `docs/diffusion_softcap_repair_findings.md`,
  `docs/diffusion_stop_repair_findings.md`).
- Nemotron-3B linear speculation matched its own AR output exactly at 4.9x to
  7.3x lower batch-1 latency on L4, with the gain shrinking as output grew. Plain
  diffusion failed exact output through adjacent-token duplication. Thinking-on
  never engaged (`docs/nemotron_3b_candidates_findings.md`,
  `docs/nemotron_diffusion_pilot_findings.md`).
- Prompts must state the exact output format. Without it, small models without
  reasoning scored 0 on every business case.

Do not carry these numbers over to the realistic workloads. They are the
hypotheses the new comparison tests.

## Authoritative working files

- `AGENTS.md`: active objective, verified status, and immediate next task.
- `bench/README.md`: how to stage and run each model runtime on Colab, and the
  durable runner constraints.
- `bench/gemma_runtimes.py`: AR `llama-cpp-python` calls and the native
  DiffusionGemma session, tokenizer helper, transcript parsing, and GPU identity.
- `bench/diffusion_runtime.py`: resident DiffusionGemma worker behind a loopback
  API.
- `bench/nemotron_runner.py`: Nemotron three-mode runner and OpenRouter AR arm.
- `bench/native/`: pinned `llama.cpp` patch, build, and CUDA probes.
- `cells/`: Colab model staging and prior runner setup.
- `docs/*_findings.md`: what each earlier run established and its limits.

## Accelerator sessions

- Operate Google Colab through the locally installed `colab` CLI by default. Use
  `colab sessions` and `colab status` to discover and reuse an existing runtime,
  and use `colab exec`, `colab upload`, and `colab download` for remote work. Do
  not assume Colab requires browser automation. Use `colab url` and the regular
  Colab UI only when interactive authentication is required or CLI Drive
  credential propagation fails.
- Use Colab CLI 0.7.4 or later: 0.6.0 drops sessions when their proxy token
  expires after 60 minutes.
- Treat a running Colab or other accelerator session with a loaded model, compiled binary, or populated local cache as expensive state.
- Before stopping or closing such a session, ask the user whether they want to keep it running for additional tests. Explain what would need to be downloaded, compiled, or loaded again if the session is closed.
- Stop the session without asking only when the user has already explicitly instructed you to close it after the current work, or when leaving it running is not possible.
