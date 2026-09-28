# AR and Diffusion Workload Discovery

## Purpose

This project is not trying to prove that one generation architecture is
universally better. It is trying to identify the conditions under which the
tested autoregressive and diffusion systems produce the most useful result.

The practical question is:

> For which combinations of output length, dependency structure, edit sparsity,
> response mode, and correctness requirement does each model-runtime system
> produce the best usable result?

The intended systems under study are
`gemma-4-26B-A4B-it-UD-Q4_K_M.gguf` through `llama-cpp-python` and
`diffusiongemma-26B-A4B-it-Q4_K_M.gguf` through `llama-diffusion-cli`, on an
NVIDIA A100. The last attempted environment used `llama-cpp-python` 0.3.34, a
diffusion runner built from source commit `daca8075d871483545dd85d58ce11970b304b541`,
and an A100-SXM4 40GB. A completed run must record the actual package version,
runner commit, model file size and hash, driver, and GPU identity rather than
assuming the next environment is identical.
Results apply to those checkpoints, quantizations, runners, prompts, and hardware.
Architecture is one possible explanation, not a conclusion guaranteed by the
comparison.

## Current execution backlog

Status as of 2026-09-08:

| Priority | Work item | Status | Completion evidence or next gate |
|---|---|---|---|
| P0 | Define the 12 recognizable business problems | Complete | `docs/business_dependency_benchmark_cases.md` defines three direct, three mixed-dependency, three chained, and three global-constraint problems. |
| P0 | Freeze three fixtures per problem with exactly 48 scored decisions | Complete | `bench/business_fixtures.py` reproducibly generates 36 fixtures; `tests/bench/test_business_fixtures.py` guards the contract. |
| P0 | Add canonical output schemas and deterministic validators | Complete | Direct, mixed, and chained cases use exact recomputation; global cases use hard constraints and a registered objective so multiple valid solutions can pass. |
| P0 | Make the DiffusionGemma launch controller safe and resumable | Complete and independently accepted | `bench/business_benchmark.py` preserves registration-bound artifacts, rejects unsafe preparation or warmup evidence, exits nonzero on incomplete runs, and resumes without repeating completed cases. The accepted ledger is `docs/proposals/first-run-launch-hardening.md`. |
| P0 | Verify the staged A100 environment without generation | Next | Stage the pinned artifacts, start the unloaded protocol-v2 worker, and run `business_benchmark.py prepare`. Continue only if it reports `launch_ready` and zero generation RPCs. |
| P0 | Run the 36-case DiffusionGemma business screen | Ready after preparation | Use the immutable registration produced by `prepare`; retain all terminal rows and the completed summary. No real business-screen result exists yet. |
| P1 | Implement and run the matching Gemma autoregressive phase | Not started | Use the same 36 frozen fixtures, ordering contract, scoring, provenance, and timing fields. The current business controller launches only DiffusionGemma. |
| P1 | Analyze the paired business screen | Blocked on both model runs | Report validity, per-decision accuracy, first error, constraint violations, and correctness-filtered latency by dependency class. Do not generalize beyond the pinned systems. |
| P2 | Promote useful separating problems to a larger confirmation set | Deferred | Start only after the three-fixture screen identifies a useful, valid separation; use at least ten frozen fixtures per promoted problem and a fresh A100 session. |

The local readiness evidence is deterministic and offline: all 26 maintained
tests passed, the business self-test registered 36 fixtures with 48 decisions
and zero generation calls, and a synthetic protocol-v2 integration completed
and safely resumed all 36 cases. This does not establish the real token counts,
context fit, accelerator behavior, or model quality. Those remain owned by the
staged `prepare` gate and model runs.

## Evidence language

Every workload claim should carry one of these labels:

- **Hypothesized:** plausible from the decoding method, but not established here.
- **Supported:** observed across a controlled screening set, with the direction
  and raw paired outcomes reported, and awaiting confirmation. The 18-row
  transport pilot described below is not a screening set.
- **Established for this system:** reproduced over the frozen confirmation set
  registered for that workflow and a fresh A100 session, with its registered
  meaningful-effect threshold met and a paired 95% confidence interval that
  excludes no difference for the claimed measure.
- **Unsupported by this runtime:** the required interface or control is absent.
- **Refuted for this system:** the registered success criterion was not met.

A workflow is not a model win when its output is invalid. Compare performance
among usable results and retain every failure in the result set.

## Capability gate

Before testing a workflow, verify that its required operation is available:

1. Full generation from a prompt.
2. Fixed-length or bounded block generation.
3. Arbitrary masked-token infilling.
4. Prefix and suffix clamping.
5. Sparse editing with protected regions or controlled input noising.
6. Intermediate denoising-state capture.
7. Streaming token delivery and a registered definition of useful partial output.
8. Reliable seed control.
9. Comparable prompt-to-final-output timing.

