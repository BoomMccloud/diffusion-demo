#!/usr/bin/env bash
# Finish the corrected run's unfinished tasks, reset, then a fresh think-history
# run. Run on diffuspace from /data/users/jason/webarena, inside tmux.
set -uo pipefail
cd /data/users/jason/webarena
fixed=$(basename "$(ls -td results/2026*-fixed/ | head -1)")

echo "$(date +%F_%T) resume $fixed"
bench/run.sh --n-jobs 6 --resume "/results/$fixed" > logs/full-fixed-resume.log 2>&1
echo "EXIT $?" >> logs/full-fixed-resume.log
[ -d results/llm_calls ] && mv results/llm_calls "results/$fixed/llm_calls-resume"

echo "$(date +%F_%T) reset"
bench/reset_sites.sh > logs/reset-thinkhist2.log 2>&1 || { echo "reset failed"; exit 1; }

echo "$(date +%F_%T) think-history run start"
bench/run.sh --n-jobs 6 --think-history --suffix thinkhist2 > logs/full-thinkhist2.log 2>&1
echo "EXIT $?" >> logs/full-thinkhist2.log
study=$(ls -td results/2026*-thinkhist2/ | head -1)
[ -d results/llm_calls ] && mv results/llm_calls "$study/llm_calls"
echo "$(date +%F_%T) done"
