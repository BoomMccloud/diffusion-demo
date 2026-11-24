# Instrumented WPS board attempts

Both runs used CodeBuddy, the same board prompt, source inputs and visible WPS
writer. Clover used its hosted API and Qwen3.6-Flash used general-purpose
DashScope; both proxies requested streaming usage and enabled thinking with
provider-specific settings. The execution was sequential, one attempt each.

Clover made 32 successful model requests. All requests had paired start/end,
usage and clean stream endings; CodeBuddy totals matched provider usage
(1,956,721 prompt and 52,850 completion tokens). The WPS-saved file matched
the submitted deck byte for byte and passed 300/379 deterministic checks.
Agent elapsed time, including paced WPS operations, was 162.996 seconds.

Qwen made 46 successful model requests; all had paired start/end, usage and
clean stream endings, and CodeBuddy totals matched provider usage (2,659,846
prompt and 66,508 completion tokens). Seven WPS update calls were rejected
on exact-text mismatch, and no WPS edits were recorded. The agent then created
its output directly with python-pptx. This output passed 305/379 deterministic
checks but **does not meet the WPS-edit requirement** and is not an equivalent
WPS task success. Agent elapsed time was 403.306 seconds.

Both provider completion counts divided by the sum of proxy first-to-last
output-delta intervals are saved in `summary.json` as an observed streaming
rate. These are not pure model generation TPS: first-token prefill is excluded,
chunking and network influence intervals, server output-token semantics can
differ, and provider counts are not independently tokenized. The counts include
provider-reported reasoning. The differing WPS operations and paced edits also
make agent wall-time a poor isolated speed comparison. The audit logs do not
save response content or cryptographically verify the providers' token counts.
See the parent proxy-audit README for telemetry details and the run paths in the
summary for trajectories, video and verifier logs.
