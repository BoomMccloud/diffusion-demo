#!/bin/sh
# Plain AR decoding with the model card settings. Usage: run-completion.sh <model.gguf>
exec llama-completion \
  -m "$1" \
  -f /work/prompt.txt \
  --temp 0 --top-k 1 --seed 42 \
  -ctk bf16 -ctv bf16 \
  -c 8192 -n 512 -b 256 -ub 256 \
  -ngl 99 -t 8 -tb 8 \
  --flash-attn on --color off -no-cnv
