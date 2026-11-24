# WPS Office five-task pilot

Status: all five selected tasks have been run locally with Clover, CodeBuddy,
and WPS. Their deterministic scores and comparison with the Spark baseline are
recorded below; these are diagnostic, single-attempt comparisons.

Goal: run Clover with CodeBuddy on five original Office tasks using a verified
WPS operation during each trial, then grade artifacts with the original
deterministic verifier and compare per-task with the existing serial run.
Preserve original inputs, task instructions, scoring and time limits. Record
which WPS operations were actually used, all failures, trajectories, artifacts,
and any unavoidable differences. Rule scores are partial-credit scores, not
full-task pass rates. LLM rubric grading is outside these baseline scores.

| Task | Existing rule score | Passed checks |
| --- | ---: | ---: |
| board-material-update-timeline-excel | 70.45% | 267/379 |
| drug-inventory-split-L2-006 | 100.00% | 15/15 |
| procurement-reconcile-L3-015 | 71.43% | 15/21 |
| safety-inspection-extract-L4-019 | 92.59% | 25/27 |
| ticket-weekly-L3-010 | 100.00% | 15/15 |

The existing five-task mean is 87.69%, with two full scores. These are one
attempt each, selected for a WPS pilot, not a representative benchmark sample.
Source: `~/diffusion-demo/runs/workbuddy-smoke/results/clover-workbuddy-serial/queue.jsonl`
and the result JSON paths it references on the Spark.

On 2026-11-18 WPS Office 12.1.29697 was installed on the Mac. Its bundled
`/Applications/wpsoffice.app/Contents/MacOS/wpscli --help` ran successfully
outside the execution sandbox and lists conversion, PDF and OCR commands, but
no workbook or slide editing command. Running `wpscli install --help` actually
installed its skill in the Claude Code, Copilot, Codex and Hermes directories;
the installer warns it overwrites existing skill files. The installed skill
describes PDF conversion, not general Office editing. No WPS installation was
found on the Spark and no WPS connector was available. WPS documents its local CLI for macOS and Windows;
the official cloud CLI mainly documents conversion, OCR and PDF operations.
WPS 365 MCP requires an application, permissions and user authorization. Its
actual editing capabilities and a secure connection to the isolated task
containers remain to be validated. Do not count file conversion alone as
WPS-based editing. Next: obtain an authorized WPS 365 editing endpoint or an
installed WPS desktop environment, inspect its actual tools, and smoke-test
one task and the native verifier before running all five. The third-party
`humoumou1215/wps-assistant` project claims a local JS add-in and MCP bridge,
but compatibility with this WPS build, safe isolation and CodeBuddy transport
have not been established; it is not an official WPS component. On 2026-11-18,
commit `dda67065086a46450d0aa72eab77954b61ba42d6` was cloned and built in
`/private/tmp/wps-assistant-pilot` with temporary Node 22.22.0. Eleven focused
registration and MCP tool tests passed against simulated WPS. The production
dependency audit reported three high-severity packages. No add-in has been
registered and no document accessed. The installer requires open WPS documents
to be closed before registration. The add-in was registered in the installed
global edition's WPS container, and a temporary loopback bridge started on port
18766 with data under `/private/tmp/wps-pilot-data`; no login service was
created. Its health endpoint is responding, but reports zero connected WPS
documents. On 2026-11-18 the user opened a disposable workbook at
`~/Documents/WPS Pilot Test.xlsx`. The bridge listed it, read A1, wrote
`WPS MCP smoke passed` to B1, read it back, and saved it via WPS; a separate
file read confirmed the value persisted. CodeBuddy 2.109.3, installed under
`/private/tmp/wps-pilot-cbc` with its own temporary home, reported the local
HTTP MCP server connected. This did not use Clover. CodeBuddy with Clover,
task isolation, a Spark-to-Mac connection and the original verifier still need
testing before any pilot trial. The bridge can execute generated JavaScript
and its own documentation says the guards are not a sandbox; do not expose
its unrestricted endpoint to benchmark containers without containment.

The one-task pilot uses `ticket-weekly-L3-010`. Its original workspace was
copied to `/private/tmp/wps-one-task/` on the Mac. The local DiffuSpace CLI
credential returned HTTP 401 against the earlier Spark Clover endpoint; its
documented `api.diffuspace.ai` endpoint returned HTTP 521. The old Spark
serial runner read a temporary key from `/dev/shm/workbuddy-clover-key` and
deleted it, and no saved replacement key was found at the checked paths. No
credential or model response was logged. A working Clover route remains
necessary; a restricted WPS tool interface and verifier handoff also remain
to be built and tested. No one-task pilot score has been produced.

