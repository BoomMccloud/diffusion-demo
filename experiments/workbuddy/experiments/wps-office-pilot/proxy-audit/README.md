# Audited model proxies

Both recorded-board runners use these proxies. Set `PROXY_AUDIT_PATH` to a new
file, `CLOVER_ENV_FILE` or `DASHSCOPE_ENV_FILE` to the appropriate credential
file, and optionally `QWEN_MODEL` (default `qwen3.8-flash`). The Qwen proxy
rejects Token Plan and Coding Plan endpoints for automated runs. Credentials,
prompts, response text, tool arguments and upstream error text are not logged.
Audit files are created mode 0600. Treat even metadata and model IDs as private.

Each proxy request creates a `request_start` and, on completion or handled
failure, `request_end` JSONL record sharing a random request ID. An unmatched
start indicates an interrupted process or missing finish. Finish records contain
safe effective settings, HTTP status, upstream response/model IDs when provided,
first byte, first text/reasoning/tool delta, first and last output delta, end
latency, observed finish reasons, stream `[DONE]`, parsing errors and all
provider usage objects. Usage objects retain numeric/boolean/null fields and
nested structure, not arbitrary strings. The times are relative to the local
proxy accepting the request; output-delta timing is not ground-truth server
inference time. Provider usage events may be absent, cumulative or differently
defined. Preserve all events, do not assume each event is incremental, and
mark missing or discrepant values explicitly.

The proxy requests `stream_options.include_usage=true`, which alters the
upstream request compared with the earlier unaudited demo and requires provider
support. It records every HTTP request attempt but does not establish whether
two separate requests are semantic retries of the same agent turn. Content is
forwarded unchanged and is intentionally not recorded. It cannot independently
verify whether a provider's counts or output-token definition are correct.

Run the local simulation with Node 22:

```sh
node --test experiments/workbuddy/experiments/wps-office-pilot/proxy-audit/audit-proxy.test.mjs
```

The 2026-11-18 dry runs used CodeBuddy 2.109.3 and a simple Bash tool task.
Clover had two HTTP 200 streaming requests; provider totals were 43,980 input
and 99 output tokens, matching CodeBuddy. Qwen3.6-Flash initially supplied a
shell command without invoking the tool (one HTTP 200 request, 21,751 input and
31 output tokens). A second, explicitly phrased tool-call attempt completed two
HTTP 200 requests with 43,638 input and 113 output tokens, matching CodeBuddy.
All five requests had paired start/finish records, response IDs, model IDs,
usage, finish reasons, first/last output timing, `[DONE]`, and zero SSE parse
errors. These are checks of telemetry plumbing, not WPS or model benchmarks.
