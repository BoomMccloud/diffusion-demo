# Repository Agent Instructions

## Start here

This file is the single source of truth for the repository's current work. Read
it before choosing a task. Update this section when the active objective or its
verified status changes. Do not infer the active task from findings documents or
git history.

For the repository layout, read `README.md`. Start with the
[experiment instructions](experiments/AGENTS.md) and
[experiment index](experiments/README.md), then read the experiment's README
before working on it. See the [launch handoff](go-live/AGENTS.md) for demos
and launch assets. Older experiment folders link to code, results, and findings at their
original paths; keep those links and existing commands working when reorganizing.
Some linked data and run artifacts exist only locally or on the DGX Spark.

## Run the Office demos

- [WPS supplier onboarding](go-live/wps-supplier-onboarding-demo/AGENTS.md)
  covers the short workbook edit and the full intake workflow.
- [WorkBuddy Office demos](experiments/workbuddy/AGENTS.md) covers the
  weekly tickets and board presentation workflows.

## DGX Spark storage

Use the [Spark workspace guide](docs/spark-workspace.md) for new Spark
deployments and experiments. Its installed copy is `~/clover/README.md`.
Use `~/clover/models/` for weights, `~/clover/dllm-inhouse/` for runtime
builds, and `~/clover/benchmarks/{inference,applications}/` for results.
Keep the two copies of the guide in sync when the layout changes.

## Current work

The hosted API reproduction handoff starts at [docs/api-experiments.md](docs/api-experiments.md).
It links setup and smoke commands for the direct API runners, WebArena,
Terminal-Bench, and WorkBuddy Office. The portable Office runner uses the
public pinned checkout and native deterministic verification.
On 2026-11-24, verified WebArena task selection and mocked judge routing,
Harbor's resolved Terminal-Bench dataset and task, and WorkBuddy dry runs
against the checksum-verified Office archive. The local Mac VM then ran
two live smokes through OpenRouter GLM 5.3 Flash. Terminal-Bench
`vf2-speedup-networkx` returned reward 0.0 with no trial exception.
WorkBuddy Office `ticket-weekly-L3-010` passed 15/15 with a saved workbook
after repairing Bash selection and proxy routing. Local verifier evidence
is under `bench/results/api-smokes-2026-11-24/`. The WebArena adapter
returned a live browser click and replayed it in Chromium. The official
fixture was unavailable, so WebArena has no score.

On 2026-11-23, tested DeepSeek V4.1 Flash 1017 and GLM 5.3 Flash through
OpenRouter for the WorkBuddy Office comparison. Both passed a synthetic
tool-call round trip with a streamed final answer. The staged model configs
and probe results are in
`experiments/workbuddy/experiments/openrouter-flash-office-2026-11-23/`.
Spark SSH is verified at its updated LAN address, `192.168.3.3`. Both weekly
ticket smokes produced workbooks and valid native deterministic scores.
DeepSeek passed 14/15 checks with an extra row. GLM passed 15/15. The Spark
container `workbuddy-openrouter-office-batch-20261123` then launched the same
50 Office tasks per model in the saved order, serially with CodeBuddy 2.109.3.
Checked on 2026-11-24: DeepSeek has 17/50 valid batch scores, with a 79.28%
mean on those 17 tasks. The runner exited after OpenRouter returned HTTP 403
on task 18 (`fund-product-table-normalize-L3-017`) before generation. The
saved logs do not identify the reason for the 403. GLM has 0/50 batch scores.
The score ledger is under `results/openrouter-flash-office-20261123/` in the
Spark WorkBuddy checkout. Rubric grading is deferred.
On 2026-11-24, retried task 18. The instrumented recovery confirmed that the
403 on tasks 18 and 19 was due to the OpenRouter key budget. The key's $30
limit had $0 remaining and no automatic reset. After the user updated the
key, verified $5 of key budget and resumed in
`workbuddy-openrouter-office-funded-20261124`. Task 18 attempt 4 passed
351/355 checks, and task 19 attempt 2 passed 12/15. The runner advanced to
task 20. DeepSeek has 19/50 valid batch scores and GLM has 0/50 at this
checkpoint.

On 2026-11-23, recorded Clover completing the fictional supplier onboarding
demo through native WPS spreadsheet edits on the Mac. A scoped writer applied
the hosted Clover pilot API's tool call to a disposable workbook. Both runs
flagged the missing signed compliance declaration and the 7 versus 10 business
day delivery conflict. The first passed 25/26 checks because it labeled the
conflict as Other. A fresh run with explicit exception category definitions
passed 26/26 and left the conflicting field blank. The scored workbook matched
the WPS-saved file byte for byte. The 13.5-second recording has a Simplified
Chinese activity panel and no audio. The RTX 5070 Ti workflow remains untested.
Evidence: `go-live/wps-supplier-onboarding-demo/runs/20261123-092943/`.

The full-workflow recording adds the two original PDF pages, the intake
checklist, and the receipt and extraction events before the native WPS edits.
The 27.5-second version passed 25/26 checks. It flagged both seeded issues and
left the delivery field blank, but listed the successful price check as an
extra exception. The PDF panels use rendered pages from the staged inputs.
Evidence: `go-live/wps-supplier-onboarding-demo/runs/20261123-093454/`.

On 2026-11-20, consolidated the Spark model library and organized the
runtime builds, inference results and application benchmarks under
`~/clover/`. Legacy mount paths are preserved for existing runners.
The original BF16 GGUF, all model versions and Docker images were retained.

On 2026-11-20, shut down the Spark experiment services at the user's request.
The last active Clover AR server, two gateways, detached bridge listener and
stale benchmark monitors were stopped. Docker reported zero running containers
and the GB10 reported zero compute processes. The earlier server health checks
below describe the state before this shutdown.

On 2026-11-20, started the Clover block-diffusion SFT experiment. Read and
pinned the upstream recipe, verified the native checkpoint's indexed files
and GSM8K split structure on Spark, and recorded the training plan in
`experiments/clover-sft/README.md`. Next is a CUDA kernel preflight on GB10,
followed by a five-step LoRA smoke if it passes. No training has run.

Reviewed Pi history as a Clover adapter data source. The Mac and Spark
benchmark archives contain the same 12 Pi sessions across three tasks,
with nine zero rewards and three missing scores. Use them for format checks.
Native tool-action SFT needs verified successful demonstrations and trainer
support for structured prefixes and targets. Findings:
`experiments/clover-sft/pi-adapter.md`.

The cached Clover chat template and tokenizer passed two offline structured
tool-turn probes on Spark. The pinned ms-swift already normalizes tool data.
The Clover plugin still rejects it, so the identified extension is its encoder
with existing diffusion alignment and masking. Live inference is unverified.

After the shutdown below, restarted the original DeepTutor workspace on Mac
port 3782 with the 128K Clover AR container on Spark port 18083 through
local SSH port 18183. The web app returned HTTP 200 and a DeepTutor chat
answered seven times eight as 56. Only the 128K AR deployment was restarted.

Shutdown verified on 2026-11-20. Both Mac DeepTutor apps, both adapters,
and both Spark SSH tunnels were stopped. All eight local ports closed.
The four DGX Clover containers (4K and 128K, AR and self-speculative)
reported exited. Local workspaces and containers remain available for reuse.

On 2026-11-20, installed DeepTutor 1.7.3 under `downloads/deeptutor-local/`
on the Mac. The packaged web UI returned HTTP 200 on loopback port 3782,
with the API on 18091. Its installed launcher was adjusted to bind both to
loopback. A local SSH forward on 18183 reaches Spark's existing Clover AR
server on 18083. The DeepTutor CLI chat returned 391 for 17 times 23 and
recorded a completed call to `clover`. Embeddings remain unconfigured.

A separate text-only DeepTutor trial runs on Mac loopback 3783, with API
18092. Its adapter on 18185 forwards to the self-speculative Spark server
on 18082 through local SSH port 18182. It sets temperature zero, disables
thinking and omits native tools because the server rejects their sampling
grammar. The chat engine answered 17 times 23 correctly in 1.98 seconds.
Spark reported 180.91 decode tokens/s for 51 tokens and accepted 55/60 draft
tokens. This single short trial does not establish a speedup versus AR.

Matched one-output-token chat probes confirmed cross-request prefix reuse
on the deployed self server. With long notes in the system message it reused
0/8317 tokens on two exact replays (AR 8294/8317). With the notes in the
user message it reused 8192/8322 on both replays and 8192/8318 after a
changed question. Both cache-disabled controls for each layout reused zero.
Reproduce with `downloads/deeptutor-local/verify_prompt_cache.py` with and
without `--source-in-user` while the two local SSH tunnels are active.

