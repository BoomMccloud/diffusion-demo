---
name: wps-agent-demo
description: Run and record a local WPS Office agent task with CodeBuddy or another harness, a scoped WPS MCP writer, synchronized activity panel, and task-specific evaluation. Use for WPS agent demos or comparisons, not ordinary Office file editing.
---

# WPS agent demo

Run a real agent on a user-selected Office task against a disposable WPS document. When requested, record the WPS window and combine it with an activity panel from timestamped tool and WPS events. Preserve the task inputs, agent trajectory, WPS-saved artifact, verifier output, model and harness configuration, and recording separately per run. Never present a reconstructed activity panel as a terminal recording.

1. Identify the task instructions, input files, output path, evaluator, and comparable baseline. Reuse the same task and grading for each model. Mark differences in prompt, harness, tools, environment, model settings, timing, and scoring. For token or speed comparisons, capture per-request provider usage and stream timings, reconcile them against agent totals, and explicitly flag missing data. One task or single run is not a benchmark pass rate.
2. Copy inputs and a fresh editable output document into a task-specific workspace. Confirm the exact WPS document is open and registered with the bridge. Keep the original files untouched. Use an independent verifier after the agent finishes; do not repair its output and silently score the repaired artifact as the agent's result.
3. Use a local scoped writer for the designated disposable document, not the raw bridge in the agent sandbox. Give the agent its normal task-appropriate tools inside a task-specific sandbox. Keep keys outside that sandbox and use an authorized provider route. Follow the selected provider's usage and billing terms.
4. Preflight the model route and tool round trip, runtime dependencies in the agent's actual shell, WPS navigation and saving, the document-to-output copy, and recording permissions. Do not assume temporary paths, running services, file IDs, screen indices, or local installations from older sessions. Mac screen capture records a rectangle of the screen: keep the WPS window visible and stationary; anything covering that rectangle is captured.
5. Start capture and agent together, log real WPS selections and edits with timestamps, and capture the agent's stream JSON. The panel is derived from events, with approximate synchronization. Record without audio unless the user asks for audio. Verify the output video, inspect a frame at an edit, and report any failure or missing evidence. Ask the user to position WPS before recording when needed.
6. Save and independently inspect the output; compare WPS and submitted file bytes when applicable. Run the original task verifier with any path adaptations disclosed. Report partial scores and errors accurately. Include video, output file, score and comparison limits. Offer an accelerated cut only when requested; preserve the full recording.

Use [references/workflow.md](references/workflow.md) for setup, script interfaces, safety boundaries, reusable writer limitations, recorded pilot examples and provider notes. For standalone spreadsheet or presentation authoring, also follow the applicable artifact skill when needed.
