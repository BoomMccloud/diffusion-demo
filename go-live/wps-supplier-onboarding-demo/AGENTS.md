# WPS supplier onboarding demo

Run this demo to have Clover review a fictional supplier packet, cite the
source pages, and fill a disposable workbook in the WPS desktop app. The
same fixtures support two runs. Use `quick` for the short workbook-edit demo
or `full` to record the receipt, page extraction, and checklist review first.
Each mode makes a fresh model call.

## Setup

- Use an interactive Mac with WPS Office and a visible spreadsheet window.
  Grant the terminal or runner Accessibility and Automation access for
  System Events. Grant Screen Recording access if making a video.
- Install Python 3, Poppler (`pdftotext` on PATH), and the Xcode Command Line
  Tools (`swiftc`). Use a Python environment with `openpyxl` for scoring.
  Recording also needs Pillow and FFmpeg with AVFoundation and libx264.
- Set `CLOVER_CHAT_URL` to your authorized complete chat-completions URL and
  `CLOVER_API_KEY` to its bearer credential in the current shell. The
  endpoint must support forced function calls. The default model name is
  `Clover-35B-A3B-Preview`. Set `CLOVER_MODEL` if your route names it
  differently and record the model used. The request sends the fictional PDF
  text to this route. Use credentials provided to you.

From the repository root, prepare a fresh run. It is safe to rerun these
commands to create another workspace. Use `full` in place of `quick` for the
longer workflow.

```sh
repo="$(pwd -P)"
demo="$repo/go-live/wps-supplier-onboarding-demo"
skill="$repo/experiments/workbuddy/skills/wps-agent-demo"
mode=quick

python3 "$demo/agent.py" preflight
mkdir -p "$demo/runs"
run="$(mktemp -d "$demo/runs/${mode}.XXXXXXXX")"
cp "$demo/03-供应商建档模板.xlsx" "$run/供应商建档草稿.xlsx"
swiftc "$demo/click.swift" -o "$run/click"
open -a wpsoffice "$run/供应商建档草稿.xlsx"
```

Open only this disposable copy in WPS. Verify that `供应商建档` is the active
sheet. The writer clicks the Name Box at a fixed offset (77 points right,
205 down from the top left of the WPS window). Confirm that offset against
your WPS version, toolbar layout, and display before running. Adjust
`write.applescript` if necessary. The title guard expects the workbook
filename to appear in the window title, including its extension. Keep the
window visible and stationary and leave the pointer and keyboard alone
during the run.

## Run and verify

For a run without video:

```sh
python3 "$demo/agent.py" "$mode" --run-dir "$run" > "$run/trajectory.jsonl"
```

For video, run the following instead. Use `swift "$skill/scripts/wps-window.swift"`
to find the WPS window in points, then convert to capture pixels for the
selected AVFoundation screen and verify the crop. Replace `X Y WIDTH HEIGHT`
with four even pixel values. The recorder creates the `capture` directory,
logs to the model trajectory and WPS event streams, and renders
`capture/combined.mp4` with an event-derived activity panel and no audio.

```sh
python3 "$skill/scripts/record.py" \
  --output "$run/capture" --crop X Y WIDTH HEIGHT --screen 0 --cwd "$run" \
  --agent-log "$run/trajectory.jsonl" --events "$run/wps-events.jsonl" \
  -- python3 "$demo/agent.py" "$mode" --run-dir "$run"
```

Score the actual WPS-saved workbook. The verifier copies it byte for byte
into the evidence folder, then writes `verification.json` there.

```sh
mkdir "$run/verified"
cp "$run/wps-events.jsonl" "$run/verified/"
python3 "$demo/verify.py" "$demo" "$run/供应商建档草稿.xlsx" "$run/verified"
```

A full pass is 26/26. The delivery period stays blank because the two
documents disagree (7 versus 10 business days). The output should flag that
conflict and the missing signed compliance declaration, with exactly two
exception rows. An earlier quick run scored 26/26 and an earlier full run
scored 25/26 because it added a successful price check as an exception.
Record the score from your own run. The generic recorder reproduces the
WPS capture and activity timeline. The original Chinese title cards,
PDF page cutaways, and edited launch clips were assembled separately.