On 2026-11-20, ran five larger generation workloads with the tuned PR #4
Q4_0 six-expert threshold configuration and full-history penalized AR.
Self/AR decode tokens per second were 81.02/79.50 handbook, 74.69/80.82
single-response novella, 100.15/76.90 catalog, 111.15/73.71 chaptered
novella and 151.66/68.76 manifest. The chaptered self run repeated one
chapter body ten times. AR capped nine chapters. Both manifests generated
13612 tokens, with 492/560 correct records for self and 560/560 for AR.
Both missed the required outer array. All four services returned healthy.
Responses, timings and scoring scripts:
`experiments/clover-gguf/results/larger-pr4-20261120.tar.gz`.

On 2026-11-20, tested DiffuSpace dllm.cpp-inhouse PR #4 at `6a3f36ed`
on the Spark. With repeat 1.05, presence 0.9 and both end biases zero, its
default verifier completed all five varied Q4_K_M prompts at 58.22 pooled
decode tokens/s versus 75.43 for ordinary one-slot AR. A locally tuned
four-expert verifier reached 79.12 with five stops, but introduced a major
unit error in the science tutorial. On a separate eight-task structured
panel, width eight, six verifier experts, threshold acceptance, repeat 1.02
and presence 0.3 ran at 122.89 versus 77.69 tokens/s. Width six with all
eight verifier experts, exact acceptance and neutral penalties reproduced
all eight AR answers byte for byte, plus all twelve answers on a new
validation set. Both passed the same 16/20 checks. Across two orders on these
20 tasks self delivered 67.09 tokens/s versus 53.09 AR including prefill and HTTP.
All four penalized PR ferry replays stopped naturally. A packed Q4_0
width-eight, six-expert threshold finalist with full penalties and fused CUDA
kernels generated identical long answers on two passes at 83.61 and 85.10
pooled tokens/s (84.35 combined). Matched Q4_0 AR with full penalty history
completed all five at 65.01. A 64-token history ran at 77.85 and capped
fiction. Both full-history utilities passed 4/5 checks. The blinded rubric
favored full-history AR 9.7/10 to 8.9/10, so general long-form parity is
unverified. All four deployed servers were restored. Measurements and PR review:
`experiments/clover-gguf/dllm-inhouse/pr4-speed-quality.md`.

The dllm Spark workspace guide is saved locally at
`experiments/clover-gguf/dllm-inhouse/README.md` and as `README.md` under
`~/diffusion-demo/runs/dllm-inhouse-4257d3dd/` on Spark. It documents artifact
locations, API endpoints, conversion commands, task-panel checks and limitations.

On 2026-11-19, built DiffuSpace `dllm.cpp-inhouse` commit
`4257d3dd6de5bbe4db1c8d9b45038009593b1bb3` for CUDA on the Spark in a
resource-limited container. `llama-server` and `llama-quantize` built, and
the CUDA backend detected the GB10. The cached official Clover Q4_K_M GGUF
failed the isolated server load on missing `clover_moe.expert_shared_count`;
it also lacks the reference-block metadata required for masked drafting.
No generation was attempted. Build and source are under
`~/diffusion-demo/runs/dllm-inhouse-4257d3dd/` on the Spark. Existing loaded
servers and the WorkBuddy recovery remained running. The README specifies the
Preview-1024 checkpoint, whose conversion and inference remain untested.
An isolated follow-up supplied `clover_moe.expert_shared_count=1` and
`clover_moe.ssm.bd_reference_block_size=32` as runtime overrides. The loader
passed the missing-key check but rejected the GGUF tensor inventory: expected
853, got 733. No generation ran, and the existing GPU processes remained up.
The public BF16 Preview checkpoint (revision `4b0402b`) was subsequently
downloaded and converted with this runtime's converter, then quantized with
its `llama-quantize` to Q4_K_M. The resulting 853-tensor GGUF loaded on the
Spark GB10 with `--spec-type self` and answered 17 times 23 as 391; the
server reported 15 of 15 draft tokens accepted on that short smoke test.
The model and conversion logs are in `~/diffusion-demo/runs/dllm-inhouse-4257d3dd/`.
The loaded container `dllm-clover-self-4257` listens on Spark loopback port
18080 and remains running. Three previously loaded GPU containers exited
cleanly together during the download, before conversion; their cause is
unknown, and they were not restarted.
Three sequential warm self-speculative tests with thinking disabled, greedy
sampling, 4096 context and up to 512 output tokens produced 512, 473 and 357
tokens at server-reported 63.93, 55.44 and 62.09 output tokens/s respectively
(60.20 tokens/s pooled over generation time). One hit the output cap. These
short prose prompts are a throughput smoke test, not a benchmark comparison.
The same three prompts on a separate server using the same Q4_K_M model,
runtime, context, temperature, thinking setting and output cap but without
self-speculation produced 512, 512 and 389 tokens at 79.48, 80.15 and 79.80
tokens/s (79.81 pooled). Outputs differed between modes and two AR responses
hit the cap. The AR run had the idle speculative model also loaded; the earlier
speculative run did not have the AR model loaded. Both containers remain running,
with AR on Spark loopback port 18081.
Two matched 2048-token prose runs per mode measured 68.75 pooled tokens/s
self-speculative and 78.92 AR; all hit the output limit. A subsequent
131072-context comparison with a 128000-token output limit and the same
500-case manual prompt ended naturally at 39014 self-speculative tokens
(185.88 tokens/s, 36389/39360 draft tokens accepted) and 33549 AR tokens
(68.46 tokens/s). Both manuals repeated many case details, so these numbers
are not representative of diverse long-form work. Full responses and timings
are under `~/diffusion-demo/runs/dllm-inhouse-4257d3dd/long-128k-*.json`.
The 128k-context servers remain loaded on loopback ports 18082 and 18083.
Long varied-output tests used five matched prompts, 8192 output tokens,
temperature 0 and seed 42. Three speculative outputs (hospital recovery,
fiction, coastal policy) degenerated into substantial repetition and hit the
cap, so their inflated rates are not clean throughput measurements. The
non-looping exoplanet tutorial ran at 74.40 speculative tokens/s for 2330
tokens versus 77.09 AR tokens/s for 5123 tokens. The code task ran at 107.45
versus 76.91 tokens/s for 4080 and 5487 tokens; repeated code structures and
different outputs limit comparison. A 12-lexical-token repeat-window check
found 0.46%/2.86% repeats in the speculative/AR science outputs, 10.13%/
12.54% in code, and 76.68% to 82.42% in the three looping speculative outputs.
These are single attempts, not a failure-rate estimate. Full outputs and
timings: `runs/dllm-inhouse-4257d3dd/varied-long*-comparison.json` on Spark.
With a 65536 output-token cap and 131072 context, two prompts were tested once
per mode with thinking enabled and once disabled, temperature 0 and seed 42.
Thinking enabled: speculative policy completed at 78.34 tokens/s (6298
tokens); AR policy and both coding runs exhausted 65536 tokens in repetitive
reasoning and emitted no final answer. Thinking disabled: policy speculative
98.41 tokens/s (1750 tokens), AR 77.68 (3042); code speculative 121.56
(4744), AR 77.15 (4161), all natural stops. Response lengths and content differ;
the code was not tested for correctness. The clean speculative policy answer
was much shorter than requested. Single attempts are not a failure-rate or
quality comparison. Full text, reasoning, settings and timing are in
`runs/dllm-inhouse-4257d3dd/varied-64k-thinking-comparison.json` on Spark.
On 2026-11-20, replayed the two thinking loops to diagnose mitigation. They
occurred within a 131072-token context at a 65536-token output cap, so context
exhaustion was not established. Clover's reference generation config applies
repetition and gradual end biases; this self-speculative server rejects
reasoning budgets, penalties and nonzero temperature. An AR 2048-token
thinking budget completed the policy task (5188 output tokens); the coding
task left reasoning but hit an 8192 output limit, and with 16384 output tokens
it repeated in the answer and again hit the limit. Penalties alone hit the
8192 cap on both tasks; budget plus penalties completed policy but not coding.
Temperature 0.6 plus budget completed policy; coding reached 8192 without a
complete answer. These are single diagnostic replays, not validated fixes.
The self-speculative endpoint returned HTTP 400 for the thinking budget.
Evidence: `runs/dllm-inhouse-4257d3dd/loop-control-*.json` on Spark.
Using the model card's presence penalty 0.9, repeat penalty 1.05 and frequency
penalty 0, with greedy decoding, thinking on, 65536 output cap and full-context
repeat history, AR completed the policy prompt in 10155 tokens at 72.17 tok/s
and the coding prompt in 28856 tokens at 66.46 tok/s. A 12-word repeat-window
check found 0% in policy reasoning and answer, and 12.81% in coding reasoning
and 1.69% in its answer; generated code correctness was not tested. Self-spec
rejected both requests with HTTP 400 because modified logits are unsupported.
The reference model's gradual end biases and exact penalty semantics were not
reproduced in this runtime. Single attempts only. Evidence:
`runs/dllm-inhouse-4257d3dd/model-card-penalties-comparison.json` on Spark.