Run three trivial cases for each capability. If the diffusion runner cannot
accept masks or protected tokens, do not describe full-document regeneration as
native infilling or zero-drift editing. Mark those hypotheses unsupported by the
runtime until the interface exists.

Current gate disposition:

| Capability | Status |
|---|---|
| Full prompt generation | Available; complex schedule validity remains poor |
| Bounded multi-block generation | Available up to the runner context; exact limits require the next remote check |
| Arbitrary masked-token infilling | Unverified |
| Prefix and suffix clamping | Unverified |
| Protected or controlled-noise editing | Unverified |
| Intermediate token-state capture | Unverified; aggregate step telemetry alone is insufficient |
| Streaming useful partial output | Unverified |
| Reproducible seed control | Runner accepts a seed; equivalent repeated-trial behavior is unverified |
| Comparable prompt-to-final timing | Verified in the 18-row A100 pilot; no pair had two valid outputs |

## Workload hypothesis register

These are questions to test, not expected winners.

| Hypothesis | Required capability | Controlled probe | Registered evidence of an advantage | Current status |
|---|---|---|---|---|
| Long independent output may favor diffusion | Block generation with comparable timing | Transform many independent records into canonical JSON | Higher valid-output throughput at one or more long-output sizes, reproduced across cases | Hypothesized |
| Increasing dependency density may hurt diffusion relative to AR | Full generation, bounded multi-block output, and comparable timing | Hold output size and format fixed while moving from direct fields to mixed and fully chained fields | Diffusion's paired correctness difference versus AR is worse on chained than direct cases, or its diffusion/AR valid-output latency ratio is higher | Hypothesized; transport pilot complete, no valid paired latency observations |
| Bidirectional infilling may favor diffusion | Native masks plus prefix and suffix clamping | Fill deterministic blanks surrounded by fixed content | Higher fill accuracy or lower latency without changing protected content | Runtime capability unverified |
| Sparse repair may favor diffusion | Protected-token or controlled-noise editing | Correct 5–20% of a structured document | Fewer changed bytes outside target regions at matched target correctness | Runtime capability unverified |
| Whole-output revision may help global consistency | Observable intermediate revisions | Repair mutually dependent fields in a fixed canvas | Higher final constraint satisfaction accompanied by measurable convergence | Runtime capability unverified |
| Short structured extraction may favor AR | Full generation | Extract a few fields into canonical JSON under 256 tokens | Lower valid-output latency | Hypothesized negative control |
| Chained transformations may favor AR | Full generation | Make every output depend on the preceding output | Higher exact accuracy or lower valid-output latency | Hypothesized negative control |
| Streaming responses may favor AR | Streaming token delivery | Produce an incrementally useful response | Lower time to first useful output | Hypothesized negative control |

Only the dependency-density hypothesis has a fully registered decision rule in
this document. The other rows are candidates for the tournament. Each requires
its own exact metric and meaningful-effect threshold before execution. The
general screening rules below are not a substitute for that registration.

For the dependency-density hypothesis, the registered screening effect is met
when either of these occurs in at least two of three output-size cells:

- The diffusion-minus-AR exact-validity difference is at least 10 percentage
  points worse on chained cases than on direct cases. Exact validity means the
  response is the sole permitted JSON object and equals the deterministic
  expected object, including output length and every value.
- Among cells where both systems achieve at least 80% validity, the
  diffusion/AR median wall-time ratio is at least 20% higher on chained cases
  than on direct cases. Latency uses only paired cases where both outputs are
  exactly valid, calculated separately within the direct and chained conditions.
  Each system must independently reach 80% validity in both conditions of that
  output-size cell. A cell that does not meet all four validity thresholds is
  ineligible for this latency endpoint.

The mixed condition is an exploratory check for a monotonic dose response, not
part of the direct-versus-chained decision rule. The full claim is established
for this system only when the same registered threshold is reproduced in a
fresh A100 session and a paired bootstrap 95% confidence interval for that
direct-versus-chained difference excludes zero. Validity is the primary endpoint;
the latency endpoint is secondary and is claimed only when its eligibility rule
is met. Output-size cells are evaluated independently and are not pooled. In
each session, bootstrap resampling is stratified independently within the direct
and chained conditions while preserving the AR/diffusion pair for each case.
At least two size cells must each meet the meaningful-effect threshold and have
an interval excluding zero in the original full run and again in the fresh-session
replication.

## Two complementary comparison tracks

### Workflow fit

Give each model a documented interface and settings that a practitioner would
reasonably deploy for that workflow. Register that choice before running. This
answers which system should be selected for a job. An AR model may emit a patch
while diffusion uses masked infilling, provided the result is explicitly called
an end-to-end workflow comparison.

