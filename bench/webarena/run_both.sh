#!/usr/bin/env bash
# Full WebArena run with the select_option and geocoding fixes, then a site
# reset, then the same run with think history on. Run on diffuspace from
# /data/users/jason/webarena, inside tmux. Sites must be freshly reset first.
set -uo pipefail
WA=/data/users/jason/webarena
cd "$WA"

file_calls() {  # move this run's model-call logs into its study folder
  local study
  study=$(ls -td results/2026*"$1"*/ | head -1)
  [ -d results/llm_calls ] && mv results/llm_calls "$study/llm_calls"
}

echo "$(date +%F_%T) fixed run start"
bench/run.sh --n-jobs 6 --suffix fixed > logs/full-fixed.log 2>&1
echo "EXIT $?" >> logs/full-fixed.log
file_calls fixed

echo "$(date +%F_%T) reset"
bench/reset_sites.sh > logs/reset-thinkhist.log 2>&1 || { echo "reset failed"; exit 1; }

echo "$(date +%F_%T) think-history run start"
bench/run.sh --n-jobs 6 --think-history --suffix thinkhist > logs/full-thinkhist.log 2>&1
echo "EXIT $?" >> logs/full-thinkhist.log
file_calls thinkhist
echo "$(date +%F_%T) done"
