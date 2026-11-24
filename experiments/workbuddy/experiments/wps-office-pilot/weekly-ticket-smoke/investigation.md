# Weekly-ticket proof-of-concept failure

The 2/15 result is diagnostic, not a controlled comparison. Two independent
failures occurred: the pilot denied the model a way to calculate aggregates,
and the initial WPS writer used an unsupported cell API. The model's attempted
table was already incorrect before the writer failed.

## Evidence

- `read_input` returned the complete 560-record workbook as JSON, with dates in
  three formats. The saved trajectory includes the final input record. This
  proves the tool result contains the data; it does not prove what the model
  attended to internally.
- The wrapper exposed only `read_input` and `write_output` and disabled normal
  file and execution tools. Clover's trace repeatedly says it needs to compute
  the sums programmatically but has no interpreter. It called `write_output`
  with five Sunday-starting ranges and repeated the same totals for four weeks.
  In a later trace message it acknowledged those numbers were placeholders.
- An independent calculation from the original input finds four Monday-starting
  weeks. Plan / resolved totals are 9,420 / 6,852 (April 6), 9,214 / 7,214
  (April 13), 9,803 / 7,310 (April 20), and 9,433 / 7,269 (April 27).
- WPS rejected the first write because the wrapper called `sheet.Cells(...)`,
  which this WPS host reports is not a function. The wrapper was repaired to
  use `sheet.Range(...)`; the unchanged model output was replayed manually and
  saved. Thus the run was not end-to-end autonomous.
- The original verifier passed only `output_is_valid_xlsx` and
  `week_labels_present`. It failed the four-week count and all 12 per-week
  value checks. Its per-week messages report label matching failed, so those
  checks do not independently isolate a numeric mismatch; the input-based
  calculation above does.
- In the successful 15/15 baseline, Clover used CodeBuddy's Bash and Write tools
  to inspect the input, write and run a Python/openpyxl aggregation, then reread
  and cross-check the output. It did not use WPS.
- The first two pilot launches did not expose tool schemas to Clover because
  MCP tools were deferred while discovery was disabled; Clover printed tool
  markup as text. Explicitly disabling deferral fixed tool calls. This was a
  pilot configuration issue, not evidence of a WPS or model scoring issue.

## Next test

Give Clover a restricted computation tool, such as execution in a separate
container over the task workspace, while preserving the WPS output tool and
verifier. Validate the corrected WPS writer independently before launch, then
let Clover produce, save and read back its result autonomously. Compare paired
task results with the baseline, recording tool access and changed environment.
Do not assume this will pass without running it.
