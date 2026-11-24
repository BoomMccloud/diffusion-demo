# Clover and Qwen3.6-Plus workshop comparison

Qwen3.6-Plus ran on November 18–19, 2026 Taipei time. The comparison uses
the saved [Clover dry run](../xmind-clover-dry-run/) from November 18.
Both used the original WorkBuddy Office v1.0 workshop task, byte-identical
inputs, the same prompt and local CodeBuddy 2.109.3 file-tool setup,
the same configured 24-turn limit, and the original local deterministic
verifier with paths redirected. The model provider and request translation
differed. Qwen used the general-purpose DashScope route with thinking
enabled and temperature zero. Its audit includes a preflight plus 24
run requests, all of which returned HTTP 200 and reported qwen3.6-plus.

Clover finished in 35.164 s and saved 13 slides, passing 87/113 checks.
Qwen recovered from generation errors, saved eight slides, and reached
the CodeBuddy turn limit after 441.692 s. The saved file passed 88/113
checks. Qwen uniquely passed eight checks, Clover uniquely passed seven,
and both missed 18. The detailed check differences are in summary.json.
These are single attempts. Elapsed time includes tools and recovery.
There was no LLM rubric grading or live WPS editing.

The 32-second silent preview pairs rendered slides by topic, then shows
the saved artifact scores. The Qwen deck is the unchanged file that was
scored. The original inputs and raw Qwen trajectory are in
`/private/tmp/wb-qwen36-xmind-4jvi6gjh/`.