On 2026-11-20, the thinking-off ferry story in the saved task panel repeated
a 270-character radio exchange 925 times under self-speculation and reached
65536 output tokens. Greedy AR from the original prompt stopped at 1413.
Replaying identical tokenized story prefixes on the 4096-context servers
showed both modes continued the loop once the prefix contained one copy.
With three copies, even AR with model-card penalties emitted three more in
210 tokens. The self verifier uses six experts and entropy-based acceptance
of non-argmax proposals. A four-way fresh-prompt replay reproduced the
70-token cycle starting at output token 727 with six experts and threshold
acceptance. Eight experts with threshold acceptance, six with exact acceptance
and eight with exact acceptance reached EOS at 1706, 1153 and 1672 tokens.
All cross-policy pairs diverged at token 3. Changing expert count diverged at
token 11 with threshold acceptance and token 7 with exact. One run per cell.
See `experiments/clover-gguf/self-spec-repetition.md` for the replay details.

The isolated Spark build in `five-prompt-verifier-20261120/` adds startup
options for verifier experts and acceptance. On the five original varied
prompts (thinking off, 8192 token cap), eight/exact stopped naturally on
5/5, eight/threshold on 4/5, and earlier six/threshold on 2/5. Eight/threshold
still looped on lighthouse fiction. On the four mutual completions exact
pooled 69.20 tokens/s versus 75.60 threshold. Eight/exact is preferred for
this workload. Exact still had 23.10% duplicate 12-token windows on policy.
One run per cell, with no quality scoring or production deployment. The 4k
self server was restored and healthy. The linked replay report has the patch,
raw responses and per-prompt results.

### WPS Office pilot

On 2026-11-18, selected five Office tasks for a Clover and CodeBuddy WPS
integration pilot. Their existing deterministic mean is 87.69%, with two
full scores. A one-task WPS proof of concept on weekly tickets passed 2/15
checks (13.33%) versus 15/15 previously. Clover's unchanged output was replayed
after repairing the WPS writer; input was extracted outside WPS, and the run
was not in the original task container. This is diagnostic, not a controlled
comparison. A fresh run with a network-isolated Python tool and preflighted WPS
writer completed autonomously and passed 10/15 checks (66.67%): weekly counts
were correct, but an extra total row and numeric percentage-point values failed
the verifier. A subsequent run used normal CodeBuddy tools in the original
Spark task image with a scoped WPS writer on the Mac. The first attempt scored
11/15 due to stale WPS cell formatting and an extra total row. After repairing
the writer, a fresh attempt scored 14/15 on both the WPS workbook and a separate
container workbook; the extra total row was the only failure. The earlier
baseline scored 15/15. Task baseline
and next steps: `experiments/workbuddy/experiments/wps-office-pilot/README.md`.

An all-Mac weekly-ticket run then passed 15/15 deterministic checks. Clover
used CodeBuddy's normal tools in a macOS sandbox, a scoped WPS writer, and a
local copy of the task. WPS's saved file was copied into the task workspace
and matched byte for byte. The original verifier ran locally with its hard-coded
gold path redirected; it also reproduced the earlier WPS result of 14/15.
This is one attempt on a different OS and is not a controlled comparison.

The remaining four Office tasks ran locally with Clover, CodeBuddy and scoped
WPS tools. Deterministic results versus the saved Spark baseline were: drug
inventory 15/15 vs 15/15; procurement 16/21 vs 15/21; safety notices 24/27 vs
25/27; board deck 242/379 vs 267/379. Equal-weight means are 82.23% vs 83.62%.
The board agent hit the 48-turn cap; four of eight WPS edit calls failed exact
text matching. These are single attempts with different OS, tool interface and
instructions; LLM judging remains excluded. Results and task trajectories:
`experiments/workbuddy/experiments/wps-office-pilot/four-local/`.

On 2026-11-18, a recorded all-local weekly-ticket demo used a scoped WPS
writer that activates the workbook and writes one selected row at a time.
Clover's output scored 3/15 because its ISO week labels were one week early;
the four totals and rates matched the reference. Its shell could not import
openpyxl and parsed the XLSX XML instead. The previous local and Spark results
were both 15/15. Evidence: `experiments/workbuddy/experiments/wps-office-pilot/weekly-ticket-visible/`.

A fresh recorded weekly-ticket retry exposed the installed openpyxl through
PYTHONPATH and verified its import in CodeBuddy's shell. Clover used openpyxl,
then wrote the correct Monday dates through the visible WPS writer. The saved
WPS workbook matched the scored file and passed 15/15 original deterministic
checks. Evidence: `experiments/workbuddy/experiments/wps-office-pilot/weekly-ticket-visible-python/`.

A recorded board-presentation run added visible WPS slide and shape selection
before edits. Clover's 11-slide deck passed 307/379 deterministic checks,
versus 242/379 in the prior WPS run and 267/379 in the Spark baseline. These
are single attempts with different settings, not a controlled comparison.
The user requested an agent-text overlay; the timestamped trajectory and a
concise tool timeline are preserved, but individual WPS edit times were not
logged. Evidence: `experiments/workbuddy/experiments/wps-office-pilot/board-visible/`.

A fresh board demo was programmatically captured and combined with a panel
rendered from timestamped agent and WPS events. The 4m 24s video has no audio
and approximate synchronization; a sampled frame showed the WPS selection and
matching event. The deck passed 310/379 deterministic checks. This is one
attempt with different settings from the baseline. Scripts and video:
`experiments/workbuddy/experiments/wps-office-pilot/board-video/`.

The Qwen3.8-Flash recorded board comparison used the general-purpose DashScope
route with thinking enabled, CodeBuddy and the same visible WPS writer. Its
original deterministic score was 326/379 (86.02%) versus recorded Clover's
310/379 (81.79%); agent elapsed times including paced WPS edits were 311.6 s
and 257.9 s. These single runs differ in provider, settings and edit counts.
Videos and evidence: `experiments/workbuddy/experiments/wps-office-pilot/board-video-qwen/`.

Created and installed the reusable `wps-agent-demo` skill for future WPS
agent tasks and recordings. Source: `experiments/workbuddy/skills/wps-agent-demo/`;
installed under `~/.codex/skills/wps-agent-demo/`. The generic WPS spreadsheet
and presentation writers passed live disposable-file tests, and the capture
helper produced a short combined video. Per-task verifiers, safe sandboxing,
and feature-specific WPS support still require configuration.

On 2026-11-18, a Clover dry run on the original WorkBuddy mind-map workshop
task generated a 13-slide deck with CodeBuddy file tools and passed 87/113
deterministic checks (76.99%). The 31-second preview uses the task reference
image, recorded tool counts, and rendered output slides. Live WPS editing
and LLM judging were outside this run. Evidence:
`experiments/workbuddy/experiments/wps-office-pilot/xmind-clover-dry-run/`.

The same original workshop task ran locally with Qwen3.6-Plus overnight
on 2026-11-18 to 2026-11-19 Taipei time. Qwen saved eight slides before the
24-turn limit and passed 88/113 checks, versus Clover's 13 slides and
87/113. The 32-second side-by-side preview compares rendered slides from
the unchanged scored files. These are single CodeBuddy file-tool runs
with different model providers and no LLM judging. Evidence:
`experiments/workbuddy/experiments/wps-office-pilot/xmind-qwen36-comparison/`.

The WPS board runners now use audited local model proxies. A 2026-11-18
CodeBuddy dry run with Clover and Qwen3.6-Flash recorded per-request provider
usage, timing and stream completion and reconciled usage with CodeBuddy. Qwen
needed a second explicit prompt to call Bash. This was telemetry validation,
not a WPS benchmark run. Evidence and limitations:
`experiments/workbuddy/experiments/wps-office-pilot/proxy-audit/`.

Full instrumented board attempts: Clover wrote through WPS and scored
300/379; Qwen3.6-Flash's seven WPS update attempts failed exact-text checks,
and its directly generated python-pptx output scored 305/379 but did not
satisfy the WPS editing requirement. All 32 Clover and 46 Qwen requests had
provider usage and clean streams, and sums matched CodeBuddy (Clover 1,956,721
input / 52,850 output; Qwen 2,659,846 / 66,508). Single runs, differing tool
behavior; proxy timing is not pure model TPS. Results:
`experiments/workbuddy/experiments/wps-office-pilot/proxy-audit/full-comparison-20261118/`.