### Mechanism

Hold the prompt semantics, output contract, amount of work, and timing boundary
as constant as possible. This tests whether output length or dependency density
explains an observed workflow result.

Workflow fit is the primary product result. Mechanism experiments explain it.
Neither track alone proves that architecture caused every difference between two
separately trained checkpoints and runtimes.

## Workflow tournament

### 1. Screen supported workflows

Use 10 deterministic cases at small, medium, and large output sizes. Candidate
workflows are:

- Independent record transformation.
- Dependency-density transformation.
- Structured-form infilling, if native masks are available.
- Sparse document repair, if protected editing is available.
- Short structured extraction.
- Chained state transformation.
- Streaming response.
- Schedule repair as a high-dependency real-world control.

### 2. Promote only observable separations

Register promotion criteria before execution. A useful initial threshold is:

- At least 8 of 10 outputs are valid.
- At least a 20% valid-output latency advantage, or a workflow-specific quality
  effect and minimum meaningful difference registered before execution.
- The advantage appears in at least two output-size buckets.
- The result does not depend on parser leniency, unequal output work, or model
  loading being included for only one system.

Thresholds are screening rules, not statistical confirmation.

### 3. Confirm promising workflows

For each promoted non-matrix workflow:

- Freeze 50 new cases in a versioned manifest before either model runs.
- Run paired cases on the same hardware.
- Counterbalance model execution order.
- Use production-appropriate settings for each model.
- Repeat the complete experiment in a fresh A100 session.
- Report confidence intervals and paired case outcomes.

Matrix experiments register their sample size per cell. The dependency-density
matrix uses 20 paired cases per cell for its full run, or 180 paired cases total,
and repeats that matrix in a fresh session for confirmation.

The final deliverable is a workload map that names the recommended tested system,
the conditions where it applies, the strength of evidence, and the failure modes.

## First controlled benchmark

The first benchmark isolates dependency density at three provisional output-size
targets. These are total-output targets, not diffusion canvas sizes. The runner
generates longer outputs as multiple fixed 256-token canvas blocks; changing the
individual canvas length is not required for this matrix and is unsupported by
the current build. The labels remain provisional until the expected answers are
counted with the actual tokenizer and the combined prompt and output are shown to
fit the runner context:

Each case is one model response. The runtime owns multi-block conditioning and
stitching; the harness does not concatenate independently generated blocks. Both
systems receive the same maximum output allowance for a case. Early stopping,
missing values, extra values, extra keys, prose, and trailing JSON all fail exact
validity, so a shorter AR response cannot satisfy the task by doing less work.

| Nominal output size | Direct fields | Mixed dependencies | Fully chained |
|---:|---:|---:|---:|
| 256 tokens | 20 cases | 20 cases | 20 cases |
| 1,024 tokens | 20 cases | 20 cases | 20 cases |
| 2,048 tokens | 20 cases | 20 cases | 20 cases |

The direct condition determines every output independently from its input. The
mixed condition makes approximately half of the outputs depend on the preceding
output. The chained condition makes every output after the first depend on its
predecessor. Schema and output width remain fixed within each size.

If diffusion is competitive on long direct cases but crosses the registered
direct-versus-chained threshold, that supports a workload boundary where the
recommended system changes with dependency density. A monotonic direct, mixed,
chained trend would provide additional exploratory evidence. Poor diffusion
results on long direct cases would argue against promoting that separate workload
hypothesis, but cannot formally refute it until that hypothesis has its own
registered metric and threshold.

The benchmark cannot establish that all diffusion or AR models behave this way,
that architecture alone caused the result, or that untested editing and infilling
workflows will show the same pattern.

## Measurement contract

Every result row should retain:

- Run, case, prompt, and case-manifest identity.
- Exact model artifact and runtime identity.
- GPU name, memory capacity, and driver.
- Seed and actual model execution order.
- Validity, canonical-format status, and task score.
- Prompt tokens, output tokens, and canonical output units.
- Model load time reported separately.
- Warm prompt-to-final-output wall time for both systems.
- Runner-specific internal compute as a separate optional measure.
- Raw output and failure category.

Report valid and canonical rates, median and p90 warm latency, median paired
latency ratio, correctness-conditioned latency, peak VRAM, and the four paired
outcomes: AR only succeeds, diffusion only succeeds, both succeed, neither
succeeds.

## Current evidence and limitations

- The current diffusion runner uses a 256-token canvas. Its recorded internal
  generation telemetry reported 1,024 tokens in 9.235 seconds, or about 110
  tokens per second; model load and prompt prefill were outside that numerator.
- AR warm request-to-final timing is now recorded in the 18-row dependency pilot.
  Only one AR answer was valid, so output-length crossover estimates remain unsupported.
