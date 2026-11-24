# Qwen3.6-Flash board rerun with repaired WPS writer

The original Qwen3.6 attempt supplied several incorrect existing-text values or
table coordinates. The writer correctly rejected them, but rejected the whole
batch and reported only the slide/shape, making repair difficult. The original
agent fell back to python-pptx, producing a non-WPS output.

This variant validates each proposed edit separately, saves each exact match,
and returns skipped indices, coordinates and current text. It never substitutes
an approximate match. A disposable WPS test confirmed a valid edit was saved,
an invalid target remained unchanged, and an entirely invalid batch returned
an error. The reusable WPS demo skill's writer was updated and tested as well.

On 2026-11-18, Qwen3.6-Flash ran a fresh original board task through CodeBuddy,
the new writer, and the audited general-purpose DashScope route. Its first
well-formed batch applied 61 edits and returned mismatches; its retry applied
16 edits with no rejections. The WPS-saved deck matched `result.pptx` byte for
byte and passed 305/379 original deterministic checks. Agent elapsed time was
237.467 s, including paced WPS operations. All 12 proxy requests had paired
start/end, HTTP 200, usage and clean stream endings; provider usage summed to
476,902 input and 17,909 output tokens and matched CodeBuddy. Output tokens
per proxy first-to-last streamed output interval was about 178.5/s. This is not
pure server generation TPS.

The audited Clover comparison run used the earlier all-or-nothing writer,
scored 300/379 through WPS, and took 162.996 s. Both runs are single attempts;
the different writer semantics, model providers and edit counts prevent a
controlled capability or speed conclusion. The combined comparison video is
`../comparison-video/qwen36-wpsfix/comparison-30s.mp4`. Full Qwen recording,
request audit, trajectory, result and verifier are under `runs/20261118-233107/`.
