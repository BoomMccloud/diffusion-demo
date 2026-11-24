#!/bin/sh
# Full benchmark for MiniCPM-V 4.7 35B-A3B (thinking-template Q4_K_M), plain and with the DSpark
# draft, on the same llama.cpp image. Waits for a free GPU before each model and logs any
# other GPU process that appears during a run.
cd "$HOME/clover"
f=thinking/MiniCPM-V-4_7-35B-A3B-Q4_K_M-thinking.gguf
for v in ${VARIANTS:-plain dspark}; do
  if [ $v = dspark ]; then
    export KEEP=1 DRAFT_DIR=minicpmv47-dspark DRAFT=dspark-MiniCPM-V-4_7-35B-A3B-Q8_0.gguf SPEC=draft-dspark ALIAS=minicpmv47-q4km-dspark
  else
    unset KEEP DRAFT DRAFT_DIR SPEC; export ALIAS=minicpmv47-q4km
  fi
  echo "waiting for a free GPU $(date -Is)"; work/gpu-guard.sh wait
  work/serve-llamacpp.sh minicpmv47-q4km $f >/dev/null; sleep 3
  for i in $(seq 90); do curl -sf localhost:8080/health >/dev/null && break; sleep 2; done
  echo "=== $ALIAS $(date -Is) other containers: $(docker ps --format '{{.Names}}' | grep -v -E '^srv-llamacpp$' | tr '\n' ' ')"
  work/gpu-guard.sh watch logs/$ALIAS/gpu-contention.log & guard=$!
  work/bench-model.sh $ALIAS http://127.0.0.1:8080/v1
  kill $guard
  [ -s logs/$ALIAS/gpu-contention.log ] && echo "!!! $ALIAS shared the GPU, see logs/$ALIAS/gpu-contention.log"
  echo "--- end $ALIAS $(date -Is) other containers: $(docker ps --format '{{.Names}}' | grep -v -E '^srv-llamacpp$' | tr '\n' ' ')"
  docker logs srv-llamacpp > logs/$ALIAS/llama-server.log 2>&1
  echo "server state: $(docker inspect -f 'running={{.State.Running}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' srv-llamacpp)"
  docker rm -f srv-llamacpp >/dev/null
done
echo "=== done $(date -Is)"
