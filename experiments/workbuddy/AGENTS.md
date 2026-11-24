# WorkBuddy Office demos

Start with the [WPS agent demo skill](skills/wps-agent-demo/SKILL.md) and
[workflow](skills/wps-agent-demo/references/workflow.md) for the macOS
setup, scoped writer, CodeBuddy command, and capture tooling. The
[supplier onboarding demo](../../go-live/wps-supplier-onboarding-demo/AGENTS.md)
has its own bundled fixtures and a direct model-to-WPS runner.

## Recreate the WorkBuddy demos

1. Obtain the original Office task inputs, instructions and verifier from
   Tencent WorkBuddy Bench v1.0 (the pilot used revision
   `625b2233093ae4f23e76be28c1f341d41cc70373`) using your own authorized
   access. Stage the task in a fresh directory. For weekly support tickets
   the task is `ticket-weekly-L3-010`. For the board update
   use `board-material-update-timeline-excel`. Check the IDs against the
   task archive before you run.
2. Set up the scoped WPS writer and the model route from the workflow.
   Register the disposable workbook or deck in WPS. The board demo applies
   exact-text replacements at identified shapes or table cells. The
   weekly-ticket demo writes rows and needs a CodeBuddy shell that can
   import `openpyxl`.
3. Run the selected task under CodeBuddy 2.109.3 with the original
   instructions and the WPS editing and output requirements. The recorded
   board pilot used a 48-turn cap. Capture the WPS window and trajectories
   using the workflow's recorder command. Record model route, harness
   settings, and any prompt or environment differences.
4. Grade the WPS-saved output with the original deterministic verifier.
   Save the artifact, event log, evaluation result, and capture metadata
   together. Note any verifier path adaptations. Use new run directories
   and your own environment settings for each attempt.

The historical WorkBuddy runs used locally staged task archives, WPS bridge
settings, and provider credentials. Obtain and configure those dependencies
for your own machine. The reusable writer and recorder are included here.