A fresh Qwen3.6-Flash board rerun used a tested WPS writer that applies
individually exact-matched edits and reports rejected locations. Its 77 WPS
edits yielded a matching saved/scored deck and 305/379 checks; all 12 audited
requests returned usage matching CodeBuddy (476,902 input / 17,909 output).
Agent elapsed time was 237.467 s including paced edits. The Clover comparison
scored 300/379 in 162.996 s with the older all-or-nothing writer. These are
single runs with different writer semantics. Evidence:
`experiments/workbuddy/experiments/wps-office-pilot/board-video-qwen-wpsfix/`.

A fresh Qwen3.6-Flash board repeat with the original all-or-nothing WPS
writer again failed the WPS requirement: four batches were rejected, no WPS
edits occurred, and its direct python-pptx output scored 251/379. All 43
requests returned usage matching CodeBuddy (2,972,901 input / 45,890 output).
A repaired-writer Qwen run scored 305/379 through WPS. These single attempts
do not establish a failure rate. Evidence:
`experiments/workbuddy/experiments/wps-office-pilot/board-video-qwen/runs/20261118-234234/`.

### Clover WorkBuddy Bench Web and Office smoke

The requested follow-up is an official-protocol Clover reproduction and a
comparison with Pi and another harness. Local WorkBuddy evidence and the
proposed experiment layout are in `experiments/workbuddy/`; both new comparisons
are planned, not yet run. Verify the Clover context limit, paper configuration,
and an eligible judge route before claiming paper-comparable scores.

On 2026-11-16, staged Tencent WorkBuddy Bench at
`625b2233093ae4f23e76be28c1f341d41cc70373` on the DGX Spark in
`~/diffusion-demo/runs/workbuddy-smoke`. The v1.0 Office and Web archives
passed their published SHA-256 checks. The smoke uses the upstream Harbor
0.18.0 runner and CodeBuddy Code 2.109.3 with Clover for rollout and Gemini
for rubric judging. The two trials are queued serially in
`workbuddy-clover-web-office`, Office `json-screener-summary-L4-004` first,
then Web `html-report-generation-L2-004`. Their Dockerfiles use native ARM
Node, and the Web Dockerfile adds the ARM Playwright dependency `libatomic1`.
Acceptance is one model-driven artifact and one completed verifier result
per track. The CodeBuddy mount image built, the Office proxy confirmed
its Clover route, and the Office agent initialized in its task container.
The Office verifier ran and reported 1/119 checks and reward 0.0067 after
CodeBuddy timed out connecting to the proxy at the Docker bridge address.
The agent recorded zero input and output tokens, so this is an infrastructure
failure. Web launched native ARM Chromium during the image build, then failed
because the Dockerfile edit inserted a second `libatomic1` line in the Git
setup command. The Web agent never started. Results and exceptions are in
the checkout's `results/` directory.

Retry: removed the stray `libatomic1` from the Web Git setup command and
built both task images. The proxy and task containers now share the dedicated
`workbuddy-smoke-private` Docker network, and the tasks address the proxy by
its Docker DNS alias. Each real task image returned HTTP 200 from the proxy
health endpoint and confirmed both model routes before the Office rollout
launched. The same checks gate the Web rollout. The serial retry runs in
`workbuddy-clover-web-office-retry`, under the `clover-*-smoke-retry` result
directories.

Both rollout proxies passed the task-container checks. Office received
118 upstream HTTP 200 responses and made seven file reads. After the
same reasoning payload appeared 97 times, the agent process was stopped
and the verifier reported 1/119 checks and reward 0.0067. Web received
18 upstream HTTP 200 responses and produced an HTML artifact. CodeBuddy
reached the 18-turn cap, and the verifier captured eight screenshots.
Web rubric grading has no valid score. WorkBuddy appended an extra
`/v1` to the Gemini API path, and a direct probe of the corrected endpoint
from the Web task image returned a region restriction. OpenRouter also
reported that the same model was unavailable in the region.

On 2026-11-19, launched `workbuddy-qwen36-flash-office-20261119` on
the Spark for all 50 Office tasks, serially, using Clover's task list,
CodeBuddy 2.109.3, one attempt, 48 turns, same context settings and task
timeouts, thinking and reasoning passback, and deterministic verification.
LLM rubric judging is deferred. The provider/model differ; the Qwen runner
stops after three rate-limited retries instead of Clover's indefinite retry.
The task container reached the Qwen proxy route, and the first task received
three HTTP 200 model responses. Its verification and benchmark results remain
pending. The rule runner did not copy container verifier files before reading
them, so completed Qwen trials initially received judge errors. A transfer fix
passed a focused simulated test and produced valid scores for tasks 12 through
50. All 50 rollouts finished with runner exit 0 on 2026-11-19; 39 scores were
collected by the fixed verifier, averaging 70.80% on that subset. One original
untruncated verifier log recovered 22/22 for channel-period comparison. Other
early task workspaces were not archived and their verifier stdout was truncated.
`experiments/workbuddy/experiments/qwen36-flash-office-2026-11-19/`.

On 2026-11-19, started `workbuddy-qwen36-office-recovery-20261119` on the
Spark to rerun the ten Qwen Office tasks whose scores were lost. The original
50 trial records remain unchanged. The runner uses the same Qwen/CodeBuddy
settings, checks each repaired verifier result, and stops on infrastructure or
verifier errors. First task reached the proxy and received HTTP 200; no
replacement scores had completed at launch. Checkpoints are under
`results/qwen36-flash-office-recovery/queue.jsonl` in the Spark WorkBuddy
checkout. Comparison compiler and recovery code:
`experiments/workbuddy/experiments/qwen36-flash-office-2026-11-19/rerun/`.
Use all 50 task-matched deterministic scores after completion, explicitly label
the ten replacement attempts, and assess deferred rubric grading separately.
All ten recovery trials completed with valid scores and the runner exited 0.
The 50-task equal-weight deterministic means are Clover 74.44% and Qwen
3.6-Flash 72.14%, a 2.30 percentage-point Clover lead. Qwen consists of 39
original fixed-verifier scores, one recovered verifier log, and ten fresh
replacement attempts. Both are single attempts per scored task; providers
differ, and Qwen rubric judging remains deferred. Results:
`experiments/workbuddy/experiments/qwen36-flash-office-2026-11-19/rerun/comparison/`.

### Clover WorkBuddy Bench Office batch

On 2026-11-16, launched ten selected Office v1.0 tasks in
`workbuddy-clover-office10` on the Spark, with one trial at a time.
The batch uses the task-native deterministic checks with rubric judging
disabled. CodeBuddy is capped at 22 turns, 8,192 output tokens per request,
and six minutes of rollout per task. The Office task image reached the
batch proxy and received HTTP 200 before launch. Results are staged under
`~/diffusion-demo/runs/workbuddy-smoke/results/clover-office10-rule/`.
All ten trials produced deterministic scores in 14m 50s. The equal-weight
task mean was 52.0%. Weekly ticket reporting was the sole full pass, two
tasks scored zero, and six rollouts hit the turn cap. Proxy logs recorded
204 HTTP 200 responses and one HTTP 400. Per-task rows:
`experiments/workbuddy/experiments/office10-rule-2026-11-16/scores.json`.

Staged `configs/models/qwen-judge.yaml` and
`configs/jobs/clover-office-qwen-smoke.yaml` in the Spark WorkBuddy checkout.
The one-task job selects `ticket-weekly-L3-010` for in-container Qwen3.6-Plus
judging. The saved DashScope key is plan-specific and was rejected by the
standard Beijing, Singapore, and Hong Kong API endpoints. Alibaba documents
the plan-specific endpoints for interactive tools. The judge smoke is pending
a general-purpose Model Studio key and its matching endpoint.

The Singapore Token Plan endpoint served Qwen3.7-Plus and Qwen3.8-Max,
but denied Qwen3.6-Plus with HTTP 403 `AccessDenied.Unpurchased`. A single
interactive request per supported model used the nine weekly ticket rubrics
against the same saved workbook evidence and an aggregate-only control.
They agreed on 17/18 verdicts. Plus correctly withheld the duplicate-handling
pass where there were no traceable record IDs. Max took 4.29 s and 189 output
tokens versus 5.92 s and 277 for Plus, with 1,482 input tokens each.
The automated judge preflight failed before rollout because the credential
loader included an endpoint assignment in the authorization value. That
diagnostic exposed the credential. Rotate the key before further use.
Alibaba limits Token Plan to interactive use and reports actual credits in
the console. An automated rubric run still needs an eligible API route.
The replacement key is also Token Plan. An interactive Qwen3.7-Plus
completion returned HTTP 200, and the Spark judge model config now selects
`qwen3.7-plus`. The weekly ticket judge job remains staged.