- Temperature settings 0.0, 0.3, and 0.8 produced byte-identical output and the
  same 1,024-token, four-block decode on the tested diffusion path.
- The diffusion schedule output degenerated during chained time arithmetic. The
  hypothesis that committing several positions per forward pass caused this is
  unfalsified, not confirmed, because
  the runner ignored attempts to change canvas length.
- The schedule workload is useful as a high-dependency negative control, but it
  does not establish a diffusion-friendly workflow.
- The 2026-09-07 dependency-density transport pilot completed all 18 rows.
  AR passed 1/9 cases; diffusion passed 0/9 and exhausted every output budget
  inside an unclosed thought channel. No pair supports valid-output latency.
  See [pilot findings](dependency_density_pilot_findings.md).

These measurements and their raw-log descriptions are sourced in
[Diffusion optimization findings](../archive/legacy-demo/docs/diffusion_optimization_findings.md). This
document does not independently reproduce them.

## Dependency benchmark status

A subsequent [diffusion-only completion diagnostic](diffusion_completion_diagnostic_findings.md)
used a 9,216-token allowance on two eight-record direct cases. Both returned
inside unclosed thought channels after only two and three canvas blocks. This
shows that a low allowance is not the only observed blocker. The exact native
stop reason is unavailable and must be instrumented before further expansion.
The completion gate stopped the remaining cases; Colab has no active sessions.


The standalone dependency-density harness and its protected offline contract are
implemented:

- `bench/dependency_density_bench.py`
- `tests/bench/test_dependency_density_bench.py`
- `docs/proposals/dependency-density-benchmark.md`
- `bench/DEPENDENCY_DENSITY_RUNBOOK.md`

Local contract tests, Python compilation, the existing schedule validation, and
the A100 pilot artifact checks pass. The pilot completed on an A100-SXM4 with
40GB VRAM and driver 580.82.07. All 18 paired rows are saved locally with raw
outputs, exact token counts, artifact hashes, and the frozen execution plan.

The user requested stopping once enough diagnostic data was available instead of
running a multi-hour experiment. The 180-row screen and full 360-row matrix were
not launched. The pilot provides sufficient evidence to investigate reasoning
budget exhaustion before spending more compute, but is not screening evidence
for or against the registered dependency-density hypothesis.

Resolved prerequisites:

1. Actual tokenizer calibration: 126, 510, and 1,022 output values correspond to
   255, 1,023, and 2,047 expected answer tokens in both tokenizers.
2. Memory: runtimes execute in isolated phases, preserving each case's planned
   order. Sampled peak pilot device memory was 28,111 MiB.
3. Remote self-test and exact native diffusion prompt counting pass.
4. Every raw diffusion transcript was inspected and redecoded. Known runner
   logs are excluded; malformed native channels and final prose remain invalid.
5. Actual prompt plus shared output allowance fits each recorded context.
6. The complete 18-row transport pilot is validated. AR passed 1/9 and diffusion
   0/9; there are no jointly valid pairs for latency comparison.

Before restarting, diagnose the pinned runtime's reasoning behavior on a few
cases and register any changed settings or budget. A new screen is required
before a larger performance claim. Full-matrix completion and fresh-session
replication remain outstanding.

See [pilot findings](dependency_density_pilot_findings.md) for results and
artifacts, and [`bench/DEPENDENCY_DENSITY_RUNBOOK.md`](../bench/DEPENDENCY_DENSITY_RUNBOOK.md)
for restart constraints.

## Interpretation rules

- Call results model-runtime findings, not universal architecture facts.
- Do not count a fast invalid answer as a workflow win.
- Do not infer infilling or editing capability from full regeneration.
- Do not claim that a visible decoding animation exposes internal reasoning.
- Publish cases where AR wins, diffusion wins, both succeed, and both fail.
- A refuted diffusion hypothesis is a successful experiment when the controls
  and measurements are sound.

For streaming workflows, define “first useful output” before execution as the
earliest prefix that passes a workload-specific partial validator. Do not infer
internal reasoning or planning from when text becomes visible.

## Verification commands

The current local implementation claims can be checked without model weights:

```bash
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest tests/bench/test_dependency_density_bench.py -v
PYTHONDONTWRITEBYTECODE=1 python -B -c 'from pathlib import Path; [compile(path.read_bytes(), str(path), "exec") for path in Path(".").rglob("*.py")]'
```

These commands verify the offline contract and compilation only. They do not
substitute for the A100 transport pilot or model results.

Latest dependency-density follow-up: [native stop repair and size ladder](diffusion_stop_repair_findings.md)
records correct diffusion final answers through 64 direct records and 64 mixed
records. A 64-record chained run reaches a CUDA softcap runtime crash; the
comparative claim remains unproved. The newer 48-decision business screen and
its current next actions are tracked in the execution backlog above.
