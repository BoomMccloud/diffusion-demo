#!/usr/bin/env bash
# Runs on the Colab L4 from a directory holding nemotron_pilot.py, business_fixtures.py,
# and the fixtures-*.json files. Each step resumes: completed (case, arm) rows are skipped.
set -u
run() { python nemotron_pilot.py nemotron "$@"; }
CAP="--tokens-per-value 16 --max-new-tokens 8192"

for f in a-length-v4 b-lines-v5 b-d3-v4; do
  run --fixtures fixtures-$f.json --out rows-$f.jsonl --modes ar,linear_spec,diffusion $CAP
  run --fixtures fixtures-$f.json --out rows-$f.jsonl --modes diffusion --arm-prefix nemotron-3b-t0.99-b8 \
      --threshold 0.99 --block-length 8 $CAP
done

f=c-chained-v4
run --fixtures fixtures-$f.json --out rows-$f-think-off.jsonl --modes ar,linear_spec,diffusion $CAP
run --fixtures fixtures-$f.json --out rows-$f-think-off.jsonl --modes diffusion --arm-prefix nemotron-3b-t0.99-b8 \
    --threshold 0.99 --block-length 8 $CAP

THINK="--thinking --max-new-tokens 6144"
run --fixtures fixtures-$f.json --out rows-$f-think-on.jsonl --modes ar,linear_spec --arm-prefix nemotron-3b-think $THINK
run --fixtures fixtures-$f.json --out rows-$f-think-on.jsonl --modes diffusion --arm-prefix nemotron-3b-think-t0.99-b8 \
    --threshold 0.99 --block-length 8 $THINK
echo ALL_DONE
