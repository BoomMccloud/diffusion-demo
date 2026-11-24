"""Rerun exactly the ten Qwen Office trials whose original scores were lost."""
import json, os, re, signal, subprocess, time
from pathlib import Path
import yaml

original = Path('results/qwen36-flash-office-serial/queue.jsonl')
root = Path('results/qwen36-flash-office-recovery')
root.mkdir(parents=True, exist_ok=True)
ledger = root / 'queue.jsonl'
base = yaml.safe_load(Path('configs/jobs/clover-office-full-uncapped.yaml').read_text())
original_rows = [json.loads(line) for line in original.read_text().splitlines()]
assert len(original_rows) == 50 and len({x['task'] for x in original_rows}) == 50
recovered = {'channel-period-compare-L4-017'}
targets = []
for row in original_rows:
    score = json.loads((Path(row['result']).parent / 'verifier/score.json').read_text())
    if score.get('test_status') in {'judge_error', 'build_error'} and row['task'] not in recovered:
        targets.append(row['task'])
assert len(targets) == 10, f'Expected 10 missing scores; found {len(targets)}'

def append(row):
    with ledger.open('a') as f:
        f.write(json.dumps(row) + '\n'); f.flush(); os.fsync(f.fileno())

def clean_proxy(job):
    for f in Path('scripts/logs/instances').glob(job + '-*/proxy.yaml'):
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit(): continue
            try:
                argv = (proc / 'cmdline').read_bytes().split(b'\x00')
                if b'workbuddy_bench.proxy' in argv and str(f.resolve()).encode() in argv:
                    os.kill(int(proc.name), signal.SIGTERM)
            except (OSError, ValueError): pass

done = {r['task'] for r in (json.loads(l) for l in ledger.read_text().splitlines()) if r['status'] == 'completed'} if ledger.exists() else set()
for index, task in enumerate(targets, 1):
    if task in done: continue
    for attempt in range(1, 4):
        tag = f'qwen36-flash-office-recovery-{index:02d}-a{attempt:03d}'
        if Path('results', tag).exists(): continue
        job = dict(base, model='qwen36-flash-serial', task_selection={'mode': 'name', 'names': [task]})
        Path(f'configs/jobs/{tag}.yaml').write_text(yaml.safe_dump(job, sort_keys=False))
        print(f'Start recovery {index}/10 {task}, attempt {attempt}', flush=True)
        try: rc = subprocess.call(['bash', 'scripts/run.sh', '--job', tag])
        finally: clean_proxy(tag)
        logs = sorted(Path('scripts/logs/proxy').glob('proxy-' + tag + '-*.log'))
        codes = [c for f in logs for c in re.findall(r'HTTP/1\.1 (\d{3})', f.read_text())]
        paths = list(Path(f'results/{tag}').glob('*/*/result.json'))
        trial = json.loads(paths[0].read_text()) if len(paths) == 1 else {}
        tokens = (trial.get('agent_result') or {}).get('n_output_tokens') or 0
        if '429' in codes and (not tokens or codes[-1] == '429'):
            append(dict(task=task, job=tag, status='retry_429', http_429=codes.count('429')))
            time.sleep(10); continue
        if rc or not trial or (not tokens and '200' not in codes):
            append(dict(task=task, job=tag, status='infrastructure_error', launcher_exit=rc, http=codes[-8:]))
            raise SystemExit(f'Infrastructure failure on {task}')
        score_path = paths[0].parent / 'verifier/score.json'
        score = json.loads(score_path.read_text()) if score_path.exists() else {}
        if score.get('test_status') in (None, 'judge_error', 'build_error') or not score.get('tests_total'):
            append(dict(task=task, job=tag, status='verifier_error', result=str(paths[0])))
            raise SystemExit(f'Verifier failure on {task}; queue stopped')
        append(dict(task=task, job=tag, status='completed', output_tokens=tokens,
                    http_200=codes.count('200'), result=str(paths[0]),
                    score=score.get('reward'), tests_passed=score.get('tests_passed'),
                    tests_total=score.get('tests_total')))
        print(f'Completed recovery {index}/10 {task}', flush=True)
        break
    else:
        raise SystemExit(f'Retry limit reached for {task}')
print('Completed all 10 recovery trials', flush=True)