### Clover WorkBuddy full Web and Office rollout

On 2026-11-16, launched one attempt per task across all 50 Office v1.0 and
70 Web v1.0 tasks. The detached Spark runner
`workbuddy-clover-full-deferred-v2` runs Office then Web with one active
Clover trial, the published task timeouts, a 48-turn CodeBuddy cap, and an
8,192-token output cap per request. Both archives passed SHA-256 checks.
The runner adapts the task Dockerfiles to native ARM and leaves native
verifiers enabled for deterministic checks and evidence capture.
LLM judging is disabled. The job slugs are
`clover-office-full-deferred` and `clover-web-full-deferred`. The Spark
checkout's `results/` directory holds the task artifacts and verifier evidence,
and its Docker daemon retains the task images for replay. Later,
validate native judge-only replay on a saved trial from each track before
grading the full batch.
The Office task container passed the proxy health check and its first live
trial received Clover HTTP 200 responses. The queued Web job passed dry-run
validation with its judge disabled. Full-run verifier outputs were still
pending at the launch check.

On 2026-11-17, Office was complete at 50/50. All tasks had deterministic
scores, with a 39.01% equal-weight mean, two full passes, 19 zeros, and
14 agent timeouts. Raw deliverables were archived for 31 tasks. Web was
still running at 21/70 finished trials. Every finished Web trial reached
evidence capture, then the verifier raised an error at the required
LLM/VLM judge stage because no judge route was configured. No Web rewards
were emitted. At that check, 13 Web workspace archives were present.
The Web queue exited on 2026-11-17 at 09:58 Taipei time with all 70 distinct
trials finished. The required LLM/VLM stage raised the missing-route error
on all 70, so none emitted a Web reward. Thirteen workspace archives were
present at the final check.

For deferred grading, the Spark now has `configs/models/luna-judge.yaml`
staged for GPT-6 Luna via the OpenAI API. The existing OpenRouter credential
returned HTTP 403 for Luna due to region availability, and no dedicated
OpenAI API key file was present. Office has extracted rubric evidence for
34 trials. Web has 13 workspace archives and nonempty patches, and eight
trials have saved screenshots. Once a supported Luna route is available,
replay the native judges on one saved submission per track before grading
the rest.

Codex CLI invoked GPT-6 Luna through the existing sign-in. A deferred
grading smoke used the saved Office weekly ticket workbook evidence and Web
chart repair patch and screenshots, with a single schema-checked response
per trial. Luna passed 7/9 Office rubric items for a weighted score of
96.67%, and passed 5/6 assessed Web items. The Web smoke did not reproduce
native browser-agent judging or emit a final score. Verdicts are under
`experiments/workbuddy/experiments/full-rollout-2026-11-16/luna-codex-smoke/`.
Automatic approval review blocked the remaining evidence upload pending
explicit authorization for the batch. The user approved the remaining
33 Office and 12 Web submissions, and all 45 Codex grading calls completed.
Office has combined scores for 50/50 trials, with a 37.50% equal-weight
mean, one full pass, and 19 zeros. Luna verdicts contributed on 31 trials.
For the other 19, every rubric lacked required evidence and failed under
the native missing-artifact rule. Web has six resolved scores and seven
score intervals across the 13 preserved submissions, with nine native
browser-agent checks pending. The 57 tasks without a saved workspace or
patch remain unscored. This used a structured Codex response per saved
trial with original rubric IDs and offline scoring, rather than the
native model-judge request path. Output:
`experiments/workbuddy/experiments/full-rollout-2026-11-16/luna-codex-grading/`.

On 2026-11-17, started the full 120-task rerun in Spark runner
`workbuddy-clover-full-uncapped`, Office first and then Web, one trial at
a time. The new Clover route strips all explicit completion-token budget
fields before sending requests. Both jobs passed dry run. A task-container
probe sent `max_tokens=1`; the final upstream body omitted it and Clover
returned 60 completion tokens with a normal stop. The first real Office
calls also reached Clover with no limit fields and returned HTTP 200.
Server limits, the 48-turn harness cap, task timeouts, and deferred LLM
grading still apply. The Web verifier now also archives the whole workspace
excluding Git metadata and node_modules to improve replay coverage. The
previous trial results remain under their original job slugs.

The user stopped the uncapped rerun on 2026-11-17. The runner and active
task container exited, with 35 Office results saved, 32 of them reporting
zero output tokens. Web never started. The Office proxy recorded 339
HTTP 200s and 238 HTTP 429s, including 231 consecutive 429s after the
last success at 17:11:02 Taipei time. A direct API probe after stopping
both containers still returned HTTP 429, `router_error`, with
`Retry-After: 1` and the message that the user concurrency limit of one
was occupied. The active request or stale reservation is unverified.

The replacement Clover key with fresh routing ID
`workbuddy-824a255331c9` passed three direct serial streaming requests.
In a simultaneous pair, one returned HTTP 200 and the other returned the
same per-user concurrency limit of one with HTTP 429. The stopped
benchmark was not restarted and its routing config was not changed.

The serial replacement run started on 2026-11-17 in Spark container
`workbuddy-clover-full-serial` with the replacement key and fresh user ID.
It queues all 50 Office then 70 Web tasks, one task and one upstream
request at a time. Each attempt has a stable, distinct session ID.
The proxy retries 429s without consuming its normal retry budget, and
the queue repeats the same task if rate limiting prevents a usable
rollout. Completed task results are checkpointed in
`~/diffusion-demo/runs/workbuddy-smoke/results/clover-workbuddy-serial/queue.jsonl`.
Explicit completion caps stay omitted and rubric grading stays deferred.
Live Office requests returned HTTP 200. A local upstream simulation
injected eight 429s and verified recovery for streaming and nonstreaming
requests with peak concurrency one.

During five-minute checks, the serial rerun completed 7 of 50 Office
trials before persistent HTTP 429 responses on cross-week dashboard
migration. The queue started a second attempt after the first timed out.
At 18:48 Taipei time on 2026-11-17, the second attempt had 65 HTTP 429
responses and no HTTP 200 responses. The runner was still retrying.

The serial run exited successfully on 2026-11-18 at 03:39 Taipei time.
All 50 Office and 70 Web trials were checkpointed, with six task attempts
restarted after HTTP 429. Office had deterministic scores for all 50
trials, a 74.44% mean, two full passes, and no zero scores. Web preserved
all 70 full workspace archives. Its verifier reported runtime errors on
all 70 and emitted no final rewards. On 2026-11-18, the user approved
deferred GPT-6 Luna grading through Codex CLI for this run. All 50 Office
and 70 Web rubric responses passed ID validation. Office has a 70.40%
combined equal-weight mean, one full pass, and no zero scores. Forty-nine
Office tasks used Luna verdicts in the score and one used the native
missing-artifact rule for every rubric. Web has 35 resolved task scores
and 35 score ranges, giving aggregate bounds of 18.57% to 46.86%. Forty-eight
browser-agent checks were left for live replay, and 27 Web evidence
packets had oversized fields shortened before grading. Results:
`experiments/workbuddy/experiments/full-rollout-2026-11-17/luna-codex-grading/`.

On 2026-11-18, replayed all 48 pending Web browser checks across 21 saved
workspaces. Native Playwright trace capture and targeted browser probes
reviewed by Luna through Codex established 13 passes and 13 failures.
The remaining 22 browser checks lacked conclusive evidence, and 15 of
those can still affect a task score. Web now has 47 resolved task scores
and 23 ranges. Applying the WorkBuddy rule that unsubmitted checks
default to failure gives a conservative mean of 25.00% over all 70 tasks,
with an evidence-supported range of 25.00% to 38.57%. This deferred
replay did not use the native browser-agent judge. Results:
`experiments/workbuddy/experiments/full-rollout-2026-11-17/luna-codex-browser-replay/`.

The browser follow-up diagnosed all 22 inconclusive checks and resolved the
15 that could affect a task score: nine passed and six failed. The other
seven belong to tasks already fixed at zero. Source-directed Playwright
checks corrected route, selector, keyboard, and evidence capture problems.
They also confirmed that booking cannot advance after valid selections,
CSV exports retain an unmapped column under an empty key, routing trace
order can disagree with the visible precedence, and a rule field change
can leave a stale numeric value active. The PWA transition was verified with
controlled connectivity events and a mocked successful sync response.
The conservative Web mean is now 26.14%, with bounds of 26.14% to 36.86%.
Web has 51 resolved task scores. Only text and visual checks contribute to
the remaining 19 ranges. Results and observations:
`experiments/workbuddy/experiments/full-rollout-2026-11-17/luna-codex-browser-followup/`.