Subsequently found `CLOVER_API_KEY` in the repository `.env`. The user's
streaming request to `43.107.54.53:31002` with that key returned HTTP 401
both from the Mac and from the Spark. The key was not printed or persisted
on the Spark during the probe. Its validity for other endpoints is unverified.
After the `.env` value was updated, the same request returned HTTP 200, 34
stream events, and a normal stop. This verifies API connectivity only; the
CodeBuddy-to-Clover-to-WPS path and the task verifier remain untested.

### Weekly-ticket proof of concept, 2026-11-18

Clover and CodeBuddy 2.109.3 used two scoped MCP tools: a read-only extraction
of the original workbook and a WPS writer restricted to a disposable output
workbook. The task ran on the Mac with built-in tools restricted, not in the
original task container. Clover read the input and requested a five-row weekly
summary. Its dates start on Sunday and several totals are repeated.

The writer initially failed because it called an unsupported WPS `Cells`
method. After stopping the agent, we changed the wrapper to use `Range`, then
replayed Clover's unchanged final write arguments. WPS saved the XLSX. The
original task's pytest checks, run in the retained baseline Docker image with
networking disabled, passed 2 of 15 checks (13.33%). The previous serial
CodeBuddy baseline passed 15 of 15 (100%). The repaired replay, data extraction,
and different execution environment mean this is a diagnostic result, not a
controlled or official harness comparison. See `weekly-ticket-smoke/` for
the workbook, model output, wrapper and result metadata. No other WPS tasks ran.

### Weekly-ticket rerun with contained computation

The writer preflight cleared and saved a marker, then WPS and an independent
disk read both confirmed it. Clover ran CodeBuddy with scoped WPS tools and a
Python tool that starts a fresh read-only Docker container with networking
disabled, resource limits, and the original task image and inputs. Clover
read the data, ran Python, wrote and saved the workbook through WPS, and read
it back without intervention. The original verifier passed 10/15 checks
(66.67%). All eight weekly plan and actual totals passed, as did the valid
XLSX and week-label checks. The four rate checks failed because Clover wrote
percentage-point values such as `72.7` as plain numbers instead of fractions
or percent strings; an extra total row failed the four-week row-count check.
The baseline scored 15/15. The agent ran on the Mac with restricted tools and
pre-opened WPS files, so this remains a single-task diagnostic rather than a
controlled harness comparison. Evidence is in `weekly-ticket-rerun/`.

### Weekly-ticket run with normal CodeBuddy tools and WPS

The agent ran in the retained original Spark task image with CodeBuddy 2.109.3,
normal Bash and file tools, the same task input and verifier, and a scoped WPS
MCP writer added. WPS itself ran on the Mac; Unix-socket SSH tunnels connected
the network-disabled task container to the scoped WPS writer and Clover proxy.
The additional task instruction required WPS output and noted that it would be
copied into the task workspace. One attempt scored 11/15: the writer used
`ClearContents`, which retained old date formatting and caused three numeric
totals to be stored as dates. The fourth failure was an extra total row.

After preserving that attempt, changed the writer to clear formatting as well,
and verified numeric and percentage cell formats independently. A fresh retry
scored 14/15 on both the WPS-saved workbook and the separate workbook CodeBuddy
created in the task container. The only failure was `has_4_weeks`: the output
contains a fifth, total row. The earlier baseline scored 15/15. The agent used
the WPS write and read tools, then independently created a container workbook
because the WPS file was not mounted into `/workspace/output`; the two files
must not be conflated. These are single attempts plus one repair retry, with
different network, prompt and launcher details; this is not a strict controlled
comparison. Evidence and scripts are in `weekly-ticket-normal/`.

### All-local weekly-ticket run

On 2026-11-18, Clover and CodeBuddy 2.109.3 ran on the Mac using the original
task input, local Python/openpyxl, and the scoped local WPS writer. CodeBuddy
had normal shell and file tools within a macOS sandbox. The writer saved in
WPS and copied the resulting file to `output/result.xlsx`; the two copies
matched byte for byte after the run. Clover used Bash, Read, Write, WPS write,
and WPS read tools. Its final workbook passed all 15 deterministic checks.

The original pytest and evaluator ran on the Mac; a small launcher redirects
the evaluator's hard-coded `/tests/gold/gold_answer.json` lookup to the copied
gold file, without changing scoring logic. As a parity check, this local setup
reproduced the earlier WPS workbook's 14/15. The prior Spark baseline also
scored 15/15, but each is one attempt and the OS, WPS instruction, WPS tool,
sandbox, verifier Python version, and launcher differ. Artifacts and the local
verifier launcher are in `weekly-ticket-local/`.

