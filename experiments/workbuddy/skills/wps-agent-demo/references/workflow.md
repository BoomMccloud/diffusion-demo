# WPS agent demo workflow

## Architecture and prerequisites

Model -> CodeBuddy (or selected harness) -> scoped task writer -> local WPS MCP bridge -> WPS document. A separate local model relay may adapt an API route. A screen recorder and event renderer run outside the task sandbox. Only the scoped writer can access the raw bridge; do not expose the bridge's arbitrary WPS JavaScript execution to the agent. Its own syntax guard is not a security sandbox. Restrict the agent's filesystem and network and preflight that the raw bridge and other unrelated local listeners are unreachable. WPS should operate on a disposable open copy, and the writer should allow only that exact registered document and designated output path. Prompt/model output must never become executable code. Do not log API keys or give the task agent access to credential files.

The tested third-party bridge is `humoumou1215/wps-assistant`, commit `dda67065086a46450d0aa72eab77954b61ba42d6`, not an official WPS component. It used a WPS add-in, Node 22, an HTTP MCP endpoint on localhost:18766, and a user-opened WPS document. Check its current installation and connection afresh. Its WPS JavaScript can execute arbitrary operations and its dependencies had known vulnerabilities at pilot time. The WPS application must remain open. If the app or add-in is not connected, complete setup using current documentation and obtain any OS permissions needed. Never silently install a login item or expose the bridge to the network.

The supplied `scripts/wps-writer.mjs` is a constrained starting point, not a universal Office API. It uses the bridge's MCP SDK and Zod: copy it into the bridge checkout (so Node can resolve its modules) and run with Node from there. Set these environment variables outside the agent sandbox:

- `WPS_DEMO_TASK_DIR`: absolute task directory, containing an `output` subdirectory and JSON payload. It must be writable by the agent and writer.
- `WPS_DEMO_DOCUMENT`: absolute path to the **open disposable WPS copy**. The writer accepts only its exact registered path.
- `WPS_DEMO_TYPE`: `spreadsheet` or `presentation`.
- `WPS_DEMO_OUTPUT`: output file basename, saved into task `output/`.
- `WPS_DEMO_EVENTS`: fresh absolute JSONL event file path writable by the writer and readable by the recorder. Set the same path in `record.py --events`.
- `WPS_DEMO_DELAY_MS`: optional nonnegative pause up to 10000 ms, default 500. Delays improve visibility and affect elapsed-time comparisons.

The writer listens on 127.0.0.1:18768, which must be free and is intended only for the isolated task. Its WPS app activation currently assumes `/Applications/wpsoffice.app`. It logs selection and edit events, without text values. Presentation mode inspects numbered shapes and table cells and applies exact-text replacements read from `wps-edits.json`; it validates each edit, applies matching targets, and returns rejected locations and actual text for correction. It rechecks each target and saves/copies after each edit. A late failure can leave a **partial saved output**. Spreadsheet mode reads `wps-data.json`, creates/renames sheets and selects/writes/saves each row. It rejects an existing workbook with more sheets than requested, and supports scalar values only, not formatting, formulas, chart creation or arbitrary Office features. Extend the narrowly scoped writer and add meaningful tests if the task requires them. Neither template supports WPS Writer documents. Do not claim generic support for unsupported operations or formats.

Writer payloads:

```json
{"edits":[{"slide":1,"shape":2,"old":"exact existing text","replacement":"updated text"}]}
```

For presentation table cells, add one-based `row` and `column`; selection highlights the table shape. A workbook payload is:

```json
{"sheets":[{"name":"Summary","rows":[["Name","Count"],["A",3]]}]}
```

Use CodeBuddy's `stream-json` output and its MCP configuration for the scoped writer. An initial sandbox must permit the input and output workspace, runtime, and agent home while denying sensitive user files and the raw bridge port. CodeBuddy may select an unexpected Python in its shell; run an actual CodeBuddy Bash preflight. For compiled packages, match the interpreter and environment; a `PYTHONPATH` from a different Python version is not sufficient. If the agent log is opened outside the sandbox, Node may abort at startup. Put `--agent-log` inside its allowed home and let the recorder copy it out later.

