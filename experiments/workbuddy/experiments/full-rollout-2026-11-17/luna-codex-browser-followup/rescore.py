"""Reapply the Web penalty formula with the verified browser overrides."""
import json
from collections import Counter
from pathlib import Path
from statistics import mean

root = Path(__file__).resolve().parent
prior = root.parent / 'luna-codex-browser-replay'
rows = json.loads((prior / 'web-scores.json').read_text())
diagnosis = json.loads((root / 'diagnosis.json').read_text())
by_id = {(x['task'], x['id']): x for x in diagnosis}
assert len(by_id) == len(diagnosis) == 22
updated = Counter()
for row in rows:
    for v in row['verdicts']:
        x = by_id.get((row['task'], v['id']))
        if not x:
            continue
        assert v['judge_type'] == 'agent' and v['verdict'] == 'unverifiable'
        assert x['score_relevant'] == (row['status'] == 'partial')
        if x['score_relevant']:
            assert x['verdict'] in {'pass', 'fail'} and x.get('probe')
            v.update(verdict=x['verdict'], reason=x['finding'], source='source_directed_browser_replay', probe=x['probe'])
            updated[x['verdict']] += 1
    if row['completion_gate_confirmed']:
        def score(default_fail):
            defects = [v for v in row['verdicts'] if v['verdict']=='fail' or (default_fail and v['verdict']=='unverifiable')]
            return 0 if any(v['severity']=='fatal' for v in defects) else round(max(0,1-sum(v['penalty'] for v in defects)),4)
        lo, hi = score(True), score(False)
        row.update(score_bounds=[lo,hi], combined_score=lo if lo==hi else None, workbuddy_default_fail_score=lo, status='resolved' if lo==hi else 'partial')
assert sum(updated.values()) == 15
browser = Counter(v['verdict'] for r in rows for v in r['verdicts'] if v['judge_type']=='agent')
assert len({r['task'] for r in rows}) == 70 and sum(browser.values()) == 48
assert all(0 <= r['score_bounds'][0] == r['workbuddy_default_fail_score'] <= r['score_bounds'][1] <= 1 for r in rows)
assert not any(r['status']=='partial' and v['judge_type']=='agent' and v['verdict']=='unverifiable' for r in rows for v in r['verdicts'])
bounds = [mean(r['score_bounds'][i] for r in rows) for i in (0,1)]
summary = dict(tasks=len(rows), resolved_tasks=sum(r['status']=='resolved' for r in rows), workbuddy_default_fail_mean=bounds[0], mean_bounds=bounds, browser_agent_verdicts=dict(browser), followup_verdicts=dict(updated), remaining_score_relevant_browser_checks=0, method='Source-directed Playwright checks of saved submissions, scored offline using the WorkBuddy penalty formula.')
(root / 'web-scores.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2)+'\n')
(root / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
print(json.dumps(summary, indent=2))
