#!/bin/sh
# Model card step 4, verbatim except the model path. Usage: run.sh <model.gguf>
exec llama-speculative-simple \
  -m "$1" \
  -f /work/prompt.txt \
  --spec-type draft-self \
  --spec-draft-n-max 15 \
  --spec-accept-ratio 0.9 \
  --spec-accept-delta 0.6 \
  --temp 0 --top-k 1 --seed 42 \
  -ctk bf16 -ctv bf16 \
  -c 8192 -n 4096 -b 256 -ub 256 \
  -ngl 99 -t 8 -tb 8 \
  --flash-attn on --color off