### Four remaining Office tasks, all local

On 2026-11-18, ran the remaining four tasks serially on the Mac using Clover,
CodeBuddy 2.109.3, and scoped WPS MCP operations. Normal shell and file tools
were available in a task-specific sandbox. The agent wrote each output through
WPS; every saved WPS file matched the scored task output byte for byte. Original
deterministic checks ran locally with absolute task and gold paths redirected.
The local verifier reproduced all four saved Spark baseline scores before the
new runs. LLM judge checks were disabled in both comparisons.

| Task | Local WPS | Spark baseline |
| --- | ---: | ---: |
| Drug inventory | 15/15 (100%) | 15/15 (100%) |
| Procurement reconciliation | 16/21 (76.19%) | 15/21 (71.43%) |
| Safety-inspection extraction | 24/27 (88.89%) | 25/27 (92.59%) |
| Board presentation | 242/379 (63.85%) | 267/379 (70.45%) |
| Equal-weight mean | 82.23% | 83.62% |

The board task hit the 48-turn cap. Its scoped presentation writer succeeded on
four update calls and rejected four on exact-text mismatch. Its saved partial
presentation was scored; the two other tasks were not retried. The OS, WPS tool
interface and added WPS instructions differ from the baseline, and each result
is one attempt. This is a practical pilot, not a controlled 1:1 comparison.
Workbooks, presentation, verifier logs, trajectories, prompts and the WPS
guard are in `four-local/`.

### Recorded weekly-ticket demo

The 2026-11-18 all-local Clover and CodeBuddy demo used a fresh task workspace
and a scoped WPS writer that brings the output workbook forward and selects
and writes each row in sequence. The user confirmed an earlier navigation
probe was visible. Clover used the WPS writer and reader, and the workbook
scored 3/15 on the original deterministic checks versus 15/15 for the prior
local run and Spark baseline. The four sums and rates match the expected rows,
but the model labeled them ISO weeks 14 through 17 instead of 15 through 18;
the verifier consequently could not match the rows. The fresh sandbox did not
expose openpyxl to CodeBuddy's shell, and Clover parsed the XLSX XML instead.
This is a single demo attempt, with a different writer and runtime setup.
Artifacts and verifier output are in `weekly-ticket-visible/`.

### Recorded weekly-ticket rerun with Python fixed

A fresh local Clover and CodeBuddy run made the installed openpyxl available
to the interpreter selected by the agent's shell through `PYTHONPATH`. A
CodeBuddy Bash preflight imported openpyxl 3.1.5 and confirmed the ISO week
for April 6, 2026. The agent read the original input using openpyxl, wrote the
output through the visible WPS writer, and read it back. The saved WPS and
scored files matched byte for byte. The original deterministic verifier passed
15/15 checks. The result uses the four correct Monday start dates. This is a
single retry with a changed environment and writer, not a controlled comparison.
Artifacts are in `weekly-ticket-visible-python/`.

### Visible board-presentation demo

A fresh 2026-11-18 local Clover and CodeBuddy run used a copy of the original
board deck and a scoped WPS writer that selected each slide and shape before
its edit. The user reported the live WPS display was a good visual demo.
Clover produced an 11-slide WPS-saved deck, identical to the scored file.
The original deterministic verifier passed 307/379 checks (81.00%), compared
with 242/379 (63.85%) in the previous local WPS run and 267/379 (70.45%) in
the Spark baseline. The run used a different writer, timing, Python path
instruction and environment; these are single attempts, not a controlled
comparison. Two initial edit batches were rejected on schema and exact-text
checks; later edits succeeded. The user requested agent text as an overlay.
The raw timestamped agent trajectory and a concise tool timeline are saved
with the deck, writer and verifier output in `board-visible/`. The timeline
records agent-level calls, not timestamps for every individual WPS edit.

### Automated board video

On 2026-11-18, recorded a fresh local Clover and CodeBuddy board task using
FFmpeg AVFoundation cropped to the WPS window and generated a side panel from
timestamped agent tool and WPS selection/edit events. The combined 4m 24s
video has no audio and approximate synchronization. It was checked visually
at an edit and shows the selected WPS shape beside its logged event. The
original deterministic checks passed 310/379 (81.79%). The prior visible
board demo passed 307/379; the Spark baseline passed 267/379. These are
single attempts with different environments and are not controlled comparisons.
Scripts, video and evidence: `board-video/`.

### Qwen3.8-Flash recorded board comparison