After Web exited, a direct Clover replay of the Office crypto-backtest
conversation preserved all 11 recorded tool-call/result pairs and used
reconstructed system and tool definitions. Three parsed HTTP 200 responses
included two identical reasoning-only streams that exhausted 8,192 tokens
and one different stream that returned a Bash call. None matched the
historical reasoning payload repeated 475 times under CodeBuddy.
At 32,768 completion tokens, all three direct replays returned a Bash
call. One used 20,124 completion tokens, and two used 4,701 each. This
checked the next tool-call response only. No benchmark job caps changed.
On 2026-11-17, the Office run had finished all 50 trials, with 14 errors
reported in its job summary. The Web run was still active; its latest saved
summary showed 15 completed trials, all with errors. These are native run
statuses, not completed Qwen rubric scores. The available Qwen credential is
Token Plan, which does not permit automated batch judging; an eligible
general-purpose API key and endpoint are needed for judge-only replay.

### Clover Terminal-Bench 4.1 pilot

On 2026-11-16, started a three-task Terminal-Bench 4.1.0 pilot with Harbor
0.26.0, mini-swe-agent 2.4.6, and a 60-minute agent cap. The Clover Chat
Completions API serves inference with both thinking flags enabled. The DGX
Spark runs native ARM task containers built from the pinned task Dockerfiles.
The published x86-64 image failed on Spark, and x86 emulation on the Mac
running Codex failed during agent installation. The API streaming smoke and
multi-turn shell loop passed. After the first task established API connectivity,
`layout-config-recreation` and `vf2-speedup-networkx` were started in parallel.
The API rejected overlapping requests with a concurrency limit of one per
user. Retries used a 4,096-token completion budget and shorter shell
observations. All three final attempts failed before verification on the
131,072-token context limit. Job wall times were 20m 46s for `music-harmony`,
32m 43s for `layout-config-recreation`, and 2m 51s for
`vf2-speedup-networkx`. Logs and trajectories were copied to
`bench/results/clover-terminal-bench-4.1-pilot/`. The next pilot would need
context compaction and serial requests under this API user ID.

The follow-up adds request-side context compaction in `bench/terminal_bench/`.
Offline replay of all three failing trajectories kept the task prompt and
last tool turn, preserved call/result pairing, and stayed below the byte
budget. The serial Spark rerun against the same API hit no context errors.
All three agents entered a loop with at least 100 identical consecutive
action/result pairs and were interrupted before grading. Job wall times were
16m 57s for `music-harmony` (658 model turns), 5m 29s for
`layout-config-recreation` (219), and 12m 59s for `vf2-speedup-networkx` (435).
Logs are in `bench/results/clover-terminal-bench-4.1-compaction/`. Next step:
smoke-test Harbor's Pi adapter against the same API, including request headers
and thinking flags on regular and compaction calls, before rerunning the pilot.

Pi 0.85.1 passed two normal calls and one forced compaction call against the
Clover API with HTTP 200, bearer auth, both routing headers, and both thinking
flags. `bench/terminal_bench/pi_agent.py` uses Harbor's Pi adapter and a
loopback relay to apply the same request settings to both call types. The
first Pi pass exposed x86-64 verifier images despite native ARM agent builds.
`bench/terminal_bench/Dockerfile.harbor` applies `--force-build` to separate
verifiers so the Spark can build both images from the pinned Dockerfiles.
The serial ARM rerun graded all three tasks at reward 0. `music-harmony`
took 9m 18s and was interrupted after 103 identical tool actions. Its loop
started before Pi's first compaction. `layout-config-recreation` took 39m 20s
and matched 29.59% of pixels against 98% required. `vf2-speedup-networkx`
took 1m 42s and failed the verifier tests. Layout and NetworkX reached a
length stop before grading. All 554 API calls returned HTTP 200, including
eight summary calls with the same required headers and flags. Artifacts:
`bench/results/clover-terminal-bench-4.1-pi-arm/`.

Pi now requests up to 32,768 output tokens and starts compaction above 90,112
context tokens, leaving 8,192 tokens of headroom beyond the output budget.
The updated Spark smoke test returned HTTP 200 on two normal calls and one
compaction call with `max_tokens=32768`. Benchmark scores above used 8,192.
The serial Spark rerun at 32K graded all three tasks at reward 0 with no
Harbor exceptions. All 173 Clover requests returned HTTP 200 and all normal
turns requested 32,768 output tokens. `music-harmony` took 7m 32s and broke out
of a 64-turn identical action/result streak before submitting. Its repeated
PDF command differed from the one in the 8K run. `layout-config-recreation`
took 4m 9s, repeated at most three consecutive action/result pairs, and hit
the 32K output ceiling. `vf2-speedup-networkx` took 1m 23s, made one tool call,
and exhausted the 32K output budget on its second model response. Artifacts:
`bench/results/clover-terminal-bench-4.1-pi-32k/`.

The MiniCPM-V 4.7 35B-A3B comparison uses the cached Q4_K_M thinking GGUF
served by llama.cpp on the Spark, in text-only mode without DSpark. Pi uses
the same tasks, 32K output limit, 60-minute agent cap, and serial execution.
A private Unix-socket gateway connects the isolated task containers to the
local model server. The smoke test passed a shell round trip and compaction.
MiniCPM returns an empty Pi summary with thinking enabled, so this arm keeps
thinking on for normal turns and turns it off for summaries. All three
MiniCPM trials graded at 0 with no Harbor exceptions. Their wall times were
4m 25s (`music-harmony`), 42m 57s (`layout-config-recreation`), and 13m 33s
(`vf2-speedup-networkx`). No consecutive identical tool actions appeared
across 116 calls. All model turns ended before the 32K cap, with a maximum of
3,201 output tokens. No benchmark trial needed compaction. This is one run
of each task, with local quantized MiniCPM versus hosted Clover. Layout's
long wall time included a brute-force task-side Python search. Artifacts:
`bench/results/minicpm-terminal-bench-4.1-pi-32k/`. The MiniCPM server and its
gateway remain loaded on the Spark.

Offline trace comparison on 2026-11-17 found a 64-turn Clover music streak
from assistant turns 59 through 122, with identical recorded thinking text
and command arguments. Pi compacted after turn 71 without breaking the streak.
Clover's two 32K length stops consisted entirely of the response field Pi
labels thinking, with repeated text and no tool action or final answer.
MiniCPM returned ordinary stop reasons in all three trials. This localizes
the difference to the responses reaching Pi in these runs. The model and
serving stack differed together, so the upstream cause remains unisolated.

For a checkpoint-matched replay, the first targets are NetworkX assistant
turn 2 and music assistant turn 60 (before the first compaction). The saved
Pi sessions preserve their message histories, but the relay audit did not
record the exact outbound JSON bodies. The Spark cache check found Clover
Q4_K_M GGUF files only, including an AR-only conversion. The hosted metadata
checks returned HTTP 429 for `/v1/models` and 404 for `/get_model_info`, so the
deployed weight revision and decoding settings are still unknown. No matched
replay was run. Obtain the deployed revision or hashes, precision, and
decoding configuration before staging the local artifact and capturing the
wire requests for a controlled comparison.

### DGX Spark benchmark setup

Run active benchmarks in Docker on the DGX Spark. The Colab setup scripts have
been retired. `bench/README.md` records the container, model cache, and native
build steps. Nemotron is the active target. The Gemma build and generation smoke
test are deferred.
On 2026-11-13 the Nemotron runner passed a one-case smoke test in `jepa:0.1`
using cached weights. `ar`, `linear_spec`, and `diffusion` each returned `4`
for `2 + 2` and stopped at EOS. The runner converts the pinned model's absolute
cache crop length to the negative drop count accepted by Transformers 5.

### Clover CLI preview

The CLI now has its own source-of-truth repository:
https://github.com/BoomMccloud/clover-cli, checked out at
`/Users/jasonbxu/Documents/GitHub/clover-cli`. Initial commit `3e5c7fb` on `main`
contains version 0.1.8, standalone install instructions, and 19 passing tests.
Make future CLI changes there; this repository's `packages/diffuspace-cli/` copy
is the original handoff snapshot. The standalone CLI was updated to 0.1.9 using
`https://api.diffuspace.ai/v1` without a custom port, with all 19 tests and a live
streaming check passing. No npm publishing or GitHub release was done.


The current user-requested deliverable is a local npm package under
`packages/diffuspace-cli/`. The command `diffuspace clover` prompts only for an API
key on first run, generates a dedicated Codex profile, starts an authenticated
loopback adapter, and launches Codex. Endpoint and model ID are fixed; context is
128,000 tokens. Claude Code is out of scope. No npm publishing is authorized.