For the DashScope Qwen run, the compatible API accepted `qwen3.8-flash` with thinking enabled. CodeBuddy's `reasoning_effort` conflicted with `enable_thinking=false`; the working relay removed `reasoning_effort` and passed `enable_thinking=true`. The subscription's eligibility matters: the pilot's Token Plan endpoint was limited to interactive use in supported tools, so the automated recording used a general-purpose Model Studio endpoint. Verify current provider rules and model support rather than assuming either.

## Record and render

`record.py` starts FFmpeg capture, waits for frames, launches a supplied agent command, finalizes capture and invokes `render.py`. It expects Pillow, FFmpeg with AVFoundation and libx264, Python 3.9+, and macOS Screen Recording permission. Use `swift scripts/wps-window.swift` to find WPS window bounds, then verify coordinate conversion for the selected AVFoundation screen: window points and capture pixels can differ on Retina or multi-display setups. `record.py` discovers the AVFoundation device for screen 0 by name rather than hard-coding device index. It currently requires an explicit even-pixel crop X Y WIDTH HEIGHT and does not track a moving window. Check a test capture; do not assume a crop remains correct after moving or resizing WPS. Close or move unrelated windows outside the crop.

After starting the bridge, scoped writer and provider relay, an example shape is:

```sh
python scripts/record.py \
  --output /absolute/new/run-directory \
  --crop X Y WIDTH HEIGHT --screen 0 --cwd /absolute/task \
  --agent-log /absolute/agent-home/trajectory.jsonl \
  --events /absolute/writer/events.jsonl \
  -- sandbox-exec -f /absolute/task.sb node /absolute/codebuddy \
     -p --output-format stream-json -y --model MODEL \
     --mcp-config /absolute/task/mcp.json -- 'TASK PROMPT'
```

Replace placeholders; use the user's authorized task prompt, model and harness. Set model credentials only on the provider side of the boundary. Writer startup is separate, so `WPS_DEMO_EVENTS` must point to the same absolute file passed with `--events`. The recorder also exports `WPS_DEMO_EVENTS` to its child for workflows that start their writer there. Use fresh paths per run. The command is passed as arguments, not through a shell. The writer logs events in UTC ISO-8601 JSONL with `type` (`select`, `edit`, `save`), and either `location` or slide/shape/row/column. Actual agent stream JSON supplies `__timestamp` and `tool_use` records. No timestamps for actions that were not logged should be invented.

`render.py RUN_DIR` generates a side-by-side `combined.mp4` from `wps.mp4`, `trajectory.jsonl`, `capture.json`, and optional `wps-events.jsonl`. It uses wall-clock event time and first FFmpeg progress time minus encoded duration; alignment is approximate. Review the video and at least one event-to-frame sample. The full recording and logs may contain sensitive on-screen or task data; review before external sharing. If an accelerated clip is requested, derive it from the full recording, preserve the full version, and explain that event times in the panel remain original elapsed times.

## Evaluation and prior evidence

Use the task's original verifier with paths redirected only where necessary. Compare the actual saved WPS file with the scored file. Preserve failures, partial work, verifier version, limits and all retries. Avoid claiming the test is controlled if the OS, prompt, tools, model endpoint, reasoning setting or timeout differ; paced editing makes wall-time comparisons especially weak.

The local pilot's source material, original task artifacts, recorded examples and local path-adapted verifiers are under `experiments/workbuddy/experiments/wps-office-pilot/` in the `diffusion-demo` checkout. These are examples, not prerequisites and not portable installations. The weekly-ticket task passed 15/15 in one recorded Clover run. The board presentation scored 310/379 for recorded Clover and 326/379 for recorded Qwen3.8-Flash, each once, with different model routes and edit counts. Never reuse those scores for a new task or run.


For telemetry comparisons, the `diffusion-demo` checkout contains audited
Clover and Qwen relays under
`experiments/workbuddy/experiments/wps-office-pilot/proxy-audit/`. Each request
is logged without prompt or response text, with paired start/end, provider
usage, model and response ID, status, effective settings, and first/last stream
event timing. Read that folder's README for limitations and run the preflight
for the selected provider. Reconcile returned usage against the agent; mark
missing provider fields, interrupted requests and semantic retry ambiguity.
This does not prove provider token counts are correct or measure pure server
generation TPS. Do not reuse old runs' unaudited token counts as verified data.