On 2026-11-18, ran the same board task and visible WPS writer locally with
Qwen3.8-Flash through the general-purpose DashScope route and CodeBuddy. The
proxy enabled thinking and a CodeBuddy shell-tool preflight passed. The WPS
saved deck matched the scored output byte for byte. The original deterministic
verifier passed 326/379 checks (86.02%), versus 310/379 (81.79%) for the
recorded Clover attempt. Agent elapsed times were 311.6 and 257.9 seconds,
respectively, including paced WPS edits. These are single attempts; model,
provider and settings differ, and WPS edit counts differ, so neither the score
or elapsed time isolates model capability. The full and 30-second videos,
trajectory, activity events and verification are in `board-video-qwen/`.

### Token accounting caveat

A trajectory audit found ten Qwen response IDs with usage; their reported
input and output sums exactly match CodeBuddy's run totals (313,725 and
17,402). Clover had 48 distinct response IDs carrying usage and 50 proxy
request log lines. CodeBuddy's Clover run total reported 3,592,500 input and
165,490 output tokens. Its largest recorded response reported 54,024 output
tokens despite only a short recorded thinking message and a tiny tool call.
The proxy did not save raw provider usage or streaming events, so this anomaly
cannot be reconciled and no reliable inference TPS or cross-provider token
comparison can be claimed from these records. Tokenizer and reporting behavior
may also differ.

### Request telemetry dry run

The two board runners now use audited local proxies which record per-request
provider usage and streamed timing without saving prompt, response or secret
contents. On 2026-11-18, a CodeBuddy Bash-tool dry run returned HTTP 200 for
all Clover and Qwen3.6-Flash requests; each final provider usage matched the
run's CodeBuddy totals. Qwen initially gave a command without calling Bash; a
second explicit instruction produced a tool round trip. All five requests had
start and finish records, IDs, usage, timing and stream completion. Details,
tests and limitations: `proxy-audit/`. No WPS task was rerun.

### Instrumented Clover and Qwen3.6-Flash board attempts

On 2026-11-18, ran the full board task serially with per-request provider
usage and timing audit. Clover's WPS-saved deck matched its submitted output
and passed 300/379 deterministic checks; 32/32 requests had clean streams
and provider usage (1,956,721 input, 52,850 output), matching CodeBuddy.
Qwen3.6-Flash had 46/46 clean requests with usage (2,659,846 input, 66,508
output), matching CodeBuddy. Seven WPS updates failed exact-text validation;
the agent created its output with python-pptx, not WPS. That output scored
305/379, but does not satisfy the WPS editing requirement. These single runs
differed in provider and actual tool behavior. Proxy streaming rates are not
pure server generation TPS. Results: `proxy-audit/full-comparison-20261118/`.

### Qwen3.6 WPS writer repair and rerun

The previous Qwen attempt supplied mismatched text and cell coordinates. The
WPS writer's all-or-nothing validation provided too little correction detail.
A new writer applies only independently exact-matched edits and returns skipped
locations and actual text. Mixed and all-invalid batches were tested on a
disposable WPS deck. A fresh recorded Qwen3.6 run applied 77 edits through
WPS, with WPS and scored output matching; the original deterministic score
was 305/379. All 12 audited requests returned usage matching CodeBuddy:
476,902 input and 17,909 output tokens. Agent elapsed time was 237.467 s.
The audited Clover attempt used the older all-or-nothing writer, scored
300/379 and took 162.996 s. One run each; writer differences and paced edits
prevent a controlled comparison. The reusable skill writer was also updated.
Evidence and video: `board-video-qwen-wpsfix/` and
`comparison-video/qwen36-wpsfix/comparison-30s.mp4`.

### Qwen3.6 repeat with original all-or-nothing WPS writer

On 2026-11-18, reran the same board task with Qwen3.6-Flash, CodeBuddy and
the original writer which rejects an entire batch on any mismatch. Four WPS
update attempts were rejected: two on schema and two on exact-text mismatch.
No WPS edit events occurred. Qwen created the submitted deck directly with
python-pptx; the file differed from the WPS-open copy and passed 251/379
deterministic checks, but did not satisfy the WPS-edit requirement. Agent
elapsed time was 268.907 seconds. All 43 model requests returned HTTP 200,
provider usage, complete streams, and matched CodeBuddy totals: 2,972,901
input and 45,890 output tokens. The earlier original-writer Qwen attempt
also failed the WPS requirement; its non-WPS output scored 305/379. The
repaired-writer Qwen run produced a WPS-edited output scoring 305/379. These
are single attempts and do not establish a population failure rate.
Evidence: `board-video-qwen/runs/20261118-234234/`.