Acceptance: preserve existing user configuration, translate namespaced function
tools and text tool results, stream responses, complete a real MCP tool and shell
file-write round trip, and produce a locally installable tarball. Focused checks:
`npm test --prefix packages/diffuspace-cli` and
`npm run check --prefix packages/diffuspace-cli`. Verified on 2026-10-26:
12 focused tests passed; the launcher completed a real namespaced MCP echo call,
shell file write/read, and final response through Clover on Codex 0.164.0. The
local tarball `packages/diffuspace-cli/diffuspace-cli-0.1.0.tgz` installed cleanly
in an isolated npm prefix. Next step: user tests `diffuspace clover` interactively;
the package is not published. Patch 0.1.1 disables inherited apps/plugins only in
the Clover profile after the normal 345-tool catalog caused upstream failure;
a separate request with normal user configuration then passed at 9,564 input
tokens. All 13 focused tests pass. Existing user sessions need to restart the
launcher to load the patched adapter. Patch 0.1.2 adds ASCII Clover branding,
first-release onboarding, a fixed upfront JSON reminder, five rotating launch
tips, and feedback/collaboration links to https://huggingface.co/Diffuspace.
Duplicate adapter stderr notices are suppressed; unsupported JSON constraints
still return explicit HTTP 400 errors. All 19 focused tests pass, including
launcher stdout preservation and once-per-session messaging. `diffuspace preview`
shows all launch variants without a key or network request. Patch 0.1.3
capitalizes Clover in display branding and diagnostic prefixes; the command
remains `diffuspace clover`. Patch 0.1.4 uses the user-provided four-leaf ASCII
Clover design with a trailing stem. Patch 0.1.5 places the Clover/by DiffuSpace
branding beside the artwork again. Patch 0.1.6 adds `diffuspace preview --designs`
for the two alternate curved-stem designs, artwork-only and a side information
panel. Patch 0.1.7 adopts variant 2 artwork for startup with only Clover/by DiffuSpace
beside it; the existing release/version/context/Codex line remains below.
Patch 0.1.8 adds the user-provided horizontal leaf veins to the artwork.
The benchmark objective below remains separate.

### LLM-JEPA on a diffusion LM

Added 2026-11-12. The question is whether LLM-JEPA fine-tuning (Huang, LeCun,
Balestriero 2025; reference code `galilai-group/llm-jepa`) helps a diffusion LM
more than it helps AR decoding. Clover can't be used yet: the public GGUF isn't
trainable, and QLoRA needs a BF16 checkpoint with a diffusion training forward.
QLoRA is deferred. JEPA comes first, with plain bf16 LoRA.

The model is Nemotron-Labs-Diffusion-3B at the runner's pinned revision. One set
of weights decodes as `ar`, `linear_spec` and `diffusion`, so one fine-tune can
show whether a gain is specific to diffusion. Its remote code has what training
needs: a gradient-capable forward, a per-layer `diffusion_lm` switch between
bidirectional and causal attention, `output_last_hidden_states_only` for
embeddings, and standard `nn.Linear` projections for PEFT. Bidirectional mode
takes no attention mask, so train at batch 1 rather than padding.

Design: two LoRA arms with the same data, steps and seeds. Both train the AR loss
and a diffusion loss on one answer block, matching how `generate` decodes. The
JEPA arm adds `lbd * (1 - cos)` between separately encoded text and code views.
Score both checkpoints in every decoding mode. Tasks are the reference repo's
NL-RX-SYNTH, NL-RX-TURK, GSM8K and Spider, scored as that repo does. Use 2 or 3
seeds, because the deltas will be small.

