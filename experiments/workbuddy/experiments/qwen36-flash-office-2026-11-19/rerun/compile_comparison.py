"""Compile a 50-task deterministic comparison from exported Qwen records."""
import argparse
import csv
import json
import statistics
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--clover', type=Path, required=True)
p.add_argument('--qwen-original', type=Path, required=True)
p.add_argument('--qwen-reruns', type=Path, required=True)
p.add_argument('--output-dir', type=Path, required=True)
a = p.parse_args()
clover = json.loads(a.clover.read_text())
original = json.loads(a.qwen_original.read_text())
reruns = json.loads(a.qwen_reruns.read_text())
assert len(clover) == len(original) == 50
assert len({x['task'] for x in clover}) == 50
assert len({x['task'] for x in original}) == 50
by_task = {x['task']: x for x in original}
for x in reruns:
    if x.get('status') == 'completed':
        by_task[x['task']] = dict(x, source='fresh_rerun')
rows = []
for c in clover:
    q = by_task[c['task']]
    if c['task'] == 'channel-period-compare-L4-017' and q['status'] == 'judge_error':
        value, source = 1.0, 'original_verifier_stdout'
    elif q.get('source') == 'fresh_rerun':
        value, source = q['score'], 'fresh_rerun'
    elif q['status'] not in {'judge_error', 'build_error', 'unreadable'}:
        value, source = q['score'], 'original_fixed_verifier'
    else:
        value, source = None, 'missing'
    rows.append(dict(task=c['task'], clover_rule_score=c['rule_score'],
                     qwen_rule_score=value, qwen_source=source))
missing = [r['task'] for r in rows if r['qwen_rule_score'] is None]
if missing:
    raise SystemExit(f'Comparison incomplete: {len(missing)} missing task scores: {missing}')
assert sum(x['qwen_source'] == 'fresh_rerun' for x in rows) == 10
a.output_dir.mkdir(parents=True, exist_ok=True)
with (a.output_dir / 'comparison.csv').open('w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader(); writer.writerows(rows)
summary = dict(tasks=50, clover_deterministic_mean=statistics.mean(x['clover_rule_score'] for x in rows),
               qwen_deterministic_mean=statistics.mean(x['qwen_rule_score'] for x in rows),
               qwen_original_fixed=39, qwen_recovered_stdout=1, qwen_fresh_reruns=10,
               caveat='One attempt per score; ten Qwen scores are fresh replacement runs. '
                      'Different model providers; rubric judging not included.')
(a.output_dir / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
