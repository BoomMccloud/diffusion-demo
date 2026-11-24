#!/bin/sh
# Model card step 4 with the speculative flags removed (plain AR decoding). Usage: run-ar.sh <model.gguf>
exec llama-speculative-simple \
  -m "$1" \
  -f /work/prompt.txt \
  --temp 0 --top-k 1 --seed 42 \
  -ctk bf16 -ctv bf16 \
  -c 8192 -n 4096 -b 256 -ub 256 \
  -ngl 99 -t 8 -tb 8 \
  --flash-attn on --color off