Smoke test: `bench/jepa/smoke.py`, written and checked locally on 2026-11-12
(compiles, chat-template views and tokenization verified) but not yet run on a
GPU. It runs on the DGX Spark (`jx25520@192.168.3.3`, GB10, 121 GB unified
memory, arm64), in a docker image built from `bench/jepa/Dockerfile` (see
Accelerator sessions). The test plan is the
Claude Doc "LLM-JEPA on a diffusion LM: test plan"
(https://claude.ai/artifact/HX8FG4gKDh714H8jVkKoTa). Acceptance: 50 steps on
`synth` fit in memory, the JEPA loss falls, and `ar` and `diffusion` outputs
still stop and parse; record seconds per step to size the main runs.

Passed on 2026-11-12 on the Spark (NGC PyTorch 26.10, torch 2.15, transformers
5.22.2, peft 0.21.2; GB10 runs on the image's sm_120 kernels). It needed one fix:
transformers 5 `DynamicCache.crop` only takes a negative count of tokens to drop.
Both arms fit at about 8.5 GB peak. With `--lbd 0.5` the JEPA loss fell from 0.55
to 0.007 in 50 steps. Both arms stopped on 20 of 20 cases in both modes and
scored 3/20 exact in `ar` and 1/20 in `diffusion`, up from 0/20 for the
untrained model, which explains instead of answering. Median step time at
grad-accum 4 was 1.6 s for JEPA and 0.9 s for baseline, so one epoch of the
8,000 NL-RX-SYNTH training examples is about 53 and 29 minutes. Rows are in
`bench/results/jepa-smoke-2026-11-12/`.

Plan step 2 (pick lbd) finished on 2026-11-13: lbd = 2.0 is frozen. Both JEPA arms
trained one epoch (7,500 NL-RX-SYNTH examples, 1,875 steps, seed 82) and were
scored on 500 cases held out of training with `--val-cases 500 --val-seed 0`,
never the test set. The rule, set before scoring, was the higher mean of `ar` and
`diffusion` exact match. lbd 2.0 scored 75.8% `ar` and 51.2% `diffusion` (mean
63.5); lbd 0.5 scored 77.8% and 39.2% (mean 58.5). Paired by case, 2.0 minus 0.5
was -2.0 points in `ar` (95% CI -5.2 to +1.0) and +12.0 in `diffusion` (+6.8 to
+17.2). One seed and no baseline arm, so this picks lbd and says nothing yet
about the hypothesis. The reference repo trains 4 epochs; this pick used 1.
Both arms ran side by side at about 2.9 s per step. Rows are in
`bench/results/jepa-lbd-pick-2026-11-13/`; adapters stay on the Spark under
`~/diffusion-demo/runs/lbd-pick/`.

Plan step 3 (main runs) started 2026-11-13 00:28 UTC with 1 epoch per run, the
user's choice. `bench/jepa/run_main.sh` runs baseline (lbd 0), JEPA bidirectional
and JEPA causal (lbd 2.0) for seeds 82, 23, 37, two docker jobs at a time on the
Spark, resumable by `run.json`. Every run trains on the full training set and
scores the full test set in `ar` and `diffusion`; the untrained model is scored on
200 cases per task in the seed-82 baseline job. GSM8K is scored as llm-jepa does
(the `#### ` answer) with a 384-token cap, since the reference's 128 would cut
long answers. A full GSM8K test scoring is about 3.5 h per checkpoint (6.2 s per
case in `ar`, 3.3 in `diffusion`), so GSM8K would use its first 500 test cases
(`GSM8K_EVAL_CASES=500`).

Stopped on 2026-11-13 at 10:10 UTC, by the user's choice, after seed 82 finished
on NL-RX-SYNTH and NL-RX-TURK. GSM8K never started. Seed 23's two partial SYNTH
runs were moved to `~/diffusion-demo/runs/aborted-s23/` on the Spark and must not
be used. Result: no support for the hypothesis from one seed. The interaction was
never positive; on content accuracy (exact, or right but running on) JEPA cut
`diffusion` by 6.5 to 10.4 points in all four arm-task pairs while `ar` moved -1.0
to +2.8. Write-up: `docs/jepa_diffusion_findings.md`; rows:
`bench/results/jepa-main/`. The Spark is idle. If this resumes, the next steps are
listed at the end of the findings doc, starting with seeds 23 and 37.

Caveats. `linear_spec_generate` turns every attached PEFT adapter off during
causal verification, so merge the LoRA before scoring that mode.
`bench/nemotron_runner.py` never loads the optional `linear_spec_lora` drafter
adapter, so earlier `linear_spec` numbers were measured without it.


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
  decoding method from the model. Runner: `bench/nemotron_runner.py`. The 3B weights have been used on the DGX Spark for JEPA.
- **Gemma 4 26B A4B** AR through `llama-cpp-python` against **DiffusionGemma 26B
  A4B** through the instrumented protocol-v2 `llama-diffusion-cli`. Runners:
  `bench/gemma_runtimes.py` and `bench/diffusion_runtime.py`. Previously run on A100. The pinned runner and tokenizer still need a DGX Spark smoke test.

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
system pair goes first. Start with Nemotron-3B on the DGX Spark.

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
- Realistic-workload screens on 2026-09-28 and 2026-09-29, batch 1 only. On
  Nemotron 3B and 14B, plain diffusion was 2x to 3x faster than AR but never
  more accurate, and it was never faster than linear speculation, which kept
  AR's output at 2.3x to 3.6x lower latency. This held for BFCL live tool
  calls, homework grading, and grid path planning
  (`docs/nemotron_bfcl_screen_findings.md`,
  `docs/nemotron_homework_planning_findings.md`).
- A seven-case Gemma smoke test found Gemma 4 AR without thinking as accurate
  as DiffusionGemma on easy items and 10x to 50x faster. DiffusionGemma always
  reasons, so that gap is reasoning against none. The subset run it prepared
  was not run (`docs/gemma_homework_planning_smoke_findings.md`).
- On 2026-10-16 a streaming probe of the hosted diffusion endpoint
  (`qwen36-iter22000-blk16-arverify-best`; 72 requests, thinking off, two reps
  per cell) decoded at about 410 tok/s per request alone, 280 at
  4 concurrent, and 210 at 10, with aggregate throughput rising from about 335
  to 1,550 tok/s. Time to first token held at 0.85 s. Output length from 1k to
  4.5k tokens didn't change the rate. Content did: code ran at 706 tok/s and
  prose at 270 to 310 alone. The 150 to 200 tok/s seen in HLE came from its 10
  concurrent workers (`bench/tps/run_tps.py`).
- On 2026-10-20 a synthetic-data benchmark (`bench/synthdata`, about 15,500
  generations) compared the hosted dLLM with Qwen3.6-35B-A3B AR on fictional
  Chinese inpatient narratives and JSON records. At each model's best
  temperature, they tied on clean and distinct records per request, so the
  pre-registered "dLLM yields more" claim failed. The dLLM is varied at 0.6,
  where Qwen needs 1.0 to 1.2, but it is less often clean. Its inconsistency
  rises with narrative length, and it is unusable above 0.8
  (`docs/synthdata_benchmark_findings.md`).
- On 2026-10-21 a long-range consistency run (`bench/tabdlm/longrange.py`, 348 requests of 10 to
  50 person records) didn't confirm that the dLLM drifts more than Qwen over long output. Both
  models drift. The dLLM drifted 21 points more on returned records when each biography came last,
  but putting the biography first removed the gap. Its main text-first error was computing ages
  from 2024. It was 2.4x to 3.3x faster per request (`docs/tabdlm_longrange_findings.md`).
- On 2026-10-21 a batch-wide constraint run (`bench/tabdlm/constraints.py`, 360 requests of 30
  records, both arms at 0.6) found no planning advantage for the dLLM. Both models passed quota,
  sorting and balance rules and failed a forward reference. Qwen hit an exact age sum 43% of the
  time against 3%, mostly by setting every age to 40. The dLLM was about 4x faster
  (`docs/tabdlm_constraints_findings.md`).
- On 2026-10-22 a tax-form loop screen (`bench/taxloop/run.py`, 120 requests) found no
  bidirectional advantage. When five 1040 lines had to be written before the forms that compute
  them, both models closed about 23% of those links. The dLLM scored higher overall only because it
  broke the requested order on 10 of 30 answers and wrote the dependent forms first. In dependency
  order both closed 98%. A stricter order instruction didn't stop the reordering, and counting
  reordered answers as failures put the dLLM 8.6 points behind Qwen. A follow-up
  (`bench/taxloop/gap.py`, 600 requests) put a memo of 0 to 1,000 words between one forward value and
  its source. Neither model improved at short gaps, and the dLLM never led. The closest case is
  still about 25 tokens apart, past one 16-token block. Removing the forward references stopped the
  reordering (0 of 30). Temperature 0 isn't deterministic on the hosted dLLM: three runs gave 3, 8
  and 8 reorderings and no identical answers. A 600-request replication on 150 new cases
  confirmed it: crediting reordered answers, the dLLM led by 18 and 45 points. Failing them, it
  trailed by 5 and 10. With the order kept, the two were within 3 points (`docs/taxloop_findings.md`).

- On 2026-11-12 a local DGX Spark screen found the official Clover GGUFs unloadable on any public
  llama.cpp: the card's `draft-self` flag was never merged, `clover_moe.expert_shared_count` is
  missing, and 120 diffusion GDN tensors aren't accepted. Bartowski's AR-only conversion loads.
  Clover in AR mode decoded at 62 tok/s against 65 for the Qwen3.6 GGUF on the same build, and
  Qwen3.6 NVFP4 with MTP on vLLM reached 105 tok/s alone and about 630 tok/s total at 32. GSM8K was
  97 to 99 of 100 for every arm, with Clover using 2.4x to 2.7x fewer tokens
  MiniCPM-V 4.7 35B-A3B Q4_K_M was the fastest GGUF at 78 tok/s; its DSpark draft helped only on
  math and code at one request and cut total throughput 32% to 42% at 8 and 32 concurrent.
  (`docs/clover_gguf_llamacpp_findings.md`, `docs/clover_vs_qwen36_spark_findings.md`).
- On 2026-11-13 an LLM-JEPA LoRA fine-tune of Nemotron-Labs-Diffusion-3B (one seed, 1 epoch,
  lbd 2.0) didn't help diffusion decoding more than AR on NL-RX-SYNTH or NL-RX-TURK. JEPA left
  `ar` within -1 to +3 points and cut `diffusion` content accuracy by 6.5 to 10.4 points, with
  more decoding passes per answer. Diffusion exact match on these short answers is dominated by
  whether the model stops inside its 32-token block (overruns 1% to 17%, AR under 1%), and it
  varies a lot between training runs (`docs/jepa_diffusion_findings.md`).

Do not carry these numbers over to the realistic workloads. They are the
hypotheses the new comparison tests.

## Authoritative working files

- `AGENTS.md`: active objective, verified status, and immediate next task.
- `bench/README.md`: how to stage and run each model runtime on the DGX Spark, and the
  durable runner constraints.
- `bench/gemma_runtimes.py`: AR `llama-cpp-python` calls and the native
  DiffusionGemma session, tokenizer helper, transcript parsing, and GPU identity.
- `bench/diffusion_runtime.py`: resident DiffusionGemma worker behind a loopback
  API.
- `bench/nemotron_runner.py`: Nemotron three-mode runner and OpenRouter AR arm.
- `bench/native/`: pinned `llama.cpp` patch, build, and CUDA probes.
- `bench/tau2/`: τ³-bench runner and the patch that swaps its OpenAI grader for
  Gemini. `bench/hle/`: HLE text-only runner and the empty-answer probe.
- `bench/tps/run_tps.py`: streaming probe that splits time to first token from
  decode tok/s across output lengths and concurrency.
- `bench/synthdata/`: synthetic-data benchmark (clean and distinct records per
  request) with resumable generate, judge, score and audit stages.
- `bench/taxloop/`: five fictional tax forms with four cross-form loops, written in form order or
  dependency order.
- `bench/tabdlm/`: few-shot structured-record consistency on TabDLM's ProfileBio and Amazon data,
  run against the synthdata arms.
- `bench/jepa/smoke.py`: LLM-JEPA LoRA smoke test on Nemotron-Labs-Diffusion-3B, AR plus
  block-diffusion loss with an optional JEPA term (`--lbd 0` is the baseline arm).
  `bench/jepa/run_main.sh` queues the main runs in docker on the Spark; `bench/jepa/Dockerfile`
  builds the image.
- `.claude/skills/race-video/`: how to record a side-by-side race video of the
  diffusion model and an AR model on WebArena, WindTunnel, or MiniWoB++.
- `docs/*_findings.md`: what each earlier run established and its limits.

## Accelerator sessions

- On the DGX Spark and any other machine we own or share, run all work inside
  containers, never directly on the host. That covers Python, pip installs,
  model downloads, training, and builds. On the DGX Spark
  (`ssh jx25520@192.168.3.3` on the LAN, or `ssh jx25520@100.67.126.100` over
  Tailscale from anywhere) use docker with `--gpus all`; podman is not
  installed there. Do not install packages, change drivers, or edit system
  config on the host. Mount the repo and a cache directory into the container, and keep
  outputs on the mounted volume so they survive the container. The host only
  runs the container engine, ssh, rsync, and read-only checks such as
  `nvidia-smi`. On the Spark, the repo copy is `~/diffusion-demo` and the
  Hugging Face cache is `~/.cache/huggingface`.
- Treat a running accelerator session with a loaded model, compiled binary, or populated local cache as expensive state.
- Before stopping or closing such a session, ask the user whether they want to keep it running for additional tests. Explain what would need to be downloaded, compiled, or loaded again if the session is closed.
- Stop the session without asking only when the user has already explicitly instructed you to close it after the current work, or when leaving it running is not possible.
