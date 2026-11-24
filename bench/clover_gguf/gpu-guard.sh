#!/bin/sh
# GPU sharing guard for the Spark benchmarks.
#   gpu-guard.sh wait          block until no other GPU process has run for 5 minutes
#   gpu-guard.sh watch <file>  append a line to <file> every 30 s while other GPU users exist
# "Other" means any GPU compute process not inside our srv-llamacpp or srv-vllm containers.
ours() { for c in srv-llamacpp srv-vllm; do docker top $c -eo pid 2>/dev/null | tail -n +2; done; }
others() {
  mine=$(ours | tr '\n' ' ')
  nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | while read p; do
    case " $mine " in *" $p "*) ;; *) echo "$p";; esac
  done
}
case $1 in
  wait)
    quiet=0
    while [ $quiet -lt 5 ]; do
      if [ -n "$(others)" ]; then quiet=0; else quiet=$((quiet + 1)); fi
      sleep 60
    done ;;
  watch)
    while true; do
      o=$(others | tr '\n' ' ')
      [ -n "$o" ] && echo "$(date -Is) other GPU pids: $o containers: $(docker ps --format '{{.Names}}' | grep -v -E '^(srv-|bench|dl-)' | tr '\n' ' ')" >> "$2"
      sleep 30
    done ;;
esac
